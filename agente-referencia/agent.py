import json
import os
import sys
import unicodedata
from urllib.parse import quote

import requests

# Configuración: editar acá.
API_URL = "http://localhost:8008"
OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen3.5:9b"
LEGAJO_ACTUAL = None
MAX_PASOS = 8

SYSTEM_PROMPT = """Sos un asistente de inscripciones de la Facultad de Informática de la UNLP.
Respondé en español, breve y claro.
Usá siempre las herramientas para consultar datos reales. No inventes códigos, legajos, cupos, IDs ni nombres.
Para inscribir, verificá que el alumno y la materia existan y elegí un turno ofrecido: manana, tarde o noche.
La API valida cupo, correlativas, choque de turno, duplicados y materias aprobadas.
Si rechaza una inscripción, incluí en la respuesta final el código exacto del error
(por ejemplo MATERIA_APROBADA, SIN_CUPO, CORRELATIVA_PENDIENTE, CHOQUE_TURNO,
INSCRIPCION_DUPLICADA o TURNO_NO_DISPONIBLE) y el detalle. No reemplaces el código
por una frase equivalente.
Cuando tengas legajo, materia y turno y el usuario pida inscribirse, llamá a inscribir
y basá la respuesta en el resultado de la API. No rechaces por tu cuenta.
Para dar de baja, listá primero las inscripciones del alumno y usá el id exacto. Si hay varias, preguntá cuál.
No crees, edites ni borres alumnos o materias. No resetees la base.
Si falta el legajo, la materia o el turno, preguntá.
{legajo}"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "obtener_alumno",
            "description": "Devuelve un alumno con sus materias aprobadas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "legajo": {
                        "type": "string",
                        "description": "Legajo del alumno, por ejemplo 1001.",
                    }
                },
                "required": ["legajo"],
            },
        },
    },
    # TODO: agregar buscar_materias, obtener_materia, listar_inscripciones,
    # inscribir y dar_de_baja.
]


def _normalizar(texto):
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", str(texto).lower())
        if not unicodedata.combining(caracter)
    )


def _debug_habilitado():
    return os.environ.get("DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _debug(*partes):
    if _debug_habilitado():
        print("[debug]", *partes, file=sys.stderr, flush=True)


def _debug_api(method, path, payload, resultado):
    partes = [method, path]
    if payload is not None:
        partes.append(json.dumps(payload, ensure_ascii=False))
    partes.append(f"-> {resultado}")
    _debug("API", *partes)


def _api(method, path, payload=None):
    try:
        respuesta = requests.request(
            method, f"{API_URL}{path}", json=payload, timeout=10
        )
    except requests.RequestException as exc:
        _debug_api(method, path, payload, f"sin conexión: {exc}")
        return {"error": f"No se pudo conectar a la API: {exc}"}

    _debug_api(method, path, payload, respuesta.status_code)
    if respuesta.status_code == 204:
        return {"ok": True}
    try:
        cuerpo = respuesta.json()
    except ValueError:
        cuerpo = respuesta.text
    if respuesta.status_code >= 400:
        return {"error": cuerpo}
    return cuerpo


def ejecutar_herramienta(nombre, argumentos):
    if not isinstance(argumentos, dict):
        return {"error": "Argumentos inválidos"}

    try:
        if nombre == "obtener_alumno":
            legajo = argumentos.get("legajo")
            if not legajo:
                return {"error": "Falta el legajo"}
            return _api("GET", f"/alumnos/{quote(str(legajo), safe='')}")

        # TODO: implementar buscar_materias, obtener_materia,
        # listar_inscripciones, inscribir y dar_de_baja.
    except (KeyError, TypeError, ValueError) as exc:
        return {"error": f"Argumentos inválidos: {exc}"}

    return {"error": f"Herramienta desconocida: {nombre}"}


def _ollama_chat(messages):
    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": TOOLS,
        "stream": False,
        "think": False,
        "options": {"temperature": 0},
    }
    try:
        respuesta = requests.post(
            f"{OLLAMA_URL}/api/chat", json=payload, timeout=120
        )
    except requests.RequestException as exc:
        return None, f"No se pudo conectar a Ollama: {exc}"

    if _debug_habilitado():
        print("[debug]", respuesta.text, file=sys.stderr, flush=True)

    if respuesta.status_code != 200:
        return None, f"Ollama respondió {respuesta.status_code}: {respuesta.text}"
    try:
        datos = respuesta.json()
    except ValueError:
        return None, "Ollama devolvió una respuesta que no es JSON"
    if "error" in datos:
        return None, f"Ollama: {datos['error']}"
    mensaje = datos.get("message")
    if not isinstance(mensaje, dict):
        return None, "Ollama devolvió una respuesta sin mensaje"
    return mensaje, None


def responder(messages):
    codigos_error = []
    for _ in range(MAX_PASOS):
        mensaje, error = _ollama_chat(messages)
        if error:
            return error

        tool_calls = mensaje.get("tool_calls") or []
        mensaje_asistente = {
            "role": "assistant",
            "content": mensaje.get("content") or "",
        }
        if tool_calls:
            mensaje_asistente["tool_calls"] = tool_calls
        messages.append(mensaje_asistente)

        if not tool_calls:
            respuesta = mensaje_asistente["content"].strip() or "(sin respuesta)"
            faltantes = list(
                dict.fromkeys(
                    codigo
                    for codigo in codigos_error
                    if codigo.lower() not in _normalizar(respuesta)
                )
            )
            if faltantes:
                respuesta += "\n\nCódigo de error: " + ", ".join(faltantes)
            return respuesta

        for tool in tool_calls:
            nombre = "desconocida"
            argumentos = {}
            try:
                nombre = tool["function"]["name"]
                argumentos = tool["function"].get("arguments") or {}
                if isinstance(argumentos, str):
                    argumentos = json.loads(argumentos)
            except (KeyError, TypeError, AttributeError, json.JSONDecodeError):
                _debug("tool_call", json.dumps(tool, ensure_ascii=False))
                resultado = {"error": "Tool call inválido"}
            else:
                _debug("tool_call", nombre, json.dumps(argumentos, ensure_ascii=False))
                resultado = ejecutar_herramienta(nombre, argumentos)

            if isinstance(resultado, dict):
                error_tool = resultado.get("error")
                if isinstance(error_tool, dict) and error_tool.get("code"):
                    codigos_error.append(error_tool["code"])

            _debug("tool_result", nombre, json.dumps(resultado, ensure_ascii=False))
            messages.append(
                {
                    "role": "tool",
                    "content": json.dumps(resultado, ensure_ascii=False),
                    "tool_name": nombre,
                }
            )

    return "El agente superó el máximo de pasos sin dar una respuesta final."


def _system_prompt():
    if LEGAJO_ACTUAL:
        nota = (
            f"El alumno actual es {LEGAJO_ACTUAL}; "
            "usalo por defecto cuando no se indique otro."
        )
    else:
        nota = "No hay un alumno fijado; pedí el legajo cuando haga falta."
    return SYSTEM_PROMPT.format(legajo=nota)


def _verificar_servicios():
    try:
        respuesta = requests.get(f"{API_URL}/openapi.json", timeout=5)
    except requests.RequestException as exc:
        print(f"No se pudo conectar a la API en {API_URL}: {exc}", file=sys.stderr)
        return False
    if respuesta.status_code != 200:
        print(
            f"La API no responde en {API_URL} (HTTP {respuesta.status_code}).",
            file=sys.stderr,
        )
        return False

    try:
        respuesta = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
    except requests.RequestException as exc:
        print(f"No se pudo conectar a Ollama en {OLLAMA_URL}: {exc}", file=sys.stderr)
        return False
    if respuesta.status_code != 200:
        print(
            f"Ollama no responde en {OLLAMA_URL} (HTTP {respuesta.status_code}).",
            file=sys.stderr,
        )
        return False

    try:
        modelos = {modelo.get("name") for modelo in respuesta.json().get("models", [])}
    except (ValueError, AttributeError):
        return True
    if MODEL not in modelos and f"{MODEL}:latest" not in modelos:
        print(
            f"Aviso: no veo {MODEL} en Ollama. Si falla, corré: ollama pull {MODEL}",
            file=sys.stderr,
        )
    return True


def main():
    if not _verificar_servicios():
        return 1

    messages = [{"role": "system", "content": _system_prompt()}]

    while True:
        if sys.stdin.isatty():
            try:
                linea = input("Vos: ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
        else:
            linea = sys.stdin.readline()
            if not linea:
                break

        linea = linea.strip()
        if not linea:
            continue
        if linea.lower() in {"/salir", "salir", "exit", "quit"}:
            break

        messages.append({"role": "user", "content": linea})
        print(responder(messages), flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
