#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_word.py
=============
Converte qualquer arquivo Markdown para DOCX usando um template Word (.dotx/.docx).

Uso:
    python gerar_word.py                 → abre a tela para escolher o .md
    python gerar_word.py relatorio.md    → abre a tela já com o .md preenchido

    Na tela, informe o arquivo .md, o título do relatório (sugerido a partir
    do H1 do Markdown), subtítulo, versão, rodapé, template e o .docx de saída,
    e clique em "Gerar Word". Os últimos valores usados (template, subtítulo,
    rodapé...) ficam salvos em gerar_word_config.json, ao lado do script.

Dependências:
    pip install python-docx

Compatibilidade:
    - Windows / Linux / Mac
    - Python 3.10+

Notas:
    - O script abre o template .dotx corrigindo o content-type internamente
      (sem precisar renomear o arquivo manualmente).
    - O Sumário é inserido como campo TOC real do Word (atualizado ao abrir).
    - Suporta: títulos (H1–H4), parágrafos, listas, tabelas, blockquotes,
      blocos de código, negrito inline (**texto**), código inline (`texto`).
    - A seção "## Sumário" do Markdown é ignorada (substituída pelo TOC do Word).
    - O H1 do Markdown (título do documento) é ignorado pois vai na capa.
    - Marcadores de lista usam formatação nativa do Word (numPr), não caracteres
      de texto — garante que bullets e numeração fiquem idênticos ao Markdown.

Mapeamento de estilos Markdown → Word (nomes dos estilos do template corporativo):
    ##    → Ttulo1   (Heading 1)
    ###   → Ttulo2   (Heading 2)
    ####  → Ttulo3   (Heading 3)
    #####  → Ttulo4  (Heading 4)
    - item → PargrafodaLista  (List Paragraph)
    > cit  → Normal com fundo cinza e barra à esquerda (ver add_quote)
    normal → Normal

Para usar com outro template, ajuste o dicionário STYLE_MAP com os
nomes exatos dos estilos presentes no seu .dotx/.docx.
"""

import json
import re
import sys
import os
import shutil
import threading
import subprocess
import tempfile
import zipfile

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.section import WD_ORIENT, WD_SECTION_START
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.stdout.reconfigure(encoding="utf-8")

# ── Listas nativas do Word (numPr) ────────────────────────────────────────────

_list_num_ids: dict = {}  # preenchido em _ensure_list_num_ids()


def _get_numbering_part(document):
    """Retorna (ou cria) o NumberingPart do documento."""
    try:
        return document.part.numbering_part
    except (KeyError, NotImplementedError):
        # python-docx 1.x não implementa NumberingPart.new(); criamos manualmente.
        from docx.parts.numbering import NumberingPart
        from docx.opc.packuri import PackURI
        from lxml import etree

        NUMBERING_CT = (
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.numbering+xml"
        )
        NUMBERING_REL = (
            "http://schemas.openxmlformats.org/officeDocument/2006/"
            "relationships/numbering"
        )
        EMPTY_XML = (
            b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            b'<w:numbering xmlns:w="http://schemas.openxmlformats.org/'
            b'wordprocessingml/2006/main"/>'
        )
        element = etree.fromstring(EMPTY_XML)
        np = NumberingPart(
            PackURI("/word/numbering.xml"),
            NUMBERING_CT,
            element,
            document.part.package,
        )
        document.part.relate_to(np, NUMBERING_REL)
        return np


def _create_abstract_num(abstract_id: int, fmt: str) -> object:
    """Cria um elemento <w:abstractNum> com 9 níveis para bullet ou decimal."""
    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))

    mlt = OxmlElement("w:multiLevelType")
    mlt.set(qn("w:val"), "hybridMultilevel")
    abstract.append(mlt)

    for lvl_idx in range(9):
        lvl = OxmlElement("w:lvl")
        lvl.set(qn("w:ilvl"), str(lvl_idx))

        start = OxmlElement("w:start")
        start.set(qn("w:val"), "1")

        numFmt_el = OxmlElement("w:numFmt")
        numFmt_el.set(qn("w:val"), fmt)

        lvlText = OxmlElement("w:lvlText")
        if fmt == "bullet":
            lvlText.set(qn("w:val"), "\u2022")  # • só no XML, não no texto
        else:
            lvlText.set(qn("w:val"), f"%{lvl_idx + 1}.")

        lvlJc = OxmlElement("w:lvlJc")
        lvlJc.set(qn("w:val"), "left")

        pPr = OxmlElement("w:pPr")
        ind = OxmlElement("w:ind")
        ind.set(qn("w:left"), str(720 * (lvl_idx + 1)))
        ind.set(qn("w:hanging"), "360")
        pPr.append(ind)

        lvl.extend([start, numFmt_el, lvlText, lvlJc, pPr])
        abstract.append(lvl)

    return abstract


def _ensure_list_num_ids(document):
    """Garante que existam definições de bullet e lista numerada no documento."""
    global _list_num_ids
    if _list_num_ids:
        return

    try:
        np_part = _get_numbering_part(document)
        numbering = np_part._element

        existing_abstract = numbering.findall(qn("w:abstractNum"))
        existing_nums = numbering.findall(qn("w:num"))

        base_abs_id = len(existing_abstract)
        base_num_id = (
            max(int(n.get(qn("w:numId"), 0)) for n in existing_nums) + 1
            if existing_nums
            else 1
        )

        bullet_abstract = _create_abstract_num(base_abs_id, "bullet")
        number_abstract = _create_abstract_num(base_abs_id + 1, "decimal")

        # abstractNum DEVE vir antes de w:num no XML (requisito OOXML)
        first_num = numbering.find(qn("w:num"))
        if first_num is not None:
            first_num.addprevious(bullet_abstract)
            first_num.addprevious(number_abstract)
        else:
            numbering.append(bullet_abstract)
            numbering.append(number_abstract)

        for offset, (key, abs_id) in enumerate(
            [
                ("bullet", base_abs_id),
                ("number", base_abs_id + 1),
            ]
        ):
            num_id = base_num_id + offset
            num_el = OxmlElement("w:num")
            num_el.set(qn("w:numId"), str(num_id))
            abs_ref = OxmlElement("w:abstractNumId")
            abs_ref.set(qn("w:val"), str(abs_id))
            num_el.append(abs_ref)
            numbering.append(num_el)
            _list_num_ids[key] = num_id

    except Exception as exc:
        print(f"AVISO: falha ao criar definições de lista ({exc}); usando fallback.")
        _list_num_ids = {"bullet": 1, "number": 2}


def _apply_list_format(paragraph, list_type: str, level: int = 0):
    """Aplica <w:numPr> ao parágrafo para formatação nativa de lista no Word."""
    _ensure_list_num_ids(doc)
    num_id = _list_num_ids.get(list_type, 1)

    pPr = paragraph._p.get_or_add_pPr()
    existing = pPr.find(qn("w:numPr"))
    if existing is not None:
        pPr.remove(existing)

    numPr = OxmlElement("w:numPr")
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), str(level))
    numId_el = OxmlElement("w:numId")
    numId_el.set(qn("w:val"), str(num_id))
    numPr.append(ilvl)
    numPr.append(numId_el)
    pPr.insert(0, numPr)


# ── Configuração ──────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "gerar_word_config.json")

# Valores padrão da tela (os últimos usados ficam salvos em CONFIG_PATH)
DEFAULTS = {
    "template": os.path.join(SCRIPT_DIR, "modelos", "modelo_exemplo.docx"),
    "subtitulo": "",
    "versao": "Versão 1.0",
    "rodape": "Sua Empresa",
    "ultima_pasta": SCRIPT_DIR,
}

# Mapeamento Markdown → estilo Word (ajuste conforme seu template)
STYLE_MAP = {
    "title": "Title",  # capa
    "subtitle": "Subtitle",  # capa
    "h1": "Heading 1",  # ## seção
    "h2": "Heading 2",  # ### subseção
    "h3": "Heading 3",  # ####
    "h4": "Heading 4",  # #####
    "normal": "Normal",
    "list": "List Paragraph",
}

# Variáveis globais de capa (preenchidas por gerar_documento)
CAPA_TITULO = ""
CAPA_SUBTITULO = ""
CAPA_RODAPE = ""

# ── Renderização de diagramas Mermaid ─────────────────────────────────────────

_MERMAID_TMP_DIR = None


def _get_mermaid_tmp_dir():
    global _MERMAID_TMP_DIR
    if _MERMAID_TMP_DIR is None:
        _MERMAID_TMP_DIR = tempfile.mkdtemp(prefix="gerar_pdf_mermaid_")
    return _MERMAID_TMP_DIR


def _render_mermaid_to_png(mermaid_src: str):
    """Renderiza um bloco ```mermaid para PNG via @mermaid-js/mermaid-cli (npx),
    igual ao que os diagramas de arquitetura do projeto já usam. Retorna o
    caminho do PNG, ou None se a renderização falhar (ex.: sem Node/npx
    disponível) — nesse caso o chamador usa o bloco de código como texto em
    vez de travar a geração do documento inteiro."""
    tmp_dir = _get_mermaid_tmp_dir()
    idx = len([f for f in os.listdir(tmp_dir) if f.endswith(".mmd")])
    mmd_path = os.path.join(tmp_dir, f"diagram_{idx}.mmd")
    png_path = os.path.join(tmp_dir, f"diagram_{idx}.png")
    with open(mmd_path, "w", encoding="utf-8") as f:
        f.write(mermaid_src)

    cmd = ["npx", "--yes", "@mermaid-js/mermaid-cli", "-i", mmd_path, "-o", png_path,
           "-b", "white", "-w", "1800"]
    try:
        if os.name == "nt":
            # No Windows, subprocess sem shell=True não resolve npx.cmd via PATH.
            quoted = " ".join(f'"{c}"' if " " in c else c for c in cmd)
            subprocess.run(quoted, check=True, capture_output=True, timeout=120, shell=True)
        else:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        if os.path.exists(png_path):
            return png_path
    except Exception as exc:
        print(f"  AVISO: falha ao renderizar diagrama Mermaid ({exc}); usando texto substituto.")
    return None

# ── Abrir template (.dotx → corrige content-type para .docx) ─────────────────


def open_template(tmpl_path):
    """Abre .dotx corrigindo o content-type internamente."""
    tmp = tmpl_path.rsplit(".", 1)[0] + "_tmp.docx"
    with zipfile.ZipFile(tmpl_path, "r") as zin:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "[Content_Types].xml":
                    data = data.replace(
                        b"application/vnd.openxmlformats-officedocument"
                        b".wordprocessingml.template.main+xml",
                        b"application/vnd.openxmlformats-officedocument"
                        b".wordprocessingml.document.main+xml",
                    )
                zout.writestr(item, data)
    document = Document(tmp)
    os.remove(tmp)
    return document


doc = None  # documento em construção (criado por gerar_documento)

# ── Helpers de parágrafo ──────────────────────────────────────────────────────


def _pick_style(*names, fallback="Normal"):
    """Primeiro estilo da lista que existe no template — permite usar
    templates diferentes do corporativo sem quebrar por estilo inexistente."""
    by_key = {}
    for s in doc.styles:
        by_key.setdefault(s.name, s.name)
        by_key.setdefault(s.style_id, s.name)  # ex.: id "Ttulo" → nome "Title"
    for name in names:
        if name in by_key:
            return by_key[name]
    return fallback


CODE_FONT = "Consolas"
CODE_BG = "EAEDF0"  # fundo cinza do `código` inline (como no GitHub/VS Code)
QUOTE_BG = "F6F8FA"  # fundo da citação (> texto)
QUOTE_BAR = "D0D7DE"  # barra vertical à esquerda da citação


def _shade_run(run, fill):
    """Fundo colorido atrás do texto de um run (`<w:shd>` respeitando a ordem
    de elementos do OOXML, senão o Word acusa conteúdo ilegível)."""
    rPr = run._r.get_or_add_rPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    rPr.insert_element_before(
        shd, "w:fitText", "w:vertAlign", "w:rtl", "w:cs", "w:em", "w:lang",
        "w:eastAsianLayout", "w:specVanish", "w:oMath",
    )


def add_inline(para, text, bold_all=False, code_bg=True):
    """Adiciona runs com suporte a **negrito**, *itálico* e `código` inline."""
    pattern = re.compile(r"\*\*(.+?)\*\*|`(.+?)`|\*(.+?)\*|([^`*]+|\*(?!\*)|(?<!\*)\*)")
    for m in pattern.finditer(text):
        if m.group(1) is not None:
            run = para.add_run(m.group(1))
            run.bold = True
        elif m.group(2) is not None:
            run = para.add_run(m.group(2))
            run.font.name = CODE_FONT
            run.font.size = Pt(9)
            if code_bg:
                _shade_run(run, CODE_BG)
        elif m.group(3) is not None:
            run = para.add_run(m.group(3))
            run.italic = True
            if bold_all:
                run.bold = True
        else:
            txt = m.group(4) or ""
            if txt:
                run = para.add_run(txt)
                if bold_all:
                    run.bold = True


def add_paragraph(style_key, text="", bold_all=False, align=None):
    style = _pick_style(STYLE_MAP.get(style_key, "Normal"))
    p = doc.add_paragraph(style=style)
    if align:
        p.alignment = align
    if text:
        add_inline(p, text, bold_all=bold_all)
    return p


def add_quote(text):
    """Citação no estilo de um visualizador Markdown: fundo cinza claro,
    barra vertical à esquerda, texto normal alinhado à esquerda. Não usa o
    estilo "Intense Quote" do template (centralizado, itálico, fonte grande e
    linhas em cima/embaixo), que ficava desproporcional no Word."""
    p = doc.add_paragraph(style="Normal")
    pPr = p._p.get_or_add_pPr()

    # pBdr e shd são criados antes de ind/spacing/jc para manter a ordem OOXML
    pBdr = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "24")  # 3pt
    left.set(qn("w:space"), "8")
    left.set(qn("w:color"), QUOTE_BAR)
    pBdr.append(left)
    pPr.append(pBdr)

    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), QUOTE_BG)
    pPr.append(shd)

    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.left_indent = Cm(0.35)
    pf.right_indent = Cm(0)
    pf.first_line_indent = Cm(0)
    pf.space_before = Pt(6)
    pf.space_after = Pt(6)

    add_inline(p, text)
    return p


def page_break():
    p = doc.add_paragraph(style="Normal")
    p.add_run().add_break(WD_BREAK.PAGE)


# ── Sumário real (campo TOC do Word) ─────────────────────────────────────────


def add_toc(levels="1-3"):
    """Insere campo TOC do Word (atualizado automaticamente pelo Word)."""
    add_paragraph("h1", "Sumário")

    p = doc.add_paragraph(style="Normal")
    run = p.add_run()

    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = ' TOC \\o "1-3" \\h \\z \\u '

    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")

    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")

    run._r.append(begin)
    run._r.append(instr)
    run._r.append(separate)
    run._r.append(end)

    page_break()


# ── Tabela ────────────────────────────────────────────────────────────────────


def parse_table_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_separator(cells):
    return all(re.match(r"^[-: ]+$", c) for c in cells if c)


def _cell_weight(text: str) -> float:
    """Comprimento aproximado do conteúdo de uma célula, para estimar a largura
    proporcional da coluna (igual ao que um renderizador Markdown faria:
    coluna com texto curto fica estreita, coluna com texto longo fica larga)."""
    plain = re.sub(r"\*\*|`", "", text)
    # quebras de linha internas (ex.: `<br/>`) não devem inflar a largura —
    # conta só o trecho mais longo entre quebras.
    parts = re.split(r"<br\s*/?>", plain, flags=re.IGNORECASE)
    return max((len(p.strip()) for p in parts), default=0)


def _longest_token_len(text: str) -> int:
    """Tamanho do maior 'token' sem espaço na célula (ex.: um identificador
    como `VENDAS_HOLDING_PRD`) — é isso que trava a largura mínima da coluna,
    não o texto inteiro: uma palavra não quebra no meio, só entre palavras."""
    plain = re.sub(r"\*\*|`", "", text)
    tokens = re.split(r"\s+", plain.strip())
    return max((len(t) for t in tokens), default=0)


def _col_min_widths_cm(rows):
    """Piso mínimo de largura por coluna (baseado no maior token indivisível
    daquela coluna, não um valor fixo genérico) — usado tanto para calcular
    a largura final das colunas quanto, antes disso, para decidir se a
    tabela cabe em retrato ou precisa de uma página em paisagem."""
    ncols = max(len(r) for r in rows)
    min_cms = []
    for j in range(ncols):
        longest_tok = 0
        for r in rows:
            if j < len(r):
                longest_tok = max(longest_tok, _longest_token_len(r[j]))
        # ~0.20cm por caractere (fonte de tabela em 9pt) + 0.4cm de folga
        # pras margens internas da célula. Só protege contra quebra de
        # palavra até ~16 caracteres — cobre a esmagadora maioria das
        # palavras/identificadores reais (`MODELO_MT_MERCADO`,
        # "recomendação", "principalmente"...); um token isolado além disso
        # (ex.: um nome de arquivo longo tipo `Usuarios_Workspaces_v2.xlsx`)
        # não deveria sozinho forçar a coluna inteira a ficar enorme — nesse
        # caso extremo é aceitável quebrar, como uma URL longa quebraria em
        # qualquer documento. Piso absoluto de 1.1cm.
        min_cms.append(max(1.1, min(longest_tok, 16) * 0.20 + 0.4))
    return min_cms


def _portrait_usable_cm(section):
    """Largura útil de página em retrato, mesmo que a seção atual já esteja
    em paisagem — usa a menor das duas dimensões da página como referência,
    para decidir corretamente mesmo depois de uma troca de orientação
    anterior."""
    w = min(section.page_width, section.page_height)
    return w.cm - section.left_margin.cm - section.right_margin.cm


def _strip_anchored_pictures(header):
    """Remove do cabeçalho as imagens *ancoradas* (`wp:anchor`), preservando
    imagens *inline* (a logo da empresa, que flui com o texto) e qualquer
    texto. O template tem um frame decorativo (`Imagem 2`) com tamanho e
    posição fixos, calibrado pra proporção de página retrato — numa página
    em paisagem ele não acompanha a mudança de forma da página e aparece
    deslocado, sem alinhar com a borda real (o defeito visual reportado)."""
    for p in header.paragraphs:
        for run in list(p.runs):
            if "wp:anchor" in run._element.xml:
                run._element.getparent().remove(run._element)


def _set_section_orientation(orientation):
    """Abre uma nova seção (com quebra de página) na orientação pedida,
    trocando largura/altura de página. Cabeçalho e rodapé continuam
    vinculados por herança padrão do Word (mesmo conteúdo em toda seção) —
    o frame decorativo problemático em paisagem já foi removido uma única
    vez, na fonte (`doc.sections[0].header`, ver `gerar_documento`), então
    não há nada sensível à orientação sobrando pra tratar seção a seção."""
    new_section = doc.add_section(WD_SECTION_START.NEW_PAGE)
    w, h = new_section.page_width, new_section.page_height
    if orientation == WD_ORIENT.LANDSCAPE and w < h:
        new_section.page_width, new_section.page_height = h, w
    elif orientation == WD_ORIENT.PORTRAIT and w > h:
        new_section.page_width, new_section.page_height = h, w
    new_section.orientation = orientation
    return new_section


def _compute_col_widths_cm(rows, total_width_cm, max_frac=0.5):
    """Distribui a largura total entre colunas proporcionalmente ao conteúdo,
    com piso mínimo por coluna (`_col_min_widths_cm`) e teto por coluna —
    para nenhuma coluna ficar ilegível (ou quebrar palavra no meio) nem uma
    única coluna 'engolir' a tabela inteira."""
    ncols = max(len(r) for r in rows)
    # Com muitas colunas, um teto fixo de 50% deixa pouco pras demais —
    # aperta o teto conforme ncols cresce (nunca acima de 50%).
    max_frac = min(max_frac, 2.6 / ncols)
    weights = []
    for j in range(ncols):
        maxlen = 0
        for r in rows:
            if j < len(r):
                maxlen = max(maxlen, _cell_weight(r[j]))
        weights.append(max(maxlen, 3))
    min_cms = _col_min_widths_cm(rows)

    total_weight = sum(weights)
    raw = [w / total_weight * total_width_cm for w in weights]

    # Teto por coluna (evita uma coluna de texto longo dominar a tabela)
    cap = total_width_cm * max_frac
    raw = [min(w, cap) for w in raw]

    # Piso por coluna (nunca menor que o maior token indivisível dela)
    widths = [max(w, m) for w, m in zip(raw, min_cms)]

    total_now = sum(widths)
    if total_now > total_width_cm:
        # Tabela densa: falta espaço. Tira o excesso primeiro das colunas que
        # têm folga acima do próprio piso (proporcional a essa folga) — só
        # encolhe uma coluna abaixo do piso (quebra palavra no meio) se
        # TODAS já estiverem exatamente no piso e mesmo assim não couber.
        excess = total_now - total_width_cm
        slack = [max(0.0, w - m) for w, m in zip(widths, min_cms)]
        total_slack = sum(slack)
        if total_slack > 0:
            take = min(excess, total_slack)
            widths = [w - take * (s / total_slack) for w, s in zip(widths, slack)]
            excess -= take
        if excess > 1e-6:
            total_now2 = sum(widths)
            scale = total_width_cm / total_now2 if total_now2 > 0 else 1.0
            widths = [w * scale for w in widths]
    elif total_now < total_width_cm:
        # Sobra espaço — estica proporcionalmente ao peso de conteúdo, pra
        # tabela ocupar a largura útil da página em vez de ficar apertada.
        surplus = total_width_cm - total_now
        widths = [w + surplus * (wt / total_weight) for w, wt in zip(widths, weights)]

    return widths


def _apply_fixed_col_widths(table, widths_cm):
    """Força layout fixo e aplica a largura calculada em cada coluna — sem
    isso, o Word ignora `table.columns[i].width` e volta a dividir tudo em
    partes iguais (o problema original)."""
    table.autofit = False
    tbl = table._tbl
    tblPr = tbl.tblPr
    layout = tblPr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tblPr.append(layout)
    layout.set(qn("w:type"), "fixed")

    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            cell.width = Cm(widths_cm[idx])
    for idx, col in enumerate(table.columns):
        col.width = Cm(widths_cm[idx])


def _set_table_cell_margins(table, margin_cm=0.08):
    """Reduz a margem interna padrão do Word (~0.19cm de cada lado) pra
    recuperar espaço real de conteúdo — importante em tabelas densas de
    muitas colunas, onde cada 0,1cm por coluna faz diferença pra caber
    palavra sem quebrar no meio."""
    tbl = table._tbl
    tblPr = tbl.tblPr
    mar = tblPr.find(qn("w:tblCellMar"))
    if mar is None:
        mar = OxmlElement("w:tblCellMar")
        tblPr.append(mar)
    w = str(int(margin_cm * 566.93))
    for side in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), w)
        el.set(qn("w:type"), "dxa")
        mar.append(el)


def add_table(rows):
    if not rows:
        return
    cols = max(len(r) for r in rows)

    # Tabela larga demais pra caber em retrato, mesmo no piso mínimo de
    # coluna (maior token indivisível) — em vez de espremer tudo e deixar o
    # texto ilegível, abre uma página em paisagem só para ela e volta pra
    # retrato logo depois. Ex.: a tabela de inventário por tipo de artefato
    # (21 colunas) da Seção 3 do Diagnóstico.
    needs_landscape = (
        sum(_col_min_widths_cm(rows)) > _portrait_usable_cm(doc.sections[-1]) + 1e-6
    )
    if needs_landscape:
        _set_section_orientation(WD_ORIENT.LANDSCAPE)

    table = doc.add_table(rows=len(rows), cols=cols)
    table_style = _pick_style("Normal Table", fallback=None)
    if table_style:
        table.style = table_style

    # Bordas azuis
    tbl = table._tbl
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)
    tblBorders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "4472C4")
        tblBorders.append(el)
    tblPr.append(tblBorders)

    for i, row_data in enumerate(rows):
        for j in range(cols):
            cell_text = row_data[j] if j < len(row_data) else ""
            cell = table.cell(i, j)
            cell.text = ""
            p = cell.paragraphs[0]
            p.style = doc.styles["Normal"]
            # sem fundo cinza no `código` do cabeçalho (fundo azul escuro)
            add_inline(p, cell_text.strip(), bold_all=(i == 0), code_bg=(i != 0))
            for run in p.runs:
                # Fonte um pouco menor dentro de tabela — padrão comum em
                # relatórios densos, e dá folga extra pra largura de coluna
                # caber o conteúdo sem quebrar palavra no meio. Código
                # (monoespaçado) é mais largo por caractere que texto normal
                # na mesma altura de fonte — por isso fica um ponto menor,
                # é justamente onde vivem os identificadores longos e
                # indivisíveis (`MODELO_MT_MERCADO`, `VENDAS_HOLDING_PRD`...)
                # que mais puxam a largura mínima da coluna.
                run.font.size = Pt(7.5) if run.font.name == CODE_FONT else Pt(8.5)

            if i == 0:  # cabeçalho: fundo azul escuro, texto branco
                for run in p.runs:
                    run.bold = True
                tc = cell._tc
                tcPr = tc.get_or_add_tcPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:color"), "auto")
                shd.set(qn("w:fill"), "1F3864")
                tcPr.append(shd)
                for run in cell.paragraphs[0].runs:
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    _set_table_cell_margins(table)

    # Largura de página útil real (calculada da seção atual, não um valor fixo)
    section = doc.sections[-1]
    usable_cm = section.page_width.cm - section.left_margin.cm - section.right_margin.cm
    widths_cm = _compute_col_widths_cm(rows, usable_cm)
    _apply_fixed_col_widths(table, widths_cm)

    doc.add_paragraph(style="Normal")  # espaço após tabela

    if needs_landscape:
        _set_section_orientation(WD_ORIENT.PORTRAIT)


# ── Capa ──────────────────────────────────────────────────────────────────────


def add_cover():
    for _ in range(4):
        doc.add_paragraph(style="Normal")

    p = doc.add_paragraph(style=_pick_style("Ttulo", STYLE_MAP["title"]))
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(style="Normal")
    p.add_run(CAPA_TITULO).bold = True

    p2 = doc.add_paragraph(style=_pick_style("Subttulo", STYLE_MAP["subtitle"]))
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.add_run(CAPA_SUBTITULO)

    doc.add_paragraph(style="Normal")

    p3 = doc.add_paragraph(style="Normal")
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p3.add_run(CAPA_RODAPE)

    for _ in range(5):
        doc.add_paragraph(style="Normal")

    page_break()


# ── Parser Markdown ───────────────────────────────────────────────────────────


def _is_block_start(raw_line: str) -> bool:
    """True se a linha inicia um novo bloco Markdown (título, tabela, lista,
    citação, código, imagem, separador, âncora) — ou seja, NÃO é uma
    continuação por soft-wrap do parágrafo/item anterior. Usado para juntar
    linhas que o Markdown renderiza como um único parágrafo, mas que no
    arquivo-fonte aparecem quebradas em várias linhas físicas."""
    s = raw_line.strip()
    if not s:
        return True
    if re.match(r"^#{1,6} ", s):
        return True
    if s.startswith("|"):
        return True
    if s.startswith(">"):
        return True
    if s.startswith("```"):
        return True
    if re.match(r"^ {0,3}[-*] ", raw_line):
        return True
    if re.match(r"^ {0,3}\d+\. ", raw_line):
        return True
    if re.match(r"^!\[", s):
        return True
    if s in ("---", "***", "___"):
        return True
    if re.match(r'^<a\s+id="[^"]*"\s*>\s*</a>\s*$', s, re.IGNORECASE):
        return True
    return False


def _collect_wrapped(lines, start_i: int, first_text: str):
    """A partir de start_i, junta linhas seguintes que são continuação por
    soft-wrap (não iniciam um novo bloco) da mesma linha lógica, unindo com
    espaço — replicando como o Markdown renderiza parágrafos/itens de lista
    quebrados em múltiplas linhas no arquivo-fonte. Retorna (texto, próximo i)."""
    parts = [first_text]
    i = start_i
    while i < len(lines):
        nxt = lines[i].rstrip("\n")
        if _is_block_start(nxt):
            break
        parts.append(nxt.strip())
        i += 1
    return " ".join(p for p in parts if p), i


def parse_md(path):
    md_dir = os.path.dirname(os.path.abspath(path))
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    in_table = False
    table_rows = []
    skip_toc = False

    while i < len(lines):
        line = lines[i].rstrip("\n")
        stripped = line.strip()

        # Ignora bloco ## Sumário do Markdown (substituído pelo TOC do Word)
        if re.match(r"^## Sum[aá]rio", stripped):
            skip_toc = True
            i += 1
            continue
        if skip_toc:
            if stripped.startswith("## ") and not re.match(r"^## Sum[aá]rio", stripped):
                skip_toc = False
            else:
                i += 1
                continue

        # Descarta tabela acumulada ao encontrar linha não-tabela
        if in_table and not stripped.startswith("|"):
            add_table(table_rows)
            table_rows = []
            in_table = False

        # Linha vazia
        if not stripped:
            i += 1
            continue

        # Âncora HTML (`<a id="sec-x"></a>`) — só navegação interna do
        # Markdown/GitHub; o Word já tem seu próprio TOC/bookmarks, não usa isso.
        if re.match(r'^<a\s+id="[^"]*"\s*>\s*</a>\s*$', stripped, re.IGNORECASE):
            i += 1
            continue

        # H1 do Markdown (título do doc) → já na capa, ignora
        if re.match(r"^# [^#]", stripped):
            i += 1
            continue

        # ── Títulos ────────────────────────────────────────────────────────
        if stripped.startswith("##### "):
            add_paragraph("h4", stripped[6:].strip())
            i += 1
            continue

        if stripped.startswith("#### "):
            add_paragraph("h3", stripped[5:].strip())
            i += 1
            continue

        if stripped.startswith("### "):
            add_paragraph("h2", stripped[4:].strip())
            i += 1
            continue

        if stripped.startswith("## "):
            add_paragraph("h1", stripped[3:].strip())
            i += 1
            continue

        # ── Tabela ─────────────────────────────────────────────────────────
        if stripped.startswith("|"):
            cells = parse_table_row(stripped)
            if not is_separator(cells):
                table_rows.append(cells)
            in_table = True
            i += 1
            continue

        # ── Blockquote (linhas `>` consecutivas; `>` vazio separa parágrafos) ─
        if stripped.startswith(">"):
            paragrafos, atual = [], []
            while i < len(lines) and lines[i].strip().startswith(">"):
                conteudo = lines[i].strip()[1:].strip()
                if conteudo:
                    atual.append(conteudo)
                elif atual:
                    paragrafos.append(" ".join(atual))
                    atual = []
                i += 1
            if atual:
                paragrafos.append(" ".join(atual))
            for texto in paragrafos:
                add_quote(texto)
            continue

        # ── Lista com marcador ou numerada (junta continuação por soft-wrap) ─
        bullet_m = re.match(r"^ {0,3}[-*] ", line)
        number_m = re.match(r"^ {0,3}(\d+)\. ", line)
        if bullet_m or number_m:
            indent = len(line) - len(line.lstrip())
            level = 1 if indent >= 4 else 0  # sublista se 4+ espaços
            if bullet_m:
                first_text = re.sub(r"^[ \t]*[-*]\s+", "", stripped)
                list_type = "bullet"
            else:
                first_text = re.sub(r"^[ \t]*\d+\.\s+", "", stripped)
                list_type = "number"
            text, i = _collect_wrapped(lines, i + 1, first_text)
            p = add_paragraph("list", text)
            _apply_list_format(p, list_type, level)
            continue

        # ── Bloco de código ────────────────────────────────────────────────
        if stripped.startswith("```"):
            fence_lang = stripped[3:].strip().lower()
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i].rstrip("\n"))
                i += 1
            i += 1
            code_text = "\n".join(code_lines)

            if fence_lang == "mermaid" and code_text.strip():
                png_path = _render_mermaid_to_png(code_text)
                if png_path:
                    p = doc.add_paragraph(style="Normal")
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    section = doc.sections[-1]
                    usable_cm = section.page_width.cm - section.left_margin.cm - section.right_margin.cm
                    p.add_run().add_picture(png_path, width=Cm(usable_cm))
                    continue
                # Sem Node/mermaid-cli disponível — cai no bloco de texto abaixo

            if code_lines:
                p = doc.add_paragraph(style="Normal")
                p.paragraph_format.left_indent = Cm(1.0)
                run = p.add_run(code_text)
                run.font.name = "Courier New"
                run.font.size = Pt(8)
            continue

        # ── Imagem ─────────────────────────────────────────────────────────
        img_m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if img_m:
            alt_text = img_m.group(1).strip()
            img_rel = img_m.group(2).strip()
            img_path = os.path.join(md_dir, img_rel)
            if os.path.exists(img_path):
                p = doc.add_paragraph(style="Normal")
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run().add_picture(img_path, width=Cm(15.0))
                if alt_text:
                    cap = doc.add_paragraph(style="Normal")
                    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    r = cap.add_run(alt_text)
                    r.italic = True
                    r.font.size = Pt(9)
            else:
                p = doc.add_paragraph(style="Normal")
                p.add_run(f"[Imagem não encontrada: {img_rel}]").italic = True
                print(f"  AVISO: imagem não encontrada — {img_path}")
            i += 1
            continue

        # ── Separador horizontal ────────────────────────────────────────────
        if stripped in ("---", "***", "___"):
            i += 1
            continue

        # ── Parágrafo normal (junta continuação por soft-wrap) ──────────────
        text, i = _collect_wrapped(lines, i + 1, stripped)
        add_paragraph("normal", text)

    # Flush tabela restante
    if in_table and table_rows:
        add_table(table_rows)


# ── Geração de um documento ───────────────────────────────────────────────────


def gerar_documento(cfg: dict):
    """Gera o DOCX. `cfg` usa caminhos absolutos: md, docx, template, e os
    textos de capa titulo, subtitulo, versao e rodape."""
    global doc, _list_num_ids, CAPA_TITULO, CAPA_SUBTITULO, CAPA_RODAPE

    md_path = cfg["md"]
    docx_path = cfg["docx"]
    tmpl_path = cfg.get("template", "")

    if not os.path.exists(md_path):
        raise FileNotFoundError(f"Arquivo Markdown não encontrado: {md_path}")

    # Reinicia estado do gerador para cada documento
    _list_num_ids = {}
    CAPA_TITULO = cfg["titulo"]
    CAPA_SUBTITULO = cfg.get("subtitulo", "")
    CAPA_RODAPE = "   ·   ".join(
        t for t in (cfg.get("versao", "").strip(), cfg.get("rodape", "").strip()) if t
    )

    if tmpl_path and os.path.exists(tmpl_path):
        doc = open_template(tmpl_path)
    else:
        print("  AVISO: template não informado/encontrado — usando o padrão do Word.")
        doc = Document()
    body = doc.element.body
    for child in list(body):
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag in ("p", "tbl", "sdt"):
            body.remove(child)

    # Remove do cabeçalho, uma única vez na fonte, o frame decorativo do
    # template: imagem ancorada com tamanho e posição fixos, calibrada pra
    # proporção de página retrato — em página de tabela larga, que abre em
    # paisagem (`_set_section_orientation`), esse frame não acompanha a
    # mudança de forma da página e aparece deslocado. Tirando da fonte
    # (`doc.sections[0].header`, herdada por vínculo padrão em toda seção
    # nova), o resultado não depende de cada leitor de .docx implementar
    # corretamente cabeçalho por seção — mais simples e mais robusto que
    # trocar o cabeçalho seção a seção. A logo da empresa (imagem inline,
    # tamanho fixo mas sem posicionamento sensível à página) permanece.
    _strip_anchored_pictures(doc.sections[0].header)

    add_cover()
    add_toc(levels="1-3")
    parse_md(md_path)
    os.makedirs(os.path.dirname(os.path.abspath(docx_path)), exist_ok=True)
    doc.save(docx_path)
    print(f"  ✔  {docx_path}")


# ── Configuração salva (últimos valores usados na tela) ───────────────────────


def carregar_config() -> dict:
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def salvar_config(cfg: dict):
    keep = {k: cfg[k] for k in DEFAULTS if k in cfg}
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(keep, f, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"AVISO: não foi possível salvar a configuração ({exc}).")


def titulo_do_md(md_path: str) -> str:
    """Sugere o título do relatório: primeiro H1 do Markdown ou, se não houver,
    o nome do arquivo sem extensão."""
    try:
        with open(md_path, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^# (?!#)(.+)", line.strip())
                if m:
                    return re.sub(r"\*\*|`", "", m.group(1)).strip()
    except OSError:
        pass
    return os.path.splitext(os.path.basename(md_path))[0].replace("-", " ").replace("_", " ")


# ── Tela (tkinter) ────────────────────────────────────────────────────────────


def abrir_tela(md_inicial: str = ""):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    cfg = carregar_config()

    root = tk.Tk()
    root.title("Gerar Word a partir de Markdown")
    root.resizable(True, False)

    frm = ttk.Frame(root, padding=14)
    frm.grid(sticky="nsew")
    root.columnconfigure(0, weight=1)
    frm.columnconfigure(1, weight=1)

    vars_ = {
        "md": tk.StringVar(),
        "titulo": tk.StringVar(),
        "subtitulo": tk.StringVar(value=cfg["subtitulo"]),
        "versao": tk.StringVar(value=cfg["versao"]),
        "rodape": tk.StringVar(value=cfg["rodape"]),
        "template": tk.StringVar(value=cfg["template"]),
        "docx": tk.StringVar(),
    }
    status = tk.StringVar(value="Selecione o arquivo .md do relatório.")

    def escolher_md():
        path = filedialog.askopenfilename(
            title="Selecione o relatório Markdown",
            initialdir=cfg.get("ultima_pasta") or SCRIPT_DIR,
            filetypes=[("Markdown", "*.md *.markdown"), ("Todos", "*.*")],
        )
        if path:
            definir_md(path)

    def definir_md(path):
        path = os.path.abspath(path)
        vars_["md"].set(path)
        vars_["titulo"].set(titulo_do_md(path))
        vars_["docx"].set(os.path.splitext(path)[0] + ".docx")
        cfg["ultima_pasta"] = os.path.dirname(path)
        status.set("Confira os dados e clique em \"Gerar Word\".")

    def escolher_template():
        path = filedialog.askopenfilename(
            title="Selecione o template Word",
            initialdir=os.path.dirname(vars_["template"].get()) or SCRIPT_DIR,
            filetypes=[("Template Word", "*.dotx *.docx"), ("Todos", "*.*")],
        )
        if path:
            vars_["template"].set(path)

    def escolher_docx():
        atual = vars_["docx"].get()
        path = filedialog.asksaveasfilename(
            title="Salvar documento Word como",
            initialdir=os.path.dirname(atual) or cfg.get("ultima_pasta") or SCRIPT_DIR,
            initialfile=os.path.basename(atual),
            defaultextension=".docx",
            filetypes=[("Documento Word", "*.docx")],
        )
        if path:
            vars_["docx"].set(path)

    campos = [
        ("Arquivo .md:", "md", escolher_md),
        ("Nome do relatório:", "titulo", None),
        ("Subtítulo:", "subtitulo", None),
        ("Versão:", "versao", None),
        ("Rodapé da capa:", "rodape", None),
        ("Template Word:", "template", escolher_template),
        ("Salvar como (.docx):", "docx", escolher_docx),
    ]
    for row, (rotulo, chave, acao) in enumerate(campos):
        ttk.Label(frm, text=rotulo).grid(row=row, column=0, sticky="w", pady=3, padx=(0, 8))
        ttk.Entry(frm, textvariable=vars_[chave], width=70).grid(
            row=row, column=1, sticky="ew", pady=3
        )
        if acao:
            ttk.Button(frm, text="Procurar...", command=acao).grid(
                row=row, column=2, padx=(6, 0), pady=3
            )

    btn_gerar = ttk.Button(frm, text="Gerar Word")
    btn_gerar.grid(row=len(campos), column=1, sticky="e", pady=(12, 0))
    ttk.Button(frm, text="Fechar", command=root.destroy).grid(
        row=len(campos), column=2, padx=(6, 0), pady=(12, 0)
    )
    ttk.Label(frm, textvariable=status, foreground="#555").grid(
        row=len(campos) + 1, column=0, columnspan=3, sticky="w", pady=(10, 0)
    )

    def gerar():
        dados = {k: v.get().strip() for k, v in vars_.items()}
        if not dados["md"] or not os.path.exists(dados["md"]):
            messagebox.showwarning("Atenção", "Selecione um arquivo .md válido.")
            return
        if not dados["titulo"]:
            messagebox.showwarning("Atenção", "Informe o nome do relatório.")
            return
        if not dados["docx"]:
            dados["docx"] = os.path.splitext(dados["md"])[0] + ".docx"
            vars_["docx"].set(dados["docx"])
        if not dados["docx"].lower().endswith(".docx"):
            dados["docx"] += ".docx"
            vars_["docx"].set(dados["docx"])

        cfg.update({k: dados[k] for k in ("template", "subtitulo", "versao", "rodape")})
        salvar_config(cfg)

        btn_gerar.state(["disabled"])
        status.set("Gerando documento... (diagramas Mermaid podem levar alguns segundos)")

        def trabalho():
            try:
                gerar_documento(dados)
                root.after(0, concluido, None)
            except Exception as exc:  # noqa: BLE001 — erro exibido ao usuário
                root.after(0, concluido, exc)

        threading.Thread(target=trabalho, daemon=True).start()

    def concluido(erro):
        btn_gerar.state(["!disabled"])
        if erro is not None:
            if isinstance(erro, PermissionError):
                msg = (f"Não foi possível salvar o arquivo.\n\n{erro}\n\n"
                       "Verifique se o .docx não está aberto no Word.")
            else:
                msg = f"Falha ao gerar o documento:\n\n{erro}"
            status.set("Erro na geração.")
            messagebox.showerror("Erro", msg)
            return
        docx_path = vars_["docx"].get()
        status.set(f"Gerado: {docx_path}")
        if messagebox.askyesno(
            "Concluído",
            f"Documento gerado com sucesso:\n{docx_path}\n\n"
            "Ao abrir no Word, pressione Ctrl+A → F9 para atualizar o Sumário.\n\n"
            "Deseja abrir o documento agora?",
        ):
            try:
                if os.name == "nt":
                    os.startfile(docx_path)  # type: ignore[attr-defined]
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", docx_path])
                else:
                    subprocess.Popen(["xdg-open", docx_path])
            except OSError as exc:
                messagebox.showerror("Erro", f"Não foi possível abrir o arquivo:\n{exc}")

    btn_gerar.configure(command=gerar)

    if md_inicial:
        definir_md(md_inicial)

    root.mainloop()


# ── Execução principal ────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        abrir_tela(sys.argv[1] if len(sys.argv) > 1 else "")
    finally:
        if _MERMAID_TMP_DIR:
            shutil.rmtree(_MERMAID_TMP_DIR, ignore_errors=True)
