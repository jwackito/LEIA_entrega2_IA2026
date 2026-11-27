import json

import agent


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self.payload = payload
        self.text = text

    def json(self):
        if self.payload is None:
            raise ValueError("sin json")
        return self.payload


def test_buscar_materias_filtra_y_normaliza(monkeypatch):
    materias = [
        {
            "codigo": "SI305",
            "nombre": "Proyecto de Software",
            "correlativas": [],
            "turnos": {},
        },
        {
            "codigo": "SI101",
            "nombre": "Matemática 1",
            "correlativas": [],
            "turnos": {},
        },
    ]
    monkeypatch.setattr(
        agent.requests,
        "request",
        lambda *args, **kwargs: FakeResponse(200, materias),
    )

    assert agent.ejecutar_herramienta("buscar_materias", {"texto": "software"}) == [
        {"codigo": "SI305", "nombre": "Proyecto de Software"}
    ]
    assert agent.ejecutar_herramienta("buscar_materias", {"texto": "matematica"}) == [
        {"codigo": "SI101", "nombre": "Matemática 1"}
    ]


def test_inscribir_llama_al_endpoint_correcto(monkeypatch):
    llamadas = []

    def fake_request(method, url, **kwargs):
        llamadas.append((method, url, kwargs.get("json")))
        return FakeResponse(
            201,
            {"id": 7, "alumno": "1001", "materia": "CNE", "turno": "manana"},
        )

    monkeypatch.setattr(agent.requests, "request", fake_request)

    resultado = agent.ejecutar_herramienta(
        "inscribir", {"alumno": "1001", "materia": "CNE", "turno": "manana"}
    )

    assert resultado["id"] == 7
    assert llamadas == [
        (
            "POST",
            f"{agent.API_URL}/inscripciones",
            {"alumno": "1001", "materia": "CNE", "turno": "manana"},
        )
    ]


def test_error_de_api_se_devuelve(monkeypatch):
    monkeypatch.setattr(
        agent.requests,
        "request",
        lambda *args, **kwargs: FakeResponse(
            409, {"code": "SIN_CUPO", "detail": "No hay cupo"}
        ),
    )

    assert agent.ejecutar_herramienta(
        "inscribir", {"alumno": "1001", "materia": "CNE", "turno": "manana"}
    ) == {"error": {"code": "SIN_CUPO", "detail": "No hay cupo"}}


def test_dar_de_baja(monkeypatch):
    llamadas = []

    def fake_request(method, url, **kwargs):
        llamadas.append((method, url))
        return FakeResponse(204)

    monkeypatch.setattr(agent.requests, "request", fake_request)

    assert agent.ejecutar_herramienta("dar_de_baja", {"inscripcion_id": 3}) == {
        "ok": True
    }
    assert llamadas == [("DELETE", f"{agent.API_URL}/inscripciones/3")]


def test_listar_inscripciones_usa_legajo_actual(monkeypatch):
    monkeypatch.setattr(agent, "LEGAJO_ACTUAL", "1001")
    inscripciones = [
        {"id": 1, "alumno": "1001", "materia": "CNE", "turno": "manana"},
        {"id": 2, "alumno": "1002", "materia": "CNE", "turno": "manana"},
    ]
    monkeypatch.setattr(
        agent.requests,
        "request",
        lambda *args, **kwargs: FakeResponse(200, inscripciones),
    )

    assert agent.ejecutar_herramienta("listar_inscripciones", {}) == [
        inscripciones[0]
    ]


def test_herramienta_desconocida():
    assert "error" in agent.ejecutar_herramienta("no_existe", {})


def test_ollama_arma_payload(monkeypatch):
    capturado = {}

    def fake_post(url, **kwargs):
        capturado["url"] = url
        capturado["json"] = kwargs["json"]
        return FakeResponse(
            200, {"message": {"role": "assistant", "content": "hola"}}
        )

    monkeypatch.setattr(agent.requests, "post", fake_post)

    mensaje, error = agent._ollama_chat([{"role": "user", "content": "hola"}])

    assert error is None
    assert mensaje["content"] == "hola"
    assert capturado["url"] == f"{agent.OLLAMA_URL}/api/chat"
    assert capturado["json"]["model"] == agent.MODEL
    assert capturado["json"]["tools"] == agent.TOOLS
    assert capturado["json"]["stream"] is False
    assert capturado["json"]["think"] is False


def test_responder_ejecuta_tool_y_devuelve_texto(monkeypatch):
    respuestas = [
        (
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "buscar_materias",
                            "arguments": {"texto": "CNE"},
                        }
                    }
                ],
            },
            None,
        ),
        ({"role": "assistant", "content": "Listo."}, None),
    ]
    monkeypatch.setattr(agent, "_ollama_chat", lambda messages: respuestas.pop(0))

    ejecutadas = []

    def fake_ejecutar(nombre, argumentos):
        ejecutadas.append((nombre, argumentos))
        return [{"codigo": "CNE", "nombre": "Expresión de Problemas y Algoritmos"}]

    monkeypatch.setattr(agent, "ejecutar_herramienta", fake_ejecutar)

    messages = [{"role": "system", "content": "sistema"}]
    assert agent.responder(messages) == "Listo."
    assert ejecutadas == [("buscar_materias", {"texto": "CNE"})]
    assert messages[-2]["role"] == "tool"
    assert messages[-2]["tool_name"] == "buscar_materias"
    assert json.loads(messages[-2]["content"]) == [
        {"codigo": "CNE", "nombre": "Expresión de Problemas y Algoritmos"}
    ]


def test_debug_muestra_respuesta_cruda(monkeypatch, capsys):
    monkeypatch.setenv("DEBUG", "1")
    crudo = '{"message": {"role": "assistant", "content": "hola"}}'
    monkeypatch.setattr(
        agent.requests,
        "post",
        lambda *args, **kwargs: FakeResponse(
            200,
            {"message": {"role": "assistant", "content": "hola"}},
            text=crudo,
        ),
    )

    mensaje, error = agent._ollama_chat([{"role": "user", "content": "hola"}])

    assert error is None
    assert mensaje["content"] == "hola"
    assert f"[debug] {crudo}" in capsys.readouterr().err


def test_debug_deshabilitado_no_escribe_en_stderr(monkeypatch, capsys):
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.setattr(
        agent.requests,
        "post",
        lambda *args, **kwargs: FakeResponse(
            200,
            {"message": {"role": "assistant", "content": "hola"}},
            text='{"message": {"role": "assistant", "content": "hola"}}',
        ),
    )

    mensaje, error = agent._ollama_chat([{"role": "user", "content": "hola"}])

    assert error is None
    assert mensaje["content"] == "hola"
    assert capsys.readouterr().err == ""


def test_debug_muestra_tool_call_api_y_resultado(monkeypatch, capsys):
    monkeypatch.setenv("DEBUG", "1")
    respuestas = [
        (
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "obtener_alumno",
                            "arguments": {"legajo": "1001"},
                        }
                    }
                ],
            },
            None,
        ),
        ({"role": "assistant", "content": "Listo."}, None),
    ]
    monkeypatch.setattr(agent, "_ollama_chat", lambda messages: respuestas.pop(0))

    alumno = {
        "legajo": "1001",
        "nombre": "Ana",
        "apellido": "Pérez",
        "aprobadas": [],
    }
    monkeypatch.setattr(
        agent.requests,
        "request",
        lambda *args, **kwargs: FakeResponse(200, alumno),
    )

    messages = [{"role": "system", "content": "sistema"}]
    assert agent.responder(messages) == "Listo."

    err = capsys.readouterr().err
    assert '[debug] tool_call obtener_alumno {"legajo": "1001"}' in err
    assert "[debug] API GET /alumnos/1001 -> 200" in err
    assert (
        '[debug] tool_result obtener_alumno '
        '{"legajo": "1001", "nombre": "Ana", "apellido": "Pérez", "aprobadas": []}'
    ) in err


def test_debug_muestra_status_de_error(monkeypatch, capsys):
    monkeypatch.setenv("DEBUG", "1")
    error = {"code": "MATERIA_APROBADA", "detail": "La materia ya está aprobada"}
    monkeypatch.setattr(
        agent.requests,
        "request",
        lambda *args, **kwargs: FakeResponse(409, error),
    )

    resultado = agent.ejecutar_herramienta(
        "inscribir", {"alumno": "1001", "materia": "SI101", "turno": "manana"}
    )

    assert resultado == {"error": error}
    err = capsys.readouterr().err
    assert "[debug] API POST /inscripciones" in err
    assert "-> 409" in err


def test_responder_agrega_codigo_si_el_modelo_lo_omite(monkeypatch):
    respuestas = [
        (
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "inscribir",
                            "arguments": {
                                "alumno": "1001",
                                "materia": "SI101",
                                "turno": "manana",
                            },
                        }
                    }
                ],
            },
            None,
        ),
        ({"role": "assistant", "content": "No se pudo inscribir."}, None),
    ]
    monkeypatch.setattr(agent, "_ollama_chat", lambda messages: respuestas.pop(0))
    monkeypatch.setattr(
        agent,
        "ejecutar_herramienta",
        lambda nombre, argumentos: {
            "error": {"code": "MATERIA_APROBADA", "detail": "La materia ya está aprobada"}
        },
    )

    messages = [{"role": "system", "content": "sistema"}]
    respuesta = agent.responder(messages)

    assert "No se pudo inscribir." in respuesta
    assert "MATERIA_APROBADA" in respuesta
