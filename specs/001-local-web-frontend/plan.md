# Implementation Plan: Frontend Web Local com Várias IAs via Login

**Branch**: `001-local-web-frontend` | **Date**: 2026-10-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-local-web-frontend/spec.md`

## Summary

Criar um frontend web que roda só na máquina do usuário para analisar, corrigir, revisar
com IA e comparar arquivos `.md` antes de gerar o Word. A lógica hoje presa na tela Tk de
`analisar_md.py` e em `revisar_md.py` é movida, sem mudar o comportamento, para um pacote
de núcleo (`gera_md/`) usado igualmente pela CLI, pela tela Tk e pelo novo servidor web.

A IA é acessada por adaptadores. O padrão é o **Claude Pro/Max pela assinatura**, chamado
pelo Claude Code logado com o ambiente limpo de chaves e verificado por `auth status` e
`apiKeySource`. A **API** existe como um tipo de acesso separado, com a chave guardada no
cofre do sistema operacional. O servidor é Starlette/uvicorn em `127.0.0.1`, com token de
sessão. O frontend é HTML/JS puro, sem build, e recebe o progresso por SSE.

## Technical Context

**Language/Version**: Python 3.10+ (desenvolvimento em 3.14); JavaScript ES2020 no navegador

**Primary Dependencies**: `python-docx` (existente), `starlette` + `uvicorn` (servidor
local), `keyring` (somente para o modo API); Claude Code CLI ≥ 2.1 instalado e logado
(externo)

**Storage**: arquivos no disco (`.md`, versões `_vN`, relatórios); `ultima_pasta` em
`gerar_word_config.json` (compartilhado com a tela Tk e o `gerar_word.py`); pastas recentes e
preferências em `gera_documents_config.json` (sem segredos); chave de API no
Gerenciador de Credenciais do Windows / keychain

**Testing**: pytest + `starlette.testclient`; provedor de IA simulado; snapshots dourados

**Target Platform**: Windows 10/11 (principal, com pastas UNC); Linux/macOS compatíveis;
navegadores Edge/Chrome/Firefox atuais

**Project Type**: aplicação local (servidor web local + frontend estático) sobre biblioteca
de núcleo com CLI

**Performance Goals**: primeiros resultados em ≤ 3 s numa pasta local de 200 arquivos
(SC-002); cancelamento efetivo em ≤ 5 s (SC-007); a tela nunca bloqueia durante operações

**Constraints**: só `127.0.0.1`; nenhum envio de conteúdo sem confirmação; modo assinatura
nunca usa chave de API; originais nunca alterados; o caminho sem IA pela CLI e pela tela Tk
funciona só com Python + `python-docx` (constituição); o frontend web é opcional e exige
também `starlette` + `uvicorn`, importados apenas por `gera_md/web/`

**Scale/Scope**: uso individual; pastas de até ~1.000 `.md`; documentos de até ~5.000
linhas; 5 telas/painéis (pasta e lista, detalhes, comparação, IA, configurações de acesso)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Como o plano atende | Status |
|---|---|---|
| I. Original Intocável | `versoes.py` único com criação exclusiva (`open "x"`); nenhuma rota escreve no caminho original; teste de integração confere hash do original | ✅ |
| II. Fidelidade ao Conversor | regras movidas sem alteração, ainda importando `parse_table_row`/`is_separator` de `gerar_word.py`; snapshots dourados (R7) | ✅ |
| III. Local-First, IA por Login | servidor em `127.0.0.1`; `ProvedorIA` com registro; Claude assinatura padrão com ambiente limpo e dupla verificação (R1); API separada com `keyring` (R2); confirmação obrigatória antes do envio (`/api/revisoes` exige `confirmado: true`) | ✅ |
| IV. Núcleo Separado da Interface | pacote `gera_md/` sem import de UI; Tk, CLI e web só chamam o núcleo; resultados em dataclasses serializáveis | ✅ |
| V. IA Protegida e Auditável | `proteger`/`restaurar` e validações atuais preservadas; reanálise da versão revisada; uso/custo por arquivo e total | ✅ |
| VI. Interface Responsiva e Clara | operações em threads com SSE e cancelamento (R5); pt-BR; situação com texto + cor; filtros/ordenação; achado com trecho da linha | ✅ |
| VII. Regras Testáveis e Idempotentes | testes positivo/negativo por regra; teste de idempotência de `corrigir`; provedor simulado | ✅ |
| Restrições: dependências justificadas | `starlette`/`uvicorn` (servidor local, já instalados), `keyring` (FR-026, só modo API, import tardio) | ✅ |

**Resultado**: nenhum desvio; Complexity Tracking não se aplica.

**Re-check pós-design (Phase 1)**: os contratos HTTP e de provedor e o modelo de dados
mantêm todos os itens acima. Pontos observados: (a) `POST /api/revisoes` sem
`confirmado: true` retorna 409 (III); (b) o provedor `claude-api` nunca aparece como
`padrao: true` (FR-025); (c) a rota de arquivo só aceita caminhos dentro da pasta da
análise atual (I e segurança). ✅

## Project Structure

### Documentation (this feature)

```text
specs/001-local-web-frontend/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── http-api.md      # rotas JSON + eventos SSE do servidor local
│   └── provedor-ia.md   # interface dos adaptadores de IA
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
gera_md/                      # núcleo — sem dependência de UI
├── __init__.py
├── modelos.py                # dataclasses: Achado, ResultadoArquivo, Correcao, Revisao...
├── analise.py                # analisar_arquivo, contar, encontrar_mds (movidos de analisar_md.py)
├── correcao.py               # corrigir_md e auxiliares (movidos)
├── versoes.py                # proxima_versao única, gravação exclusiva
├── relatorio.py              # escrever_relatorio (movido)
├── revisao.py                # proteger/restaurar, trechos, revisar_md (movidos de revisar_md.py)
├── comparacao.py             # diff entre versões (difflib)
├── operacoes.py              # gerenciador de operações: progresso, eventos, cancelamento
├── config.py                 # pastas recentes e preferências (gera_documents_config.json)
├── provedores/
│   ├── __init__.py           # registro: listar(), obter(id)
│   ├── base.py               # ProvedorIA, EstadoProvedor, RespostaIA
│   ├── claude_cli.py         # ClaudeAssinatura e ClaudeApi (mesmo adaptador, modos distintos)
│   └── simulado.py           # provedor falso para testes
└── web/
    ├── __main__.py           # python -m gera_md.web → sobe servidor e abre navegador
    ├── app.py                # rotas Starlette (contrato em contracts/http-api.md)
    ├── seguranca.py          # token de sessão, Host/Origin, validação de caminhos
    └── static/
        ├── index.html
        ├── app.js            # estado da tela, chamadas à API, SSE
        ├── componentes/      # lista.js, detalhes.js, comparacao.js, painel-ia.js
        └── estilo.css

analisar_md.py                # CLI + tela Tk, agora importando de gera_md (mesma interface)
revisar_md.py                 # CLI fina sobre gera_md.revisao (reexporta funções públicas)
gerar_word.py                 # inalterado
Gera Documents.cmd            # atalho Windows: python -m gera_md.web
requirements.txt              # python-docx, starlette, uvicorn, keyring

tests/
├── fixtures/                 # .md de exemplo por regra + pasta de amostra
├── golden/                   # snapshots gerados com o código atual (antes da refatoração)
├── unit/                     # analise, correcao (idempotência), versoes, revisao, comparacao, provedores
└── integration/              # rotas web com TestClient + provedor simulado; CLI
```

**Structure Decision**: projeto único em Python com o núcleo `gera_md/` e o frontend
estático servido pelo próprio pacote (`gera_md/web/static`). Não há projeto separado de
frontend porque não existe etapa de build. Os scripts na raiz continuam sendo pontos de
entrada compatíveis (FR-028).

## Complexity Tracking

Sem violações à constituição; seção não aplicável.
