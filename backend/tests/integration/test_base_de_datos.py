from sqlalchemy import Engine, text


def test_consulta_trivial(motor: Engine):
    with motor.connect() as conexion:
        assert conexion.execute(text("SELECT 1")).scalar_one() == 1


def test_version_mayor_del_servidor_es_18(motor: Engine):
    with motor.connect() as conexion:
        version = conexion.execute(text("SHOW server_version_num")).scalar_one()

    assert int(version) // 10000 == 18


def test_btree_gist_figura_como_extension_disponible(motor: Engine):
    with motor.connect() as conexion:
        nombres = conexion.execute(
            text("SELECT name FROM pg_available_extensions")
        ).scalars().all()

    assert "btree_gist" in nombres


def test_la_suite_corre_sobre_la_base_de_pruebas(motor: Engine):
    with motor.connect() as conexion:
        actual = conexion.execute(text("SELECT current_database()")).scalar_one()

    assert actual == "turnos_test"
    assert actual != "turnos"
