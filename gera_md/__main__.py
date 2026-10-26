# -*- coding: utf-8 -*-
"""Linha de comando do núcleo (paridade com o frontend, constituição IV).

Uso:
    python -m gera_md comparar original.md versao_v2.md

Para analisar/corrigir em lote use analisar_md.py --relatorio [--v2]; para revisar
com IA, revisar_md.py; para o frontend web, python -m gera_md.web.

Código de saída de `comparar`: 0 se os arquivos são iguais, 1 se há diferenças.
"""

import argparse
import os
import sys

from .comparacao import comparar

if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def formatar(blocos):
    """Linhas no formato unificado: só os trechos diferentes, com números de linha."""
    out = []
    for b in blocos:
        if b["tipo"] == "igual":
            continue
        (a1, a2), (b1, b2) = b["a"], b["b"]
        out.append(f"@@ {b['tipo']}: original {a1}-{a2 - 1 if a2 > a1 else a1} · "
                   f"versão {b1}-{b2 - 1 if b2 > b1 else b1} @@")
        out += [f"-{a1 + i:>5} | {t}" for i, t in enumerate(b["linhas_a"])]
        out += [f"+{b1 + i:>5} | {t}" for i, t in enumerate(b["linhas_b"])]
    return out


def cmd_comparar(args):
    for p in (args.a, args.b):
        if not os.path.isfile(p):
            print(f"ERRO: arquivo não encontrado: {p}")
            return 2
    blocos = comparar(args.a, args.b)
    linhas = formatar(blocos)
    if not linhas:
        print("Os dois arquivos são idênticos.")
        return 0
    print(f"--- {args.a}\n+++ {args.b}")
    print("\n".join(linhas))
    print(f"\n{sum(b['tipo'] != 'igual' for b in blocos)} trecho(s) diferente(s).")
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m gera_md", description="Ferramentas do Gera Documents")
    sub = ap.add_subparsers(dest="comando", required=True)
    c = sub.add_parser("comparar", help="mostra as diferenças entre duas versões de um .md")
    c.add_argument("a", help="arquivo original")
    c.add_argument("b", help="versão a comparar")
    c.set_defaults(funcao=cmd_comparar)
    args = ap.parse_args(argv)
    return args.funcao(args)


if __name__ == "__main__":
    sys.exit(main())
