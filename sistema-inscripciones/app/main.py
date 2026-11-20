import sqlite3
from contextlib import asynccontextmanager
from enum import Enum
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import db

Cupo = Annotated[int, Field(ge=0)]


class Turno(str, Enum):
    manana = "manana"
    tarde = "tarde"
    noche = "noche"


class AlumnoBase(BaseModel):
    nombre: str = Field(min_length=1)
    apellido: str = Field(min_length=1)
    aprobadas: list[str] = Field(default_factory=list)


class AlumnoCreate(AlumnoBase):
    legajo: str = Field(min_length=1)


class AlumnoUpdate(AlumnoBase):
    pass


class MateriaBase(BaseModel):
    nombre: str = Field(min_length=1)
    correlativas: list[str] = Field(default_factory=list)
    turnos: dict[Turno, Cupo] = Field(default_factory=dict)


class MateriaCreate(MateriaBase):
    codigo: str = Field(min_length=1)


class MateriaUpdate(MateriaBase):
    pass


class InscripcionCreate(BaseModel):
    alumno: str = Field(min_length=1)
    materia: str = Field(min_length=1)
    turno: Turno


class AlumnoOut(BaseModel):
    legajo: str
    nombre: str
    apellido: str
    aprobadas: list[str]


class MateriaOut(BaseModel):
    codigo: str
    nombre: str
    correlativas: list[str]
    turnos: dict[str, int]


class InscripcionOut(BaseModel):
    id: int
    alumno: str
    materia: str
    turno: str


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, detail: str):
        self.status_code = status_code
        self.code = code
        self.detail = detail


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Sistema de Inscripciones", lifespan=lifespan)


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "detail": exc.detail},
    )


def get_db():
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


def _dedupe(codigos: list[str]) -> list[str]:
    return list(dict.fromkeys(codigos))


def _require_materias(conn: sqlite3.Connection, codigos: list[str]) -> list[str]:
    codigos = _dedupe(codigos)
    if not codigos:
        return []
    placeholders = ",".join("?" for _ in codigos)
    filas = conn.execute(
        f"SELECT codigo FROM materias WHERE codigo IN ({placeholders})", codigos
    ).fetchall()
    existentes = {fila["codigo"] for fila in filas}
    faltantes = [codigo for codigo in codigos if codigo not in existentes]
    if faltantes:
        raise HTTPException(
            status_code=422,
            detail=f"Materias inexistentes: {', '.join(faltantes)}",
        )
    return codigos


def _alumno(conn: sqlite3.Connection, legajo: str):
    fila = conn.execute(
        "SELECT legajo, nombre, apellido FROM alumnos WHERE legajo = ?", (legajo,)
    ).fetchone()
    if fila is None:
        return None
    aprobadas = [
        fila_aprobada["materia_codigo"]
        for fila_aprobada in conn.execute(
            "SELECT materia_codigo FROM alumno_aprobadas WHERE alumno_legajo = ? ORDER BY materia_codigo",
            (legajo,),
        )
    ]
    return {**dict(fila), "aprobadas": aprobadas}


def _materia(conn: sqlite3.Connection, codigo: str):
    fila = conn.execute(
        "SELECT codigo, nombre FROM materias WHERE codigo = ?", (codigo,)
    ).fetchone()
    if fila is None:
        return None
    correlativas = [
        fila_correlativa["correlativa_codigo"]
        for fila_correlativa in conn.execute(
            "SELECT correlativa_codigo FROM materia_correlativas WHERE materia_codigo = ? ORDER BY correlativa_codigo",
            (codigo,),
        )
    ]
    turnos = {
        fila_turno["turno"]: fila_turno["cupo"]
        for fila_turno in conn.execute(
            """
            SELECT turno, cupo FROM materia_turnos
            WHERE materia_codigo = ?
            ORDER BY CASE turno WHEN 'manana' THEN 1 WHEN 'tarde' THEN 2 ELSE 3 END
            """,
            (codigo,),
        )
    }
    return {**dict(fila), "correlativas": correlativas, "turnos": turnos}


def _inscripcion(conn: sqlite3.Connection, inscripcion_id: int):
    fila = conn.execute(
        """
        SELECT id, alumno_legajo AS alumno, materia_codigo AS materia, turno
        FROM inscripciones WHERE id = ?
        """,
        (inscripcion_id,),
    ).fetchone()
    return dict(fila) if fila is not None else None


def _guardar_aprobadas(
    conn: sqlite3.Connection, legajo: str, codigos: list[str]
) -> None:
    conn.execute("DELETE FROM alumno_aprobadas WHERE alumno_legajo = ?", (legajo,))
    conn.executemany(
        "INSERT INTO alumno_aprobadas (alumno_legajo, materia_codigo) VALUES (?, ?)",
        [(legajo, codigo) for codigo in codigos],
    )


def _guardar_correlativas(
    conn: sqlite3.Connection, codigo: str, correlativas: list[str]
) -> None:
    conn.execute(
        "DELETE FROM materia_correlativas WHERE materia_codigo = ?", (codigo,)
    )
    conn.executemany(
        "INSERT INTO materia_correlativas (materia_codigo, correlativa_codigo) VALUES (?, ?)",
        [(codigo, correlativa) for correlativa in correlativas],
    )


def _guardar_turnos(conn: sqlite3.Connection, codigo: str, turnos: dict) -> None:
    conn.execute("DELETE FROM materia_turnos WHERE materia_codigo = ?", (codigo,))
    conn.executemany(
        "INSERT INTO materia_turnos (materia_codigo, turno, cupo) VALUES (?, ?, ?)",
        [(codigo, turno.value, cupo) for turno, cupo in turnos.items()],
    )


@app.post("/alumnos", response_model=AlumnoOut, status_code=201)
def crear_alumno(data: AlumnoCreate, conn: sqlite3.Connection = Depends(get_db)):
    with db.tx(conn):
        if _alumno(conn, data.legajo) is not None:
            raise HTTPException(
                status_code=409, detail="Ya existe un alumno con ese legajo"
            )
        aprobadas = _require_materias(conn, data.aprobadas)
        conn.execute(
            "INSERT INTO alumnos (legajo, nombre, apellido) VALUES (?, ?, ?)",
            (data.legajo, data.nombre, data.apellido),
        )
        _guardar_aprobadas(conn, data.legajo, aprobadas)
    return _alumno(conn, data.legajo)


@app.get("/alumnos", response_model=list[AlumnoOut])
def listar_alumnos(conn: sqlite3.Connection = Depends(get_db)):
    legajos = [
        fila["legajo"]
        for fila in conn.execute("SELECT legajo FROM alumnos ORDER BY legajo")
    ]
    return [_alumno(conn, legajo) for legajo in legajos]


@app.get("/alumnos/{legajo}", response_model=AlumnoOut)
def obtener_alumno(legajo: str, conn: sqlite3.Connection = Depends(get_db)):
    alumno = _alumno(conn, legajo)
    if alumno is None:
        raise HTTPException(status_code=404, detail="Alumno inexistente")
    return alumno


# shortcut: los PUT no revalidan inscripciones existentes; las validaciones corren solo al inscribir.
@app.put("/alumnos/{legajo}", response_model=AlumnoOut)
def actualizar_alumno(
    legajo: str, data: AlumnoUpdate, conn: sqlite3.Connection = Depends(get_db)
):
    with db.tx(conn):
        if _alumno(conn, legajo) is None:
            raise HTTPException(status_code=404, detail="Alumno inexistente")
        aprobadas = _require_materias(conn, data.aprobadas)
        conn.execute(
            "UPDATE alumnos SET nombre = ?, apellido = ? WHERE legajo = ?",
            (data.nombre, data.apellido, legajo),
        )
        _guardar_aprobadas(conn, legajo, aprobadas)
    return _alumno(conn, legajo)


@app.delete("/alumnos/{legajo}", status_code=204)
def borrar_alumno(legajo: str, conn: sqlite3.Connection = Depends(get_db)):
    with db.tx(conn):
        if _alumno(conn, legajo) is None:
            raise HTTPException(status_code=404, detail="Alumno inexistente")
        if conn.execute(
            "SELECT 1 FROM inscripciones WHERE alumno_legajo = ? LIMIT 1", (legajo,)
        ).fetchone():
            raise HTTPException(
                status_code=409, detail="El alumno tiene inscripciones"
            )
        conn.execute("DELETE FROM alumnos WHERE legajo = ?", (legajo,))
    return Response(status_code=204)


@app.post("/materias", response_model=MateriaOut, status_code=201)
def crear_materia(data: MateriaCreate, conn: sqlite3.Connection = Depends(get_db)):
    with db.tx(conn):
        if _materia(conn, data.codigo) is not None:
            raise HTTPException(
                status_code=409, detail="Ya existe una materia con ese código"
            )
        correlativas = _require_materias(conn, data.correlativas)
        conn.execute(
            "INSERT INTO materias (codigo, nombre) VALUES (?, ?)",
            (data.codigo, data.nombre),
        )
        _guardar_correlativas(conn, data.codigo, correlativas)
        _guardar_turnos(conn, data.codigo, data.turnos)
    return _materia(conn, data.codigo)


@app.get("/materias", response_model=list[MateriaOut])
def listar_materias(conn: sqlite3.Connection = Depends(get_db)):
    codigos = [
        fila["codigo"]
        for fila in conn.execute("SELECT codigo FROM materias ORDER BY codigo")
    ]
    return [_materia(conn, codigo) for codigo in codigos]


@app.get("/materias/{codigo}", response_model=MateriaOut)
def obtener_materia(codigo: str, conn: sqlite3.Connection = Depends(get_db)):
    materia = _materia(conn, codigo)
    if materia is None:
        raise HTTPException(status_code=404, detail="Materia inexistente")
    return materia


# shortcut: no se validan ciclos ni autocorrelativas.
@app.put("/materias/{codigo}", response_model=MateriaOut)
def actualizar_materia(
    codigo: str, data: MateriaUpdate, conn: sqlite3.Connection = Depends(get_db)
):
    with db.tx(conn):
        if _materia(conn, codigo) is None:
            raise HTTPException(status_code=404, detail="Materia inexistente")
        correlativas = _require_materias(conn, data.correlativas)
        conn.execute(
            "UPDATE materias SET nombre = ? WHERE codigo = ?", (data.nombre, codigo)
        )
        _guardar_correlativas(conn, codigo, correlativas)
        _guardar_turnos(conn, codigo, data.turnos)
    return _materia(conn, codigo)


@app.delete("/materias/{codigo}", status_code=204)
def borrar_materia(codigo: str, conn: sqlite3.Connection = Depends(get_db)):
    with db.tx(conn):
        if _materia(conn, codigo) is None:
            raise HTTPException(status_code=404, detail="Materia inexistente")
        if conn.execute(
            "SELECT 1 FROM inscripciones WHERE materia_codigo = ? LIMIT 1", (codigo,)
        ).fetchone():
            raise HTTPException(
                status_code=409, detail="La materia tiene inscripciones"
            )
        if conn.execute(
            "SELECT 1 FROM alumno_aprobadas WHERE materia_codigo = ? LIMIT 1", (codigo,)
        ).fetchone():
            raise HTTPException(
                status_code=409, detail="La materia figura como aprobada"
            )
        if conn.execute(
            "SELECT 1 FROM materia_correlativas WHERE correlativa_codigo = ? LIMIT 1",
            (codigo,),
        ).fetchone():
            raise HTTPException(
                status_code=409, detail="La materia es correlativa de otra"
            )
        conn.execute("DELETE FROM materias WHERE codigo = ?", (codigo,))
    return Response(status_code=204)


@app.post("/inscripciones", response_model=InscripcionOut, status_code=201)
def crear_inscripcion(
    data: InscripcionCreate, conn: sqlite3.Connection = Depends(get_db)
):
    turno = data.turno.value
    with db.tx(conn):
        if conn.execute(
            "SELECT 1 FROM alumnos WHERE legajo = ?", (data.alumno,)
        ).fetchone() is None:
            raise ApiError(404, "NO_ENCONTRADO", "Alumno inexistente")
        if conn.execute(
            "SELECT 1 FROM materias WHERE codigo = ?", (data.materia,)
        ).fetchone() is None:
            raise ApiError(404, "NO_ENCONTRADO", "Materia inexistente")
        oferta = conn.execute(
            "SELECT cupo FROM materia_turnos WHERE materia_codigo = ? AND turno = ?",
            (data.materia, turno),
        ).fetchone()
        if oferta is None:
            raise ApiError(
                409,
                "TURNO_NO_DISPONIBLE",
                f"La materia {data.materia} no ofrece el turno {turno}",
            )
        if conn.execute(
            "SELECT 1 FROM inscripciones WHERE alumno_legajo = ? AND materia_codigo = ?",
            (data.alumno, data.materia),
        ).fetchone():
            raise ApiError(
                409,
                "INSCRIPCION_DUPLICADA",
                f"El alumno ya está inscripto en {data.materia}",
            )
        if conn.execute(
            "SELECT 1 FROM alumno_aprobadas WHERE alumno_legajo = ? AND materia_codigo = ?",
            (data.alumno, data.materia),
        ).fetchone():
            raise ApiError(
                409,
                "MATERIA_APROBADA",
                f"El alumno ya tiene aprobada la materia {data.materia}",
            )
        faltantes = [
            fila["correlativa_codigo"]
            for fila in conn.execute(
                """
                SELECT mc.correlativa_codigo
                FROM materia_correlativas mc
                WHERE mc.materia_codigo = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM alumno_aprobadas aa
                      WHERE aa.alumno_legajo = ?
                        AND aa.materia_codigo = mc.correlativa_codigo
                  )
                ORDER BY mc.correlativa_codigo
                """,
                (data.materia, data.alumno),
            )
        ]
        if faltantes:
            raise ApiError(
                409,
                "CORRELATIVA_PENDIENTE",
                f"Faltan aprobar: {', '.join(faltantes)}",
            )
        choque = conn.execute(
            """
            SELECT materia_codigo FROM inscripciones
            WHERE alumno_legajo = ? AND turno = ? AND materia_codigo <> ?
            LIMIT 1
            """,
            (data.alumno, turno, data.materia),
        ).fetchone()
        if choque is not None:
            raise ApiError(
                409,
                "CHOQUE_TURNO",
                f"El alumno ya cursa {choque['materia_codigo']} en el turno {turno}",
            )
        usados = conn.execute(
            "SELECT COUNT(*) AS cantidad FROM inscripciones WHERE materia_codigo = ? AND turno = ?",
            (data.materia, turno),
        ).fetchone()["cantidad"]
        if usados >= oferta["cupo"]:
            raise ApiError(
                409,
                "SIN_CUPO",
                f"No hay cupo en {data.materia} turno {turno}",
            )
        cur = conn.execute(
            "INSERT INTO inscripciones (alumno_legajo, materia_codigo, turno) VALUES (?, ?, ?)",
            (data.alumno, data.materia, turno),
        )
        nuevo_id = cur.lastrowid
    return {
        "id": nuevo_id,
        "alumno": data.alumno,
        "materia": data.materia,
        "turno": turno,
    }


@app.get("/inscripciones", response_model=list[InscripcionOut])
def listar_inscripciones(conn: sqlite3.Connection = Depends(get_db)):
    return [
        dict(fila)
        for fila in conn.execute(
            """
            SELECT id, alumno_legajo AS alumno, materia_codigo AS materia, turno
            FROM inscripciones ORDER BY id
            """
        )
    ]


@app.get("/inscripciones/{inscripcion_id}", response_model=InscripcionOut)
def obtener_inscripcion(
    inscripcion_id: int, conn: sqlite3.Connection = Depends(get_db)
):
    inscripcion = _inscripcion(conn, inscripcion_id)
    if inscripcion is None:
        raise HTTPException(status_code=404, detail="Inscripción inexistente")
    return inscripcion


@app.delete("/inscripciones/{inscripcion_id}", status_code=204)
def borrar_inscripcion(
    inscripcion_id: int, conn: sqlite3.Connection = Depends(get_db)
):
    with db.tx(conn):
        if _inscripcion(conn, inscripcion_id) is None:
            raise HTTPException(status_code=404, detail="Inscripción inexistente")
        conn.execute("DELETE FROM inscripciones WHERE id = ?", (inscripcion_id,))
    return Response(status_code=204)


@app.post("/reset", status_code=204)
def reset(conn: sqlite3.Connection = Depends(get_db)):
    # Reset destructivo para volver a la base del seed; no hay autenticación.
    with db.tx(conn):
        conn.execute("DELETE FROM inscripciones")
        conn.execute("DELETE FROM alumno_aprobadas")
        conn.execute("DELETE FROM materia_correlativas")
        conn.execute("DELETE FROM materia_turnos")
        conn.execute("DELETE FROM alumnos")
        conn.execute("DELETE FROM materias")
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'inscripciones'")
    return Response(status_code=204)
