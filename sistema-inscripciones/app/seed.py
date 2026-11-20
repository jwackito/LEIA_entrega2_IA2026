import argparse
import random
import sys

import requests

RANDOM_SEED = 2021
ESPECIALES = {"0I503", "OPT"}

MATERIAS = [
    # Primer año
    {
        "codigo": "CNE",
        "nombre": "Expresión de Problemas y Algoritmos",
        "correlativas": [],
    },
    {
        "codigo": "CNC",
        "nombre": "Conceptos de Organización de Computadoras",
        "correlativas": [],
    },
    {"codigo": "CNM", "nombre": "Matemática 0", "correlativas": []},
    {
        "codigo": "SI106",
        "nombre": "Conceptos de Algoritmos, Datos y Programas",
        "correlativas": ["CNE"],
    },
    {
        "codigo": "SI104",
        "nombre": "Organización de Computadoras",
        "correlativas": ["CNC"],
    },
    {"codigo": "SI101", "nombre": "Matemática 1", "correlativas": ["CNM"]},
    {"codigo": "SI107", "nombre": "Taller de Programación", "correlativas": ["SI106"]},
    {
        "codigo": "SI105",
        "nombre": "Arquitectura de Computadoras",
        "correlativas": ["SI104"],
    },
    {"codigo": "SI102", "nombre": "Matemática 2", "correlativas": ["SI101"]},
    # Segundo año
    {
        "codigo": "SI209",
        "nombre": "Fundamentos de Organización de Datos",
        "correlativas": ["SI107"],
    },
    {
        "codigo": "SI203",
        "nombre": "Algoritmos y Estructuras de Datos",
        "correlativas": ["SI102", "SI107"],
    },
    {"codigo": "SI207", "nombre": "Seminario de Lenguajes", "correlativas": ["SI107"]},
    {
        "codigo": "SI210",
        "nombre": "Diseño de Bases de Datos",
        "correlativas": ["SI209"],
    },
    {
        "codigo": "SI202",
        "nombre": "Ingeniería de Software 1",
        "correlativas": ["SI107"],
    },
    {
        "codigo": "SI206",
        "nombre": "Orientación a Objetos 1",
        "correlativas": ["SI107"],
    },
    {
        "codigo": "SI204",
        "nombre": "Introducción a los Sistemas Operativos",
        "correlativas": ["SI107", "SI105"],
    },
    {
        "codigo": "SI208",
        "nombre": "Taller de lecto-comprensión y Traducción en Inglés",
        "correlativas": [],
    },
    # Tercer año
    {"codigo": "SI308", "nombre": "Matemática 3", "correlativas": ["SI102"]},
    {
        "codigo": "SI302",
        "nombre": "Ingeniería de Software 2",
        "correlativas": ["SI202", "SI208"],
    },
    {
        "codigo": "SI306",
        "nombre": "Conceptos y Paradigmas de Lenguajes de Programación",
        "correlativas": ["SI203", "SI207", "SI208"],
    },
    {
        "codigo": "SI307",
        "nombre": "Orientación a Objetos 2",
        "correlativas": ["SI206", "SI208"],
    },
    {
        "codigo": "SI304",
        "nombre": "Redes y Comunicaciones",
        "correlativas": ["SI102", "SI204", "SI208"],
    },
    {
        "codigo": "SI301",
        "nombre": "Programación Concurrente",
        "correlativas": ["SI204", "SI207", "SI208"],
    },
    {
        "codigo": "SI305",
        "nombre": "Proyecto de Software",
        "correlativas": ["SI210", "SI202", "SI203", "SI206", "SI207", "SI208"],
    },
    {
        "codigo": "0I309",
        "nombre": "Computabilidad y Complejidad",
        "correlativas": ["SI203", "SI308", "SI208"],
    },
    # Cuarto año
    {
        "codigo": "0I401",
        "nombre": "Teoría de la Computación y Verificación de Programas",
        "correlativas": ["SI308", "SI306"],
    },
    {"codigo": "SI403", "nombre": "Sistemas Operativos", "correlativas": ["SI304"]},
    {"codigo": "0I404", "nombre": "Sistemas Paralelos", "correlativas": ["SI301"]},
    {"codigo": "OPT", "nombre": "Optativa 1 LI", "correlativas": []},
    {
        "codigo": "0I406",
        "nombre": "Lógica e Inteligencia Artificial",
        "correlativas": ["SI102", "SI306"],
    },
    {"codigo": "SI409", "nombre": "Matemática 4", "correlativas": ["SI308"]},
    {
        "codigo": "0I402",
        "nombre": "Laboratorio de Software",
        "correlativas": ["SI305"],
    },
    {
        "codigo": "0I405",
        "nombre": "Programación Distribuida y Tiempo Real",
        "correlativas": ["SI306", "SI304"],
    },
    # Quinto año
    {
        "codigo": "0I502",
        "nombre": "Diseño de Experiencia de Usuario",
        "correlativas": ["SI302", "0I402"],
    },
    {
        "codigo": "SI504",
        "nombre": "Aspectos Sociales y Profesionales de Informática",
        "correlativas": ["SI305"],
    },
    {
        "codigo": "SI505",
        "nombre": "Aspectos Éticos, Sociales y Profesionales Avanzados de Informática",
        "correlativas": ["SI305"],
    },
    # Regla especial (todos los finales de 1º y 2º año + 2 más), no expresable como correlativas simples.
    {
        "codigo": "0I503",
        "nombre": "Tesina de Licenciatura en Informática",
        "correlativas": [],
    },
]

NOMBRES = [
    "Ana",
    "Bruno",
    "Carla",
    "Diego",
    "Elena",
    "Facundo",
    "Lucía",
    "Martín",
    "Nicolás",
    "Sofía",
]
APELLIDOS = ["Pérez", "Gómez", "Fernández", "López", "Martínez"]


def orden_topologico(materias=None):
    materias = MATERIAS if materias is None else materias
    pendientes = list(materias)
    orden = []
    listos = set()
    while pendientes:
        disponibles = [
            materia
            for materia in pendientes
            if all(correlativa in listos for correlativa in materia["correlativas"])
        ]
        if not disponibles:
            raise ValueError("Hay correlativas inexistentes o un ciclo en MATERIAS")
        for materia in disponibles:
            orden.append(materia)
            pendientes.remove(materia)
            listos.add(materia["codigo"])
    return orden


def cupos_para(indice):
    return {
        "manana": 15 + (indice * 7) % 26,
        "tarde": 15 + (indice * 11) % 26,
        "noche": 15 + (indice * 13) % 26,
    }


def generar_alumnos(materias=None):
    materias = MATERIAS if materias is None else materias
    elegibles = [
        materia
        for materia in orden_topologico(materias)
        if materia["codigo"] not in ESPECIALES
    ]
    rng = random.Random(RANDOM_SEED)
    alumnos = []
    for i in range(50):
        probabilidad = rng.uniform(0.35, 0.85)
        aprobadas = set()
        for materia in elegibles:
            if all(
                correlativa in aprobadas
                for correlativa in materia["correlativas"]
            ) and rng.random() < probabilidad:
                aprobadas.add(materia["codigo"])
        alumnos.append(
            {
                "legajo": str(1001 + i),
                "nombre": NOMBRES[i % len(NOMBRES)],
                "apellido": APELLIDOS[(i // len(NOMBRES)) % len(APELLIDOS)],
                "aprobadas": sorted(aprobadas),
            }
        )
    return alumnos


def _fallar(response, contexto):
    try:
        detalle = response.json()
    except ValueError:
        detalle = response.text
    print(f"Error {response.status_code} en {contexto}: {detalle}")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Carga el dataset base del sistema de inscripciones."
    )
    parser.add_argument(
        "--base-url", default="http://localhost:8008", help="URL de la API"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Borra todos los datos antes de sembrar",
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    try:
        orden = orden_topologico()
        alumnos = generar_alumnos()
    except ValueError as exc:
        print(f"Error en el dataset: {exc}")
        sys.exit(1)

    indices = {materia["codigo"]: i for i, materia in enumerate(orden)}

    with requests.Session() as session:
        try:
            if args.reset:
                response = session.post(f"{base_url}/reset", timeout=10)
                if response.status_code != 204:
                    _fallar(response, "POST /reset")
                print("Base reiniciada.")

            creadas = existentes = 0
            for materia in orden:
                response = session.post(
                    f"{base_url}/materias",
                    json={
                        "codigo": materia["codigo"],
                        "nombre": materia["nombre"],
                        "correlativas": materia["correlativas"],
                        "turnos": cupos_para(indices[materia["codigo"]]),
                    },
                    timeout=10,
                )
                if response.status_code == 201:
                    creadas += 1
                elif response.status_code == 409:
                    existentes += 1
                else:
                    _fallar(response, f"POST /materias {materia['codigo']}")
            print(f"Materias: {creadas} creadas, {existentes} existentes.")

            creados = existentes = 0
            for alumno in alumnos:
                response = session.post(
                    f"{base_url}/alumnos", json=alumno, timeout=10
                )
                if response.status_code == 201:
                    creados += 1
                elif response.status_code == 409:
                    existentes += 1
                else:
                    _fallar(response, f"POST /alumnos {alumno['legajo']}")
            print(f"Alumnos: {creados} creados, {existentes} existentes.")
        except requests.RequestException as exc:
            print(f"No se pudo conectar a {base_url}: {exc}")
            sys.exit(1)


if __name__ == "__main__":
    main()
