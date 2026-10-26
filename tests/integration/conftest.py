import queue
import time

import pytest
from starlette.testclient import TestClient

import gerar_word
from gera_md import config, provedores
from gera_md.web.app import criar_app

TOKEN = "token-de-teste-" + "x" * 30
PORTA = 8765
BASE = f"http://127.0.0.1:{PORTA}"


@pytest.fixture(autouse=True)
def config_isolada(tmp_path, monkeypatch):
    """Nenhum teste toca a configuração real do usuário."""
    monkeypatch.setattr(config, "CAMINHO", str(tmp_path / "gera_documents_config.json"))
    monkeypatch.setattr(gerar_word, "CONFIG_PATH", str(tmp_path / "gerar_word_config.json"))


@pytest.fixture
def app():
    return criar_app(TOKEN, PORTA)


@pytest.fixture
def cliente(app):
    with TestClient(app, base_url=BASE) as c:
        r = c.get(f"/?t={TOKEN}", follow_redirects=False)
        assert r.status_code == 303
        c.app_estado = app.estado
        c.eventos = app.estado.gerenciador.assinar()
        yield c


@pytest.fixture
def simulado(monkeypatch):
    """Troca os provedores reais por um simulado padrão (sem Claude, sem rede)."""
    from gera_md.provedores.simulado import ProvedorSimulado
    originais = dict(provedores._provedores)
    provedores._provedores.clear()
    provedores.invalidar()
    sim = ProvedorSimulado(padrao=True, id="claude-assinatura")
    sim.nome = "Claude (Pro/Max)"
    provedores.registrar(sim)
    yield sim
    provedores._provedores.clear()
    provedores._provedores.update(originais)
    provedores.invalidar()


def esperar(cliente, operacao_id, timeout=10):
    fim = time.time() + timeout
    while time.time() < fim:
        op = cliente.get(f"/api/operacoes/{operacao_id}").json()
        if op["estado"] not in ("executando", "cancelando"):
            return op
        time.sleep(0.02)
    raise AssertionError(f"operação {operacao_id} não terminou")


def eventos(cliente, operacao_id=None):
    out = []
    while True:
        try:
            ev, dados = cliente.eventos.get_nowait()
        except queue.Empty:
            return out
        if operacao_id is None or dados.get("operacao_id") == operacao_id:
            out.append((ev, dados))


def analisar(cliente, pasta, subpastas=True):
    r = cliente.post("/api/analises", json={"pasta": pasta, "subpastas": subpastas})
    assert r.status_code == 202, r.text
    dados = r.json()
    op = esperar(cliente, dados["operacao_id"])
    assert op["estado"] == "concluida", op
    return dados["analise_id"], op
