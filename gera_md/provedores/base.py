# -*- coding: utf-8 -*-
"""Contrato dos adaptadores de IA (specs/001-local-web-frontend/contracts/provedor-ia.md).

O núcleo de revisão conhece só esta interface. Uma IA nova é uma subclasse
registrada em provedores/__init__.py — nada mais muda.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass

ESTADOS = ("logado", "login_necessario", "nao_instalado", "chave_ausente", "erro")


class ErroProvedor(Exception):
    """Base das falhas de envio; a mensagem é exibida ao usuário (pt-BR)."""


class LoginNecessario(ErroProvedor):
    pass


class LimiteAtingido(ErroProvedor):
    pass


class AcessoIncorreto(ErroProvedor):
    """Ex.: o modo assinatura detectou uso de chave de API."""


class Cancelado(ErroProvedor):
    pass


class FalhaProvedor(ErroProvedor):
    pass


@dataclass
class EstadoProvedor:
    estado: str  # ver ESTADOS
    detalhe: str = ""  # sem e-mail, token ou chave

    def to_dict(self):
        return asdict(self)


@dataclass
class RespostaIA:
    texto: str
    custo_usd: float = 0.0
    tokens_entrada: int = 0
    tokens_saida: int = 0


class ProvedorIA(ABC):
    id: str = ""
    nome: str = ""
    tipo_acesso: str = "assinatura"  # assinatura | api
    cobranca: str = "limite_assinatura"  # limite_assinatura | por_uso
    padrao: bool = False

    def modelos(self) -> list[str]:
        return ["padrão"]

    @abstractmethod
    def estado(self) -> EstadoProvedor:
        """Não consome uso da IA; termina em até 10 s."""

    def instrucoes_login(self) -> list[str]:
        return []

    @abstractmethod
    def enviar(self, prompt: str, sistema: str, modelo: str,
               cancelar: threading.Event | None = None) -> RespostaIA:
        """`sistema` é o caminho de um arquivo com o prompt de sistema."""

    def rotulo_acesso(self) -> str:
        if self.tipo_acesso == "api":
            return "API — cobrado por uso"
        return "Assinatura — sem cobrança extra (consome o limite do plano)"

    def to_dict(self, estado: EstadoProvedor | None = None) -> dict:
        e = estado or self.estado()
        return {"id": self.id, "nome": self.nome, "tipo_acesso": self.tipo_acesso,
                "estado": e.estado, "detalhe": e.detalhe, "cobranca": self.cobranca,
                "padrao": self.padrao, "modelos": self.modelos(),
                "instrucoes_login": self.instrucoes_login() if e.estado != "logado" else [],
                "rotulo_acesso": self.rotulo_acesso()}
