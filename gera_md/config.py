# -*- coding: utf-8 -*-
"""Preferências do usuário. Nunca guarda chave de API (constituição III).

`ultima_pasta` continua no gerar_word_config.json (compartilhado com a tela Tk e o
gerar_word.py). As preferências novas ficam em gera_documents_config.json, porque
o salvar_config do gerar_word.py só mantém as chaves que ele conhece.
"""

import json
import os
import re
import threading

import gerar_word

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMINHO = os.environ.get("GERA_MD_CONFIG") or os.path.join(RAIZ, "gera_documents_config.json")
MAX_RECENTES = 10
PADROES = {
    "pastas_recentes": [],
    "provedor_padrao": "claude-assinatura",
    "skill_padrao": "technical-documentation",
    "modelo_padrao": "padrão",
}
_PROIBIDO = re.compile(r"chave|key|token|senha|password|secret", re.I)
_trava = threading.Lock()


def _ler():
    dados = dict(PADROES)
    try:
        with open(CAMINHO, encoding="utf-8") as f:
            dados.update({k: v for k, v in json.load(f).items() if k in PADROES})
    except (OSError, ValueError):
        pass
    return dados


def _gravar(dados):
    for k in dados:
        if _PROIBIDO.search(k):
            raise ValueError(f"A configuração não pode guardar '{k}' (credenciais ficam no cofre do sistema).")
    with open(CAMINHO, "w", encoding="utf-8") as f:
        json.dump({k: dados[k] for k in PADROES if k in dados}, f, ensure_ascii=False, indent=2)


def obter():
    dados = _ler()
    dados["ultima_pasta"] = gerar_word.carregar_config().get("ultima_pasta", "")
    if not dados["pastas_recentes"] and dados["ultima_pasta"]:
        dados["pastas_recentes"] = [dados["ultima_pasta"]]
    return dados


def registrar_pasta(pasta):
    """Pasta usada: vira `ultima_pasta` e vai para o topo das recentes (máx. 10)."""
    with _trava:
        dados = _ler()
        recentes = [p for p in dados["pastas_recentes"] if os.path.normcase(p) != os.path.normcase(pasta)]
        dados["pastas_recentes"] = ([pasta] + recentes)[:MAX_RECENTES]
        _gravar(dados)
        cfg = gerar_word.carregar_config()
        cfg["ultima_pasta"] = pasta
        gerar_word.salvar_config(cfg)


def salvar_preferencias(**valores):
    """provedor_padrao, skill_padrao, modelo_padrao."""
    with _trava:
        dados = _ler()
        for k, v in valores.items():
            if _PROIBIDO.search(k):
                raise ValueError(f"A configuração não pode guardar '{k}'.")
            if k in PADROES and k != "pastas_recentes" and v:
                dados[k] = v
        _gravar(dados)
