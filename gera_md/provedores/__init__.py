# -*- coding: utf-8 -*-
"""Registro dos provedores de IA.

Nesta versão: Claude pela assinatura Pro/Max (padrão) e Claude pela API (acesso
separado, cobrado por uso). Para uma IA nova: criar a classe e registrar aqui.
"""

import time

from .base import (AcessoIncorreto, Cancelado, ErroProvedor, EstadoProvedor, FalhaProvedor,  # noqa: F401
                   LimiteAtingido, LoginNecessario, ProvedorIA, RespostaIA)
from .claude_cli import ClaudeApi, ClaudeAssinatura

CACHE_ESTADO = 30  # segundos

_provedores = {}
_cache = {}


def registrar(provedor):
    _provedores[provedor.id] = provedor
    _cache.pop(provedor.id, None)


def remover(provedor_id):
    _provedores.pop(provedor_id, None)
    _cache.pop(provedor_id, None)


def listar():
    return list(_provedores.values())


def obter(provedor_id):
    return _provedores.get(provedor_id)


def padrao():
    return next((p for p in _provedores.values() if p.padrao), None) or next(iter(_provedores.values()), None)


def estado(provedor, atualizar=False):
    """estado() com cache de 30 s (a verificação chama um processo externo)."""
    agora = time.monotonic()
    em_cache = _cache.get(provedor.id)
    if not atualizar and em_cache and agora - em_cache[0] < CACHE_ESTADO:
        return em_cache[1]
    e = provedor.estado()
    _cache[provedor.id] = (agora, e)
    return e


def invalidar(provedor_id=None):
    if provedor_id is None:
        _cache.clear()
    else:
        _cache.pop(provedor_id, None)


registrar(ClaudeAssinatura())
registrar(ClaudeApi())
