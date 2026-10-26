# -*- coding: utf-8 -*-
"""Operações longas (busca, correção, revisão) em threads, com eventos e cancelamento.

A mesma peça serve a web (eventos via SSE) e pode servir a CLI/Tk. A função da
operação recebe (op, emitir, cancelar) e retorna o resultado serializável.
"""

import queue
import threading
import uuid

from .modelos import Operacao


class OperacaoEmAndamento(RuntimeError):
    """Já existe uma revisão por IA executando."""


class Cancelado(Exception):
    """A função da operação pode levantar isto ao perceber o cancelamento."""


EXCLUSIVAS = {"revisao"}  # só uma por vez


class GerenciadorOperacoes:
    def __init__(self, max_guardadas=200):
        self._ops = {}
        self._eventos = {}
        self._assinantes = []
        self._trava = threading.Lock()
        self._max = max_guardadas

    # ── Eventos ──────────────────────────────────────────────────────────────
    def assinar(self):
        q = queue.Queue()
        with self._trava:
            self._assinantes.append(q)
        return q

    def cancelar_assinatura(self, q):
        with self._trava:
            if q in self._assinantes:
                self._assinantes.remove(q)

    def publicar(self, evento, dados):
        with self._trava:
            alvos = list(self._assinantes)
        for q in alvos:
            q.put((evento, dados))

    # ── Operações ────────────────────────────────────────────────────────────
    def obter(self, op_id):
        return self._ops.get(op_id)

    def em_execucao(self, tipo):
        return [o for o in self._ops.values()
                if o.tipo == tipo and o.estado in ("executando", "cancelando")]

    def iniciar(self, tipo, funcao):
        with self._trava:
            if tipo in EXCLUSIVAS and any(o.tipo == tipo and o.estado in ("executando", "cancelando")
                                          for o in self._ops.values()):
                raise OperacaoEmAndamento("Já há uma revisão com IA em andamento. "
                                          "Aguarde terminar ou cancele.")
            op = Operacao(id=uuid.uuid4().hex[:12], tipo=tipo)
            cancelar = threading.Event()
            self._ops[op.id] = op
            self._eventos[op.id] = cancelar
            self._limpar()

        def emitir(evento, **dados):
            if evento == "progresso":
                op.progresso.feito = dados.get("feito", op.progresso.feito)
                op.progresso.total = dados.get("total", op.progresso.total)
                op.progresso.mensagem = dados.get("mensagem", op.progresso.mensagem)
            self.publicar(evento, {"operacao_id": op.id, **dados})

        def rodar():
            try:
                resultado = funcao(op, emitir, cancelar)
            except Cancelado:
                resultado = None
                cancelar.set()
            except Exception as exc:  # noqa: BLE001 — vira evento para a tela
                op.estado, op.erro = "erro", str(exc) or exc.__class__.__name__
                self.publicar("erro", {"operacao_id": op.id, "erro": op.erro,
                                       "acao": getattr(exc, "acao", "")})
                return
            op.resultado = resultado
            if cancelar.is_set():
                op.estado = "cancelada"
                self.publicar("cancelado", {"operacao_id": op.id, "resultado": resultado})
            else:
                op.estado = "concluida"
                self.publicar("concluido", {"operacao_id": op.id, "tipo": op.tipo,
                                            "resultado": resultado})

        threading.Thread(target=rodar, daemon=True, name=f"op-{tipo}-{op.id}").start()
        return op

    def cancelar(self, op_id):
        op = self._ops.get(op_id)
        if not op:
            return None
        if op.estado == "executando":
            op.estado = "cancelando"
            self._eventos[op_id].set()
        return op

    def _limpar(self):
        terminadas = [o for o in self._ops.values() if o.estado not in ("executando", "cancelando")]
        excesso = len(self._ops) - self._max
        for o in sorted(terminadas, key=lambda o: o.criada_em)[:max(0, excesso)]:
            self._ops.pop(o.id, None)
            self._eventos.pop(o.id, None)
