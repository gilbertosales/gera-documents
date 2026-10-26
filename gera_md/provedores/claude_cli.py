# -*- coding: utf-8 -*-
"""Claude pelo Claude Code CLI (research R1 e R2).

Dois tipos de acesso sobre o mesmo comando `claude -p`:

- ClaudeAssinatura (padrão): usa o login Pro/Max já feito na máquina. O processo
  filho roda SEM variáveis de chave/provedor, o login é conferido com
  `claude auth status --json` (authMethod "claude.ai") e cada chamada é abortada
  se o Claude Code anunciar outra fonte de credencial (apiKeySource ≠ "none").
  Nunca usa --bare: nesse modo o Claude Code ignora o login da assinatura.
- ClaudeApi: mesma chamada com ANTHROPIC_API_KEY lida do cofre do sistema
  (keyring) só no momento do envio. Cobrado por uso.
"""

from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time

from .base import (AcessoIncorreto, Cancelado, EstadoProvedor, FalhaProvedor, LimiteAtingido,
                   LoginNecessario, ProvedorIA, RespostaIA)

VARIAVEIS_DE_CREDENCIAL = (
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
    "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
)
MODELOS = ["padrão", "sonnet", "opus", "haiku"]
TIMEOUT_ESTADO = 10
TIMEOUT_ENVIO = 900  # segundos por trecho
SERVICO_KEYRING = "gera-documents"
USUARIO_KEYRING = "anthropic-api-key"

_RE_LOGIN = re.compile(r"log ?in|logged|authenticat|oauth|401|credencia|expired|expirad", re.I)
_RE_LIMITE = re.compile(r"usage limit|rate limit|limit reached|limite|429|quota|overloaded", re.I)


def executavel():
    return shutil.which("claude")


def _comando(exe, args):
    cmd = [exe, *args]
    if exe.lower().endswith((".cmd", ".bat")):
        cmd = ["cmd", "/c", *cmd]
    return cmd


def _matar(proc):
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        proc.kill()


def _erro_de_texto(texto):
    texto = (texto or "").strip() or "erro desconhecido do Claude Code"
    if _RE_LIMITE.search(texto):
        return LimiteAtingido(f"Limite de uso atingido: {texto[:200]}")
    if _RE_LOGIN.search(texto):
        return LoginNecessario(f"Login necessário: {texto[:200]}")
    return FalhaProvedor(texto[:300])


class ClaudeCli(ProvedorIA):
    modo = "assinatura"

    def modelos(self):
        return list(MODELOS)

    # ── ambiente do processo filho ───────────────────────────────────────────
    def _chave(self):
        return None

    def _ambiente(self):
        env = {k: v for k, v in os.environ.items() if k.upper() not in VARIAVEIS_DE_CREDENCIAL}
        chave = self._chave()
        if chave:
            env["ANTHROPIC_API_KEY"] = chave
        return env

    def _rodar(self, args, timeout):
        exe = executavel()
        if not exe:
            raise FileNotFoundError("claude")
        return subprocess.run(_comando(exe, args), capture_output=True, timeout=timeout,
                              env=self._ambiente(), cwd=tempfile.gettempdir(),
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def _auth_status(self):
        """dict do `claude auth status --json`, ou EstadoProvedor em caso de falha."""
        if not executavel():
            return EstadoProvedor("nao_instalado", "Comando 'claude' não encontrado no PATH.")
        try:
            proc = self._rodar(["auth", "status", "--json"], TIMEOUT_ESTADO)
        except subprocess.TimeoutExpired:
            return EstadoProvedor("erro", "O Claude Code não respondeu à verificação de login.")
        except OSError as exc:
            return EstadoProvedor("erro", f"Não foi possível executar o Claude Code ({exc}).")
        try:
            dados = json.loads(proc.stdout.decode("utf-8", "replace"))
        except ValueError:
            return EstadoProvedor("erro", "Não foi possível ler o estado do login. "
                                          "Atualize o Claude Code (versão 2.1 ou mais nova).")
        return dados if isinstance(dados, dict) else EstadoProvedor("erro", "Resposta inesperada.")

    # ── envio ────────────────────────────────────────────────────────────────
    def _conferir_fonte(self, fonte):
        """Levanta AcessoIncorreto se a credencial usada não for a do tipo de acesso."""
        if fonte != "none":
            raise AcessoIncorreto("O Claude Code tentou usar chave de API no modo assinatura "
                                  f"(fonte: {fonte}). Nada foi enviado como cobrança por uso.")

    def enviar(self, prompt, sistema, modelo, cancelar=None):
        exe = executavel()
        if not exe:
            raise LoginNecessario("Comando 'claude' não encontrado. Instale o Claude Code e faça login.")
        args = ["-p", "--output-format", "stream-json", "--verbose", "--tools", "",
                "--no-session-persistence", "--append-system-prompt-file", sistema]
        if modelo and modelo != "padrão":
            args += ["--model", modelo]
        try:
            proc = subprocess.Popen(_comando(exe, args), stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    env=self._ambiente(), cwd=tempfile.gettempdir(),
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as exc:
            raise FalhaProvedor(f"Não foi possível executar o Claude Code ({exc}).")

        linhas, erros = queue.Queue(), []

        def ler_saida():
            for linha in proc.stdout:
                linhas.put(linha)
            linhas.put(None)

        def ler_erros():
            erros.append(proc.stderr.read())

        threading.Thread(target=ler_saida, daemon=True).start()
        threading.Thread(target=ler_erros, daemon=True).start()
        try:
            proc.stdin.write(prompt.encode("utf-8"))
            proc.stdin.close()
        except OSError:
            pass

        resultado, fim = None, time.monotonic() + TIMEOUT_ENVIO
        try:
            while True:
                if cancelar is not None and cancelar.is_set():
                    raise Cancelado("Revisão cancelada.")
                if time.monotonic() > fim:
                    raise FalhaProvedor("O Claude Code demorou demais para responder.")
                try:
                    linha = linhas.get(timeout=0.5)
                except queue.Empty:
                    continue
                if linha is None:
                    break
                try:
                    msg = json.loads(linha.decode("utf-8", "replace"))
                except ValueError:
                    continue
                if msg.get("type") == "system" and msg.get("subtype") == "init":
                    self._conferir_fonte(msg.get("apiKeySource", ""))
                elif msg.get("type") == "result":
                    resultado = msg
        except BaseException:
            _matar(proc)
            raise
        proc.wait(timeout=10)

        if resultado is None:
            stderr = b"".join(e for e in erros if e).decode("utf-8", "replace")
            raise _erro_de_texto(stderr or "o Claude Code terminou sem resposta")
        if resultado.get("is_error"):
            raise _erro_de_texto(str(resultado.get("result") or resultado.get("subtype") or ""))
        uso = resultado.get("usage") or {}
        entrada = sum(int(uso.get(k) or 0) for k in
                      ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
        return RespostaIA(texto=str(resultado.get("result") or ""),
                          custo_usd=float(resultado.get("total_cost_usd") or 0),
                          tokens_entrada=entrada, tokens_saida=int(uso.get("output_tokens") or 0))


class ClaudeAssinatura(ClaudeCli):
    id = "claude-assinatura"
    nome = "Claude (Pro/Max)"
    tipo_acesso = "assinatura"
    cobranca = "limite_assinatura"
    padrao = True

    def instrucoes_login(self):
        if not executavel():
            return ["Instale o Claude Code (https://claude.com/claude-code)",
                    "Abra um terminal e execute: claude auth login",
                    "Entre com a conta do plano Pro ou Max",
                    "Volte aqui e clique em Verificar de novo"]
        return ["Abra um terminal", "Execute: claude auth login",
                "Entre com a conta do plano Pro ou Max",
                "Volte aqui e clique em Verificar de novo"]

    def estado(self):
        dados = self._auth_status()
        if isinstance(dados, EstadoProvedor):
            return dados
        if not dados.get("loggedIn"):
            return EstadoProvedor("login_necessario", "O Claude Code não está logado.")
        metodo = dados.get("authMethod")
        if metodo != "claude.ai":
            return EstadoProvedor("login_necessario",
                                  f"O Claude Code está logado por outro método ({metodo}); "
                                  "faça login com a conta do plano Pro/Max.")
        plano = dados.get("subscriptionType")
        return EstadoProvedor("logado", f"Plano: {plano}" if plano else "Conta claude.ai")


class ClaudeApi(ClaudeCli):
    id = "claude-api"
    nome = "Claude — API (cobrado por uso)"
    tipo_acesso = "api"
    cobranca = "por_uso"
    padrao = False
    modo = "api"

    @staticmethod
    def _keyring():
        try:
            import keyring  # import tardio: só o modo API precisa
        except ImportError:
            return None
        return keyring

    def _chave(self):
        kr = self._keyring()
        if kr is None:
            return None
        try:
            return kr.get_password(SERVICO_KEYRING, USUARIO_KEYRING)
        except Exception:  # noqa: BLE001 — cofre indisponível
            return None

    def salvar_chave(self, chave):
        kr = self._keyring()
        if kr is None:
            raise FalhaProvedor("Instale: pip install keyring")
        kr.set_password(SERVICO_KEYRING, USUARIO_KEYRING, chave)

    def remover_chave(self):
        kr = self._keyring()
        if kr is None:
            return
        try:
            kr.delete_password(SERVICO_KEYRING, USUARIO_KEYRING)
        except Exception:  # noqa: BLE001 — já não existia
            pass

    def instrucoes_login(self):
        return ["Crie uma chave em console.anthropic.com (cobrança por uso, separada da assinatura)",
                "Informe a chave em Acesso por API (opcional) e clique em Salvar"]

    def estado(self):
        if self._keyring() is None:
            return EstadoProvedor("erro", "Instale: pip install keyring")
        if not executavel():
            return EstadoProvedor("nao_instalado", "Comando 'claude' não encontrado no PATH.")
        if not self._chave():
            return EstadoProvedor("chave_ausente", "Nenhuma chave de API configurada.")
        return EstadoProvedor("logado", "Chave de API configurada (cobrança por uso)")

    def _conferir_fonte(self, fonte):
        if fonte in ("", "none"):
            raise AcessoIncorreto("O Claude Code não usou a chave de API configurada.")
