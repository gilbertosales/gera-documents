# -*- coding: utf-8 -*-
"""Versões nome_vN.md: o original nunca é sobrescrito (constituição I)."""

import os
import re


def proxima_versao(md_path):
    """nome.md → nome_v2.md; se já existir (ou o arquivo já for _vN), usa o
    próximo número livre — nunca sobrescreve nada."""
    base, ext = os.path.splitext(md_path)
    m = re.match(r"^(.*)_v(\d+)$", base)
    n = int(m.group(2)) + 1 if m else 2
    base = m.group(1) if m else base
    while os.path.exists(f"{base}_v{n}{ext}"):
        n += 1
    return f"{base}_v{n}{ext}"


def numero_versao(path):
    """2 para nome_v2.md; None para um original."""
    m = re.search(r"_v(\d+)$", os.path.splitext(path)[0])
    return int(m.group(1)) if m else None


def gravar_nova_versao(md_path, texto):
    """Grava `texto` no próximo nome_vN livre e retorna o caminho. A criação é
    exclusiva: se outra operação pegar o mesmo número, tenta o seguinte."""
    while True:
        destino = proxima_versao(md_path)
        try:
            with open(destino, "x", encoding="utf-8", newline="\n") as f:
                f.write(texto)
            return destino
        except FileExistsError:
            continue
