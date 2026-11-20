import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("DATABASE_PATH", "inscripciones.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS alumnos (
    legajo TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    apellido TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS materias (
    codigo TEXT PRIMARY KEY,
    nombre TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alumno_aprobadas (
    alumno_legajo TEXT NOT NULL REFERENCES alumnos(legajo) ON DELETE CASCADE,
    materia_codigo TEXT NOT NULL REFERENCES materias(codigo) ON DELETE RESTRICT,
    PRIMARY KEY (alumno_legajo, materia_codigo)
);

CREATE TABLE IF NOT EXISTS materia_correlativas (
    materia_codigo TEXT NOT NULL REFERENCES materias(codigo) ON DELETE CASCADE,
    correlativa_codigo TEXT NOT NULL REFERENCES materias(codigo) ON DELETE RESTRICT,
    PRIMARY KEY (materia_codigo, correlativa_codigo)
);

CREATE TABLE IF NOT EXISTS materia_turnos (
    materia_codigo TEXT NOT NULL REFERENCES materias(codigo) ON DELETE CASCADE,
    turno TEXT NOT NULL CHECK (turno IN ('manana', 'tarde', 'noche')),
    cupo INTEGER NOT NULL CHECK (cupo >= 0),
    PRIMARY KEY (materia_codigo, turno)
);

CREATE TABLE IF NOT EXISTS inscripciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alumno_legajo TEXT NOT NULL REFERENCES alumnos(legajo) ON DELETE RESTRICT,
    materia_codigo TEXT NOT NULL REFERENCES materias(codigo) ON DELETE RESTRICT,
    turno TEXT NOT NULL CHECK (turno IN ('manana', 'tarde', 'noche')),
    UNIQUE (alumno_legajo, materia_codigo)
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
    finally:
        conn.close()


@contextmanager
def tx(conn: sqlite3.Connection):
    # BEGIN IMMEDIATE serializa las escrituras y evita sobreventa de cupo entre requests concurrentes.
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
