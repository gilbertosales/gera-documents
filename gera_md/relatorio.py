# -*- coding: utf-8 -*-
"""Relatório .md da análise de uma pasta (movido de analisar_md.py)."""

import os
from datetime import datetime

from .analise import contar


def _rel(md, pasta):
    """Caminho relativo com "/" para o relatório ser igual no Windows e no Linux."""
    return os.path.relpath(md, pasta).replace(os.sep, "/")


def escrever_relatorio(pasta, resultados, saida):
    """resultados: lista de (caminho .md, achados)."""
    tot_e = sum(contar(a)[0] for _, a in resultados)
    tot_w = sum(contar(a)[1] for _, a in resultados)
    out = [
        "# Análise de arquivos Markdown para o Word",
        "",
        f"**Pasta:** `{pasta}`  ",
        f"**Data:** {datetime.now():%d/%m/%Y %H:%M}  ",
        f"**Arquivos:** {len(resultados)} · **Erros:** {tot_e} · **Avisos:** {tot_w}",
        "",
        "## Resumo",
        "",
        "| Arquivo | Erros | Avisos | Situação |",
        "|---|---|---|---|",
    ]
    for md, achados in resultados:
        e, w, sit = contar(achados)
        out.append(f"| {_rel(md, pasta)} | {e} | {w} | {sit} |")
    for md, achados in resultados:
        if not achados:
            continue
        out += ["", f"## {_rel(md, pasta)}", "",
                "| Nível | Linha | Problema |", "|---|---|---|"]
        for nivel, linha, msg in achados:
            out.append(f"| {nivel} | {linha or '-'} | {msg.replace('|', '/')} |")
    with open(saida, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
