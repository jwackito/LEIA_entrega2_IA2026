# Ollama para la evaluación

Servicio Ollama separado para el módulo de evaluación. Los modelos quedan guardados en el volumen `ollama_data`.

## Requisitos

- Docker y Docker Compose.
- Opcional: GPU NVIDIA con NVIDIA Container Toolkit. Sin eso, Ollama corre en CPU.

## Levantar

```bash
cd ollama
docker compose up -d --wait
```

## Descargar modelos

```bash
docker compose exec ollama ollama pull qwen3.5:0.8b
docker compose exec ollama ollama pull qwen3.5:9b
```

- `qwen3.5:9b`: recomendado para tool calling.
- `qwen3.5:0.8b`: más liviano y rápido, pero menos confiable para razonamiento y herramientas.

Verificar:

```bash
docker compose exec ollama ollama list
curl -s http://localhost:11434/api/tags
```

## Puerto

Por defecto publica `11434`, que es el puerto que usa el módulo de evaluación:

```
http://host.docker.internal:11434
```

Si ya tenés otro Ollama ocupando ese puerto, levantalo en otro:

```bash
OLLAMA_PORT=11435 docker compose up -d --wait
```

Y en la evaluación pasá:

```bash
OLLAMA_URL=http://host.docker.internal:11435
```

## Persistencia

Los modelos quedan en el volumen `ollama_data`.

- `docker compose down` no borra los modelos.
- `docker compose down -v` sí borra el volumen y obliga a descargarlos de nuevo.

## Si ya tenés Ollama

No hace falta levantar este servicio. Podés usar tu Ollama existente desde la evaluación con:

```bash
OLLAMA_URL=http://host.docker.internal:11434
```

La primera descarga del modelo de 9B puede tardar varios minutos y ocupar varios GB.
