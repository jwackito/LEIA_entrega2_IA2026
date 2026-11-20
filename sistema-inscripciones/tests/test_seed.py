from app.seed import ESPECIALES, MATERIAS, generar_alumnos, orden_topologico


def test_materias_del_seed_son_37_y_estan_en_orden_topologico():
    orden = orden_topologico(MATERIAS)
    assert len(orden) == 37
    codigos = [materia["codigo"] for materia in orden]
    assert len(set(codigos)) == 37

    posiciones = {codigo: i for i, codigo in enumerate(codigos)}
    for materia in orden:
        for correlativa in materia["correlativas"]:
            assert posiciones[correlativa] < posiciones[materia["codigo"]]


def test_alumnos_del_seed_son_50_validos_y_repetibles():
    alumnos = generar_alumnos(MATERIAS)
    assert len(alumnos) == 50
    assert len({alumno["legajo"] for alumno in alumnos}) == 50
    assert alumnos == generar_alumnos(MATERIAS)

    codigos = {materia["codigo"] for materia in MATERIAS}
    correlativas = {
        materia["codigo"]: set(materia["correlativas"]) for materia in MATERIAS
    }
    for alumno in alumnos:
        aprobadas = set(alumno["aprobadas"])
        assert aprobadas <= codigos
        assert not (aprobadas & ESPECIALES)
        for codigo in aprobadas:
            assert correlativas[codigo] <= aprobadas
