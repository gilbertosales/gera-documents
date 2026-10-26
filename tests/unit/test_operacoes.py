import queue
import threading
import time

import pytest

from gera_md.operacoes import GerenciadorOperacoes, OperacaoEmAndamento


def _eventos(q, ate, timeout=5):
    out, fim = [], time.time() + timeout
    while time.time() < fim:
        try:
            ev, dados = q.get(timeout=0.1)
        except queue.Empty:
            continue
        out.append((ev, dados))
        if ev in ate:
            return out
    raise AssertionError(f"sem evento final: {out}")


def test_eventos_em_ordem():
    g = GerenciadorOperacoes()
    q = g.assinar()

    def f(op, emitir, cancelar):
        for i in range(3):
            emitir("progresso", feito=i + 1, total=3, mensagem=f"{i + 1}/3")
        return {"ok": True}

    op = g.iniciar("busca", f)
    evs = _eventos(q, {"concluido"})
    assert [e for e, _ in evs] == ["progresso"] * 3 + ["concluido"]
    assert evs[-1][1]["resultado"] == {"ok": True}
    assert g.obter(op.id).estado == "concluida" and g.obter(op.id).progresso.feito == 3


def test_cancelar():
    g = GerenciadorOperacoes()
    q = g.assinar()
    iniciou = threading.Event()

    def f(op, emitir, cancelar):
        iniciou.set()
        while not cancelar.is_set():
            time.sleep(0.01)
        return {"parcial": True}

    op = g.iniciar("busca", f)
    iniciou.wait(2)
    assert g.cancelar(op.id).estado == "cancelando"
    evs = _eventos(q, {"cancelado"})
    assert evs[-1][0] == "cancelado"
    assert g.obter(op.id).estado == "cancelada"


def test_revisao_exclusiva():
    g = GerenciadorOperacoes()
    libera = threading.Event()
    op = g.iniciar("revisao", lambda op, e, c: libera.wait(5))
    with pytest.raises(OperacaoEmAndamento):
        g.iniciar("revisao", lambda op, e, c: None)
    g.iniciar("busca", lambda op, e, c: None)  # outros tipos seguem livres
    libera.set()
    for _ in range(100):
        if g.obter(op.id).estado == "concluida":
            break
        time.sleep(0.02)
    g.iniciar("revisao", lambda op, e, c: None)


def test_excecao_vira_evento_erro():
    g = GerenciadorOperacoes()
    q = g.assinar()

    def f(op, emitir, cancelar):
        raise RuntimeError("pasta sumiu")

    op = g.iniciar("busca", f)
    evs = _eventos(q, {"erro"})
    assert evs[-1][1]["erro"] == "pasta sumiu"
    assert g.obter(op.id).estado == "erro"
