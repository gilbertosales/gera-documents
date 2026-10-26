"""SC-002: primeiros resultados rápidos e a tela continua respondendo durante a busca."""

import shutil
import time

from tests.conftest import AMOSTRA
from tests.integration.conftest import esperar


def test_200_arquivos(cliente, tmp_path):
    pasta = tmp_path / "grande"
    for i in range(8):  # 8 cópias × ~28 .md ≈ 224 arquivos
        shutil.copytree(AMOSTRA, pasta / f"lote{i}")
    t0 = time.perf_counter()
    r = cliente.post("/api/analises", json={"pasta": str(pasta), "subpastas": True})
    op_id = r.json()["operacao_id"]
    primeiro = None
    while primeiro is None and time.perf_counter() - t0 < 10:
        try:
            ev, _ = cliente.eventos.get(timeout=0.05)
        except Exception:  # noqa: BLE001 — fila vazia
            continue
        if ev == "arquivo":
            primeiro = time.perf_counter() - t0
    assert primeiro is not None and primeiro <= 3
    t1 = time.perf_counter()
    assert cliente.get("/api/config").status_code == 200
    assert time.perf_counter() - t1 < 0.5
    op = esperar(cliente, op_id, timeout=60)
    assert op["resultado"]["total"] >= 200
