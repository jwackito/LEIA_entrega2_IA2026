# LEIA — Entrega 2 (IA 2026)

Trabajo práctico de agentes de inscripciones a materias.

## Contenido

- `sistema-inscripciones/`: API FastAPI + SQLite con alumnos, materias, turnos y correlativas.
- `evaluacion/`: corrector automático de agentes contra un dataset de casos.
- `ollama/`: servicio Ollama opcional para correr la evaluación.

El dataset privado de corrección no se incluye en este repositorio.

## Sistema de inscripciones

```bash
cd sistema-inscripciones
docker compose up --build
```

API: http://localhost:8008 — Documentación: http://localhost:8008/docs

Tests:

```bash
cd sistema-inscripciones
pip install -r requirements.txt
python -m pytest
```

## Evaluación

```bash
cd ollama
docker compose up -d --wait
docker compose exec ollama ollama pull qwen3.5:9b

cd ../evaluacion
docker compose build
ENTREGA=/ruta/entregas/Apellido_N docker compose run --rm evaluacion
```

La carpeta de entrega debe contener `agent.py`. Ver [`evaluacion/README.md`](evaluacion/README.md) para el detalle de las opciones.
