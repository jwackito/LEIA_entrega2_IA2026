# Evaluación de agentes de inscripciones

Corre el agente de un alumno o un lote completo de entregas dentro de un contenedor. No hace falta instalar Python ni dependencias locales: solo Docker.

## Requisitos

- Docker y Docker Compose.
- Ollama con el modelo descargado.
  - Podés usar el Docker separado de [`../ollama`](../ollama/README.md).
  - O tu Ollama existente en `http://host.docker.internal:11434`.

Con el Ollama separado (desde la raíz del repo):

```bash
cd ollama
docker compose up -d --wait
docker compose exec ollama ollama pull qwen3.5:9b
```

El `9B` es el recomendado para tool calling. El `0.8b` es más liviano pero menos confiable.

## Construir la imagen

Desde la raíz del repo:

```bash
cd evaluacion
docker compose build
```

## Corregir una entrega

La carpeta debe contener `agent.py`:

```text
entregas/
  Apellido1_N/
    agente.py
```

```bash
ENTREGA=/ruta/entregas/Apellido1_N \
  docker compose run --rm evaluacion
```

Usa `publico.json` por defecto. El resultado se muestra por consola.

## Corregir un lote

```bash
ENTREGA=/ruta/entregas \
  DATASET=privado \
  docker compose run --rm evaluacion
```

El corrector detecta automáticamente las subcarpetas con `agent.py`.

Genera:

```text
entregas/
  resumen.csv
  Apellido1_N/
    agente.py
    resultado.txt
  Apellido2_N/
    agente.py
    resultado.txt
```

### `resultado.txt`

```text
modelo: qwen3.5:9b
aprobados: 20/24
priv_aceptada_directa_si302_manana_1025,OK,""
priv_correlativa_1026,FAIL,"la respuesta final no incluye el código CORRELATIVA_PENDIENTE"
priv_insuficiente_legajo_si302,OK,""
```

- Una línea por caso.
- `codigo,OK,""` si pasa.
- `codigo,FAIL,"mensaje"` si falla.
- Arriba, modelo y aprobados/total.
- Si falta `agent.py` o falla el import, se escribe una línea `ERROR,"..."` y `aprobados: 0/N`.

### `resumen.csv`

```csv
grupo,aprobados,total
Apellido1_N,20,24
Apellido2_N,23,24
```

## Opciones

- `--verbose`: muestra también los casos OK en la consola del lote.
- `--caso ID`: corre un solo caso.
- `MODEL`: cambia el modelo.
- `DATASET`: `publico` o `privado`.
- `OLLAMA_URL`: cambia la URL de Ollama.

Ejemplos:

```bash
ENTREGA=/ruta/entregas DATASET=privado \
  docker compose run --rm evaluacion /agente --verbose

ENTREGA=/ruta/entregas DATASET=privado \
  docker compose run --rm evaluacion /agente \
  --caso priv_aceptada_directa_si302_manana_1025

ENTREGA=/ruta/entregas \
  MODEL=qwen3.5:9b \
  OLLAMA_URL=http://host.docker.internal:11434 \
  docker compose run --rm evaluacion
```

## Permisos de escritura

El contenedor corre con el UID/GID 1000 por defecto para poder escribir `resultado.txt` y `resumen.csv`. Si tu usuario tiene otro UID/GID:

```bash
EVAL_UID=$(id -u) EVAL_GID=$(id -g) \
  ENTREGA=/ruta/entregas DATASET=privado \
  docker compose run --rm evaluacion
```

La carpeta `entregas` se monta en lectura/escritura. El código del alumno también puede escribir en ella; el contenedor no es un sandbox completo.

## Datasets

- `publico.json`: para que los alumnos se autocorrijan.
- `privado.json`: para la corrección docente. No distribuir.

El `resultado.txt` incluye IDs de casos del dataset privado. Si vas a devolver la carpeta al alumno, usá el dataset público o quitá ese archivo.

## Ollama

El módulo usa Ollama por `host.docker.internal:11434`. El Docker separado de `../ollama` publica ese puerto. Si ya tenés Ollama, no hace falta levantarlo.

Si usás otro puerto:

```bash
OLLAMA_PORT=11435 docker compose up -d --wait   # en ollama/
OLLAMA_URL=http://host.docker.internal:11435 \
  ENTREGA=/ruta/entregas \
  docker compose run --rm evaluacion
```

## Rebuild

Si cambia el código de `sistema-inscripciones` o `evaluacion/corregir.py`:

```bash
docker compose build
```

La imagen incluye la app de inscripciones y el corrector; los datasets y las entregas se montan desde el host.
