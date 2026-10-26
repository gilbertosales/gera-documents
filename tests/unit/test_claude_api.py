"""User Story 4: acesso por API separado, nunca padrão, chave só no cofre do sistema."""

import json
import sys
import types

import pytest

from gera_md import config
from gera_md.provedores import claude_cli
from gera_md.provedores.base import AcessoIncorreto
from gera_md.provedores.claude_cli import ClaudeApi
from tests.unit.test_provedores import INIT_OK, RESULTADO, Proc, _popen

CHAVE = "sk-ant-api03-" + "z" * 40


@pytest.fixture
def cofre(monkeypatch):
    guardado = {}
    kr = types.SimpleNamespace(
        get_password=lambda s, u: guardado.get((s, u)),
        set_password=lambda s, u, v: guardado.__setitem__((s, u), v),
        delete_password=lambda s, u: guardado.pop((s, u), None),
    )
    monkeypatch.setitem(sys.modules, "keyring", kr)
    monkeypatch.setattr(claude_cli, "executavel", lambda: r"C:\fake\claude.exe")
    monkeypatch.setattr(claude_cli, "_matar", lambda proc: proc.matar())
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return guardado


def test_sem_chave_e_com_chave(cofre):
    p = ClaudeApi()
    assert p.estado().estado == "chave_ausente"
    p.salvar_chave(CHAVE)
    assert p.estado().estado == "logado"
    assert p.padrao is False and p.cobranca == "por_uso" and p.tipo_acesso == "api"
    assert CHAVE not in json.dumps(p.to_dict())
    p.remover_chave()
    assert p.estado().estado == "chave_ausente"


def test_chave_so_no_processo_da_chamada(cofre, monkeypatch):
    chamadas = {"popen": []}
    _popen(monkeypatch, chamadas, Proc([{**INIT_OK, "apiKeySource": "ANTHROPIC_API_KEY"}, RESULTADO]))
    p = ClaudeApi()
    p.salvar_chave(CHAVE)
    p.enviar("p", "s", "padrão")
    _cmd, kw = chamadas["popen"][0]
    assert kw["env"]["ANTHROPIC_API_KEY"] == CHAVE
    import os
    assert os.environ.get("ANTHROPIC_API_KEY") != CHAVE


def test_api_que_nao_usa_chave_e_recusada(cofre, monkeypatch):
    _popen(monkeypatch, {"popen": []}, Proc([INIT_OK, RESULTADO]))
    p = ClaudeApi()
    p.salvar_chave(CHAVE)
    with pytest.raises(AcessoIncorreto):
        p.enviar("p", "s", "padrão")


def test_sem_keyring(monkeypatch):
    monkeypatch.setitem(sys.modules, "keyring", None)
    e = ClaudeApi().estado()
    assert e.estado == "erro" and "pip install keyring" in e.detalhe


def test_config_recusa_credenciais(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CAMINHO", str(tmp_path / "c.json"))
    with pytest.raises(ValueError):
        config.salvar_preferencias(chave_api=CHAVE)
    config.salvar_preferencias(provedor_padrao="claude-api")
    assert CHAVE not in (tmp_path / "c.json").read_text(encoding="utf-8")


def test_rotas_da_chave(cofre):
    from starlette.testclient import TestClient
    from gera_md.web.app import criar_app
    from tests.integration.conftest import BASE, TOKEN
    app = criar_app(TOKEN, 8765)
    with TestClient(app, base_url=BASE) as c:
        c.get(f"/?t={TOKEN}", follow_redirects=False)
        r = c.put("/api/provedores/claude-api/chave", json={"chave": CHAVE})
        assert r.status_code == 200 and CHAVE not in r.text
        assert r.json()["estado"] == "logado" and r.json()["padrao"] is False
        assert c.put("/api/provedores/claude-api/chave", json={"chave": "curta"}).status_code == 400
        assert c.delete("/api/provedores/claude-api/chave").json()["estado"] == "chave_ausente"
