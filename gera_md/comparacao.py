# -*- coding: utf-8 -*-
"""Diferença entre duas versões de um .md, em blocos para a tela de comparação."""

import difflib

_TIPOS = {"equal": "igual", "insert": "inserido", "delete": "removido", "replace": "alterado"}


def _ler(caminho):
    try:
        with open(caminho, encoding="utf-8") as f:
            return f.read().splitlines()
    except UnicodeDecodeError:
        with open(caminho, encoding="cp1252", errors="replace") as f:
            return f.read().splitlines()


def comparar_linhas(a, b):
    """Blocos {tipo, a: [ini, fim], b: [ini, fim], linhas_a, linhas_b} (linhas a partir de 1,
    fim exclusivo)."""
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return [{"tipo": _TIPOS[op], "a": [i1 + 1, i2 + 1], "b": [j1 + 1, j2 + 1],
             "linhas_a": a[i1:i2], "linhas_b": b[j1:j2]}
            for op, i1, i2, j1, j2 in sm.get_opcodes()]


def comparar(caminho_a, caminho_b):
    return comparar_linhas(_ler(caminho_a), _ler(caminho_b))
