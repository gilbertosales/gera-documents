"""User Story 2: revisão com IA pela assinatura, com confirmação, progresso e cancelamento."""

import os
import threading

from tests.integration.conftest import analisar, esperar, eventos


def _md(amostra, nome="ok.md"):
    return os.path.realpath(os.path.join(amostra, nome))


def test_provedores_padrao_assinatura(cliente, monkeypatch):
    from gera_md import provedores
    from gera_md.provedores.base import EstadoProvedor
    monkeypatch.setattr(provedores, "estado", lambda p, atualizar=False: EstadoProvedor("logado", ""))
    lista = cliente.get("/api/provedores").json()
    padrao = [p for p in lista if p["padrao"]]
    assert len(padrao) == 1 and padrao[0]["id"] == "claude-assinatura"
    assert padrao[0]["tipo_acesso"] == "assinatura"
    api = next(p for p in lista if p["id"] == "claude-api")
    assert api["padrao"] is False and api["cobranca"] == "por_uso"


def test_skills(cliente):
    skills = cliente.get("/api/skills").json()
    assert any(s["nome"] == "technical-documentation" and s["padrao"] for s in skills)


def test_previa_e_confirmacao_obrigatoria(cliente, amostra, simulado):
    analise_id, _ = analisar(cliente, amostra)
    corpo = {"analise_id": analise_id, "caminhos": [_md(amostra)], "provedor": "claude-assinatura",
             "skill": "technical-documentation", "modelo": "padrão"}
    p = cliente.post("/api/revisoes/previa", json=corpo).json()
    assert p["arquivos"][0]["trechos"] >= 1
    assert "sem cobrança extra" in p["aviso"] and p["tipo_acesso"] == "assinatura"
    r = cliente.post("/api/revisoes", json=corpo)
    assert r.status_code == 409 and simulado.chamadas == 0
    r = cliente.post("/api/revisoes", json={**corpo, "confirmado": "sim"})
    assert r.status_code == 409


def test_revisao_completa(cliente, amostra, simulado, hash_arquivos):
    for nome in ("ok.md", "links.md"):  # o simulado troca "muito bom": garante texto alterado
        with open(_md(amostra, nome), "a", encoding="utf-8") as f:
            f.write("\nO resultado foi muito bom.\n")
    antes = hash_arquivos(amostra)
    analise_id, _ = analisar(cliente, amostra)
    eventos(cliente)
    corpo = {"analise_id": analise_id, "caminhos": [_md(amostra), _md(amostra, "links.md")],
             "provedor": "claude-assinatura", "skill": "technical-documentation", "modelo": "padrão",
             "confirmado": True}
    r = cliente.post("/api/revisoes", json=corpo)
    assert r.status_code == 202
    op = esperar(cliente, r.json()["operacao_id"])
    assert op["estado"] == "concluida"
    feitos = op["resultado"]["feitos"]
    assert len(feitos) == 2 and all(os.path.exists(f["relatorio"]) for f in feitos)
    assert op["resultado"]["cobranca"] == "limite_assinatura"
    evs = eventos(cliente, op["id"])
    assert any(e == "progresso" and "trecho" in d["mensagem"] for e, d in evs)
    novos = [d["arquivo"] for e, d in evs if e == "arquivo"]
    assert len(novos) == 2 and all(a["tipo_versao"] == "revisao_ia" and a["revisao"] for a in novos)
    depois = {k: v for k, v in hash_arquivos(amostra).items() if "_v" not in k}
    assert depois == antes


def test_provedor_nao_logado_409(cliente, amostra, simulado):
    simulado._estado = "login_necessario"
    analise_id, _ = analisar(cliente, amostra)
    r = cliente.post("/api/revisoes", json={"analise_id": analise_id, "caminhos": [_md(amostra)],
                                            "provedor": "claude-assinatura", "confirmado": True})
    assert r.status_code == 409 and r.json()["instrucoes_login"]


def test_uma_revisao_por_vez_e_cancelar(cliente, amostra, simulado):
    simulado.atraso = 0.5
    analise_id, _ = analisar(cliente, amostra)
    corpo = {"analise_id": analise_id, "caminhos": [_md(amostra), _md(amostra, "links.md")],
             "provedor": "claude-assinatura", "confirmado": True}
    op_id = cliente.post("/api/revisoes", json=corpo).json()["operacao_id"]
    assert cliente.post("/api/revisoes", json=corpo).status_code == 409
    threading.Event().wait(0.1)
    assert cliente.post(f"/api/operacoes/{op_id}/cancelar").status_code == 202
    op = esperar(cliente, op_id)
    assert op["estado"] == "cancelada"
    assert any(e == "cancelado" for e, _ in eventos(cliente, op_id))
    assert not [n for n in os.listdir(amostra) if n.startswith("ok_v")]


def test_sessao_expirada_atualiza_provedor(cliente, amostra, simulado):
    simulado.login_em = {1, 2, 3}
    analise_id, _ = analisar(cliente, amostra)
    eventos(cliente)
    r = cliente.post("/api/revisoes", json={"analise_id": analise_id, "caminhos": [_md(amostra)],
                                            "provedor": "claude-assinatura", "confirmado": True})
    op = esperar(cliente, r.json()["operacao_id"])
    assert op["resultado"]["erros"] and "expirada" in op["resultado"]["erros"][0]["erro"]
    assert any(e == "provedor" for e, _ in eventos(cliente))


def test_revisao_sem_alteracao_liga_relatorio_ao_original(cliente, amostra, simulado):
    analise_id, _ = analisar(cliente, amostra)
    md = _md(amostra, "riscado.md")  # o simulado só altera "muito bom": texto fica igual
    r = cliente.post("/api/revisoes", json={"analise_id": analise_id, "caminhos": [md],
                                            "provedor": "claude-assinatura", "confirmado": True})
    op = esperar(cliente, r.json()["operacao_id"])
    feito = op["resultado"]["feitos"][0]
    assert feito["destino"] is None and feito["relatorio"].endswith("riscado_revisao.md")
    assert not [n for n in os.listdir(amostra) if n.startswith("riscado_v")]
    original = cliente.get(f"/api/analises/{analise_id}/arquivo", params={"caminho": md}).json()
    assert original["revisao"]["relatorio"] == feito["relatorio"]


def test_provedor_padrao_nunca_e_api(cliente, amostra, simulado):
    from gera_md import config, provedores
    from gera_md.provedores.simulado import ProvedorSimulado
    api = ProvedorSimulado(id="claude-api")
    api.tipo_acesso, api.cobranca = "api", "por_uso"
    provedores.registrar(api)
    analise_id, _ = analisar(cliente, amostra)
    corpo = {"analise_id": analise_id, "caminhos": [_md(amostra)], "confirmado": True,
             "skill": "technical-documentation", "modelo": "padrão"}
    esperar(cliente, cliente.post("/api/revisoes", json={**corpo, "provedor": "claude-assinatura"}).json()["operacao_id"])
    assert config.obter()["provedor_padrao"] == "claude-assinatura"
    esperar(cliente, cliente.post("/api/revisoes", json={**corpo, "provedor": "claude-api"}).json()["operacao_id"])
    assert config.obter()["provedor_padrao"] == "claude-assinatura"
