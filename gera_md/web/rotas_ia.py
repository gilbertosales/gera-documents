# -*- coding: utf-8 -*-
"""Rotas de IA: provedores, skills, prévia/confirmação, revisão e chave de API."""

import os

from starlette.concurrency import run_in_threadpool
from starlette.routing import Route

from .. import config, provedores, revisao
from ..provedores.base import FalhaProvedor
from .seguranca import ErroApi, validar_caminho


def _provedor(provedor_id):
    p = provedores.obter(provedor_id) if provedor_id else provedores.padrao()
    if not p:
        raise ErroApi(400, "IA não reconhecida.", "Escolha uma IA da lista.")
    return p


def _aviso(p):
    if p.cobranca == "por_uso":
        return ("Acesso por API: será COBRADO POR USO na sua conta da API, "
                "separado da assinatura.")
    return ("Assinatura — sem cobrança extra (consome o limite do plano). "
            "Nenhuma chave de API é usada.")


def rotas(estado):
    from .app import json_ok, ler_json
    from .rotas_analise import evento_arquivo

    async def listar_provedores(request):
        atualizar = request.query_params.get("atualizar") == "1"

        def montar():
            return [p.to_dict(provedores.estado(p, atualizar)) for p in provedores.listar()]

        return json_ok(await run_in_threadpool(montar))

    async def listar_skills(_request):
        prefs = config.obter()
        padrao = prefs.get("skill_padrao") or revisao.SKILL_PADRAO
        return json_ok([{"nome": s, "padrao": s == padrao} for s in revisao.listar_skills()])

    def _caminhos(dados):
        analise = estado.analise(dados.get("analise_id"))
        caminhos = dados.get("caminhos")
        if not isinstance(caminhos, list) or not caminhos:
            raise ErroApi(400, "Selecione um ou mais arquivos na lista.")
        return analise, [validar_caminho(c, analise.pasta) for c in caminhos]

    def _pronto(p, atualizar=False):
        e = provedores.estado(p, atualizar)
        if e.estado != "logado":
            raise ErroApi(409, f"{p.nome}: {e.detalhe}", "Siga os passos para fazer login.",
                          instrucoes_login=p.instrucoes_login(), provedor=p.to_dict(e))
        return e

    async def previa(request):
        dados = await ler_json(request)
        analise, caminhos = _caminhos(dados)
        p = _provedor(dados.get("provedor"))

        def montar():
            arquivos = []
            for c in caminhos:
                try:
                    _l, _t, _b, trechos = revisao.preparar(c)
                except UnicodeDecodeError:
                    raise ErroApi(400, f"{os.path.basename(c)} não está em UTF-8.",
                                  "Crie a versão corrigida antes de revisar com IA.")
                arquivos.append({"caminho": c, "rotulo": os.path.relpath(c, analise.pasta),
                                 "trechos": len(trechos)})
            return arquivos

        arquivos = await run_in_threadpool(montar)
        return json_ok({"arquivos": arquivos, "provedor": p.id, "nome": p.nome,
                        "tipo_acesso": p.tipo_acesso, "cobranca": p.cobranca,
                        "rotulo_acesso": p.rotulo_acesso(), "aviso": _aviso(p),
                        "skill": dados.get("skill") or revisao.SKILL_PADRAO,
                        "modelo": dados.get("modelo") or "padrão"})

    async def iniciar_revisao(request):
        dados = await ler_json(request)
        if dados.get("confirmado") is not True:
            raise ErroApi(409, "A revisão precisa ser confirmada antes do envio.",
                          "Confirme na janela que lista os arquivos e a IA.")
        analise, caminhos = _caminhos(dados)
        p = _provedor(dados.get("provedor"))
        skill = dados.get("skill") or revisao.SKILL_PADRAO
        if skill not in revisao.listar_skills():
            raise ErroApi(400, f"Skill não encontrada: {skill}")
        modelo = dados.get("modelo") or "padrão"
        if modelo not in p.modelos():
            raise ErroApi(400, f"Modelo não disponível: {modelo}")
        await run_in_threadpool(_pronto, p, True)
        try:
            # FR-025: a IA padrão lembrada é sempre de assinatura, nunca de API
            prefs = {"skill_padrao": skill, "modelo_padrao": modelo}
            if p.tipo_acesso == "assinatura":
                prefs["provedor_padrao"] = p.id
            config.salvar_preferencias(**prefs)
        except (OSError, ValueError):
            pass

        def revisar(op, emitir, cancelar):
            feitos, erros = [], []
            uso_total = {"custo_usd": 0.0, "tokens_entrada": 0, "tokens_saida": 0}
            n = len(caminhos)
            for k, path in enumerate(caminhos, 1):
                if cancelar.is_set():
                    break
                prefixo = f"[{k}/{n}] {os.path.basename(path)}: "

                def progresso(msg, feito=0, total=0, prefixo=prefixo):
                    emitir("progresso", feito=k - 1, total=n, mensagem=prefixo + msg,
                           trecho=feito, trechos=total)

                try:
                    rev, novo = revisao.revisar_md(path, p, skill, modelo, progresso, cancelar,
                                                   analise.pasta)
                except (OSError, UnicodeDecodeError, FalhaProvedor) as exc:
                    erros.append({"caminho": path, "erro": str(exc)})
                    continue
                for chave in uso_total:
                    uso_total[chave] += getattr(rev.uso, chave)
                if rev.cancelada:
                    break
                if novo is not None:
                    analise.inserir(novo, depois_de=path)
                    emitir("arquivo", **evento_arquivo(analise, novo))
                else:
                    # texto sem diferença: nenhuma versão; o relatório fica ligado ao original
                    original = analise.obter(path)
                    if original is not None:
                        original.revisao = rev
                        emitir("arquivo", **evento_arquivo(analise, original))
                feitos.append(rev.to_dict())
                if rev.login_expirado:
                    provedores.invalidar(p.id)
                    emitir("provedor", provedor=p.to_dict(provedores.estado(p, True)))
                if rev.erro_fatal:
                    erros.append({"caminho": path, "erro": rev.erro_fatal})
                    break
            return {"analise_id": analise.id, "feitos": feitos, "erros": erros,
                    "uso": uso_total, "provedor": p.id, "cobranca": p.cobranca,
                    "aviso": _aviso(p)}

        try:
            op = estado.gerenciador.iniciar("revisao", revisar)
        except RuntimeError as exc:
            raise ErroApi(409, str(exc), "Aguarde a revisão atual terminar ou cancele-a.")
        return json_ok({"operacao_id": op.id}, 202)

    async def chave_api(request):
        p = provedores.obter("claude-api")
        if not p:
            raise ErroApi(404, "Acesso por API indisponível.")
        if request.method == "DELETE":
            await run_in_threadpool(p.remover_chave)
        else:
            dados = await ler_json(request)
            chave = (dados.get("chave") or "").strip()
            if len(chave) < 20:
                raise ErroApi(400, "Chave de API inválida.", "Cole a chave completa (sk-ant-...).")
            try:
                await run_in_threadpool(p.salvar_chave, chave)
            except FalhaProvedor as exc:
                raise ErroApi(400, str(exc), "Instale o pacote e tente de novo.")
            except Exception as exc:  # noqa: BLE001 — cofre do sistema indisponível
                raise ErroApi(400, f"Não foi possível gravar no cofre do sistema: {exc}")
        provedores.invalidar(p.id)
        return json_ok(p.to_dict(await run_in_threadpool(provedores.estado, p, True)))

    return [
        Route("/api/provedores", listar_provedores),
        Route("/api/skills", listar_skills),
        Route("/api/revisoes/previa", previa, methods=["POST"]),
        Route("/api/revisoes", iniciar_revisao, methods=["POST"]),
        Route("/api/provedores/claude-api/chave", chave_api, methods=["PUT", "DELETE"]),
    ]
