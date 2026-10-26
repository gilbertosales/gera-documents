"""Correção automática: original intocado, v2 nunca pior e idempotente (constituição I e VII)."""

import os

from gera_md.analise import analisar_arquivo, contar, encontrar_mds
from gera_md.correcao import corrigir_md


def test_original_intocado_e_v2_sem_mais_erros(amostra, hash_arquivos):
    antes = hash_arquivos(amostra)
    for md in list(encontrar_mds(amostra)):
        erros_orig = contar(analisar_arquivo(md))[0]
        v2, fixes = corrigir_md(md)
        if fixes:
            assert contar(analisar_arquivo(v2))[0] <= erros_orig, md
        os.remove(v2)
    assert hash_arquivos(amostra) == antes


def test_idempotente(amostra):
    for md in list(encontrar_mds(amostra)):
        v2, fixes = corrigir_md(md)
        if not fixes:
            os.remove(v2)
            continue
        v3, fixes2 = corrigir_md(v2)
        os.remove(v3)
        # a única correção que pode reaparecer é a de título, se o v2 não tiver H1 (não ocorre)
        assert fixes2 == [], (md, fixes2)


def test_cp1252_vira_utf8(amostra):
    v2, fixes = corrigir_md(os.path.join(amostra, "cp1252.md"))
    assert any("UTF-8" in d for _, d in fixes)
    with open(v2, encoding="utf-8") as f:
        assert "coração" in f.read()


def test_versao_criada_no_proximo_numero(amostra):
    md = os.path.join(amostra, "riscado.md")
    v2, _ = corrigir_md(md)
    v2b, _ = corrigir_md(md)
    assert v2.endswith("riscado_v2.md") and v2b.endswith("riscado_v3.md")
