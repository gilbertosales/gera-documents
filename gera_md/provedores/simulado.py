# -*- coding: utf-8 -*-
"""Provedor falso para testes: sem rede e sem Claude."""

import re
import threading
import time

from .base import (Cancelado, EstadoProvedor, FalhaProvedor, LimiteAtingido, LoginNecessario,
                   ProvedorIA, RespostaIA)


class ProvedorSimulado(ProvedorIA):
    id = "simulado"
    nome = "Simulado"
    tipo_acesso = "assinatura"
    cobranca = "limite_assinatura"

    def __init__(self, estado="logado", atraso=0.0, falhar_em=(), perder_marcador_em=(),
                 pendencia='"prazo" — confirmar a data',
                 limite_em=(), login_em=(), custo=0.01, padrao=False, id=None):
        self._estado = estado
        self.atraso = atraso
        self.falhar_em = set(falhar_em)
        self.perder_marcador_em = set(perder_marcador_em)
        self.limite_em = set(limite_em)
        self.login_em = set(login_em)
        self.custo = custo
        self.pendencia = pendencia
        self.padrao = padrao
        if id:
            self.id = id
        self.chamadas = 0
        self.prompts = []
        self._trava = threading.Lock()

    def estado(self):
        return EstadoProvedor(self._estado, "Simulado")

    def instrucoes_login(self):
        return ["Faça login no simulador"]

    def enviar(self, prompt, sistema, modelo, cancelar=None):
        with self._trava:
            self.chamadas += 1
            n = self.chamadas
            self.prompts.append(prompt)
        fim = time.monotonic() + self.atraso
        while time.monotonic() < fim:
            if cancelar is not None and cancelar.is_set():
                raise Cancelado("Revisão cancelada.")
            time.sleep(0.01)
        if n in self.falhar_em:
            raise FalhaProvedor("falha simulada")
        if n in self.limite_em:
            raise LimiteAtingido("Limite de uso atingido (simulado)")
        if n in self.login_em:
            raise LoginNecessario("Sessão expirada (simulado)")
        trecho = re.search(r"<trecho>\n(.*)\n</trecho>", prompt, re.S).group(1)
        doc = trecho.replace("muito bom", "adequado")
        if n in self.perder_marcador_em:
            doc = re.sub(r"⟦BLOCO_\d+⟧", "", doc)
        alteracoes = "- [Vício de linguagem] \"muito bom\" → \"adequado\" — adjetivo vago\n"
        alteracoes += f"- [Pendente] {self.pendencia}\n"
        texto = f"<alteracoes>\n{alteracoes}</alteracoes>\n<documento>\n{doc}\n</documento>"
        return RespostaIA(texto=texto, custo_usd=self.custo, tokens_entrada=100, tokens_saida=50)
