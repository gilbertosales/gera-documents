# Contrato: adaptador de provedor de IA (`gera_md/provedores/base.py`)

Todo provedor implementa a mesma interface. O núcleo de revisão (`gera_md/revisao.py`)
conhece apenas esta interface, nunca um provedor específico.

## Interface

```text
ProvedorIA
  id: str                       # "claude-assinatura", "claude-api", futuros: "codex-assinatura"...
  nome: str
  tipo_acesso: "assinatura" | "api"
  cobranca: "limite_assinatura" | "por_uso"
  padrao: bool
  modelos() -> list[str]
  estado() -> EstadoProvedor    # não consome uso da IA; deve terminar em ≤ 10 s
  instrucoes_login() -> list[str]
  enviar(prompt: str, sistema: str, modelo: str, cancelar: Event) -> RespostaIA

EstadoProvedor
  estado: "logado" | "login_necessario" | "nao_instalado" | "chave_ausente" | "erro"
  detalhe: str                  # sem e-mail, token ou chave

RespostaIA
  texto: str
  custo_usd: float
  tokens_entrada: int
  tokens_saida: int

Exceções de enviar():
  LoginNecessario      # sessão expirada / não logado → estado volta a login_necessario
  LimiteAtingido       # limite da assinatura ou quota
  AcessoIncorreto      # ex.: modo assinatura detectou uso de chave de API
  Cancelado            # cancelar.set() durante a chamada; processo filho encerrado
  FalhaProvedor        # qualquer outro erro (mensagem em pt-BR)
```

## Obrigações

1. `enviar` MUST NOT ser chamado pelo núcleo sem a confirmação do usuário (a camada de
   operações garante isso; o provedor não confirma).
2. `estado()` e `enviar()` MUST verificar `cancelar` e encerrar o processo filho em ≤ 5 s
   após `cancelar.set()`.
3. Provedores de `tipo_acesso = "assinatura"` MUST NOT usar chave de API, mesmo que exista
   no ambiente.
4. Nenhum provedor grava credenciais em arquivo; chaves de API são lidas do cofre do
   sistema só no momento da chamada.

## Implementações nesta versão

| id | Como | `estado()` | Garantia de acesso |
|---|---|---|---|
| `claude-assinatura` | `claude -p --output-format stream-json --verbose --tools "" --no-session-persistence --append-system-prompt-file <tmp> [--model m]`, cwd temporário, ambiente sem variáveis de chave/provedor (research R1) | `claude auth status --json` → `loggedIn` e `authMethod == "claude.ai"` | `system/init.apiKeySource == "none"`, senão `AcessoIncorreto` |
| `claude-api` | mesmo comando com `ANTHROPIC_API_KEY` vinda do `keyring` | chave presente no cofre → `logado`; senão `chave_ausente` | `apiKeySource != "none"` |
| `simulado` (testes) | devolve o trecho com alterações previsíveis; pode simular erro, atraso e limite | configurável | — |

## Como adicionar uma IA futura

Criar uma classe em `gera_md/provedores/`, registrá-la em `provedores/__init__.py` e
adicionar testes de `estado()` e `enviar()` com processo simulado. Nenhum outro módulo muda.
