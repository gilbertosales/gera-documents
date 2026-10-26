"""Claude pela assinatura: sem chave de API, login conferido e fonte da credencial verificada (SC-004)."""

import io
import json
import subprocess
import threading
import time

import pytest

from gera_md.provedores import claude_cli
from gera_md.provedores.base import AcessoIncorreto, Cancelado, LimiteAtingido, LoginNecessario
from gera_md.provedores.claude_cli import VARIAVEIS_DE_CREDENCIAL, ClaudeAssinatura


class Proc:
    """Popen falso: devolve as linhas de stream-json informadas."""

    def __init__(self, linhas, travar=False, stderr=b""):
        self._linhas = [json.dumps(l).encode() + b"\n" if isinstance(l, dict) else l for l in linhas]
        self._travar = travar
        self._morto = threading.Event()
        self.stdin = io.BytesIO()
        self.stdin.close = lambda: None
        self.stderr = io.BytesIO(stderr)
        self.pid = 4321
        self.returncode = None

    @property
    def stdout(self):
        for l in self._linhas:
            yield l
        if self._travar:
            self._morto.wait(30)

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.returncode = 0
        return 0

    def matar(self):
        self._morto.set()
        self.returncode = -9


@pytest.fixture
def ambiente(monkeypatch):
    """Ambiente com chaves de API 'esquecidas' + claude falso no PATH."""
    for v in VARIAVEIS_DE_CREDENCIAL:
        monkeypatch.setenv(v, "valor-que-nao-pode-vazar")
    monkeypatch.setattr(claude_cli, "executavel", lambda: r"C:\fake\claude.exe")
    chamadas = {"run": [], "popen": []}

    def fake_matar(proc):
        proc.matar()

    monkeypatch.setattr(claude_cli, "_matar", fake_matar)
    return chamadas


def _auth(monkeypatch, chamadas, saida, codigo=0):
    def fake_run(cmd, **kw):
        chamadas["run"].append((cmd, kw))
        return subprocess.CompletedProcess(cmd, codigo, json.dumps(saida).encode() if isinstance(saida, dict) else saida, b"")
    monkeypatch.setattr(claude_cli.subprocess, "run", fake_run)


def _popen(monkeypatch, chamadas, proc):
    def fake_popen(cmd, **kw):
        chamadas["popen"].append((cmd, kw))
        return proc
    monkeypatch.setattr(claude_cli.subprocess, "Popen", fake_popen)


INIT_OK = {"type": "system", "subtype": "init", "apiKeySource": "none"}
RESULTADO = {"type": "result", "is_error": False, "result": "<documento>\nx\n</documento>",
             "total_cost_usd": 0.12, "usage": {"input_tokens": 10, "cache_read_input_tokens": 5,
                                               "output_tokens": 7}}


def test_estado_logado_sem_email(monkeypatch, ambiente):
    _auth(monkeypatch, ambiente, {"loggedIn": True, "authMethod": "claude.ai", "subscriptionType": "pro",
                                  "email": "alguem@exemplo.com", "orgId": "x"})
    e = ClaudeAssinatura().estado()
    assert e.estado == "logado" and e.detalhe == "Plano: pro"
    assert "@" not in json.dumps(ClaudeAssinatura().to_dict(e))
    cmd, kw = ambiente["run"][0]
    assert cmd[1:] == ["auth", "status", "--json"]
    assert not any(v in kw["env"] for v in VARIAVEIS_DE_CREDENCIAL)


def test_estado_nao_logado(monkeypatch, ambiente):
    _auth(monkeypatch, ambiente, {"loggedIn": False})
    e = ClaudeAssinatura().estado()
    assert e.estado == "login_necessario"
    assert any("claude auth login" in p for p in ClaudeAssinatura().instrucoes_login())


def test_estado_outro_metodo(monkeypatch, ambiente):
    _auth(monkeypatch, ambiente, {"loggedIn": True, "authMethod": "api_key"})
    e = ClaudeAssinatura().estado()
    assert e.estado == "login_necessario" and "api_key" in e.detalhe


def test_estado_nao_instalado(monkeypatch):
    monkeypatch.setattr(claude_cli, "executavel", lambda: None)
    assert ClaudeAssinatura().estado().estado == "nao_instalado"


def test_estado_resposta_invalida(monkeypatch, ambiente):
    _auth(monkeypatch, ambiente, b"comando desconhecido", 1)
    assert ClaudeAssinatura().estado().estado == "erro"


def test_enviar_ambiente_limpo_e_sem_bare(monkeypatch, ambiente):
    _popen(monkeypatch, ambiente, Proc([INIT_OK, RESULTADO]))
    r = ClaudeAssinatura().enviar("prompt", "sistema.md", "sonnet")
    assert r.texto.startswith("<documento>") and r.custo_usd == 0.12
    assert r.tokens_entrada == 15 and r.tokens_saida == 7
    cmd, kw = ambiente["popen"][0]
    assert "--bare" not in cmd
    assert cmd[cmd.index("--output-format") + 1] == "stream-json" and "--verbose" in cmd
    assert cmd[cmd.index("--tools") + 1] == "" and "--no-session-persistence" in cmd
    assert cmd[cmd.index("--model") + 1] == "sonnet"
    assert not any(v in kw["env"] for v in VARIAVEIS_DE_CREDENCIAL)


def test_enviar_recusa_chave_de_api(monkeypatch, ambiente):
    proc = Proc([{"type": "system", "subtype": "init", "apiKeySource": "ANTHROPIC_API_KEY"}, RESULTADO])
    _popen(monkeypatch, ambiente, proc)
    with pytest.raises(AcessoIncorreto):
        ClaudeAssinatura().enviar("p", "s", "padrão")
    assert proc.returncode == -9  # processo encerrado antes da resposta


def test_enviar_sessao_expirada(monkeypatch, ambiente):
    erro = {"type": "result", "is_error": True, "result": "Invalid API key · Please run /login"}
    _popen(monkeypatch, ambiente, Proc([INIT_OK, erro]))
    with pytest.raises(LoginNecessario):
        ClaudeAssinatura().enviar("p", "s", "padrão")


def test_enviar_limite(monkeypatch, ambiente):
    erro = {"type": "result", "is_error": True, "result": "Claude AI usage limit reached|1760000000"}
    _popen(monkeypatch, ambiente, Proc([INIT_OK, erro]))
    with pytest.raises(LimiteAtingido):
        ClaudeAssinatura().enviar("p", "s", "padrão")


def test_enviar_sem_resultado_usa_stderr(monkeypatch, ambiente):
    _popen(monkeypatch, ambiente, Proc([INIT_OK], stderr=b"Not logged in"))
    with pytest.raises(LoginNecessario):
        ClaudeAssinatura().enviar("p", "s", "padrão")


def test_cancelar_mata_processo_rapido(monkeypatch, ambiente):
    proc = Proc([INIT_OK], travar=True)
    _popen(monkeypatch, ambiente, proc)
    cancelar = threading.Event()
    threading.Timer(0.2, cancelar.set).start()
    t0 = time.monotonic()
    with pytest.raises(Cancelado):
        ClaudeAssinatura().enviar("p", "s", "padrão", cancelar)
    assert time.monotonic() - t0 < 5  # SC-007
    assert proc.returncode == -9


def test_registro_padrao_e_assinatura():
    from gera_md import provedores
    p = provedores.padrao()
    assert p.id == "claude-assinatura" and p.tipo_acesso == "assinatura"
    assert not provedores.obter("claude-api").padrao
