#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
revisar_md.py
=============
Revisa o texto de um .md com IA usando uma skill da pasta .claude/skills
(padrão: technical-documentation): corrige vícios de linguagem, redundâncias e
ambiguidades e deixa o texto em tom técnico e de consultoria. Grava o resultado
como nova versão (nome_v2.md, _v3...) e um relatório das alterações
(nome_v2_revisao.md). Se o texto não mudar, nenhuma versão é gravada e o relatório
fica em nome_revisao.md (pendências e trechos não revisados). O original não é alterado.

Uso direto:
    python revisar_md.py a.md [b.md ...] [--skill technical-documentation] [--modelo sonnet]
                                         [--provedor claude-assinatura]
    python revisar_md.py --definir-chave-api   → pede a chave (não aparece na tela) e grava
                                                 no cofre do sistema (acesso por API)
    python revisar_md.py --remover-chave-api

Normalmente é chamado pelo frontend web (python -m gera_md.web) ou pelo botão
"Revisar texto (IA)" do analisar_md.py. A lógica fica em gera_md/revisao.py.

Garantias:
    - Blocos de código, imagens e âncoras são substituídos por marcadores
      antes do envio e restaurados depois — a IA não tem como alterá-los.
    - Trecho cuja resposta perder marcador, vier truncada ou com erro é
      mantido como no original e listado no relatório como "não revisado".

Tipos de acesso:
    claude-assinatura (padrão) → usa o login do Claude Code com a conta Pro/Max.
        Consome o limite de uso da assinatura, sem cobrança extra. Mesmo que exista
        ANTHROPIC_API_KEY no ambiente, ela NÃO é usada. Confira o login com
        `claude auth status --text`. O valor em US$ do relatório é só o
        equivalente em preço de API.
    claude-api → acesso separado, cobrado por uso, com a chave guardada no cofre
        do sistema (configure pelo frontend web).
"""

import argparse
import getpass
import os
import sys

from gera_md import provedores
from gera_md.provedores.base import FalhaProvedor
from gera_md.provedores.claude_cli import executavel
from gera_md.revisao import (INSTRUCOES, MODELOS, SKILL_PADRAO, SKILLS_DIR, TAM_TRECHO,  # noqa: F401
                             carregar_skill, dividir_em_trechos, listar_skills, proteger,
                             proxima_versao, restaurar)
from gera_md.revisao import revisar_md as _revisar

if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]


def claude_disponivel():
    return executavel()


def revisar_md(md_path, skill=SKILL_PADRAO, modelo="padrão", progresso=None, provedor=None):
    """Interface antiga (usada pela tela Tk): retorna dict com origem, destino (None se o
    texto não mudou), relatorio, custo, contagem, pendencias [(seção, texto)],
    falhas [(seção, erro)] e trechos."""
    prov = provedores.obter(provedor) if isinstance(provedor, str) else provedor
    prog = (lambda msg, *_: progresso(msg)) if progresso else None
    rev, _novo = _revisar(md_path, prov, skill, modelo, prog)
    return {"origem": md_path, "destino": rev.destino, "relatorio": rev.relatorio,
            "custo": rev.uso.custo_usd, "contagem": rev.contagem,
            "pendencias": [(p["secao"], p["texto"]) for p in rev.pendencias],
            "falhas": [(f["secao"], f["erro"]) for f in rev.falhas],
            "trechos": rev.trechos}


def _chave_api(remover):
    prov = provedores.obter("claude-api")
    if remover:
        prov.remover_chave()
        print("Chave de API removida do cofre do sistema.")
        return
    chave = getpass.getpass("Chave de API da Anthropic (não aparece na tela): ").strip()
    if len(chave) < 20:
        print("ERRO: chave de API inválida.")
        sys.exit(1)
    try:
        prov.salvar_chave(chave)
    except FalhaProvedor as exc:
        print(f"ERRO: {exc}")
        sys.exit(1)
    print("Chave salva no cofre do sistema. Use --provedor claude-api (cobrado por uso).")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Revisa o texto de .md com uma skill e uma IA")
    ap.add_argument("md", nargs="*", help="um ou mais arquivos .md")
    ap.add_argument("--skill", default=SKILL_PADRAO, choices=listar_skills() or None)
    ap.add_argument("--modelo", default="padrão", choices=MODELOS)
    ap.add_argument("--provedor", default="claude-assinatura",
                    choices=[p.id for p in provedores.listar()])
    chave = ap.add_mutually_exclusive_group()
    chave.add_argument("--definir-chave-api", action="store_true",
                       help="grava a chave de API no cofre do sistema (pede pelo terminal)")
    chave.add_argument("--remover-chave-api", action="store_true")
    args = ap.parse_args(argv)
    if args.definir_chave_api or args.remover_chave_api:
        _chave_api(args.remover_chave_api)
        return
    if not args.md:
        ap.error("informe ao menos um arquivo .md")
    prov = provedores.obter(args.provedor)
    e = prov.estado()
    if e.estado != "logado":
        print(f"ERRO: {prov.nome} — {e.detalhe}")
        for passo in prov.instrucoes_login():
            print(f"  · {passo}")
        sys.exit(1)
    cobranca = ("cobrado por uso (API)" if prov.cobranca == "por_uso"
                else "equivalente em API, não cobrado no plano Pro/Max")
    total, falhas = 0.0, 0
    for k, md in enumerate(args.md, 1):
        print(f"[{k}/{len(args.md)}] {md}")
        try:
            r = revisar_md(os.path.abspath(md), args.skill, args.modelo, provedor=prov)
        except (OSError, UnicodeDecodeError) as exc:
            print(f"  ERRO: {exc}")
            falhas += 1
            continue
        total += r["custo"]
        destino = r["destino"] or "sem alterações (nenhuma versão gravada)"
        print(f"  Revisado:  {destino}\n  Relatório: {r['relatorio']}\n"
              f"  Alterações: {sum(r['contagem'].values())} · Pendências: {len(r['pendencias'])} · "
              f"Falhas: {len(r['falhas'])} · US$ {r['custo']:.2f} ({cobranca})")
    if len(args.md) > 1:
        print(f"\nTotal: {len(args.md) - falhas} arquivo(s) · US$ {total:.2f} ({cobranca})")
    if falhas:
        sys.exit(1)


if __name__ == "__main__":
    main()
