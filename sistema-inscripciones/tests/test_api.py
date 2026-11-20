import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    with TestClient(app) as test_client:
        yield test_client


def crear_alumno(client, legajo="A1", aprobadas=None):
    respuesta = client.post(
        "/alumnos",
        json={
            "legajo": legajo,
            "nombre": "Ana",
            "apellido": "Perez",
            "aprobadas": aprobadas or [],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta


def crear_materia(client, codigo="M1", correlativas=None, turnos=None):
    respuesta = client.post(
        "/materias",
        json={
            "codigo": codigo,
            "nombre": f"Materia {codigo}",
            "correlativas": correlativas or [],
            "turnos": {"manana": 2} if turnos is None else turnos,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta


def inscribir(client, alumno="A1", materia="M1", turno="manana"):
    return client.post(
        "/inscripciones",
        json={"alumno": alumno, "materia": materia, "turno": turno},
    )


def test_crud_alumno(client):
    crear_alumno(client, "A1")
    assert client.get("/alumnos/A1").json()["aprobadas"] == []

    respuesta = client.put(
        "/alumnos/A1",
        json={"nombre": "Ana", "apellido": "Gomez", "aprobadas": []},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["apellido"] == "Gomez"

    assert client.delete("/alumnos/A1").status_code == 204
    assert client.get("/alumnos/A1").status_code == 404


def test_crud_materia(client):
    crear_materia(client, "M1", turnos={"manana": 2, "noche": 0})

    respuesta = client.put(
        "/materias/M1",
        json={"nombre": "Otra", "correlativas": [], "turnos": {"tarde": 1}},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Otra"
    assert respuesta.json()["turnos"] == {"tarde": 1}

    assert client.delete("/materias/M1").status_code == 204
    assert client.get("/materias/M1").status_code == 404


def test_inscripcion_y_baja_liberan_cupo(client):
    crear_alumno(client, "A1")
    crear_materia(client, "M1", turnos={"manana": 1})

    respuesta = inscribir(client)
    assert respuesta.status_code == 201, respuesta.text
    inscripcion = respuesta.json()
    assert inscripcion["alumno"] == "A1"
    assert inscripcion["materia"] == "M1"
    assert inscripcion["turno"] == "manana"
    assert client.get(f"/inscripciones/{inscripcion['id']}").status_code == 200

    assert client.delete(f"/inscripciones/{inscripcion['id']}").status_code == 204

    crear_alumno(client, "A2")
    respuesta = inscribir(client, "A2")
    assert respuesta.status_code == 201, respuesta.text


def test_inscripcion_duplicada(client):
    crear_alumno(client)
    crear_materia(client, turnos={"manana": 2})
    assert inscribir(client).status_code == 201

    respuesta = inscribir(client)
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "INSCRIPCION_DUPLICADA"


def test_sin_cupo(client):
    crear_alumno(client, "A1")
    crear_alumno(client, "A2")
    crear_materia(client, turnos={"manana": 1})
    assert inscribir(client, "A1").status_code == 201

    respuesta = inscribir(client, "A2")
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "SIN_CUPO"


def test_choque_turno(client):
    crear_alumno(client)
    crear_materia(client, "M1", turnos={"manana": 2})
    crear_materia(client, "M2", turnos={"manana": 2})
    assert inscribir(client, materia="M1").status_code == 201

    respuesta = inscribir(client, materia="M2")
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "CHOQUE_TURNO"


def test_correlativa_pendiente(client):
    crear_materia(client, "M1", turnos={"manana": 1})
    crear_materia(client, "M2", correlativas=["M1"], turnos={"manana": 1})
    crear_alumno(client, "A1")

    respuesta = inscribir(client, materia="M2")
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "CORRELATIVA_PENDIENTE"

    respuesta = client.put(
        "/alumnos/A1",
        json={"nombre": "Ana", "apellido": "Perez", "aprobadas": ["M1"]},
    )
    assert respuesta.status_code == 200
    assert inscribir(client, materia="M2").status_code == 201


def test_turno_no_disponible(client):
    crear_alumno(client)
    crear_materia(client, turnos={"manana": 1})

    respuesta = inscribir(client, turno="tarde")
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "TURNO_NO_DISPONIBLE"


def test_inscripcion_no_encontrada(client):
    crear_materia(client)
    respuesta = inscribir(client, alumno="NOEXISTE")
    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "NO_ENCONTRADO"

    crear_alumno(client)
    respuesta = inscribir(client, materia="NOEXISTE")
    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "NO_ENCONTRADO"


def test_no_borrar_en_uso(client):
    crear_alumno(client, "A1")
    crear_materia(client, "M1", turnos={"manana": 1})
    assert inscribir(client, "A1", "M1").status_code == 201

    respuesta = client.delete("/alumnos/A1")
    assert respuesta.status_code == 409
    assert "code" not in respuesta.json()

    respuesta = client.delete("/materias/M1")
    assert respuesta.status_code == 409
    assert "code" not in respuesta.json()


def test_materia_referenciada_no_se_borra(client):
    crear_materia(client, "M1", turnos={})
    crear_materia(client, "M2", correlativas=["M1"], turnos={})
    crear_alumno(client, "A1", aprobadas=["M1"])

    assert client.delete("/materias/M1").status_code == 409


def test_referencias_inexistentes(client):
    respuesta = client.post(
        "/alumnos",
        json={
            "legajo": "A1",
            "nombre": "Ana",
            "apellido": "Perez",
            "aprobadas": ["NOEXISTE"],
        },
    )
    assert respuesta.status_code == 422

    respuesta = client.post(
        "/materias",
        json={
            "codigo": "M1",
            "nombre": "Materia",
            "correlativas": ["NOEXISTE"],
            "turnos": {},
        },
    )
    assert respuesta.status_code == 422


def test_claves_duplicadas(client):
    crear_alumno(client, "A1")
    respuesta = client.post(
        "/alumnos",
        json={"legajo": "A1", "nombre": "Otra", "apellido": "Perez", "aprobadas": []},
    )
    assert respuesta.status_code == 409
    assert "code" not in respuesta.json()

    crear_materia(client, "M1", turnos={})
    respuesta = client.post(
        "/materias",
        json={"codigo": "M1", "nombre": "Otra", "correlativas": [], "turnos": {}},
    )
    assert respuesta.status_code == 409
    assert "code" not in respuesta.json()


def test_cupo_negativo(client):
    respuesta = client.post(
        "/materias",
        json={
            "codigo": "M1",
            "nombre": "Materia",
            "correlativas": [],
            "turnos": {"manana": -1},
        },
    )
    assert respuesta.status_code == 422


def test_no_inscribir_materia_aprobada(client):
    crear_materia(client, "M1", turnos={"manana": 2})
    crear_alumno(client, "A1", aprobadas=["M1"])

    respuesta = inscribir(client, "A1", "M1")

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "MATERIA_APROBADA"
    assert client.get("/inscripciones").json() == []


def test_reset_vacia_todo_y_reinicia_ids(client):
    crear_alumno(client, "A1")
    crear_materia(client, "M1", turnos={"manana": 1})
    assert inscribir(client, "A1", "M1").json()["id"] == 1

    assert client.post("/reset").status_code == 204
    assert client.get("/alumnos").json() == []
    assert client.get("/materias").json() == []
    assert client.get("/inscripciones").json() == []

    crear_alumno(client, "A2")
    crear_materia(client, "M2", turnos={"manana": 1})
    respuesta = inscribir(client, "A2", "M2")
    assert respuesta.status_code == 201
    assert respuesta.json()["id"] == 1
