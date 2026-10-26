# -*- coding: utf-8 -*-
"""Aplicação Starlette do frontend local (contrato: specs/001-local-web-frontend/contracts/http-api.md)."""

import asyncio
import json
import os
import queue
import secrets

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from ..operacoes import GerenciadorOperacoes
from . import rotas_analise, rotas_ia
from .seguranca import ErroApi, MiddlewareSeguranca, nome_cookie

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
HEARTBEAT = 15  # segundos


class Estado:
    """Estado da sessão em memória: análises, operações e arquivos extras abríveis."""

    def __init__(self, token, porta, gerenciador=None):
        self.token, self.porta = token, porta
        self.gerenciador = gerenciador or GerenciadorOperacoes()
        self.analises = {}
        self.extras = set()  # relatórios gravados fora da pasta analisada

    def analise(self, analise_id):
        a = self.analises.get(analise_id)
        if not a:
            raise ErroApi(404, "Análise não encontrada.", "Clique em Buscar de novo.")
        return a


async def ler_json(request: Request) -> dict:
    try:
        dados = await request.json()
    except (ValueError, UnicodeDecodeError):
        raise ErroApi(400, "Requisição inválida (JSON esperado).")
    if not isinstance(dados, dict):
        raise ErroApi(400, "Requisição inválida (objeto JSON esperado).")
    return dados


def json_ok(dados, status=200):
    return JSONResponse(dados, status_code=status)


def criar_app(token=None, porta=8765, gerenciador=None):
    token = token or secrets.token_urlsafe(32)
    estado = Estado(token, porta, gerenciador)

    async def inicio(request: Request):
        t = request.query_params.get("t")
        if t is not None:
            if not secrets.compare_digest(t, token):
                return JSONResponse({"erro": "Link de acesso inválido.",
                                     "acao": "Abra a ferramenta pelo atalho de novo."}, 401)
            resp = RedirectResponse("/", status_code=303)
            resp.set_cookie(nome_cookie(porta), token, httponly=True, samesite="strict", path="/")
            return resp
        cookie = request.cookies.get(nome_cookie(porta))
        if not cookie or not secrets.compare_digest(cookie, token):
            return JSONResponse({"erro": "Sessão inválida.",
                                 "acao": "Abra a ferramenta pelo atalho (o link traz o acesso)."}, 401)
        with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as f:
            return Response(f.read(), media_type="text/html; charset=utf-8",
                            headers={"Cache-Control": "no-store"})

    async def eventos(request: Request):
        q = estado.gerenciador.assinar()

        async def gerar():
            try:
                yield "retry: 2000\n\n"
                ocioso = 0.0
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        evento, dados = q.get_nowait()
                    except queue.Empty:
                        await asyncio.sleep(0.1)
                        ocioso += 0.1
                        if ocioso >= HEARTBEAT:
                            ocioso = 0.0
                            yield ": ping\n\n"
                        continue
                    ocioso = 0.0
                    yield f"event: {evento}\ndata: {json.dumps(dados, ensure_ascii=False)}\n\n"
            finally:
                estado.gerenciador.cancelar_assinatura(q)

        return StreamingResponse(gerar(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    async def operacao(request: Request):
        op = estado.gerenciador.obter(request.path_params["id"])
        if not op:
            raise ErroApi(404, "Operação não encontrada.")
        return json_ok(op.to_dict())

    async def cancelar(request: Request):
        op = estado.gerenciador.cancelar(request.path_params["id"])
        if not op:
            raise ErroApi(404, "Operação não encontrada.")
        return json_ok(op.to_dict(), 202)

    async def erro_api(_request, exc: ErroApi):
        return JSONResponse({"erro": exc.erro, "acao": exc.acao, **exc.extra}, exc.status)

    async def erro_404(_request, _exc):
        return JSONResponse({"erro": "Não encontrado.", "acao": ""}, 404)

    rotas = [
        Route("/", inicio),
        Route("/api/eventos", eventos),
        Route("/api/operacoes/{id}", operacao),
        Route("/api/operacoes/{id}/cancelar", cancelar, methods=["POST"]),
        *rotas_analise.rotas(estado),
        *rotas_ia.rotas(estado),
        Mount("/static", StaticFiles(directory=STATIC), name="static"),
    ]
    app = Starlette(routes=rotas, exception_handlers={ErroApi: erro_api, 404: erro_404})
    app.state.estado = estado
    asgi = MiddlewareSeguranca(app, token, porta)
    asgi.estado = estado
    return asgi
