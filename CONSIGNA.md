# Entrega 2 — Agente de inscripciones

**Materia:** LEIA — IA 2026
**Modalidad:** individual
**Plazo:** jueves 10 de diciembre de 2026, 23:59 (hora Argentina)
**Entrega:** un Pull Request al repositorio del curso con `entregas/<tu-carpeta>/agent.py`.

## 1. Contexto y objetivo

La cátedra tiene una API de inscripciones a materias con alumnos, materias, turnos, cupos y correlativas. La API ya valida todo: cupo, correlativas, choque de turno, duplicados y materias aprobadas.

El objetivo de esta entrega es construir un agente conversacional que reciba mensajes en lenguaje natural y use herramientas para consultar y modificar ese sistema. El agente tiene que:

- entender qué quiere hacer el usuario;
- consultar los datos reales antes de responder;
- pedir los datos que falten;
- inscribir o dar de baja usando la API;
- explicar los rechazos con el código exacto que devuelve la API.

El agente usa un modelo local servido por Ollama (`qwen3.5:9b`) y no tiene acceso directo a la base: solo puede actuar a través de las herramientas que ustedes implementen.

## 2. Qué reciben

En el repositorio van a encontrar:

- `agente-referencia/agent.py`: agente base. Ya tiene implementada la herramienta `obtener_alumno`, el bucle de conversación y el cliente de Ollama. Tiene TODOs para las herramientas que faltan.
- `agente-referencia/README.md`: explicación detallada de la arquitectura, el bucle, las herramientas, los errores y el formato de los mensajes.
- `agente-referencia/test_agent.py`: tests que describen el comportamiento esperado de las herramientas y del bucle. Son una guía, no una obligación.
- `agente-referencia/agente-explicado.ipynb`: explicación del agente por bloques, usada en clase.
- `evaluacion/publico.json`: 24 casos de prueba con sus fixtures y resultados esperados.
- `evaluacion/corregir.py` y `evaluacion/compose.yaml`: el corrector automático.
- `sistema-inscripciones/`: la API y su seed. No se modifica.
- `ollama/compose.yaml`: el servicio de Ollama para correr el modelo localmente.
- `entregas/`: una carpeta por alumno. Cada uno usa la suya.

No se distribuye el dataset privado de corrección ni una solución resuelta del agente.

## 3. Qué tienen que hacer

1. Leer el `README.md` del agente de referencia y mirar `test_agent.py`.
2. Correr el agente base contra el dataset público para ver el punto de partida.
3. Implementar las herramientas que faltan. El mínimo es:
   - `buscar_materias`
   - `obtener_materia`
   - `listar_inscripciones`
   - `inscribir`
   - `dar_de_baja`

   Además de `obtener_alumno`, que ya viene implementada. Pueden agregar más herramientas si les sirven.
4. Ajustar el system prompt y, si quieren, el bucle. Pueden refactorizar todo, siempre que respeten el contrato de la sección 4.
5. Probar con el dataset público y con casos propios.
6. Entregar el PR con `agent.py`.

La referencia está para arrancar, no para copiar y pegar sin entender. Si refactorizan, mejor: lo importante es que el agente funcione y que puedan explicar cómo.

## 4. Contrato técnico con el corrector

El corrector importa tu `agent.py`, le inyecta la configuración y llama a tres funciones. Si refactorizás, estas reglas no se negocian:

| Requisito | Detalle |
|---|---|
| Importable sin efectos | Nada de conexiones, prints ni `sys.exit` al importar. El REPL va dentro de `if __name__ == "__main__":`. |
| Funciones requeridas | `responder(messages) -> str`, `_system_prompt() -> str`, `ejecutar_herramienta(nombre, argumentos)`. |
| Variables inyectadas | El corrector setea `MODEL`, `OLLAMA_URL`, `API_URL` y `LEGAJO_ACTUAL` después de importar. Leelas en el momento de usarlas; no las copies a constantes al importar. |
| Historial | `responder` recibe la lista completa de mensajes y debe dejarla actualizada con el `assistant` (tool calls) y los `tool` (resultados). La lista se reutiliza entre turnos. |
| API | Todas las llamadas a la API pasan por `ejecutar_herramienta`. El corrector envuelve esa función para trazar; llamala por nombre desde `responder`, no guardes una referencia local. |
| Errores de API | Devolvé `{"error": <cuerpo>}`. Los rechazos de inscripción traen `{"code": ..., "detail": ...}`. |
| Nombre `inscribir` | Es obligatorio: el corrector busca ese nombre en la traza para verificar el código de rechazo. Las demás herramientas pueden mantener los nombres de la referencia. |
| Un solo archivo | Todo el código va en `agent.py`. No hay módulos auxiliares ni `requirements.txt` propios. |
| Entorno | Python 3.12; stdlib + `requests`. Nada de dependencias extra. |
| Servicios | No arranques la API, no resetees/siembre la base y no escribas archivos. El corrector ya lo hace. |
| Red | El agente solo habla con `API_URL` y `OLLAMA_URL`. No llames a servicios externos ni leas datasets para responder. |
| Límite de pasos | Mantené un límite de pasos. La referencia usa `MAX_PASOS = 8` y devuelve un mensaje claro si se agota. |

### Cómo clasifica el corrector

- **Inscripción aceptada:** tiene que haber exactamente 1 inscripción nueva, con `alumno`, `materia` y `turno` esperados.
- **Inscripción rechazada:** no tiene que haber inscripciones nuevas; la traza de `inscribir` tiene que incluir el `code` esperado y la respuesta final tiene que incluir ese código exacto.
- **Datos insuficientes:** no tiene que haber inscripciones nuevas y la respuesta final tiene que nombrar el dato que falta: `legajo`, `materia` o `turno`.

Si el agente crea una inscripción cuando no debía, el caso falla.

## 5. Comportamiento esperado

- El agente usa la API como fuente de verdad. No inventa legajos, códigos, cupos, IDs ni nombres.
- Si falta el legajo, la materia o el turno, pregunta. No inscribe con datos incompletos.
- Si la API rechaza una inscripción, la respuesta final incluye el código exacto: `MATERIA_APROBADA`, `SIN_CUPO`, `CORRELATIVA_PENDIENTE`, `CHOQUE_TURNO`, `INSCRIPCION_DUPLICADA` o `TURNO_NO_DISPONIBLE`.
- No rechaza por su cuenta: llama a la API y basa la respuesta en el resultado.
- Usa `LEGAJO_ACTUAL` cuando está fijado; si no, pide el legajo.
- Para dar de baja, primero lista las inscripciones del alumno y usa el `id` exacto. Si hay varias, pregunta cuál.
- Mantiene el contexto entre turnos: si el usuario dice “inscribime en SI302” y después “al turno tarde”, tiene que entender que se refiere a la misma materia.
- No crea, edita ni borra alumnos o materias. Solo inscribe y da de baja.
- Responde en español, breve y claro.

## 6. Cómo probar tu agente

### 6.1 Levantar Ollama

```bash
cd ollama
docker compose up -d --wait
docker compose exec ollama ollama pull qwen3.5:9b
```

La primera descarga son ~6.5 GB. Si ya tenés Ollama en tu máquina, podés usarlo, pero asegurate de que escuche en el puerto 11434 y tenga el modelo.

### 6.2 Construir el corrector

```bash
cd ../evaluacion
docker compose build
```

### 6.3 Correr el dataset público

```bash
ENTREGA="$PWD/../entregas/<tu-carpeta>" \
  docker compose run --rm evaluacion /agente
```

El corrector levanta su propia API en un puerto temporal: no hace falta levantar `sistema-inscripciones`.

La salida muestra una línea por caso (`OK` o `FAIL`) y al final `Resultado: X/24`. Si un caso falla, imprime el resultado esperado, la respuesta final y las herramientas que llamó el agente.

### 6.4 Correr un solo caso

```bash
ENTREGA="$PWD/../entregas/<tu-carpeta>" \
  docker compose run --rm evaluacion /agente --caso insuficiente_legajo_si302
```

Cambiá el id por cualquier caso de `publico.json`.

### 6.5 Agregar tus propios casos

Podés crear `evaluacion/mis_casos.json` copiando `publico.json` y agregando casos con el mismo formato. Después:

```bash
ENTREGA="$PWD/../entregas/<tu-carpeta>" DATASET=mis_casos \
  docker compose run --rm evaluacion /agente
```

El archivo tiene que estar dentro de `evaluacion/`, porque esa carpeta se monta en `/datos`. Tus casos son solo para probar: no forman parte de la entrega.

### 6.6 Tests provistos

Si querés correr los tests de la referencia, copialos a tu carpeta:

```bash
cp ../agente-referencia/test_agent.py "../entregas/<tu-carpeta>/test_agent.py"
docker run --rm --entrypoint python \
  -v "$PWD/../entregas/<tu-carpeta>":/agente -w /agente \
  evaluacion-evaluacion:latest -m pytest -q
```

No los incluyas en el PR. Son una guía, no un requisito.

### 6.7 Permisos de Docker

Si tu usuario no tiene UID 1000, agregá delante de `docker compose run`:

```bash
EVAL_UID=$(id -u) EVAL_GID=$(id -g)
```

## 7. Cómo entregar: fork y Pull Request paso a paso

Esta sección es para quienes nunca hicieron un PR. Seguila en orden.

### 7.1 Antes de empezar

Necesitás:

- una cuenta de GitHub;
- Git instalado (`git --version`);
- Docker y Docker Compose para probar;
- Ollama con `qwen3.5:9b` para probar.

El repositorio de la cátedra es:

```text
https://github.com/jwackito/LEIA_entrega2_IA2026
```

### 7.2 Hacer el fork

1. Abrí la URL del repositorio en el navegador.
2. Arriba a la derecha, hacé clic en **Fork**.
3. Elegí tu cuenta como owner y dejá el mismo nombre.
4. Hacé clic en **Create fork**.

Ahora tenés una copia propia en:

```text
https://github.com/<tu-usuario>/LEIA_entrega2_IA2026
```

### 7.3 Clonar tu fork

Cloná **tu fork**, no el repositorio de la cátedra:

```bash
git clone https://github.com/<tu-usuario>/LEIA_entrega2_IA2026.git
cd LEIA_entrega2_IA2026
```

Si Git te pide usuario y contraseña al hacer `push`, GitHub ya no acepta contraseñas. Usá GitHub Desktop o un token personal. Al final de esta sección está la alternativa con GitHub Desktop.

En Windows, usá Git Bash o GitHub Desktop; los comandos son los mismos.

### 7.4 Configurar Git (solo la primera vez)

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu-email@ejemplo.com"
```

### 7.5 Buscar tu carpeta

```bash
ls entregas
```

Buscá la carpeta que te asignó la cátedra. No la renombres ni crees otra. Si no sabés cuál es, preguntá en las consultas.

### 7.6 Crear tu `agent.py`

Copiá el agente de referencia a tu carpeta:

```bash
cp agente-referencia/agent.py "entregas/<tu-carpeta>/agent.py"
```

Editá ese archivo con el editor que prefieras. Todo tu código va ahí.

### 7.7 Probar

Seguí la sección 6. Antes de entregar, asegurate de que el dataset público corre sin errores de importación y que el agente responde.

### 7.8 Revisar qué cambió

```bash
git status
```

Tiene que aparecer solamente:

```text
?? entregas/<tu-carpeta>/agent.py
```

Si ves `privado.json`, `__pycache__`, `test_agent.py` o cambios en otras carpetas, no los agregues al commit.

### 7.9 Commit y push

```bash
git add "entregas/<tu-carpeta>/agent.py"
git status --short
git commit -m "Entrega 2 - <tu-carpeta>"
git push origin main
```

Antes del `commit`, `git status --short` tiene que mostrar solo:

```text
A  entregas/<tu-carpeta>/agent.py
```

Si preferís trabajar en una branch:

```bash
git checkout -b entrega2
git add "entregas/<tu-carpeta>/agent.py"
git commit -m "Entrega 2 - <tu-carpeta>"
git push -u origin entrega2
```

Usá la misma branch para actualizar la entrega.

### 7.10 Abrir el Pull Request

1. Volvé a la página del repositorio de la cátedra:
   `https://github.com/jwackito/LEIA_entrega2_IA2026`
2. Después del push, GitHub suele mostrar un botón **Compare & pull request**. Hacé clic.
3. Si no aparece, andá a **Pull requests** → **New pull request** → **compare across forks**.
4. Elegí:
   - **base repository:** `jwackito/LEIA_entrega2_IA2026`
   - **base:** `main`
   - **head repository:** `<tu-usuario>/LEIA_entrega2_IA2026`
   - **compare:** `main` (o `entrega2` si usaste branch)
5. Título: `Entrega 2 - <tu-carpeta>`.
6. En la descripción, incluí la declaración de uso de IA:

```markdown
## Entrega 2 - <tu-carpeta>

### Declaración de uso de IA
- Herramientas usadas: ...
- Para qué: ...
```

Si no usaste asistentes, escribí: “No usé asistentes/LLMs”.

7. Hacé clic en **Create pull request**. No lo mergees.

### 7.11 Verificar el PR

- En **Files changed** tiene que aparecer **solo** `entregas/<tu-carpeta>/agent.py`.
- El PR tiene que estar contra `jwackito/LEIA_entrega2_IA2026:main`, no contra tu fork.
- Si agregaste otros archivos, cerralo y corregí el commit.

### 7.12 Actualizar la entrega

Si querés cambiar algo antes del plazo, editá el archivo, hacé commit y push a la misma branch:

```bash
git add "entregas/<tu-carpeta>/agent.py"
git commit -m "Ajustes entrega 2"
git push
```

El PR se actualiza solo. No hace falta abrir otro.

### 7.13 Alternativa con GitHub Desktop

Si no te sentís cómodo con la terminal:

1. Instalá GitHub Desktop e iniciá sesión.
2. **File → Clone repository → URL** y pegá tu fork.
3. Editá `entregas/<tu-carpeta>/agent.py`.
4. En GitHub Desktop, revisá los cambios y dejá tildado **solo** `agent.py`.
5. Escribí el resumen `Entrega 2 - <tu-carpeta>`, hacé **Commit to main** y **Push origin**.
6. Hacé clic en **Create Pull Request** o abrí el PR desde la web.

### 7.14 Antes de enviar

- [ ] El PR toca solo `entregas/<tu-carpeta>/agent.py`.
- [ ] No incluí `test_agent.py`, `__pycache__`, datasets, README ni otros archivos.
- [ ] El agente importa y corre con el corrector.
- [ ] El dataset público corre sin errores de importación.
- [ ] La declaración de IA está en la descripción del PR.
- [ ] El PR está abierto contra `jwackito/LEIA_entrega2_IA2026:main`.
- [ ] El PR está abierto antes del 10/12/2026 a las 23:59.

## 8. Cómo se evalúa

El corrector está en `evaluacion/corregir.py` y es público: pueden leerlo.

Para cada caso:

1. Importa tu `agent.py`.
2. Levanta una API temporal con una base SQLite vacía.
3. Carga los fixtures del caso.
4. Setea `LEGAJO_ACTUAL` y arma el historial con `_system_prompt()`.
5. Ejecuta los mensajes del caso llamando a `responder`.
6. Revisa la API y la traza de herramientas para clasificar.

Los resultados posibles son los de la sección 4: aceptada, rechazada o datos insuficientes.

El dataset público tiene **24 casos** y es el que usás para autocorregirte. La corrección final usa un dataset privado de **48 casos** que no se distribuye. El público es una muestra; pasar los 24 no garantiza pasar los 48.

Después del plazo se publica el `pass/total` de cada entrega sobre el dataset privado. Ese número es **orientativo**: no define la aprobación. La decisión final surge de la revisión manual del `agent.py`.

## 9. Checklist de revisión (guía)

Esta lista es una guía de lo que se va a mirar. No es una rúbrica automática ni hace falta cumplir todo al pie de la letra; la aprobación es una decisión manual.

### Bucle y comportamiento (foco principal)

- `responder` envía el historial completo a Ollama en cada paso.
- Agrega el mensaje `assistant` con `tool_calls` antes de los mensajes `tool`.
- Ejecuta todas las `tool_calls` de una respuesta, no solo la primera.
- Parsea `arguments` como diccionario o string JSON.
- Maneja tool calls inválidas o sin función sin romper.
- Agrega un mensaje `tool` por cada resultado, con el nombre correcto.
- Respeta un límite de pasos y devuelve un mensaje claro si se agota.
- Maneja errores de Ollama: conexión, HTTP, JSON inválido, respuesta sin mensaje.
- Devuelve siempre un string; no propaga excepciones al corrector.
- Mantiene el estado entre turnos y no reenvía mensajes duplicados.
- No entra en bucles infinitos ni repite herramientas sin control.

### Prompt y política

- Define rol, idioma y brevedad.
- Prohíbe inventar códigos, legajos, cupos, IDs y nombres.
- Pide legajo, materia o turno cuando faltan; no inscribe sin los tres.
- Incluye el código exacto del error en la respuesta final.
- No rechaza por su cuenta: se basa en el resultado de la API.
- Usa `LEGAJO_ACTUAL` cuando está fijado; pide legajo cuando no.
- Para dar de baja, lista primero y usa el id exacto; si hay varias, pregunta.

### Herramientas

- Implementa las 5 mínimas, además de `obtener_alumno`.
- Declara cada una en `TOOLS` con nombre, descripción y esquema de parámetros.
- Usa los endpoints y métodos correctos.
- Normaliza mayúsculas y acentos en la búsqueda.
- Filtra inscripciones por alumno.
- Maneja `204` como `{"ok": True}` y los errores como `{"error": ...}`.
- Codifica los parámetros de path con `quote`.
- Valida argumentos faltantes o inválidos sin romper.
- No crea, edita ni borra alumnos o materias.

### Contrato y ejecución

- `agent.py` importa sin errores ni efectos secundarios.
- Expone `responder`, `_system_prompt` y `ejecutar_herramienta`.
- Lee `MODEL`, `OLLAMA_URL`, `API_URL` y `LEGAJO_ACTUAL` en tiempo de ejecución.
- Llama a `ejecutar_herramienta` por nombre, sin alias local.
- `inscribir` devuelve el error de la API con `code` y `detail`.
- Corre con Python 3.12 y solo stdlib + `requests`.
- No inicia servidores, no resetea la base y no escribe archivos.

### Robustez y calidad (deseable)

- Maneja API caída, timeout, JSON inválido y respuestas inesperadas.
- No duplica inscripciones en turnos siguientes.
- No hardcodea casos, legajos, respuestas ni IDs.
- Código legible, nombres claros y sin código muerto.
- Si refactoriza, mantiene el contrato y la claridad.
- Los tests provistos pasan (señal, no obligatorio).
- Agrega casos propios para probar lo que le interesa (señal, no obligatorio).

## 10. Uso de asistentes y LLMs

Está permitido usar asistentes, copilotos o LLMs. Si los usás, declaralo en la descripción del PR: qué herramientas y para qué (diseño, código, debugging, redacción). No hace falta pegar prompts.

Asegurate de poder explicar el código que entregás. La revisión es manual y puede incluir preguntas sobre las decisiones que tomaste.

## 11. Consultas

Las dudas se ven en las consultas de la materia. Si es un problema de instalación o de Docker, traé el comando exacto, el error completo y lo que esperabas que pasara.

## 12. Recursos

- `agente-referencia/README.md`: arquitectura del agente, bucle, herramientas y errores.
- `evaluacion/README.md`: cómo correr el corrector y las opciones.
- `sistema-inscripciones/README.md`: API, seed y endpoints.
- `ollama/README.md`: cómo levantar el modelo.
- Documentación de GitHub:
  - Fork: https://docs.github.com/en/get-started/quickstart/fork-a-repo
  - PR desde un fork: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork
- Documentación interactiva de la API: `http://localhost:8008/docs` (si levantás `sistema-inscripciones`).
