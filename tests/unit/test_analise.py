"""Regras do analisador: um caso positivo e um negativo por regra (constituição VII)."""

import os
import threading

import pytest

from gera_md import analise
from gera_md.analise import analisar, analisar_arquivo, encontrar_mds


def _achados(tmp_path, texto, nome="doc.md", com_h1=True):
    p = tmp_path / nome
    p.write_text(("# Título\n\n" if com_h1 else "") + texto, encoding="utf-8")
    return analisar_arquivo(str(p))


def _tem(achados, nivel, trecho):
    return any(a[0] == nivel and trecho in a[2] for a in achados)


# (nivel, trecho da mensagem, md que dispara, md correto equivalente)
REGRAS = [
    ("AVISO", "sem a linha separadora", "| A | B |\n| 1 | 2 |\n", "| A | B |\n|---|---|\n| 1 | 2 |\n"),
    ("ERRO", "colunas, cabeçalho tem", "| A | B |\n|---|---|\n| 1 | 2 | 3 |\n", "| A | B |\n|---|---|\n| 1 | 2 |\n"),
    ("AVISO", "<br> dentro de célula", "| A |\n|---|\n| a<br>b |\n", "| A |\n|---|\n| a; b |\n"),
    ("AVISO", "nível 6", "###### Seis\n", "##### Cinco\n"),
    ("AVISO", "sem espaço após o #", "##Título\n", "## Título\n"),
    ("ERRO", "recuado com TAB", "- a\n\t- b\n", "- a\n   - b\n"),
    ("ERRO", "4+ espaços", "- a\n    - b\n", "- a\n   - b\n"),
    ("ERRO", 'Marcador "+"', "+ item\n", "- item\n"),
    ("ERRO", '"1)"', "1) item\n", "1. item\n"),
    ("AVISO", "Checklist", "- [ ] tarefa\n", "- tarefa\n"),
    ("AVISO", "dentro de citação", "> - item\n", "> item\n"),
    ("ERRO", "Imagem da internet", "![x](https://a.com/x.png)\n", None),
    ("ERRO", "Imagem não encontrada", "![x](nao_existe.png)\n", None),
    ("AVISO", "Texto depois da imagem", "![x](img.png) legenda\n", "![x](img.png)\n"),
    ("ERRO", "Imagem no meio do texto", "veja ![x](img.png) aqui\n", "veja `![x](img.png)` aqui\n"),
    ("AVISO", "Link [texto](url)", "[a](https://b.com)\n", "a (https://b.com)\n"),
    ("AVISO", "~~riscado~~", "~~x~~\n", "x\n"),
    ("AVISO", "__negrito__", "a __b__ c\n", "a **b** c\n"),
    ("AVISO", "_itálico_", "a _b_ c\n", "a *b* c\n"),
    ("AVISO", "HTML (", "a <span>b</span>\n", '<a id="x"></a>\n'),
    ("AVISO", "Nota de rodapé", "a[^1]\n", "a\n"),
    ("ERRO", "aberto e nunca fechado", "```\ncódigo\n", "```\ncódigo\n```\n"),
]


@pytest.mark.parametrize("nivel,msg,ruim,bom", REGRAS, ids=[r[1] for r in REGRAS])
def test_regra(tmp_path, nivel, msg, ruim, bom):
    (tmp_path / "img.png").write_bytes(b"png")
    assert _tem(_achados(tmp_path, ruim), nivel, msg)
    if bom is not None:
        assert not _tem(_achados(tmp_path, bom, "bom.md"), nivel, msg)


def test_imagem_local_existente_nao_gera_erro(tmp_path):
    (tmp_path / "img.png").write_bytes(b"png")
    assert _achados(tmp_path, "![x](img.png)\n") == []


def test_sem_h1_info(tmp_path):
    assert _tem(_achados(tmp_path, "## Sub\n", com_h1=False), "INFO", "Sem título")
    assert not _tem(_achados(tmp_path, "## Sub\n"), "INFO", "Sem título")


def test_mermaid_sem_npx(tmp_path, monkeypatch):
    monkeypatch.setattr(analise.shutil, "which", lambda *_a, **_k: None)
    assert _tem(_achados(tmp_path, "```mermaid\nA-->B\n```\n"), "AVISO", "Mermaid")
    monkeypatch.setattr(analise.shutil, "which", lambda *_a, **_k: "npx")
    assert not _tem(_achados(tmp_path, "```mermaid\nA-->B\n```\n"), "AVISO", "Mermaid")


def test_codigo_nao_e_analisado(tmp_path):
    assert _achados(tmp_path, "```\n~~x~~ [a](b) <span>\n```\n") == []


def test_arquivo_nao_utf8(tmp_path):
    p = tmp_path / "x.md"
    p.write_bytes("# Ação\n".encode("cp1252"))
    assert _tem(analisar_arquivo(str(p)), "ERRO", "UTF-8")


def test_analisar_preenche_trecho_e_situacao(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("# T\n\nTexto ~~velho~~.\n", encoding="utf-8")
    r = analisar(str(p), str(tmp_path))
    assert r.rotulo == "x.md" and r.situacao == "Revisar" and r.avisos == 1
    assert r.achados[0].linha == 3 and r.achados[0].trecho == "Texto ~~velho~~."
    assert r.to_dict()["situacao"] == "Revisar"


def test_encontrar_ignora_pastas(amostra):
    rel = {os.path.relpath(p, amostra).replace("\\", "/") for p in encontrar_mds(amostra)}
    assert "sub/interno.md" in rel
    assert not any(r.startswith(("node_modules", ".oculta")) for r in rel)
    sem_sub = {os.path.relpath(p, amostra) for p in encontrar_mds(amostra, recursivo=False)}
    assert all(os.sep not in r for r in sem_sub)


def test_encontrar_para_ao_cancelar(amostra):
    ev = threading.Event()
    achados = []
    for p in encontrar_mds(amostra, cancelar=ev):
        achados.append(p)
        ev.set()
    assert len(achados) == 1


def test_relatorios_nao_entram_na_busca(tmp_path):
    """FR-030: relatórios gerados pela ferramenta não são documentos."""
    from gera_md.analise import eh_relatorio
    relatorios = ["x_revisao.md", "x_v3_revisao.md", "x_revisao_2.md", "relatorio_analise_md.md",
                  "Y_V2_REVISAO.MD"]
    documentos = ["revisao.md", "minha_revisao_geral.md", "x_v3.md", "relatorio.md"]
    for nome in relatorios + documentos:
        (tmp_path / nome).write_text("# T\n", encoding="utf-8")
    achados = {os.path.basename(p) for p in encontrar_mds(str(tmp_path))}
    assert achados == set(documentos)
    assert all(eh_relatorio(str(tmp_path / n)) for n in relatorios)
    assert not any(eh_relatorio(str(tmp_path / n)) for n in documentos)
