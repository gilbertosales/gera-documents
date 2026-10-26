# -*- coding: utf-8 -*-
"""Rotas sem IA: pasta, análise, correção, relatório, abrir arquivo, Word e comparação."""

import os
import subprocess
import sys
import uuid

from starlette.concurrency import run_in_threadpool
from starlette.routing import Route

from .. import config
from ..analise import analisar, encontrar_mds
from ..comparacao import comparar
from ..correcao import corrigir_md
from ..modelos import Analise, Correcao
from ..relatorio import escrever_relatorio
from .seguranca import ErroApi, validar_caminho

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GERAR_WORD = os.path.join(RAIZ, "gerar_word.py")
RELATORIO_PADRAO = os.path.join(RAIZ, "relatorio_analise_md.md")

_ESCOLHER_PASTA = (
    "import sys, tkinter as tk\n"
    "from tkinter import filedialog\n"
    "r = tk.Tk(); r.withdraw(); r.attributes('-topmost', True)\n"
    "p = filedialog.askdirectory(title='Pasta com os arquivos .md (local ou de rede)',"
    " initialdir=sys.argv[1] or None)\n"
    "sys.stdout.write(p or '')\n"
)


def abrir_no_sistema(path):
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])


def reanalisar_se_mudou(analise, r):
    """Se o arquivo mudou no disco desde a análise, refaz (edge case da spec)."""
    try:
        mtime = os.path.getmtime(r.caminho)
    except OSError:
        raise ErroApi(400, f"Arquivo não encontrado: {r.rotulo}", "Busque a pasta de novo.")
    if mtime == r.modificado_em:
        return r, False
    novo = analisar(r.caminho, analise.pasta, origem=r.origem, tipo_versao=r.tipo_versao)
    novo.correcoes, novo.revisao = r.correcoes, r.revisao
    analise.inserir(novo)
    return novo, True


def evento_arquivo(analise, r):
    idx = next(i for i, a in enumerate(analise.arquivos) if a.caminho == r.caminho)
    return {"analise_id": analise.id, "arquivo": r.to_dict(), "depois_de": r.origem, "indice": idx}


def rotas(estado):
    from .app import json_ok, ler_json  # import tardio: evita ciclo

    def caminho_valido(analise, caminho, permitir_relatorio=False):
        return validar_caminho(caminho, analise.pasta, estado.extras, permitir_relatorio)

    async def obter_config(_request):
        return json_ok(config.obter())

    async def escolher_pasta(request):
        dados = await ler_json(request)
        inicial = dados.get("inicial") or ""

        def dialogo():
            try:
                proc = subprocess.run([sys.executable, "-c", _ESCOLHER_PASTA, inicial],
                                      capture_output=True, timeout=600)
            except (OSError, subprocess.TimeoutExpired):
                return None
            return os.path.normpath(proc.stdout.decode("utf-8", "replace")) if proc.stdout else None

        return json_ok({"pasta": await run_in_threadpool(dialogo)})

    async def criar_analise(request):
        dados = await ler_json(request)
        pasta = (dados.get("pasta") or "").strip().strip('"')
        if not pasta:
            raise ErroApi(400, "Informe a pasta.", "Digite o caminho ou clique em Procurar...")
        pasta = os.path.realpath(os.path.normpath(pasta))
        if not await run_in_threadpool(os.path.isdir, pasta):
            raise ErroApi(400, f"Pasta não encontrada ou sem acesso: {pasta}",
                          "Confira o caminho, a conexão com a rede e a sua permissão de leitura.")
        subpastas = bool(dados.get("subpastas", True))
        analise = Analise(id=uuid.uuid4().hex[:12], pasta=pasta, subpastas=subpastas)
        estado.analises[analise.id] = analise
        try:
            config.registrar_pasta(pasta)
        except (OSError, ValueError):
            pass

        def buscar(op, emitir, cancelar):
            falhas = []
            n = 0
            for md in encontrar_mds(pasta, subpastas, cancelar, onerror=falhas.append):
                r = analisar(md, pasta)
                analise.inserir(r)
                n += 1
                emitir("arquivo", **evento_arquivo(analise, r))
                emitir("progresso", feito=n, total=None, mensagem=f"Analisando... {n} arquivo(s)")
            erros = sum(a.erros for a in analise.arquivos)
            avisos = sum(a.avisos for a in analise.arquivos)
            return {"analise_id": analise.id, "total": n, "erros": erros, "avisos": avisos,
                    "falhas": [f"{getattr(f, 'filename', '') or ''}: {f.strerror or f}" for f in falhas]}

        op = estado.gerenciador.iniciar("busca", buscar)
        return json_ok({"analise_id": analise.id, "operacao_id": op.id}, 202)

    async def obter_analise(request):
        return json_ok(estado.analise(request.path_params["id"]).to_dict())

    async def obter_arquivo(request):
        analise = estado.analise(request.path_params["id"])
        caminho = caminho_valido(analise, request.query_params.get("caminho"))
        r = analise.obter(caminho)
        if not r:
            raise ErroApi(404, "Arquivo não está nesta análise.")
        return json_ok(r.to_dict())

    async def criar_correcoes(request):
        dados = await ler_json(request)
        analise = estado.analise(dados.get("analise_id"))
        alvo = dados.get("caminhos")
        if alvo == "todos_com_problema":
            caminhos = [a.caminho for a in analise.arquivos if a.situacao != "OK"]
            if not caminhos:
                raise ErroApi(400, "Nenhum arquivo com problemas para corrigir.")
        elif isinstance(alvo, list) and alvo:
            caminhos = [caminho_valido(analise, c) for c in alvo]
        else:
            raise ErroApi(400, "Selecione um ou mais arquivos.")

        def corrigir(op, emitir, cancelar):
            criados, sem_mudanca, restantes = [], [], 0
            for k, path in enumerate(caminhos, 1):
                if cancelar.is_set():
                    break
                emitir("progresso", feito=k - 1, total=len(caminhos),
                       mensagem=f"Corrigindo {k}/{len(caminhos)}: {os.path.basename(path)}")
                r = analise.obter(path) or analisar(path, analise.pasta)
                r, mudou = reanalisar_se_mudou(analise, r)
                if mudou:
                    emitir("arquivo", **evento_arquivo(analise, r))
                if r.situacao == "OK" and len(caminhos) > 1:
                    continue
                v2, fixes = corrigir_md(path)
                if not fixes:
                    os.remove(v2)
                    sem_mudanca.append(path)
                    continue
                novo = analisar(v2, analise.pasta, origem=path, tipo_versao="correcao")
                novo.correcoes = [Correcao(n, msg) for n, msg in fixes]
                analise.inserir(novo, depois_de=path)
                restantes += novo.erros + novo.avisos
                criados.append(novo.to_dict())
                emitir("arquivo", **evento_arquivo(analise, novo))
            emitir("progresso", feito=len(caminhos), total=len(caminhos), mensagem="Correção concluída")
            return {"analise_id": analise.id, "criados": criados, "sem_mudanca": sem_mudanca,
                    "restantes": restantes}

        op = estado.gerenciador.iniciar("correcao", corrigir)
        return json_ok({"operacao_id": op.id}, 202)

    async def salvar_relatorio(request):
        dados = await ler_json(request)
        analise = estado.analise(dados.get("analise_id"))
        destino = dados.get("destino") or RELATORIO_PADRAO
        if not destino.lower().endswith(".md"):
            raise ErroApi(400, "O relatório precisa ter extensão .md.")
        resultados = [(a.caminho, [(x.nivel, x.linha, x.mensagem) for x in a.achados])
                      for a in analise.arquivos]
        try:
            await run_in_threadpool(escrever_relatorio, analise.pasta, resultados, destino)
        except OSError as exc:
            raise ErroApi(400, f"Não foi possível salvar o relatório: {exc}",
                          "Escolha outra pasta de destino.")
        estado.extras.add(destino)
        return json_ok({"caminho": destino})

    async def abrir(request):
        dados = await ler_json(request)
        analise = estado.analise(dados.get("analise_id"))
        # único ponto que aceita relatórios: o link "Abrir relatório" (FR-030)
        caminho = caminho_valido(analise, dados.get("caminho"), permitir_relatorio=True)
        if not os.path.exists(caminho):
            raise ErroApi(404, "Arquivo não encontrado.")
        await run_in_threadpool(abrir_no_sistema, caminho)
        return json_ok({}, 200)

    async def gerar_word(request):
        dados = await ler_json(request)
        analise = estado.analise(dados.get("analise_id"))
        caminho = caminho_valido(analise, dados.get("caminho"))
        subprocess.Popen([sys.executable, GERAR_WORD, caminho], cwd=RAIZ)
        return json_ok({}, 200)

    async def comparacao(request):
        analise = estado.analise(request.query_params.get("analise_id"))
        a = caminho_valido(analise, request.query_params.get("a"))
        b = caminho_valido(analise, request.query_params.get("b"))
        try:
            blocos = await run_in_threadpool(comparar, a, b)
        except OSError as exc:
            raise ErroApi(400, f"Não foi possível ler os arquivos: {exc}")
        return json_ok({"a": a, "b": b, "blocos": blocos})

    return [
        Route("/api/config", obter_config),
        Route("/api/pastas/escolher", escolher_pasta, methods=["POST"]),
        Route("/api/analises", criar_analise, methods=["POST"]),
        Route("/api/analises/{id}", obter_analise),
        Route("/api/analises/{id}/arquivo", obter_arquivo),
        Route("/api/correcoes", criar_correcoes, methods=["POST"]),
        Route("/api/relatorios", salvar_relatorio, methods=["POST"]),
        Route("/api/abrir", abrir, methods=["POST"]),
        Route("/api/word", gerar_word, methods=["POST"]),
        Route("/api/comparacao", comparacao),
    ]
