# Sistema de Inscripciones

API de inscripciones a materias para el trabajo práctico. Sin UI ni autenticación.

## Ejecutar

```bash
docker compose up --build
```

- API: http://localhost:8008
- Documentación: http://localhost:8008/docs

Los datos quedan en el volumen `sqlite_data`. Para borrarlos:

```bash
docker compose down -v
```

## Tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
```

## Seed

Con la API levantada:

```bash
docker compose exec api python -m app.seed --reset
```

`--reset` llama a `POST /reset`, borra todos los datos y vuelve a cargar 37 materias y 50 alumnos. Sin `--reset`, el script solo crea los registros que faltan. El dataset es reproducible (seed 2021).

También se puede ejecutar desde el host:

```bash
python -m app.seed --reset --base-url http://localhost:8008
```

## Datos

La base arranca vacía. El grafo de correlativas de Licenciatura en Informática (Plan 2021) está en [correlativas-li-unlp.md](correlativas-li-unlp.md).

## Limitaciones

- Sin autenticación.
- `POST /reset` y el seed con `--reset` borran toda la base.
- Los `PUT` no revalidan inscripciones existentes; las validaciones corren solo al inscribir.
- No se validan ciclos ni autocorrelativas.
