# -*- coding: utf-8 -*-
"""Revisão de texto com IA (movido de revisar_md.py).

A IA é chamada só pela interface ProvedorIA (provedores/base.py). Garantias:
    - Blocos de código, imagens e âncoras são substituídos por marcadores
      antes do envio e restaurados depois — a IA não tem como alterá-los.
    - Trecho cuja resposta perder marcador, vier truncada ou com erro é
      mantido como no original e listado no relatório como "não revisado".
    - Cancelada a revisão, nenhum trecho novo é enviado e nenhuma versão é gravada.
"""

import os
import re
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from . import provedores
from .analise import analisar
from .modelos import Revisao, Uso
from .provedores.base import AcessoIncorreto, Cancelado, ErroProvedor, LimiteAtingido, LoginNecessario
from .versoes import gravar_nova_versao, proxima_versao  # noqa: F401 — reexportada

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(RAIZ, ".claude", "skills")
SKILL_PADRAO = "technical-documentation"
MODELOS = ["padrão", "sonnet", "opus", "haiku"]

TAM_TRECHO = 12000  # caracteres por chamada (seções ## inteiras são agrupadas até esse tamanho)
PARALELO = 3  # chamadas simultâneas à IA
FATAIS = (LoginNecessario, LimiteAtingido, AcessoIncorreto)  # não adianta tentar os demais trechos

INSTRUCOES = """
# Tarefa: revisão de texto técnico e de consultoria (pt-BR)

Você é revisor sênior de documentação técnica de uma consultoria de TI. Aplique a
skill acima para revisar o trecho de documento Markdown recebido entre <trecho> e
</trecho>. O público são clientes e equipes técnicas; o texto final deve ter tom
técnico, objetivo e de consultoria.

## O que corrigir

1. Vícios de linguagem: gerundismo ("vamos estar enviando"), "a nível de",
   "onde" sem sentido de lugar, pleonasmos ("subir para cima", "elo de ligação"),
   muletas ("basicamente", "na verdade", "simplesmente", "realizar" genérico,
   "fazer com que"), coloquialismos, gírias, exclamações, emojis, primeira pessoa
   do singular, adjetivos vagos ("muito", "bastante", "ótimo") e voz passiva
   desnecessária.
2. Redundâncias: ideias repetidas, frases que dizem o mesmo com outras palavras,
   introduções que só anunciam o que vem a seguir.
3. Ambiguidades: pronomes e referências vagas ("isso", "o mesmo", "ele", "lá"),
   termos diferentes para o mesmo conceito, frases com mais de uma leitura.
   Resolva quando o próprio texto deixar claro o sentido. Quando depender de
   informação que você não tem, NÃO invente: mantenha o texto e registre como
   [Pendente] em <alteracoes>.
4. Tom: impessoal ou primeira pessoa do plural institucional, frases diretas,
   verbos de ação, terminologia consistente, sem perder precisão.

## O que NÃO pode mudar

- Marcadores no formato ⟦BLOCO_n⟧: copie cada um exatamente, sozinho na linha,
  na mesma posição relativa.
- Estrutura Markdown: mesma quantidade e nível de títulos (#, ##, ###...), mesmas
  listas, citações (>) e tabelas (mesmas linhas e colunas). Pode melhorar a
  redação dentro deles.
- Conteúdo técnico: comandos, `código inline`, caminhos, URLs, nomes de produtos,
  servidores, tabelas de dados, números, datas, versões, valores e siglas.
- Não acrescente fatos, seções, conclusões ou recomendações novas e não remova
  informação técnica.
- Mantenha o idioma português do Brasil.

## Formato da resposta (obrigatório, nada fora destas duas tags)

<alteracoes>
- [Vício de linguagem] "trecho original" → "trecho revisado" — motivo curto
- [Redundância] "..." → "..." — motivo
- [Ambiguidade] "..." → "..." — motivo
- [Tom] "..." → "..." — motivo
- [Pendente] "trecho" — o que precisa ser confirmado pelo autor
</alteracoes>
<documento>
(o trecho completo revisado, em Markdown)
</documento>

Se não houver nada a alterar, devolva o trecho idêntico e escreva "- Nenhuma
alteração" em <alteracoes>.
"""


# ── Skills ────────────────────────────────────────────────────────────────────


def listar_skills():
    if not os.path.isdir(SKILLS_DIR):
        return []
    return sorted(d for d in os.listdir(SKILLS_DIR)
                  if os.path.isfile(os.path.join(SKILLS_DIR, d, "SKILL.md")))


def carregar_skill(nome):
    """Texto completo da skill: SKILL.md + todos os .md de references/."""
    pasta = os.path.join(SKILLS_DIR, nome)
    partes = []
    with open(os.path.join(pasta, "SKILL.md"), encoding="utf-8") as f:
        partes.append(f.read())
    refs = os.path.join(pasta, "references")
    if os.path.isdir(refs):
        for nome_ref in sorted(os.listdir(refs)):
            if nome_ref.endswith(".md"):
                with open(os.path.join(refs, nome_ref), encoding="utf-8") as f:
                    partes.append(f"\n\n<!-- references/{nome_ref} -->\n\n" + f.read())
    return "".join(partes)


# ── Proteção de blocos (código, imagens, âncoras) ─────────────────────────────


def proteger(linhas):
    """Troca blocos que a IA não deve tocar por ⟦BLOCO_n⟧. Retorna (linhas, blocos)."""
    out, blocos = [], []
    i = 0
    while i < len(linhas):
        s = linhas[i].strip()
        if s.startswith("```"):
            ini = i
            i += 1
            while i < len(linhas) and not linhas[i].strip().startswith("```"):
                i += 1
            bloco = linhas[ini:i + 1]
            i += 1
        elif re.match(r"^!\[[^\]]*\]\([^)]+\)\s*$", s) or re.match(r'^<a\s+id="[^"]*"', s, re.I):
            bloco = [linhas[i]]
            i += 1
        else:
            out.append(linhas[i])
            i += 1
            continue
        out.append(f"⟦BLOCO_{len(blocos)}⟧")
        blocos.append("\n".join(bloco))
    return out, blocos


def restaurar(texto, blocos):
    return re.sub(r"⟦BLOCO_(\d+)⟧", lambda m: blocos[int(m.group(1))], texto)


def descrever_bloco(bloco):
    """Resumo legível de um bloco protegido, para o relatório (FR-023)."""
    s = bloco.strip()
    if s.startswith("```"):
        conteudo = next((l.strip() for l in s.splitlines()[1:]
                         if l.strip() and not l.strip().startswith("```")), "")
        return f"[bloco de código: {conteudo[:60]}…]" if conteudo else "[bloco de código]"
    m = re.match(r"^!\[[^\]]*\]\(\s*<?([^)\s>]+)", s)
    if m:
        return f"[imagem: {m.group(1)}]"
    m = re.search(r'id="([^"]*)"', s, re.I)
    if m:
        return f"[âncora: {m.group(1)}]"
    return "[bloco]"


def sem_marcadores(texto, blocos):
    """Troca cada ⟦BLOCO_n⟧ citado pela IA pelo resumo do bloco; marcador sem bloco → [bloco]."""
    def trocar(m):
        i = int(m.group(1))
        return descrever_bloco(blocos[i]) if i < len(blocos) else "[bloco]"
    return re.sub(r"⟦BLOCO_(\d+)⟧", trocar, texto)


def dividir_em_trechos(linhas, limite=TAM_TRECHO):
    """Agrupa seções inteiras (quebra só antes de # / ##) até ~limite caracteres."""
    trechos, atual, tam = [], [], 0
    for linha in linhas:
        if re.match(r"^#{1,2} ", linha) and atual and tam > limite * 0.5:
            trechos.append(atual)
            atual, tam = [], 0
        atual.append(linha)
        tam += len(linha) + 1
        if tam > limite * 1.5 and not linha.strip():
            trechos.append(atual)  # seção muito longa: corta num parágrafo
            atual, tam = [], 0
    if atual:
        trechos.append(atual)
    return ["\n".join(t) for t in trechos]


def _extrair(tag, texto):
    m = re.search(rf"<{tag}>\s*\n?(.*?)\n?\s*</{tag}>", texto, re.S)
    return m.group(1) if m else None


def revisar_trecho(trecho, idx, total, titulo, arquivo_sistema, modelo, provedor, cancelar=None):
    """Retorna dict: texto, alteracoes [(categoria, texto)], uso, erro, fatal."""
    marcadores = re.findall(r"⟦BLOCO_\d+⟧", trecho)
    uso = Uso()
    if not re.sub(r"⟦BLOCO_\d+⟧", "", trecho).strip():
        return {"texto": trecho, "alteracoes": [], "uso": uso, "erro": None, "fatal": None}
    prompt = (f'Documento: "{titulo}" — trecho {idx} de {total}.\n\n'
              f"<trecho>\n{trecho}\n</trecho>")
    ultimo_erro = None
    for _tentativa in range(2):
        try:
            r = provedor.enviar(prompt, arquivo_sistema, modelo, cancelar)
        except Cancelado:
            raise
        except FATAIS as exc:
            return {"texto": trecho, "alteracoes": [], "uso": uso, "erro": str(exc), "fatal": exc}
        except (ErroProvedor, OSError) as exc:
            ultimo_erro = str(exc)
            continue
        uso.somar(Uso(r.custo_usd, r.tokens_entrada, r.tokens_saida))
        resposta = r.texto
        doc = _extrair("documento", resposta)
        if doc is None:
            ultimo_erro = "resposta sem a tag <documento>"
            continue
        if sorted(re.findall(r"⟦BLOCO_\d+⟧", doc)) != sorted(marcadores):
            ultimo_erro = "a resposta alterou/perdeu blocos protegidos (código/imagens)"
            continue
        if len(doc) < len(trecho) * 0.5:
            ultimo_erro = "resposta muito menor que o original (possível corte)"
            continue
        alteracoes = []
        for linha in (_extrair("alteracoes", resposta) or "").splitlines():
            m = re.match(r"^\s*-\s*\[([^\]]+)\]\s*(.*)$", linha)
            if m:
                alteracoes.append((m.group(1).strip(), m.group(2).strip()))
        return {"texto": doc, "alteracoes": alteracoes, "uso": uso, "erro": None, "fatal": None}
    return {"texto": trecho, "alteracoes": [], "uso": uso, "erro": ultimo_erro, "fatal": None}


# ── Revisão de um arquivo ─────────────────────────────────────────────────────


def _titulo(linhas, md_path):
    for l in linhas:
        if re.match(r"^# (?!#)", l):
            return l[2:].strip()
    return os.path.splitext(os.path.basename(md_path))[0]


def preparar(md_path):
    """(linhas, titulo, blocos protegidos, trechos) — usado também na prévia."""
    with open(md_path, encoding="utf-8") as f:
        linhas = f.read().splitlines()
    protegidas, blocos = proteger(linhas)
    return linhas, _titulo(linhas, md_path), blocos, dividir_em_trechos(protegidas)


def _gravar_exclusivo(base, ext, texto):
    """base+ext, ou base_2+ext, base_3+ext... no primeiro nome livre (nunca sobrescreve)."""
    n = 1
    while True:
        destino = f"{base}{ext}" if n == 1 else f"{base}_{n}{ext}"
        try:
            with open(destino, "x", encoding="utf-8") as f:
                f.write(texto)
            return destino
        except FileExistsError:
            n += 1


def texto_cobranca(provedor, custo):
    if provedor.cobranca == "por_uso":
        return f"Cobrado por uso (API): US$ {custo:.2f}"
    return f"Equivalente em API: US$ {custo:.2f} (não cobrado no plano Pro/Max)"


def revisar_md(md_path, provedor=None, skill=SKILL_PADRAO, modelo="padrão", progresso=None,
               cancelar=None, pasta_base=None):
    """Revisa o .md e grava nova versão + relatório.

    Retorna (Revisao, ResultadoArquivo da nova versão). O segundo é None se a revisão foi
    cancelada (Revisao.cancelada) ou se o texto não mudou (Revisao.destino é None; só o
    relatório é gravado)."""
    provedor = provedor or provedores.padrao()
    progresso = progresso or (lambda msg, feito=0, total=0: print("  " + msg))
    cancelar = cancelar or threading.Event()
    linhas_orig, titulo, blocos, trechos = preparar(md_path)

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(carregar_skill(skill) + "\n\n" + INSTRUCOES)
        arquivo_sistema = tmp.name

    feitos = [0]
    parar = threading.Event()  # login expirou / limite atingido: não envia mais trechos
    motivo = []
    trava = threading.Lock()

    def tarefa(args):
        i, t = args
        if cancelar.is_set():
            raise Cancelado("Revisão cancelada.")
        if parar.is_set():
            r = {"texto": t, "alteracoes": [], "uso": Uso(), "erro": motivo[0], "fatal": None}
        else:
            r = revisar_trecho(t, i + 1, len(trechos), titulo, arquivo_sistema, modelo, provedor,
                               cancelar)
            if r["fatal"] is not None:
                with trava:
                    if not motivo:
                        motivo.append(str(r["fatal"]))
                parar.set()
        with trava:
            feitos[0] += 1
            n = feitos[0]
        progresso(f"Revisando com IA... {n}/{len(trechos)} trecho(s)", n, len(trechos))
        return r

    progresso(f"Revisando com IA... 0/{len(trechos)} trecho(s)", 0, len(trechos))
    revisao = Revisao(origem=md_path, destino=None, relatorio=None, provedor=provedor.id,
                      tipo_acesso=provedor.tipo_acesso, cobranca=provedor.cobranca,
                      skill=skill, modelo=modelo, trechos=len(trechos))
    resultados = []
    try:
        with ThreadPoolExecutor(max_workers=PARALELO) as ex:
            futuros = [ex.submit(tarefa, a) for a in enumerate(trechos)]
            for f in futuros:
                try:
                    resultados.append(f.result())
                except Cancelado:
                    cancelar.set()
                    resultados.append(None)
    finally:
        os.remove(arquivo_sistema)

    for r in resultados:
        if r is not None:
            revisao.uso.somar(r["uso"])
            if r["fatal"] is not None and not revisao.erro_fatal:
                revisao.erro_fatal = str(r["fatal"])
                revisao.login_expirado = isinstance(r["fatal"], LoginNecessario)
    if cancelar.is_set():
        revisao.cancelada = True
        return revisao, None

    texto_final = restaurar("\n".join(r["texto"] for r in resultados), blocos).rstrip("\n") + "\n"
    # FR-023: sem diferença no texto, nenhuma versão é gravada — só o relatório
    mudou = texto_final != "\n".join(linhas_orig).rstrip("\n") + "\n"
    destino = gravar_nova_versao(md_path, texto_final) if mudou else None

    # ── Relatório ─────────────────────────────────────────────────────────
    contagem, pendencias, falhas = {}, [], []
    secoes = []
    for i, (t, r) in enumerate(zip(trechos, resultados), 1):
        cab = next((l.lstrip("# ").strip() for l in t.splitlines() if l.startswith("#")),
                   f"Trecho {i}")
        if r["erro"]:
            falhas.append((cab, sem_marcadores(r["erro"], blocos)))
        # o relatório nunca mostra marcadores internos (FR-023)
        itens = [(c, sem_marcadores(txt, blocos)) for c, txt in r["alteracoes"]
                 if not c.lower().startswith("nenhuma")]
        for c, txt in itens:
            if c.lower().startswith("pendente"):
                pendencias.append((cab, txt))
            else:
                contagem[c] = contagem.get(c, 0) + 1
        if itens:
            secoes.append((cab, itens))

    custo = revisao.uso.custo_usd
    out = [
        f"# Revisão de texto — {os.path.basename(md_path)}",
        "",
        f"**Original:** `{md_path}`  ",
        (f"**Revisado:** `{destino}`  " if destino
         else "**Revisado:** sem alterações no texto — nenhuma versão foi gravada  "),
        f"**IA:** {provedor.nome} · **Acesso:** {provedor.rotulo_acesso()}  ",
        f"**Skill:** {skill} · **Modelo:** {modelo} · **{texto_cobranca(provedor, custo)}**  ",
        f"**Data:** {datetime.now():%d/%m/%Y %H:%M}",
        "",
        "## Resumo",
        "",
        "| Tipo | Alterações |",
        "|---|---|",
    ]
    out += [f"| {c} | {n} |" for c, n in sorted(contagem.items(), key=lambda x: -x[1])]
    out.append(f"| Pendências para o autor | {len(pendencias)} |")
    if falhas:
        out += ["", "## Trechos não revisados (mantidos como no original)", ""]
        out += [f"- **{cab}:** {erro}" for cab, erro in falhas]
    if pendencias:
        out += ["", "## Pendências para o autor confirmar", ""]
        out += [f"- **{cab}:** {txt}" for cab, txt in pendencias]
    for cab, itens in secoes:
        itens = [(c, t) for c, t in itens if not c.lower().startswith("pendente")]
        if itens:
            out += ["", f"## {cab}", ""] + [f"- **[{c}]** {t}" for c, t in itens]
    if destino:
        relatorio = os.path.splitext(destino)[0] + "_revisao.md"
        with open(relatorio, "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
    else:
        relatorio = _gravar_exclusivo(os.path.splitext(md_path)[0] + "_revisao", ".md",
                                      "\n".join(out) + "\n")

    revisao.destino, revisao.relatorio = destino, relatorio
    revisao.contagem = contagem
    revisao.pendencias = [{"secao": c, "texto": t} for c, t in pendencias]
    revisao.falhas = [{"secao": c, "erro": e} for c, e in falhas]
    if not destino:
        return revisao, None
    novo = analisar(destino, pasta_base or os.path.dirname(md_path), origem=md_path,
                    tipo_versao="revisao_ia")
    novo.revisao = revisao
    return revisao, novo
