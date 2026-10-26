# -*- coding: utf-8 -*-
"""Proteções do servidor local (research R4).

- só 127.0.0.1 (o bind é feito em __main__.py);
- Host precisa ser 127.0.0.1:<porta> ou localhost:<porta> (contra DNS rebinding);
- Origin, quando presente em POST/PUT/DELETE, precisa ser o próprio servidor (contra CSRF);
- toda rota /api/* exige o cookie de sessão criado a partir do token da URL inicial.
"""

import json
import os
import secrets

METODOS_ESCRITA = {"POST", "PUT", "DELETE", "PATCH"}


class ErroApi(Exception):
    """Erro exibível: vira {"erro", "acao"} com o status HTTP."""

    def __init__(self, status, erro, acao="", **extra):
        super().__init__(erro)
        self.status, self.erro, self.acao, self.extra = status, erro, acao, extra


def gerar_token():
    return secrets.token_urlsafe(32)


def nome_cookie(porta):
    return f"gera_sessao_{porta}"


def hosts_permitidos(porta):
    return {f"127.0.0.1:{porta}", f"localhost:{porta}"}


def origens_permitidas(porta):
    return {f"http://{h}" for h in hosts_permitidos(porta)}


def _cookie(headers, nome):
    for item in headers.get("cookie", "").split(";"):
        k, _, v = item.strip().partition("=")
        if k == nome:
            return v
    return None


class MiddlewareSeguranca:
    """ASGI puro (não atrapalha o streaming do SSE)."""

    def __init__(self, app, token, porta):
        self.app, self.token, self.porta = app, token, porta
        self.hosts = hosts_permitidos(porta)
        self.origens = origens_permitidas(porta)
        self.cookie = nome_cookie(porta)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        if headers.get("host", "") not in self.hosts:
            return await _negar(send, 403, "Acesso permitido só pelo endereço local (127.0.0.1).")
        origem = headers.get("origin")
        if scope["method"] in METODOS_ESCRITA and origem and origem not in self.origens:
            return await _negar(send, 403, "Requisição de outra origem recusada.")
        if scope["path"].startswith("/api/"):
            valor = _cookie(headers, self.cookie)
            if not valor or not secrets.compare_digest(valor, self.token):
                return await _negar(send, 401, "Sessão inválida.",
                                    "Feche esta aba e abra a ferramenta de novo pelo atalho.")
        return await self.app(scope, receive, send)


async def _negar(send, status, erro, acao=""):
    corpo = json.dumps({"erro": erro, "acao": acao}, ensure_ascii=False).encode("utf-8")
    await send({"type": "http.response.start", "status": status,
                "headers": [(b"content-type", b"application/json; charset=utf-8"),
                            (b"content-length", str(len(corpo)).encode())]})
    await send({"type": "http.response.body", "body": corpo})


def _dentro(caminho, pasta):
    c, p = os.path.normcase(caminho), os.path.normcase(pasta)
    try:
        return os.path.commonpath([c, p]) == p
    except ValueError:  # unidades diferentes
        return False


def validar_caminho(caminho, pasta_analise, extras=(), permitir_relatorio=False):
    """Caminho absoluto real de um .md dentro da pasta da análise (ou em `extras`).
    Relatórios da ferramenta só passam com permitir_relatorio (rota de abrir, FR-030).
    Qualquer outra coisa → ErroApi 400."""
    from ..analise import eh_relatorio

    if not caminho or not isinstance(caminho, str):
        raise ErroApi(400, "Caminho de arquivo não informado.")
    real = os.path.realpath(caminho)
    if not real.lower().endswith((".md", ".markdown")):
        raise ErroApi(400, "Só arquivos .md podem ser usados aqui.")
    if eh_relatorio(real) and not permitir_relatorio:
        raise ErroApi(400, "Relatórios não podem ser usados como documento.",
                      "Selecione o documento (por exemplo, nome_v3.md), não o relatório _revisao.md.")
    extras_reais = {os.path.normcase(os.path.realpath(e)) for e in extras}
    if os.path.normcase(real) in extras_reais:
        return real
    if not pasta_analise or not _dentro(real, os.path.realpath(pasta_analise)):
        raise ErroApi(400, "O arquivo não pertence à pasta analisada.",
                      "Busque de novo a pasta que contém o arquivo.")
    return real
