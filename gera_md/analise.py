# -*- coding: utf-8 -*-
"""Análise de .md para conversão com gerar_word.py (movido de analisar_md.py).

As regras são as mesmas do gerar_word.py (constituição II): qualquer mudança aqui
precisa refletir o que o conversor faz e atualizar tests/golden.

Níveis:
    ERRO   → conteúdo some ou aparece quebrado no Word
    AVISO  → aparece como texto literal (ex.: [link](url), ~~riscado~~)
    INFO   → funciona, mas vale saber
"""

import os
import re
import shutil

from gerar_word import is_separator, parse_table_row, titulo_do_md

from .modelos import TAM_TRECHO_ACHADO, Achado, ResultadoArquivo
from .versoes import numero_versao

PASTAS_IGNORADAS = {"node_modules", "venv", "__pycache__"}

# HTML que o gerar_word.py trata: âncora <a id="..."></a> (ignorada) e <br> em tabela
_ANCORA = re.compile(r'^<a\s+id="[^"]*"\s*>\s*</a>$', re.IGNORECASE)
_HTML_TAG = re.compile(r"</?[a-zA-Z][a-zA-Z0-9]*(\s[^<>]*)?/?>")
_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_LINK = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)\s]*)[^)]*\)")
_IMG = re.compile(r"!\[[^\]]*\]\([^)]+\)")
_ITEM_LISTA = re.compile(r"^[ \t]*([-*+]|\d+[.)]) ")
_H1 = re.compile(r"^# (?!#)")


def _sem_codigo_inline(texto):
    return re.sub(r"`[^`]*`", "", texto)


def _fora_do_codigo(texto, fn):
    """Aplica fn só aos trechos fora de `código inline`."""
    partes = re.split(r"(`[^`]*`)", texto)
    return "".join(p if i % 2 else fn(p) for i, p in enumerate(partes))


# ── Análise ───────────────────────────────────────────────────────────────────

def analisar_arquivo(md_path):
    """Retorna lista de (nível, linha, mensagem) para um .md."""
    achados = []

    def add(nivel, linha, msg):
        achados.append((nivel, linha, msg))

    try:
        with open(md_path, encoding="utf-8") as f:
            linhas = f.read().splitlines()
    except UnicodeDecodeError:
        add("ERRO", 0, "Arquivo não está em UTF-8 — o gerar_word.py falha ao ler.")
        return achados
    except OSError as exc:
        add("ERRO", 0, f"Não foi possível ler o arquivo ({exc}).")
        return achados

    md_dir = os.path.dirname(md_path)

    if not any(_H1.match(l.strip()) for l in linhas):
        add("INFO", 0, f'Sem título "# ..." — a tela do gerar_word vai sugerir '
                       f'"{titulo_do_md(md_path)}" como nome do relatório.')

    em_codigo = False
    abertura_codigo = 0
    tabela = []  # [(nº linha, células)]

    def fechar_tabela():
        if not tabela:
            return
        n_ini, cab = tabela[0]
        if len(tabela) < 2 or not is_separator(tabela[1][1]):
            add("AVISO", n_ini, "Tabela sem a linha separadora (|---|---|) após o cabeçalho.")
        for n, cel in tabela[1:]:
            if is_separator(cel):
                continue
            if len(cel) != len(cab):
                add("ERRO", n, f"Linha da tabela com {len(cel)} colunas, cabeçalho tem "
                               f"{len(cab)} — células ficam desalinhadas/vazias no Word.")
        for n, cel in tabela:
            if any(_BR.search(c) for c in cel):
                add("AVISO", n, "<br> dentro de célula aparece como texto literal no Word.")
        tabela.clear()

    for n, linha in enumerate(linhas, 1):
        s = linha.strip()

        # ── Blocos de código: nada dentro deles é analisado ──────────────────
        if s.startswith("```"):
            fechar_tabela()
            if not em_codigo:
                em_codigo, abertura_codigo = True, n
                if s[3:].strip().lower() == "mermaid" and not shutil.which("npx"):
                    add("AVISO", n, "Diagrama Mermaid, mas o npx (Node.js) não foi "
                                    "encontrado — no Word sai como código em texto.")
            else:
                em_codigo = False
            continue
        if em_codigo:
            continue

        if s.startswith("|"):
            tabela.append((n, parse_table_row(s)))
            continue
        fechar_tabela()

        if not s:
            continue

        # ── Títulos ───────────────────────────────────────────────────────
        if re.match(r"^#{6,} ", s):
            add("AVISO", n, "Título ###### (nível 6) não é suportado — sai como texto com os #.")
        elif re.match(r"^#{2,5}[^# ]", s):
            add("AVISO", n, 'Título sem espaço após o # (ex.: "##Título") — sai como texto.')

        # ── Listas ────────────────────────────────────────────────────────
        if _ITEM_LISTA.match(linha):
            recuo = linha[: len(linha) - len(linha.lstrip(" \t"))]
            if "\t" in recuo:
                add("ERRO", n, "Item de lista recuado com TAB não é reconhecido.")
            elif len(recuo) >= 4:
                add("ERRO", n, "Sublista com 4+ espaços de recuo é colada no texto do item anterior.")
            corpo = linha.lstrip(" \t")
            if corpo.startswith("+ "):
                add("ERRO", n, 'Marcador "+" não é reconhecido — é colado no item anterior.')
            if re.match(r"^\d+\) ", corpo):
                add("ERRO", n, 'Lista numerada com "1)" não é reconhecida — o certo é "1."')
            if re.match(r"^[-*+] \[[ xX]\] ", corpo):
                add("AVISO", n, "Checklist ([ ] / [x]) sai com os colchetes como texto.")

        # ── Citação com conteúdo de bloco ─────────────────────────────────
        if re.match(r"^>\s*([-*+] |\d+[.)] |#{1,6} )", s):
            add("AVISO", n, "Lista/título dentro de citação (>) sai como texto literal.")

        # ── Imagens ───────────────────────────────────────────────────────
        img = re.match(r"^!\[[^\]]*\]\(([^)]+)\)", s)
        if img:
            alvo = img.group(1).strip().split(" ")[0].strip("<>")
            if re.match(r"^https?://", alvo, re.IGNORECASE):
                add("ERRO", n, f"Imagem da internet ({alvo}) não é baixada — salve a imagem "
                               "na pasta e aponte para o arquivo local.")
            elif not os.path.exists(os.path.join(md_dir, alvo)):
                add("ERRO", n, f"Imagem não encontrada: {alvo}")
            if s[img.end():].strip():
                add("AVISO", n, "Texto depois da imagem na mesma linha é descartado.")
        elif _IMG.search(_sem_codigo_inline(s)):
            add("ERRO", n, "Imagem no meio do texto não é inserida — sai como texto.")

        # ── Formatação inline não suportada ───────────────────────────────
        texto = _sem_codigo_inline(s)
        if _LINK.search(texto):
            add("AVISO", n, "Link [texto](url) sai literal, com colchetes e URL.")
        if "~~" in texto:
            add("AVISO", n, "~~riscado~~ não é suportado — sai com os ~~.")
        if re.search(r"(?<![\w_])__[^_]+__(?![\w_])", texto):
            add("AVISO", n, "__negrito__ com sublinhado não é suportado — o certo é **negrito**.")
        if re.search(r"(?<![\w_])_[^_\s][^_]*_(?![\w_])", texto):
            add("AVISO", n, "_itálico_ com sublinhado não é suportado — o certo é *itálico*.")
        if not _ANCORA.match(s):
            tag = _HTML_TAG.search(texto)
            if tag:
                add("AVISO", n, f"HTML ({tag.group(0)[:30]}) sai como texto literal.")
        if re.search(r"\[\^[^\]]+\]", texto):
            add("AVISO", n, "Nota de rodapé [^n] não é suportada — sai como texto.")

    fechar_tabela()
    if em_codigo:
        add("ERRO", abertura_codigo, "Bloco de código ``` aberto e nunca fechado — todo o "
                                     "resto do documento vira código.")

    ordem = {"ERRO": 0, "AVISO": 1, "INFO": 2}
    achados.sort(key=lambda a: (ordem[a[0]], a[1]))
    return achados


def contar(achados):
    e = sum(1 for a in achados if a[0] == "ERRO")
    w = sum(1 for a in achados if a[0] == "AVISO")
    return e, w, ("Corrigir" if e else ("Revisar" if w else "OK"))


def analisar(md_path, pasta_base=None, origem=None, tipo_versao="original"):
    """analisar_arquivo + trecho de cada linha, como ResultadoArquivo."""
    achados = analisar_arquivo(md_path)
    try:
        with open(md_path, encoding="utf-8") as f:
            linhas = f.read().splitlines()
    except (UnicodeDecodeError, OSError):
        linhas = []
    try:
        rotulo = os.path.relpath(md_path, pasta_base) if pasta_base else md_path
    except ValueError:  # outra unidade no Windows
        rotulo = md_path
    try:
        mtime = os.path.getmtime(md_path)
    except OSError:
        mtime = 0.0
    lista = []
    for nivel, n, msg in achados:
        trecho = linhas[n - 1][:TAM_TRECHO_ACHADO] if 0 < n <= len(linhas) else None
        lista.append(Achado(nivel, n, msg, trecho))
    return ResultadoArquivo(caminho=md_path, rotulo=rotulo, achados=lista,
                            versao=numero_versao(md_path), origem=origem,
                            tipo_versao=tipo_versao, modificado_em=mtime)


# ── Busca ─────────────────────────────────────────────────────────────────────


_RELATORIO = re.compile(r"(_revisao(_\d+)?\.md|^relatorio_analise_md\.md)$", re.IGNORECASE)


def eh_relatorio(caminho):
    """Relatório gerado pela ferramenta (*_revisao.md, *_revisao_N.md ou
    relatorio_analise_md.md): não é documento — não entra na busca nem vira Word (FR-030)."""
    return bool(_RELATORIO.search(os.path.basename(caminho)))


def encontrar_mds(pasta, recursivo=True, cancelar=None, onerror=None):
    """onerror(OSError) recebe pastas que não puderam ser lidas (ex.: rede caiu).
    Relatórios da ferramenta (eh_relatorio) são ignorados."""
    for raiz, dirs, arquivos in os.walk(pasta, onerror=onerror):
        if cancelar is not None and cancelar.is_set():
            return
        if not recursivo:
            dirs[:] = []
        else:
            dirs[:] = sorted(d for d in dirs if d not in PASTAS_IGNORADAS and not d.startswith("."))
        for nome in sorted(arquivos):
            if cancelar is not None and cancelar.is_set():
                return
            if nome.lower().endswith((".md", ".markdown")) and not eh_relatorio(nome):
                yield os.path.join(raiz, nome)
