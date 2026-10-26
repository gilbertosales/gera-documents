"""Servidor local: só esta máquina, só com a sessão, só caminhos da pasta analisada (FR-002, R4)."""

import os

import pytest
from starlette.testclient import TestClient

from gera_md.web.seguranca import ErroApi, validar_caminho
from tests.integration.conftest import BASE, TOKEN


def test_api_sem_cookie_401(app):
    with TestClient(app, base_url=BASE) as c:
        assert c.get("/api/config").status_code == 401
        assert c.get("/").status_code == 401


def test_host_estranho_403(app):
    with TestClient(app, base_url="http://192.168.0.10:8765") as c:
        assert c.get(f"/?t={TOKEN}").status_code == 403
    with TestClient(app, base_url="http://evil.example:8765") as c:
        assert c.get("/api/config").status_code == 403


def test_origin_estranha_403(cliente):
    r = cliente.post("/api/analises", json={"pasta": "x"}, headers={"Origin": "http://exemplo.com"})
    assert r.status_code == 403
    r = cliente.post("/api/analises", json={"pasta": ""}, headers={"Origin": BASE})
    assert r.status_code == 400  # passou pela origem; falhou na validação


def test_token_errado_401(app):
    with TestClient(app, base_url=BASE) as c:
        assert c.get("/?t=errado", follow_redirects=False).status_code == 401


def test_token_certo_define_cookie(app):
    with TestClient(app, base_url=BASE) as c:
        r = c.get(f"/?t={TOKEN}", follow_redirects=False)
        assert r.status_code == 303
        cookie = r.headers["set-cookie"].lower()
        assert "httponly" in cookie and "samesite=strict" in cookie
        assert c.get("/api/config").status_code == 200
        assert "Gera Documents" in c.get("/").text


def test_validar_caminho(tmp_path):
    pasta = tmp_path / "docs"
    pasta.mkdir()
    (pasta / "a.md").write_text("x")
    (tmp_path / "fora.md").write_text("x")
    assert validar_caminho(str(pasta / "a.md"), str(pasta)) == os.path.realpath(pasta / "a.md")
    for ruim in (str(pasta / ".." / "fora.md"), str(pasta / "a.txt"), str(tmp_path / "fora.md"), "", None):
        with pytest.raises(ErroApi) as e:
            validar_caminho(ruim, str(pasta))
        assert e.value.status == 400
    # extras (relatórios salvos fora da pasta) são aceitos
    assert validar_caminho(str(tmp_path / "fora.md"), str(pasta), {str(tmp_path / "fora.md")})


def test_rota_de_arquivo_recusa_fora_da_analise(cliente, amostra, tmp_path):
    from tests.integration.conftest import analisar
    analise_id, _ = analisar(cliente, amostra)
    (tmp_path / "x.md").write_text("x")
    r = cliente.post("/api/abrir", json={"analise_id": analise_id, "caminho": str(tmp_path / "x.md")})
    assert r.status_code == 400 and r.json()["erro"]
