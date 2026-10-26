# -*- coding: utf-8 -*-
"""Correção automática: grava nome_v2.md (movido de analisar_md.py).

O original nunca é alterado; a gravação usa versoes.gravar_nova_versao.
"""

import os
import re

from gerar_word import is_separator, parse_table_row

from .analise import _ANCORA, _BR, _H1, _HTML_TAG, _IMG, _ITEM_LISTA, _LINK, _fora_do_codigo, _sem_codigo_inline
from .versoes import gravar_nova_versao, proxima_versao  # noqa: F401 — proxima_versao reexportada


def _corrigir_inline(texto, registrar, n):
    """Corrige a formatação inline fora de `código`. Retorna o texto novo."""

    def fn(t):
        orig = t
        # [texto](#ancora) → texto ; [texto](url) → texto (url)
        t = _LINK.sub(
            lambda m: m.group(1) if (not m.group(2) or m.group(2).startswith("#")
                                     or m.group(2) == m.group(1))
            else f"{m.group(1)} ({m.group(2)})",
            t,
        )
        if t != orig:
            registrar(n, "Link [texto](url) convertido para texto (url).")
        antes = t
        t = re.sub(r"~~(.+?)~~", r"\1", t)
        if t != antes:
            registrar(n, "~~riscado~~ removido (mantido o texto).")
        antes = t
        t = re.sub(r"(?<![\w_])__([^_]+)__(?![\w_])", r"**\1**", t)
        t = re.sub(r"(?<![\w_*])_([^_\s][^_]*)_(?![\w_*])", r"*\1*", t)
        if t != antes:
            registrar(n, "__negrito__/_itálico_ convertidos para **negrito**/*itálico*.")
        antes = t
        t = _BR.sub(" ", t)
        t = _HTML_TAG.sub("", t)
        if t != antes:
            registrar(n, "Tags HTML removidas (mantido o texto).")
        return t

    return _fora_do_codigo(texto, fn)


def _titulo_pelo_nome(md_path):
    return os.path.splitext(os.path.basename(md_path))[0].replace("-", " ").replace("_", " ")


def corrigir_md(md_path):
    """Grava a versão corrigida (nome_v2.md) e retorna (caminho_v2, correções),
    onde correções é uma lista de (linha original, descrição)."""
    correcoes = []

    def registrar(n, msg):
        if (n, msg) not in correcoes:
            correcoes.append((n, msg))

    try:
        with open(md_path, encoding="utf-8") as f:
            texto = f.read()
    except UnicodeDecodeError:
        with open(md_path, encoding="cp1252", errors="replace") as f:
            texto = f.read()
        registrar(0, "Arquivo convertido para UTF-8.")

    linhas = texto.splitlines()
    out = []

    if not any(_H1.match(l.strip()) for l in linhas):
        out += [f"# {_titulo_pelo_nome(md_path)}", ""]
        registrar(0, 'Título "# ..." adicionado a partir do nome do arquivo.')

    em_codigo = False
    tabela = []  # [(nº linha, texto da linha)]

    def fechar_tabela():
        if not tabela:
            return
        n0, l0 = tabela[0]
        cab = [_corrigir_inline(_BR.sub("; ", c), registrar, n0)
               for c in parse_table_row(l0.strip())]
        ncols = len(cab)
        linhas_tab = [(n0, l0, cab)]
        tem_sep = len(tabela) > 1 and is_separator(parse_table_row(tabela[1][1].strip()))
        if not tem_sep:
            registrar(n0, "Linha separadora |---| adicionada após o cabeçalho da tabela.")
        for n, l in tabela[1:]:
            cel = parse_table_row(l.strip())
            if is_separator(cel):
                if len(cel) != ncols:
                    linhas_tab.append((n, "|" + "---|" * ncols, None))
                else:
                    linhas_tab.append((n, l, None))
                continue
            novas = []
            for c in cel:
                c2 = _BR.sub("; ", c)
                if c2 != c:
                    registrar(n, "<br> da célula trocado por \"; \".")
                novas.append(_corrigir_inline(c2, registrar, n))
            if len(novas) > ncols:
                extras = novas[ncols:]
                if all(not x for x in extras):
                    novas = novas[:ncols]
                else:
                    novas = novas[: ncols - 1] + [" ".join(x for x in novas[ncols - 1:] if x)]
                registrar(n, "Colunas a mais na linha da tabela foram ajustadas ao cabeçalho.")
            elif len(novas) < ncols:
                novas += [""] * (ncols - len(novas))
                registrar(n, "Colunas faltando na linha da tabela foram completadas.")
            linhas_tab.append((n, l, novas))

        for idx, (n, l, cel) in enumerate(linhas_tab):
            if cel is not None and cel != parse_table_row(l.strip()):
                l = "| " + " | ".join(cel) + " |"
            out.append(l)
            if idx == 0 and not tem_sep:
                out.append("|" + "---|" * ncols)
        tabela.clear()

    for n, linha in enumerate(linhas, 1):
        s = linha.strip()

        if s.startswith("```"):
            fechar_tabela()
            em_codigo = not em_codigo
            out.append(linha)
            continue
        if em_codigo:
            out.append(linha)
            continue
        if s.startswith("|"):
            tabela.append((n, linha))
            continue
        fechar_tabela()

        if not s or _ANCORA.match(s):
            out.append(linha)
            continue

        nova = linha

        # ── Títulos nível 6+ → nível 5 ────────────────────────────────────
        if re.match(r"^\s*#{6,} ", nova):
            nova = "##### " + re.sub(r"^\s*#{6,} ", "", nova)
            registrar(n, "Título ###### rebaixado para #####.")

        # ── Listas ────────────────────────────────────────────────────────
        if _ITEM_LISTA.match(nova):
            recuo = nova[: len(nova) - len(nova.lstrip(" \t"))]
            corpo = nova.lstrip(" \t")
            larg = len(recuo.expandtabs(4))
            if "\t" in recuo:
                registrar(n, "Recuo com TAB na lista trocado por espaços.")
            if larg >= 4:
                larg = 3
                registrar(n, "Sublista com 4+ espaços ajustada para 3 espaços "
                             "(vira item próprio no Word).")
            if corpo.startswith("+ "):
                corpo = "- " + corpo[2:]
                registrar(n, 'Marcador "+" trocado por "-".')
            m = re.match(r"^(\d+)\) ", corpo)
            if m:
                corpo = f"{m.group(1)}. " + corpo[m.end():]
                registrar(n, 'Numeração "1)" trocada por "1."')
            m = re.match(r"^([-*]) \[([ xX])\] ", corpo)
            if m:
                marca = "☑" if m.group(2) in "xX" else "☐"
                corpo = f"{m.group(1)} {marca} " + corpo[m.end():]
                registrar(n, "Checklist [ ]/[x] trocado por ☐/☑.")
            nova = " " * larg + corpo

        # ── Lista/título dentro de citação ────────────────────────────────
        m = re.match(r"^(\s*>\s*)([-*+]|\d+[.)]|#{1,6}) (.*)$", nova)
        if m:
            marca, resto = m.group(2), m.group(3)
            if marca.startswith("#"):
                nova = f"> **{resto}**"
            elif marca[0].isdigit():
                nova = f"> {marca.rstrip('.)')}. {resto}"
            else:
                nova = f"> • {resto}"
            # `>` vazio antes do item: cada item vira um parágrafo da citação
            if out and re.match(r"^\s*>\s*\S", out[-1]):
                out.append(">")
            registrar(n, "Lista/título dentro de citação convertido para texto (• item).")

        # ── Imagem no meio do texto / texto após imagem → linhas separadas ─
        s2 = nova.strip()
        tem_img = _IMG.search(_sem_codigo_inline(s2))
        if tem_img and not (_IMG.fullmatch(s2)):
            partes = [p for p in re.split(r"(!\[[^\]]*\]\([^)]+\))", nova) if p.strip()]
            for i, p in enumerate(partes):
                if _IMG.fullmatch(p.strip()):
                    if out and out[-1].strip():
                        out.append("")
                    out += [p.strip(), ""]
                else:
                    # 1º trecho mantém o recuo/marcador de lista; os demais começam limpos
                    p = p.rstrip() if i == 0 else p.strip()
                    out.append(_corrigir_inline(p, registrar, n))
            registrar(n, "Imagem colocada sozinha numa linha (antes saía como texto).")
            continue

        if not _IMG.fullmatch(s2):
            nova = _corrigir_inline(nova, registrar, n)
            if not nova.strip() and s:
                registrar(n, "Linha só com HTML removida.")
        out.append(nova)

    fechar_tabela()
    if em_codigo:
        out.append("```")
        registrar(len(linhas), "Bloco de código ``` sem fechamento — fechado no fim do arquivo.")


    destino = gravar_nova_versao(md_path, "\n".join(out) + "\n")
    correcoes.sort(key=lambda c: c[0])
    return destino, correcoes
