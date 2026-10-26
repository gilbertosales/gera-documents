"""User Story 1: analisar e corrigir uma pasta pelo navegador, sem IA."""

import os
import time

from gera_md import config
from tests.integration.conftest import analisar, esperar, eventos


def test_busca_emite_um_evento_por_arquivo(cliente, amostra):
    analise_id, op = analisar(cliente, amostra)
    evs = eventos(cliente, op["id"])
    arquivos = [d["arquivo"]["rotulo"].replace("\\", "/") for e, d in evs if e == "arquivo"]
    assert "sub/interno.md" in arquivos and "ok.md" in arquivos
    assert not any("node_modules" in a or ".oculta" in a for a in arquivos)
    assert [e for e, _ in evs][-1] == "concluido"
    assert op["resultado"]["total"] == len(arquivos)
    a = cliente.get(f"/api/analises/{analise_id}").json()
    assert len(a["arquivos"]) == len(arquivos)
    assert {"erros", "avisos", "situacao"} <= set(a["arquivos"][0])
    assert config.obter()["pastas_recentes"][0] == os.path.normpath(amostra)


def test_sem_subpastas(cliente, amostra):
    analise_id, _ = analisar(cliente, amostra, subpastas=False)
    rotulos = [a["rotulo"] for a in cliente.get(f"/api/analises/{analise_id}").json()["arquivos"]]
    assert all(os.sep not in r and "/" not in r for r in rotulos)


def test_pasta_inexistente(cliente, tmp_path):
    r = cliente.post("/api/analises", json={"pasta": str(tmp_path / "nao_existe")})
    assert r.status_code == 400
    assert r.json()["acao"]


def test_arquivo_traz_trecho(cliente, amostra):
    analise_id, _ = analisar(cliente, amostra)
    caminho = os.path.realpath(os.path.join(amostra, "riscado.md"))
    r = cliente.get(f"/api/analises/{analise_id}/arquivo", params={"caminho": caminho})
    assert r.status_code == 200
    achado = r.json()["achados"][0]
    assert achado["linha"] == 3 and achado["trecho"] == "Texto ~~antigo~~ novo."


def test_corrigir_todos_com_problema(cliente, amostra, hash_arquivos):
    antes = hash_arquivos(amostra)
    analise_id, _ = analisar(cliente, amostra)
    eventos(cliente)
    r = cliente.post("/api/correcoes", json={"analise_id": analise_id, "caminhos": "todos_com_problema"})
    assert r.status_code == 202
    op = esperar(cliente, r.json()["operacao_id"])
    criados = op["resultado"]["criados"]
    assert criados and all(c["tipo_versao"] == "correcao" and c["origem"] for c in criados)
    assert all(c["caminho"].endswith("_v2.md") for c in criados)
    # imagens inexistentes não têm correção → sem_mudanca
    assert any(p.endswith("imagem_inexistente.md") for p in op["resultado"]["sem_mudanca"])
    # originais intactos (SC-005)
    depois = {k: v for k, v in hash_arquivos(amostra).items() if "_v2" not in k}
    assert depois == antes
    # versão aparece logo após a origem
    lista = [a["caminho"] for a in cliente.get(f"/api/analises/{analise_id}").json()["arquivos"]]
    for c in criados:
        assert lista.index(c["caminho"]) == lista.index(c["origem"]) + 1
    evs = eventos(cliente, op["id"])
    assert any(e == "arquivo" and d["depois_de"] for e, d in evs)


def test_corrigir_selecionados_e_validacao(cliente, amostra):
    analise_id, _ = analisar(cliente, amostra)
    md = os.path.realpath(os.path.join(amostra, "links.md"))
    r = cliente.post("/api/correcoes", json={"analise_id": analise_id, "caminhos": [md]})
    op = esperar(cliente, r.json()["operacao_id"])
    assert len(op["resultado"]["criados"]) == 1
    r = cliente.post("/api/correcoes", json={"analise_id": analise_id, "caminhos": []})
    assert r.status_code == 400


def test_arquivo_alterado_e_reanalisado(cliente, amostra):
    analise_id, _ = analisar(cliente, amostra)
    md = os.path.realpath(os.path.join(amostra, "ok.md"))
    time.sleep(0.05)
    with open(md, "a", encoding="utf-8") as f:
        f.write("\nNovo ~~riscado~~.\n")
    os.utime(md, (time.time() + 5, time.time() + 5))
    r = cliente.post("/api/correcoes", json={"analise_id": analise_id, "caminhos": [md]})
    op = esperar(cliente, r.json()["operacao_id"])
    assert len(op["resultado"]["criados"]) == 1
    atual = cliente.get(f"/api/analises/{analise_id}/arquivo", params={"caminho": md}).json()
    assert atual["avisos"] == 1


def test_relatorio(cliente, amostra, tmp_path):
    analise_id, _ = analisar(cliente, amostra)
    destino = str(tmp_path / "rel.md")
    r = cliente.post("/api/relatorios", json={"analise_id": analise_id, "destino": destino})
    assert r.status_code == 200 and r.json()["caminho"] == destino
    texto = open(destino, encoding="utf-8").read()
    assert "# Análise de arquivos Markdown para o Word" in texto and "riscado.md" in texto


def test_analise_desconhecida_404(cliente):
    assert cliente.get("/api/analises/naoexiste").status_code == 404


def test_relatorio_nao_vira_documento(cliente, amostra, monkeypatch):
    """FR-030: relatório fica fora da lista e só pode ser aberto (nunca virar Word)."""
    from gera_md.web import rotas_analise
    rel = os.path.realpath(os.path.join(amostra, "ok_v3_revisao.md"))
    with open(rel, "w", encoding="utf-8") as f:
        f.write("# Revisão de texto — ok.md\n\n- [Vício de linguagem] \"a\" → \"b\"\n")
    analise_id, _ = analisar(cliente, amostra)
    rotulos = [a["rotulo"] for a in cliente.get(f"/api/analises/{analise_id}").json()["arquivos"]]
    assert "ok_v3_revisao.md" not in rotulos
    for url, corpo in (("/api/word", {"caminho": rel}),
                       ("/api/correcoes", {"caminhos": [rel]}),
                       ("/api/revisoes/previa", {"caminhos": [rel]})):
        r = cliente.post(url, json={"analise_id": analise_id, **corpo})
        assert r.status_code == 400 and "Relatório" in r.json()["erro"], (url, r.text)
    abertos = []
    monkeypatch.setattr(rotas_analise, "abrir_no_sistema", abertos.append)
    assert cliente.post("/api/abrir", json={"analise_id": analise_id, "caminho": rel}).status_code == 200
    assert abertos == [rel]
