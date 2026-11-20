#!/usr/bin/env python3
import argparse
import csv
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unicodedata
import uuid
from contextlib import contextmanager
from pathlib import Path

import requests

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "sistema-inscripciones"
DEFAULT_DATASET = Path(
    os.environ.get(
        "DATASET_FILE",
        str(Path(__file__).resolve().parent / "privado.json"),
    )
)
DEFAULT_MODEL = os.environ.get("MODEL", "qwen3.5:9b")
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
STARTUP_TIMEOUT = 30
OLLAMA_TIMEOUT = 30
REPORT_NAME = "resultado.txt"
SUMMARY_NAME = "resumen.csv"


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _puerto_libre():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _esperar_api(base_url, proceso, log_path, timeout=STARTUP_TIMEOUT):
    inicio = time.monotonic()
    while time.monotonic() - inicio < timeout:
        if proceso.poll() is not None:
            log = Path(log_path).read_text(encoding="utf-8", errors="replace")
            raise RuntimeError(f"La API no arrancó.\n{log[-3000:]}")
        try:
            respuesta = requests.get(f"{base_url}/openapi.json", timeout=1)
            if respuesta.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.2)
    log = Path(log_path).read_text(encoding="utf-8", errors="replace")
    raise RuntimeError(f"Timeout esperando la API.\n{log[-3000:]}")


@contextmanager
def api_temporal():
    tempdir = Path(tempfile.mkdtemp(prefix="inscripciones-eval-"))
    db_path = tempdir / "inscripciones.db"
    log_path = tempdir / "uvicorn.log"
    puerto = _puerto_libre()
    base_url = f"http://127.0.0.1:{puerto}"

    env = os.environ.copy()
    env["DATABASE_PATH"] = str(db_path)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("DEBUG", None)

    log = open(log_path, "w", encoding="utf-8")
    proceso = None
    try:
        proceso = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(puerto),
                "--log-level",
                "warning",
            ],
            cwd=str(APP_DIR),
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        _esperar_api(base_url, proceso, log_path)
        yield base_url
    finally:
        if proceso is not None:
            proceso.terminate()
            try:
                proceso.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proceso.kill()
                proceso.wait(timeout=5)
        log.close()
        shutil.rmtree(tempdir, ignore_errors=True)


def _post(base_url, path, payload, esperado=201):
    respuesta = requests.post(f"{base_url}{path}", json=payload, timeout=10)
    if respuesta.status_code != esperado:
        raise RuntimeError(
            f"POST {path} devolvió {respuesta.status_code}: {respuesta.text}"
        )
    return respuesta


def sembrar(base_url, fixtures):
    _post(base_url, "/reset", None, esperado=204)
    for materia in fixtures["materias"]:
        _post(base_url, "/materias", materia)
    for alumno in fixtures["alumnos"]:
        _post(base_url, "/alumnos", alumno)
    for inscripcion in fixtures["inscripciones"]:
        _post(base_url, "/inscripciones", inscripcion)


def inscripciones(base_url):
    respuesta = requests.get(f"{base_url}/inscripciones", timeout=10)
    respuesta.raise_for_status()
    return respuesta.json()


def descubrir_entregas(path):
    ruta = Path(path).resolve()
    if ruta.is_file():
        if ruta.name != "agent.py":
            raise RuntimeError(
                "Pasá la carpeta de una entrega, la carpeta entregas o un agent.py."
            )
        return [ruta.parent], False, None
    if not ruta.is_dir():
        raise RuntimeError(f"No existe la ruta: {ruta}")
    if (ruta / "agent.py").is_file():
        return [ruta], False, None

    subcarpetas = sorted(
        p
        for p in ruta.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name != "__pycache__"
    )
    if not subcarpetas:
        raise RuntimeError("No encontré agent.py ni subcarpetas de entregas.")
    return subcarpetas, True, ruta


def importar_agente(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise RuntimeError(f"No existe el agente: {path}")

    nombre_modulo = f"agente_alumno_{uuid.uuid4().hex}"
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(nombre_modulo, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo importar el agente: {path}")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    faltantes = [
        nombre
        for nombre in ("responder", "_system_prompt", "ejecutar_herramienta")
        if not hasattr(modulo, nombre)
    ]
    if faltantes:
        raise RuntimeError(f"El agente no define: {', '.join(faltantes)}")
    return modulo


def envolver_herramienta(agente):
    original = agente.ejecutar_herramienta
    traza = []

    def registrada(nombre, argumentos):
        resultado = original(nombre, argumentos)
        traza.append(
            {"tool": nombre, "args": argumentos, "resultado": resultado}
        )
        return resultado

    agente.ejecutar_herramienta = registrada
    return traza, original


def codigos_inscribir(traza):
    codigos = set()
    for paso in traza:
        if paso.get("tool") != "inscribir":
            continue
        resultado = paso.get("resultado")
        if not isinstance(resultado, dict):
            continue
        error = resultado.get("error")
        if isinstance(error, dict) and isinstance(error.get("code"), str):
            codigos.add(error["code"])
    return codigos


def clasificar(caso, respuesta, traza, nuevas):
    esperado = caso["esperado"]
    resultado = esperado["resultado"]
    texto = normalizar(respuesta)

    if resultado == "inscripcion_aceptada":
        if len(nuevas) != 1:
            return False, f"se esperaba 1 inscripción nueva, hay {len(nuevas)}"
        fila = nuevas[0]
        for campo in ("alumno", "materia", "turno"):
            if str(fila.get(campo)) != str(esperado[campo]):
                return False, (
                    f"la inscripción nueva no coincide en {campo}: "
                    f"{fila.get(campo)!r} != {esperado[campo]!r}"
                )
        return True, "inscripción aceptada"

    if resultado == "inscripcion_rechazada":
        if nuevas:
            return False, f"se creó una inscripción nueva: {nuevas}"
        codigo = esperado["codigo"]
        codigos = codigos_inscribir(traza)
        if codigos and codigo not in codigos:
            return False, (
                f"la API devolvió otros códigos: {sorted(codigos)}; "
                f"se esperaba {codigo}"
            )
        if codigo.lower() not in texto:
            return False, f"la respuesta final no incluye el código {codigo}"
        return True, f"rechazada con {codigo}"

    if resultado == "datos_insuficientes":
        if nuevas:
            return False, f"se creó una inscripción nueva: {nuevas}"
        campo = esperado["campo"]
        if campo not in texto:
            return False, f"la respuesta final no pide el campo {campo}"
        return True, f"datos insuficientes: {campo}"

    return False, f"resultado esperado desconocido: {resultado}"


def ejecutar_caso(agente, base_url, fixtures, caso, traza):
    sembrar(base_url, fixtures)
    antes = inscripciones(base_url)
    ids_antes = {i["id"] for i in antes}

    agente.LEGAJO_ACTUAL = caso.get("legajo_actual")
    messages = [{"role": "system", "content": agente._system_prompt()}]
    respuesta = ""
    traza_ultimo = []

    for mensaje in caso["mensajes"]:
        messages.append({"role": "user", "content": mensaje})
        traza.clear()
        respuesta = agente.responder(messages)
        traza_ultimo = list(traza)

    despues = inscripciones(base_url)
    nuevas = [i for i in despues if i["id"] not in ids_antes]
    return respuesta, traza_ultimo, nuevas


def verificar_ollama(url, modelo):
    url = url.rstrip("/")
    inicio = time.monotonic()
    ultimo_error = ""
    while True:
        try:
            respuesta = requests.get(f"{url}/api/tags", timeout=5)
            if respuesta.status_code == 200:
                break
            ultimo_error = f"HTTP {respuesta.status_code}: {respuesta.text}"
        except requests.RequestException as exc:
            ultimo_error = str(exc)
        if time.monotonic() - inicio >= OLLAMA_TIMEOUT:
            raise RuntimeError(
                f"No se pudo conectar a Ollama en {url}: {ultimo_error}"
            )
        time.sleep(1)

    modelos = {m.get("name"): m for m in respuesta.json().get("models", [])}
    info = modelos.get(modelo) or modelos.get(f"{modelo}:latest")
    if info is None:
        raise RuntimeError(
            f"El modelo {modelo} no está disponible en Ollama. "
            f"Descargalo con `ollama pull {modelo}` o, si usás el Docker de ollama/, "
            f"`docker compose exec ollama ollama pull {modelo}`."
        )
    if "capabilities" in info and "tools" not in info["capabilities"]:
        print(
            f"Aviso: {modelo} no declara soporte de tools.",
            file=sys.stderr,
        )


def imprimir_fallo(caso, detalle, respuesta, traza, nuevas):
    print(f"     esperado: {json.dumps(caso['esperado'], ensure_ascii=False)}")
    print(f"     detalle:  {detalle}")
    print(f"     respuesta: {respuesta!r}")
    if nuevas:
        print(f"     inscripciones nuevas: {json.dumps(nuevas, ensure_ascii=False)}")
    if traza:
        print("     tools del último turno:")
        for paso in traza:
            args = json.dumps(paso.get("args"), ensure_ascii=False)
            resultado = json.dumps(paso.get("resultado"), ensure_ascii=False)
            print(f"       - {paso.get('tool')} {args} -> {resultado[:600]}")
    else:
        print("     tools del último turno: ninguna")


def cargar_dataset(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        fixtures = data["fixtures"]
        casos = data["casos"]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        raise RuntimeError(f"Dataset inválido: {exc}")
    if not isinstance(fixtures, dict) or not isinstance(casos, list):
        raise RuntimeError("Dataset inválido: faltan fixtures o casos.")
    return data, fixtures, casos


def _campo_csv(texto):
    return '"' + str(texto).replace('"', '""').replace("\n", " ") + '"'


def escribir_resultado_txt(entrega, modelo, resultados, total, error):
    aprobados = sum(1 for resultado in resultados if resultado["ok"])
    lineas = [
        f"modelo: {modelo}",
        f"aprobados: {aprobados}/{total}",
    ]
    if error:
        lineas.append(f"ERROR,{_campo_csv(error)}")
    for resultado in resultados:
        estado = "OK" if resultado["ok"] else "FAIL"
        mensaje = "" if resultado["ok"] else resultado["detalle"]
        lineas.append(
            f"{resultado['id']},{estado},{_campo_csv(mensaje)}"
        )
    (entrega / REPORT_NAME).write_text(
        "\n".join(lineas) + "\n", encoding="utf-8"
    )


def escribir_resumen_csv(batch_dir, filas):
    with (batch_dir / SUMMARY_NAME).open(
        "w", newline="", encoding="utf-8"
    ) as archivo:
        writer = csv.writer(archivo)
        writer.writerow(["grupo", "aprobados", "total"])
        writer.writerows(filas)


def ejecutar_entrega(entrega, base_url, fixtures, casos, args, mostrar_todos):
    agente_path = entrega / "agent.py"
    if not agente_path.is_file():
        return [], "No se encontró agent.py"

    try:
        agente = importar_agente(agente_path)
    except Exception as exc:
        return [], f"No se pudo importar el agente: {exc}"

    agente.MODEL = args.model
    agente.OLLAMA_URL = args.ollama_url
    agente.API_URL = base_url
    agente.LEGAJO_ACTUAL = None
    traza, original = envolver_herramienta(agente)

    resultados = []
    try:
        for indice, caso in enumerate(casos, 1):
            print(
                f"  [{indice}/{len(casos)}] {caso.get('id')} ... ",
                end="",
                flush=True,
            )
            try:
                respuesta, traza_ultimo, nuevas = ejecutar_caso(
                    agente, base_url, fixtures, caso, traza
                )
                ok, detalle = clasificar(
                    caso, respuesta, traza_ultimo, nuevas
                )
            except Exception as exc:
                ok = False
                detalle = f"ERROR: {exc}"
                respuesta = ""
                traza_ultimo = list(traza)
                nuevas = []

            if ok:
                print("OK" if mostrar_todos else "")
            else:
                print("FAIL")
                imprimir_fallo(
                    caso, detalle, respuesta, traza_ultimo, nuevas
                )

            resultados.append(
                {
                    "id": caso.get("id"),
                    "ok": ok,
                    "detalle": detalle,
                }
            )
    finally:
        agente.ejecutar_herramienta = original

    return resultados, None


def main():
    parser = argparse.ArgumentParser(
        description="Corrige agentes de inscripciones contra un dataset de interacciones."
    )
    parser.add_argument(
        "agente",
        type=Path,
        help="Carpeta de una entrega, carpeta entregas o archivo agent.py",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="Dataset JSON: publico.json o privado.json",
    )
    parser.add_argument(
        "--model", default=DEFAULT_MODEL, help="Modelo de Ollama"
    )
    parser.add_argument(
        "--ollama-url", default=DEFAULT_OLLAMA_URL, help="URL de Ollama"
    )
    parser.add_argument(
        "--caso", help="Correr solo el caso con este id"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostrar también los casos OK en modo lote",
    )
    args = parser.parse_args()

    os.environ.pop("DEBUG", None)

    try:
        data, fixtures, casos = cargar_dataset(args.dataset)
        if args.caso:
            casos = [caso for caso in casos if caso.get("id") == args.caso]
            if not casos:
                print(f"No existe el caso {args.caso!r}.", file=sys.stderr)
                return 1
        if not casos:
            print("El dataset no tiene casos.", file=sys.stderr)
            return 1

        entregas, es_lote, batch_dir = descubrir_entregas(args.agente)
        verificar_ollama(args.ollama_url, args.model)
    except RuntimeError as exc:
        print(f"Error de setup: {exc}", file=sys.stderr)
        return 1

    print(f"Dataset: {args.dataset}")
    print(f"Entregas: {len(entregas)}")
    print(f"Modelo: {args.model}")
    print(f"Casos por entrega: {len(casos)}")
    print(f"Modo: {'lote' if es_lote else 'individual'}")
    print()

    filas_resumen = []
    todos_ok = True

    try:
        with api_temporal() as base_url:
            for entrega in entregas:
                if es_lote:
                    print(f"=== {entrega.name} ===")

                try:
                    resultados, error = ejecutar_entrega(
                        entrega,
                        base_url,
                        fixtures,
                        casos,
                        args,
                        mostrar_todos=(not es_lote) or args.verbose,
                    )
                except Exception as exc:
                    resultados, error = [], f"ERROR: {exc}"

                aprobados = sum(
                    1 for resultado in resultados if resultado["ok"]
                )
                total = len(casos)

                if es_lote:
                    try:
                        escribir_resultado_txt(
                            entrega,
                            args.model,
                            resultados,
                            total,
                            error,
                        )
                    except OSError as exc:
                        print(
                            f"No se pudo escribir {entrega / REPORT_NAME}: {exc}",
                            file=sys.stderr,
                        )
                        todos_ok = False
                    filas_resumen.append(
                        (entrega.name, aprobados, total)
                    )

                if error:
                    print(f"  ERROR: {error}")
                    todos_ok = False
                else:
                    print(f"  Resultado: {aprobados}/{total}")
                    if aprobados != total:
                        todos_ok = False
                print()
    except Exception as exc:
        print(f"Error de setup de la API: {exc}", file=sys.stderr)
        return 1

    if es_lote and batch_dir is not None:
        try:
            escribir_resumen_csv(batch_dir, filas_resumen)
        except OSError as exc:
            print(
                f"No se pudo escribir {batch_dir / SUMMARY_NAME}: {exc}",
                file=sys.stderr,
            )
            todos_ok = False

        print("=== Resumen ===")
        for grupo, aprobados, total in filas_resumen:
            print(f"{grupo}: {aprobados}/{total}")

    return 0 if todos_ok else 1


if __name__ == "__main__":
    sys.exit(main())
