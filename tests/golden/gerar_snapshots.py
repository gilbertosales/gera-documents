#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Grava em tests/golden/snapshots/ a saída do analisador para a amostra.

Gerado uma vez com o analisar_md.py ANTERIOR à extração do núcleo gera_md/;
test_golden.py compara o núcleo novo com esses arquivos (SC-003). Só rode de
novo quando uma mudança de regra for intencional.
"""

import json
import os
import re
import shutil
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
AMOSTRA = os.path.join(RAIZ, "tests", "fixtures", "amostra")
SNAPSHOTS = os.path.join(AQUI, "snapshots")


def normalizar_relatorio(texto, pasta):
    texto = re.sub(r"^\*\*Data:\*\* .*$", "**Data:** <DATA>  ", texto, flags=re.M)
    return texto.replace(pasta, "<PASTA>")


def coletar(analisar_arquivo, corrigir_md, encontrar_mds, escrever_relatorio, pasta):
    """Snapshot da pasta: {rel: {achados, correcoes, v2}} e o relatório normalizado.
    Não depende de onde as funções vêm (código antigo ou gera_md)."""
    originais = list(encontrar_mds(pasta))
    resultados, dados = [], {}
    for md in originais:
        rel = os.path.relpath(md, pasta).replace("\\", "/")
        achados = analisar_arquivo(md)
        resultados.append((md, achados))
        v2, fixes = corrigir_md(md)
        with open(v2, encoding="utf-8") as f:
            conteudo = f.read()
        os.remove(v2)
        dados[rel] = {
            "achados": [list(a) for a in achados],
            "correcoes": [list(c) for c in fixes],
            "v2": conteudo if fixes else None,
        }
    saida = os.path.join(tempfile.mkdtemp(), "relatorio.md")
    escrever_relatorio(pasta, resultados, saida)
    with open(saida, encoding="utf-8") as f:
        relatorio = normalizar_relatorio(f.read(), pasta)
    shutil.rmtree(os.path.dirname(saida))
    return dados, relatorio


def main():
    sys.path.insert(0, RAIZ)
    import analisar_md as am

    pasta = os.path.join(tempfile.mkdtemp(), "amostra")
    shutil.copytree(AMOSTRA, pasta)
    try:
        dados, relatorio = coletar(am.analisar_arquivo, am.corrigir_md, am.encontrar_mds,
                                   am.escrever_relatorio, pasta)
    finally:
        shutil.rmtree(os.path.dirname(pasta))
    os.makedirs(SNAPSHOTS, exist_ok=True)
    with open(os.path.join(SNAPSHOTS, "arquivos.json"), "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1, sort_keys=True)
    with open(os.path.join(SNAPSHOTS, "relatorio.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(relatorio)
    print(f"{len(dados)} arquivo(s) gravados em {SNAPSHOTS}")


if __name__ == "__main__":
    main()
