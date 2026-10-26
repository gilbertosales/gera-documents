"""O núcleo gera_md/ produz exatamente o que o analisar_md.py antigo produzia (SC-003)."""

import json
import os
import shutil

import pytest

from gera_md import analise
from gera_md.analise import analisar_arquivo, encontrar_mds
from gera_md.correcao import corrigir_md
from gera_md.relatorio import escrever_relatorio
from tests.golden.gerar_snapshots import SNAPSHOTS, coletar


@pytest.fixture(autouse=True)
def _npx_presente(monkeypatch):
    # Os snapshots foram gravados numa máquina com Node.js; fixa o resultado do Mermaid.
    real = shutil.which
    monkeypatch.setattr(analise.shutil, "which",
                        lambda nome, *a, **k: "npx" if nome == "npx" else real(nome, *a, **k))


def _esperado():
    with open(os.path.join(SNAPSHOTS, "arquivos.json"), encoding="utf-8") as f:
        dados = json.load(f)
    with open(os.path.join(SNAPSHOTS, "relatorio.md"), encoding="utf-8") as f:
        return dados, f.read()


def test_nucleo_igual_aos_snapshots(amostra):
    dados_esp, rel_esp = _esperado()
    dados, rel = coletar(analisar_arquivo, corrigir_md, encontrar_mds, escrever_relatorio, amostra)
    assert sorted(dados) == sorted(dados_esp)
    for nome in dados_esp:
        assert dados[nome] == dados_esp[nome], nome
    assert rel == rel_esp


def test_analisar_md_reexporta_o_nucleo():
    import analisar_md
    assert analisar_md.analisar_arquivo is analisar_arquivo
    assert analisar_md.corrigir_md is corrigir_md
    assert analisar_md.escrever_relatorio is escrever_relatorio
