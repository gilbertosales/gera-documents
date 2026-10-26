---

description: "Task list for Frontend Web Local com Várias IAs via Login"
---

# Tasks: Frontend Web Local com Várias IAs via Login

**Input**: Design documents from `specs/001-local-web-frontend/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: incluídos. A constituição (princípio VII) exige testes positivo/negativo por regra,
idempotência da correção e testes do núcleo sem UI e sem IA real; o quickstart.md lista os
testes esperados.

**Organization**: tarefas agrupadas por história de usuário (spec.md): US1 e US2 são P1,
US3 é P2, US4 é P3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: história de usuário (US1–US4)
- Caminhos relativos à raiz do repositório (`gera-documents/`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: estrutura de pastas, dependências e base de testes. Os snapshots dourados MUST
ser gerados **antes** de qualquer mudança em `analisar_md.py` ou `revisar_md.py`.

- [X] T001 Criar a estrutura do plano com `__init__.py` vazios: `gera_md/`, `gera_md/provedores/`, `gera_md/web/`, `gera_md/web/static/componentes/`, `tests/`, `tests/unit/`, `tests/integration/`, `tests/golden/`, `tests/fixtures/amostra/`
- [X] T002 Criar `requirements.txt` na raiz com `python-docx`, `starlette`, `uvicorn`, `keyring` e um comentário explicando que `keyring` só é usado no modo API
- [X] T003 [P] Criar arquivos de exemplo em `tests/fixtures/amostra/`, um por regra de `analisar_arquivo`: sem H1; tabela sem separador; tabela com colunas a mais/a menos; `<br>` em célula; Mermaid; título nível 6; `##Título` sem espaço; lista com TAB; sublista com 4 espaços; marcador `+`; numeração `1)`; checklist `[ ]`/`[x]`; lista/título dentro de `>`; imagem da internet; imagem inexistente; texto após imagem; imagem no meio do texto; link `[t](url)` e `[t](#ancora)`; `~~riscado~~`; `__negrito__`; `_itálico_`; tag HTML; âncora `<a id="x"></a>` (não deve gerar aviso); nota `[^1]`; bloco ``` não fechado; arquivo em cp1252; arquivo OK (zero achados); subpasta `sub/` com um `.md`; pasta ignorada `node_modules/` com um `.md`; `img/existe.png` (PNG 1×1) referenciada por um arquivo
- [X] T004 [P] Criar `tests/conftest.py` com fixtures: `amostra` (cópia de `tests/fixtures/amostra` em `tmp_path`), `hash_arquivos(pasta) -> dict[caminho, sha256]` e inserção da raiz do repositório no `sys.path`
- [X] T005 Criar `tests/golden/gerar_snapshots.py`, que importa o `analisar_md.py` **atual**, roda `analisar_arquivo` e `corrigir_md` sobre uma cópia de `tests/fixtures/amostra` e grava em `tests/golden/snapshots/` um JSON por arquivo (`achados`, `correcoes`, conteúdo da `_v2` ou `null`) e o relatório de `escrever_relatorio`, com a linha `**Data:**` normalizada para `**Data:** <DATA>` e os caminhos relativos à pasta
- [X] T006 Rodar `python tests/golden/gerar_snapshots.py` e conferir que `tests/golden/snapshots/` foi preenchido (depende de T003, T005)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: núcleo `gera_md/` sem UI, gerenciador de operações e esqueleto seguro do servidor.

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [X] T007 Criar `gera_md/modelos.py` com dataclasses e `to_dict()` conforme data-model.md: `Achado(nivel: "ERRO"|"AVISO"|"INFO", linha: int (0 = arquivo inteiro), mensagem, trecho: str|None "até 200 caracteres")`, `Correcao(linha, descricao)`, `ResultadoArquivo(caminho, rotulo, versao: int|None, origem: str|None, tipo_versao: "original"|"correcao"|"revisao_ia", achados, erros, avisos, situacao: "Corrigir"|"Revisar"|"OK", correcoes, revisao, modificado_em)`, `Analise(id, pasta, subpastas, iniciada_em, arquivos)`, `Revisao(...)` e `Operacao(id, tipo: "busca"|"correcao"|"revisao", estado: "executando"|"concluida"|"cancelando"|"cancelada"|"erro", progresso{feito, total|None, mensagem}, resultado)`. Regra: `situacao` = "`Corrigir` se erros > 0; `Revisar` se avisos > 0; senão `OK`"
- [X] T008 [P] Criar `gera_md/versoes.py` com `proxima_versao(md_path)` (lógica idêntica a `proximo_v2`/`proxima_versao` atuais), `numero_versao(path) -> int|None` e `gravar_nova_versao(md_path, texto) -> str`, que tenta `open(destino, "x", encoding="utf-8", newline="\n")` e, em `FileExistsError`, recalcula o próximo número livre (nunca sobrescreve)
- [X] T009 Criar `gera_md/analise.py` movendo de `analisar_md.py`, **sem alterar a lógica**: regexes (`_ANCORA`, `_HTML_TAG`, `_BR`, `_LINK`, `_IMG`, `_ITEM_LISTA`, `_H1`), `_sem_codigo_inline`, `_fora_do_codigo`, `analisar_arquivo`, `contar`, `encontrar_mds` (aceitando `cancelar: threading.Event|None`, verificado a cada arquivo) e `PASTAS_IGNORADAS`; continuar importando `is_separator`, `parse_table_row` e `titulo_do_md` de `gerar_word.py`. Adicionar `analisar(md_path, pasta_base) -> ResultadoArquivo`, que envolve `analisar_arquivo` e preenche `trecho` com a linha correspondente (≤ 200 caracteres) (depende de T007)
- [X] T010 Criar `gera_md/correcao.py` movendo `_corrigir_inline`, `_titulo_pelo_nome` e `corrigir_md` sem alterar a lógica; a gravação final passa a usar `versoes.gravar_nova_versao`. Assinatura pública mantida: `corrigir_md(md_path) -> (destino, [(linha, descricao)])` (depende de T008, T009)
- [X] T011 [P] Criar `gera_md/relatorio.py` movendo `escrever_relatorio(pasta, resultados, saida)` sem alteração (depende de T009)
- [X] T012 [P] Criar `gera_md/config.py` sobre `carregar_config`/`salvar_config` de `gerar_word.py`: `obter()`, `registrar_pasta(pasta)` (atualiza `ultima_pasta` e `pastas_recentes`, "máx. 10", mais recente primeiro, sem duplicatas) e `salvar_preferencias(provedor_padrao, skill_padrao, modelo_padrao)`; rejeitar qualquer chave cujo nome contenha `chave`, `key` ou `token` ("**Nunca** contém chave de API")
- [X] T013 Criar `gera_md/operacoes.py`: `GerenciadorOperacoes` com `iniciar(tipo, funcao) -> Operacao` (thread daemon; `funcao(op, emitir, cancelar)`), `cancelar(id)` (estado `cancelando` → `cancelada` quando a função retorna), `obter(id)`, `assinar() -> queue.Queue` / `cancelar_assinatura(q)` para eventos `progresso|arquivo|concluido|erro|cancelado|provedor`, e a regra "Só uma operação `revisao` pode estar `executando` por vez" (`OperacaoEmAndamento`) (depende de T007)
- [X] T014 Refatorar `analisar_md.py` para importar de `gera_md.analise`, `gera_md.correcao`, `gera_md.relatorio` e `gera_md.versoes`, mantendo os nomes públicos (`analisar_arquivo`, `contar`, `corrigir_md`, `encontrar_mds`, `escrever_relatorio`, `proximo_v2 = proxima_versao`), a CLI (`--relatorio`, `--v2`, `--saida`) e a tela Tk sem mudança visível (depende de T009–T011)
- [X] T015 Criar `tests/golden/test_golden.py`, que roda o núcleo novo sobre uma cópia da amostra e compara com `tests/golden/snapshots/` (achados, correções, conteúdo da `_v2`, relatório normalizado); deve passar 100% (SC-003) (depende de T006, T014)
- [X] T016 [P] Criar `tests/unit/test_analise.py`, com um teste positivo (achado com nível e mensagem esperados) e um negativo (variação correta sem achado) para cada regra listada em T003, além de `encontrar_mds` ignorando `node_modules` e pastas com `.` e parando quando `cancelar` é acionado
- [X] T017 [P] Criar `tests/unit/test_correcao.py`: para cada arquivo da amostra, `corrigir_md` não altera o original (hash); a `_v2` não tem mais `ERRO` que o original; rodar `corrigir_md` sobre a `_v2` não gera correções novas (idempotência; a `_v3` extra é removida pelo teste); cp1252 → `_v2` em UTF-8
- [X] T018 [P] Criar `tests/unit/test_versoes.py`: `a.md` → `a_v2.md`; `a_v2.md` → `a_v3.md`; números ocupados são pulados; duas threads chamando `gravar_nova_versao` ao mesmo tempo geram arquivos distintos
- [X] T019 [P] Criar `tests/unit/test_operacoes.py`: eventos chegam na ordem; cancelar leva a `cancelada`; segunda revisão simultânea levanta `OperacaoEmAndamento`; exceção na função vira evento `erro` com mensagem
- [X] T020 Criar `gera_md/web/seguranca.py`: `gerar_token()` (`secrets.token_urlsafe(32)`); middleware que (a) responde 403 se `Host` não for `127.0.0.1:<porta>` ou `localhost:<porta>`, (b) responde 403 em POST/PUT/DELETE com `Origin` diferente desses, (c) responde 401 em `/api/*` sem o cookie `sessao` igual ao token; `validar_caminho(caminho, pasta_analise) -> str` que resolve com `os.path.realpath`, exige extensão `.md`/`.markdown` e que o caminho esteja dentro da pasta da análise (senão `ValueError` → 400)
- [X] T021 Criar `gera_md/web/app.py` com `criar_app(token, porta, gerenciador)`: `GET /?t=<token>` define o cookie `sessao` (`HttpOnly`, `SameSite=Strict`) e redireciona para `/` (token inválido → 401); arquivos estáticos de `gera_md/web/static`; `GET /api/eventos` (SSE via `StreamingResponse`, `text/event-stream`, heartbeat a cada 15 s, repassando os eventos de `GerenciadorOperacoes`); `GET /api/operacoes/{id}`; `POST /api/operacoes/{id}/cancelar` → 202; tratador de erros no formato `{"erro": "...", "acao": "..."}` com os códigos 400/401/403/404/409 de contracts/http-api.md; montagem de rotas a partir de `rotas_analise.py` e `rotas_ia.py` (inicialmente vazios) (depende de T013, T020)
- [X] T022 Criar `gera_md/web/__main__.py`: escolhe a porta 8765 ou a próxima livre, gera o token, sobe o uvicorn **somente** em `127.0.0.1`, abre o navegador em `http://127.0.0.1:<porta>/?t=<token>` e imprime a URL e "Ctrl+C para sair" (depende de T021)
- [X] T023 [P] Criar `gera_md/web/static/index.html` (`lang="pt-BR"`, título "Gera Documents"), `gera_md/web/static/estilo.css` (tokens de cor em `:root`, tema escuro com `prefers-color-scheme`, layout com barra da pasta, lista à esquerda, detalhes à direita, barra de ações e de status; coluna única abaixo de 900 px) e `gera_md/web/static/app.js` (módulo ES: `api(metodo, url, corpo)` que trata `{erro, acao}` exibindo a mensagem; conexão `EventSource('/api/eventos')` com reconexão; barra de status com `aria-live="polite"`)
- [X] T024 [P] Criar `tests/integration/test_seguranca.py` com `starlette.testclient`: `/api/config` sem cookie → 401; `Host: 192.168.0.10:8765` → 403; POST com `Origin: http://exemplo.com` → 403; `/?t=errado` → 401; `/?t=<token>` define o cookie; `validar_caminho` recusa `..\\fora.md`, `.txt` e caminho fora da pasta
- [X] T025 [P] Criar `Gera Documents.cmd` na raiz: `cd /d "%~dp0"` e `python -m gera_md.web`, com mensagem clara se o Python não for encontrado

**Checkpoint**: núcleo extraído com snapshots passando, CLI e Tk funcionando como antes, servidor seguro subindo com tela vazia.

---

## Phase 3: User Story 1 - Analisar e corrigir uma pasta pelo navegador (Priority: P1) 🎯 MVP

**Goal**: buscar, filtrar, ver problemas no contexto, criar versões corrigidas, salvar o relatório, abrir o arquivo e gerar o Word pelo navegador, sem IA.

**Independent Test**: numa máquina sem IA configurada, analisar `tests/fixtures/amostra`, criar as `_v2` e conferir que os originais ficaram intactos e que as `_v2` aparecem com menos problemas (quickstart seção 3).

### Tests for User Story 1

- [X] T026 [P] [US1] Criar `tests/integration/test_analise_web.py`: `POST /api/analises` com a pasta da amostra → 202, e os eventos `arquivo` chegam para todos os `.md` (exceto `node_modules`) antes de `concluido`; pasta inexistente → 400 com `acao`; `GET /api/analises/{id}/arquivos/...` traz `achados[].trecho`; `POST /api/correcoes` com `"todos_com_problema"` cria as `_v2` com `tipo_versao="correcao"` e `origem` preenchida; hashes dos originais iguais antes e depois (SC-005); `POST /api/relatorios` grava o relatório; caminho fora da análise → 400; arquivo alterado após a análise (mtime) é reanalisado antes de corrigir

### Implementation for User Story 1

- [X] T027 [US1] Criar `gera_md/web/rotas_analise.py` com `GET /api/config`, `POST /api/pastas/escolher` (executa `python -c` com `tkinter.filedialog.askdirectory` em subprocesso, retorna `{pasta}` ou `{pasta: null}`), `POST /api/analises` (`{pasta, subpastas}`; valida a pasta; chama `config.registrar_pasta`; inicia uma operação `busca` que emite um evento `arquivo` por `.md` com `analise.analisar`; erros de rede viram evento `erro` mantendo os arquivos já analisados), `GET /api/analises/{id}` e `GET /api/analises/{id}/arquivos/{caminho_codificado}`; análises guardadas em memória por id (depende de T021)
- [X] T028 [US1] Adicionar a `gera_md/web/rotas_analise.py`: `POST /api/correcoes` (`{analise_id, caminhos: [str] | "todos_com_problema"}`; operação `correcao`; reanalisa se `modificado_em` mudou; remove a versão criada quando não há correções, como hoje; emite `arquivo` com `depois_de=origem`; resultado `{criados, sem_mudanca}`), `POST /api/relatorios` (`{analise_id, destino?}`; padrão `relatorio_analise_md.md` na pasta dos scripts), `POST /api/abrir` (`os.startfile`/`open`/`xdg-open`; 204) e `POST /api/word` (`subprocess.Popen([sys.executable, gerar_word.py, caminho])`; 204), todos com `validar_caminho` (depende de T027)
- [X] T029 [P] [US1] Criar `gera_md/web/static/componentes/pasta.js`: campo de caminho com lista de `pastas_recentes` (datalist), botão "Procurar..." (`/api/pastas/escolher`), caixa "Subpastas" (padrão marcada), botão "Buscar .md" que vira "Cancelar busca" durante a operação, e mensagem de erro com a ação sugerida
- [X] T030 [P] [US1] Criar `gera_md/web/static/componentes/lista.js`: tabela preenchida pelos eventos `arquivo`, com colunas Arquivo, Erros, Avisos e Situação (texto + cor, FR-008); versões inseridas logo abaixo da origem com recuo; seleção múltipla (Ctrl/Shift e caixas de seleção); filtro por situação (Todos/Corrigir/Revisar/OK) e por nome; ordenação por nome, erros ou avisos; navegação por teclado (setas, Enter abre detalhes)
- [X] T031 [P] [US1] Criar `gera_md/web/static/componentes/detalhes.js`: rótulo do arquivo; problemas agrupados por nível, cada um com "linha N" e o `trecho` em fonte monoespaçada; seção "Correções aplicadas" para versões de correção; dicas iguais às da tela Tk ("Clique em Criar versão corrigida..." / "Os problemas acima não têm correção automática..."); "Nenhum problema encontrado — pronto para o Word. ✔"
- [X] T032 [US1] Integrar em `gera_md/web/static/app.js`: montar `pasta.js`, `lista.js` e `detalhes.js`; barra de ações com "Criar versão corrigida" (sem seleção → confirmação "Criar a versão corrigida dos N arquivo(s) com problemas?"), "Abrir .md", "Gerar Word", "Salvar relatório"; resumo final ("N arquivo(s) .md · E erro(s) · W aviso(s)"); aviso de que restam problemas sem correção automática (depende de T029–T031)

**Checkpoint**: US1 completa. O frontend substitui a tela Tk para tudo que não usa IA.

---

## Phase 4: User Story 2 - Revisar texto com IA usando a assinatura logada (Priority: P1)

**Goal**: revisar arquivos com o Claude Pro/Max logado, sem chave de API, com confirmação, progresso, cancelamento e resultado auditável.

**Independent Test**: com o Claude logado pela assinatura e `ANTHROPIC_API_KEY` falsa no ambiente, revisar um arquivo; a nova versão e o `_revisao.md` são criados, não há uso de API e os blocos protegidos ficam idênticos (quickstart seção 4).

### Tests for User Story 2

- [X] T033 [P] [US2] Criar `tests/unit/test_provedores.py` com `subprocess` simulado (monkeypatch): o ambiente do processo filho não contém `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX` e `CLAUDE_CODE_USE_FOUNDRY`; `auth status` com `loggedIn: true, authMethod: "claude.ai", subscriptionType: "pro"` → `logado` com detalhe "Plano: pro" e sem e-mail; `loggedIn: false` → `login_necessario`; `authMethod` diferente de `claude.ai` → `login_necessario` com explicação; `claude` ausente → `nao_instalado`; stream-json com `system/init.apiKeySource: "ANTHROPIC_API_KEY"` → `AcessoIncorreto` e o processo é encerrado; mensagem `result` → `RespostaIA(texto, custo_usd, tokens_entrada, tokens_saida)`; erro de sessão expirada → `LoginNecessario`; mensagem de limite → `LimiteAtingido`; `cancelar.set()` mata o processo em ≤ 5 s → `Cancelado`; o comando nunca contém `--bare`
- [X] T034 [P] [US2] Criar `tests/unit/test_revisao.py` usando `provedores/simulado.py`: blocos de código, imagens e âncoras idênticos após a revisão (SC-006); resposta sem `<documento>`, com marcador perdido ou curta demais → trecho original e entrada em `falhas`; cancelamento no meio → nenhuma versão gravada e `cancelada=True`; a nova versão é reanalisada (`ResultadoArquivo` com `tipo_versao="revisao_ia"`); relatório `_revisao.md` com o tipo de acesso e a cobrança corretos
- [X] T035 [P] [US2] Criar `tests/integration/test_revisao_web.py` com o provedor simulado registrado: `GET /api/provedores` → `claude-assinatura` com `padrao: true`; `POST /api/revisoes/previa` lista arquivos e trechos e traz o aviso "Assinatura — sem cobrança extra (consome o limite do plano)"; `POST /api/revisoes` sem `confirmado: true` → 409; segunda revisão simultânea → 409; provedor não logado → 409 com `instrucoes_login`; eventos `progresso` por trecho e `concluido` com `Revisao`; `POST /api/operacoes/{id}/cancelar` → `cancelado`

### Implementation for User Story 2

- [X] T036 [US2] Criar `gera_md/provedores/base.py` conforme contracts/provedor-ia.md: classe abstrata `ProvedorIA` (`id`, `nome`, `tipo_acesso: "assinatura"|"api"`, `cobranca: "limite_assinatura"|"por_uso"`, `padrao`, `modelos()`, `estado()`, `instrucoes_login()`, `enviar(prompt, sistema, modelo, cancelar)`), `EstadoProvedor(estado: "logado"|"login_necessario"|"nao_instalado"|"chave_ausente"|"erro", detalhe)` ("sem e-mail, token ou chave"), `RespostaIA` e as exceções `LoginNecessario`, `LimiteAtingido`, `AcessoIncorreto`, `Cancelado`, `FalhaProvedor`
- [X] T037 [US2] Criar `gera_md/provedores/claude_cli.py` com `ClaudeCli(modo)` e `ClaudeAssinatura(ClaudeCli)` (`id="claude-assinatura"`, nome "Claude (Pro/Max)", `padrao=True`, modelos `padrão, sonnet, opus, haiku`): `_ambiente()` remove as variáveis listadas em T033; `estado()` roda `claude auth status --json` (timeout 10 s); `enviar()` usa `Popen` com `-p --output-format stream-json --verbose --tools "" --no-session-persistence --append-system-prompt-file <arquivo> [--model m]`, `cwd=tempfile.gettempdir()`, `CREATE_NO_WINDOW`, prompt por stdin, leitura linha a linha, checagem de `apiKeySource == "none"` no `system/init`, verificação de `cancelar` a cada 0,5 s e mapeamento de erros para as exceções; `.cmd`/`.bat` via `cmd /c` como hoje; `instrucoes_login()` = ["Abra um terminal", "Execute: claude auth login", "Entre com a conta do plano Pro ou Max", "Volte aqui e clique em Verificar de novo"] (depende de T036)
- [X] T038 [P] [US2] Criar `gera_md/provedores/simulado.py`: `ProvedorSimulado` configurável (estado, atraso, falha em N chamadas, perda de marcador, limite atingido) que devolve `<alteracoes>- [Clareza] ...</alteracoes><documento>trecho</documento>` (depende de T036)
- [X] T039 [US2] Criar o registro em `gera_md/provedores/__init__.py`: `registrar(provedor)`, `listar() -> list[ProvedorIA]`, `obter(id)`, `padrao()`; registra `ClaudeAssinatura` por padrão; cache de `estado()` por 30 s com `atualizar=True` para forçar (depende de T037)
- [X] T040 [US2] Criar `gera_md/revisao.py` movendo de `revisar_md.py` (`INSTRUCOES`, `SKILLS_DIR`, `SKILL_PADRAO`, `TAM_TRECHO`, `PARALELO`, `listar_skills`, `carregar_skill`, `proteger`, `restaurar`, `dividir_em_trechos`, `_extrair`, `revisar_trecho`, `revisar_md`) e trocando `_chamar_claude` por `provedor.enviar(...)`; `revisar_md(md_path, provedor, skill, modelo, progresso, cancelar)` não envia trechos novos após `cancelar`, propaga `LoginNecessario`/`LimiteAtingido` como falha com mensagem clara, grava via `versoes.gravar_nova_versao` só se não cancelada, soma `uso` (custo e tokens), escreve no relatório "Equivalente em API (não cobrado no plano Pro/Max)" ou "Cobrado por uso (API)" conforme `provedor.cobranca` e retorna `Revisao` mais o `ResultadoArquivo` reanalisado (depende de T008, T009, T036)
- [X] T041 [US2] Reduzir `revisar_md.py` a uma CLI fina sobre `gera_md.revisao` que reexporta `listar_skills`, `SKILL_PADRAO`, `SKILLS_DIR`, `MODELOS`, `claude_disponivel` e `revisar_md` com a assinatura antiga (`md_path, skill, modelo, progresso`) usando o provedor padrão e devolvendo o dict antigo (`destino, relatorio, custo, contagem, pendencias, falhas, trechos`); adicionar `--provedor` (padrão `claude-assinatura`) (depende de T039, T040)
- [X] T042 [US2] Ajustar a seção de IA de `abrir_tela` em `analisar_md.py` para continuar funcionando com o `revisar_md.py` novo, sem mudança visível (depende de T041)
- [X] T043 [US2] Criar `gera_md/web/rotas_ia.py`: `GET /api/provedores` (`?atualizar=1`), `GET /api/skills`, `POST /api/revisoes/previa` (trechos por arquivo via `proteger` + `dividir_em_trechos`, tipo de acesso, cobrança e texto do aviso), `POST /api/revisoes` (exige `confirmado: true`, senão 409; provedor não logado → 409 com `instrucoes_login`; inicia a operação `revisao` arquivo a arquivo emitindo `progresso` "[k/n] arquivo: Revisando... t/T trecho(s)", `arquivo` (`depois_de=origem`) e `concluido` com totais de uso; `LoginNecessario` emite o evento `provedor` com o estado atualizado); salvar skill, modelo e provedor escolhidos com `config.salvar_preferencias` (depende de T021, T039, T040)
- [X] T044 [P] [US2] Criar `gera_md/web/static/componentes/painel-ia.js`: lista de provedores com selo de estado ("Assinatura — logado" / "Assinatura — login necessário" / "Não instalado"), detalhe do plano, passos de login quando `estado ≠ logado` e botão "Verificar de novo" (`?atualizar=1`); seletores de skill e modelo; botão "Revisar texto (IA)" desabilitado sem seleção ou sem provedor logado
- [X] T045 [US2] Integrar a revisão em `gera_md/web/static/app.js` e `gera_md/web/static/componentes/detalhes.js`: diálogo de confirmação (`<dialog>`) com os dados de `/api/revisoes/previa` (arquivos, trechos, IA, tipo de acesso, aviso de cobrança); progresso por arquivo e trecho com botão "Cancelar"; seção "Revisão de texto com IA" nos detalhes (alterações por categoria, "✖ Trecho não revisado", pendências para o autor, uso "equivalente em API US$ X (não cobrado no Pro/Max)", link para o relatório) seguida dos problemas da reanálise; evento `provedor` atualiza o painel e mostra "Sessão expirada — faça login de novo" (depende de T043, T044)

**Checkpoint**: US1 e US2 completas. Este é o escopo P1 inteiro.

---

## Phase 5: User Story 3 - Comparar versões antes de aceitar (Priority: P2)

**Goal**: mostrar lado a lado o que mudou entre o original e uma versão.

**Independent Test**: criar a `_v2` de um arquivo da amostra e abrir a comparação; todas as linhas alteradas, e só elas, aparecem destacadas.

- [X] T046 [P] [US3] Criar `tests/unit/test_comparacao.py`: arquivos idênticos → um bloco `igual`; inserção, remoção e alteração geram blocos com os tipos e intervalos de linha corretos; arquivo de 5.000 linhas compara em < 1 s
- [X] T047 [US3] Criar `gera_md/comparacao.py` com `comparar(caminho_a, caminho_b) -> list[dict]` usando `difflib.SequenceMatcher` e blocos `{tipo: "igual"|"inserido"|"removido"|"alterado", a: [ini, fim], b: [ini, fim], linhas_a, linhas_b}` (contracts/http-api.md)
- [X] T048 [US3] Adicionar `GET /api/comparacao?a=&b=` em `gera_md/web/rotas_analise.py`, com `validar_caminho` nos dois caminhos (depende de T047)
- [X] T049 [US3] Criar `gera_md/web/static/componentes/comparacao.js` (painel lado a lado com números de linha, cores distintas para inserido, removido e alterado, blocos `igual` longos recolhidos, coluna única abaixo de 900 px) e adicionar o botão "Comparar com a origem" em `gera_md/web/static/app.js`, habilitado quando o arquivo selecionado tem `origem` (depende de T048)

**Checkpoint**: US3 completa.

---

## Phase 6: User Story 4 - Usar IA por API como tipo de acesso separado (Priority: P3)

**Goal**: acesso por API configurável, exibido à parte com aviso de cobrança, nunca padrão, com a chave no cofre do sistema.

**Independent Test**: informar uma chave, ver a opção "Claude — API (cobrado por uso)" separada e não selecionada, conferir que `gerar_word_config.json` não contém a chave e revisar um arquivo com custo exibido (quickstart seção 6).

- [X] T050 [P] [US4] Criar `tests/unit/test_claude_api.py` com `keyring` simulado: sem chave → `chave_ausente`; com chave → `logado`; o processo filho recebe `ANTHROPIC_API_KEY` só nessa chamada; `padrao` é sempre `False`; `cobranca == "por_uso"`; `apiKeySource == "none"` → `AcessoIncorreto`; a chave nunca aparece em `to_dict()`, logs ou config
- [X] T051 [US4] Adicionar `ClaudeApi(ClaudeCli)` em `gera_md/provedores/claude_cli.py` (`id="claude-api"`, nome "Claude — API (cobrado por uso)", `tipo_acesso="api"`, `cobranca="por_uso"`, `padrao=False`) com `import keyring` tardio (serviço `gera-documents`, usuário `anthropic-api-key`); se `keyring` não estiver instalado → `estado="erro"` com "Instale: pip install keyring"; registrar em `gera_md/provedores/__init__.py` (depende de T037, T039)
- [X] T052 [US4] Adicionar `PUT /api/provedores/claude-api/chave` (`{chave}` → `keyring.set_password`; 204) e `DELETE` em `gera_md/web/rotas_ia.py`; a resposta nunca devolve a chave; a prévia e o `concluido` para `claude-api` trazem "Cobrado por uso (API)" e o custo real (depende de T051)
- [X] T053 [US4] Em `gera_md/web/static/componentes/painel-ia.js`, adicionar a seção recolhida "Acesso por API (opcional)" com campo de senha, botões Salvar/Remover e o texto "Será cobrado por uso na sua conta da API, separado da assinatura"; exibir `claude-api` como opção distinta, com selo "API — cobrado por uso"; destacar o aviso de cobrança no diálogo de confirmação quando escolhido (depende de T052)

**Checkpoint**: todas as histórias completas.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T054 [P] Criar `tests/integration/test_cli.py`: `python analisar_md.py <amostra> --relatorio --v2 --saida <tmp>` gera o mesmo relatório normalizado dos snapshots e os mesmos números da API web (FR-028); `python revisar_md.py --help` mostra `--provedor`
- [X] T055 [P] Criar `tests/integration/test_desempenho.py`: pasta temporária com 200 cópias da amostra; o primeiro evento `arquivo` chega em ≤ 3 s e a busca completa termina sem bloquear `GET /api/config` (resposta em < 500 ms durante a busca) (SC-002)
- [X] T056 Revisar a acessibilidade em `gera_md/web/static/` (foco visível, rótulos em todos os controles, `aria-live` no progresso, contraste AA nos selos de situação nos temas claro e escuro)
- [X] T057 [P] Atualizar as docstrings de uso em `analisar_md.py` e `revisar_md.py` e o cabeçalho de `gera_md/web/__main__.py` com o novo modo web (`python -m gera_md.web` / `Gera Documents.cmd`), a diferença entre assinatura e API e o comando `claude auth status`
- [X] T058 Rodar `python -m pytest tests -q` e todo o `specs/001-local-web-frontend/quickstart.md` manualmente (seções 2 a 6, incluindo o teste com `ANTHROPIC_API_KEY` falsa e o `claude auth logout`/login), registrando o resultado no fim do quickstart

---

## Phase 8: Remediação do /speckit-analyze (2026-10-14)

**Purpose**: fechar os achados C1 (paridade da CLI, constituição IV — opção A), C2 (caminho
sem IA só com `python-docx`), A1 (revisão sem alterações não grava versão) e A2
(`provedor_padrao` nunca é de API).

- [X] T059 [P] Em `revisar_md.py`, aceitar vários arquivos (`md` com `nargs="+"`), revisando um por vez com o mesmo provedor/skill/modelo e imprimindo o resumo por arquivo e o total de uso
- [X] T060 [P] Criar `gera_md/__main__.py` com o subcomando `comparar <a.md> <b.md>`, que imprime os blocos de `gera_md.comparacao.comparar` em formato unificado (`-`/`+`, com números de linha)
- [X] T061 [P] Em `revisar_md.py`, adicionar `--definir-chave-api` (lê com `getpass`, grava por `ClaudeApi.salvar_chave`) e `--remover-chave-api`; a chave nunca é ecoada nem aceita como argumento
- [X] T062 Estender `tests/integration/test_cli.py`: revisão de 2 arquivos com provedor simulado, `python -m gera_md comparar` e `--definir-chave-api` com keyring simulado (depende de T059–T061)
- [X] T063 [P] Criar `tests/integration/test_dependencias.py`: em subprocesso com `sys.modules` bloqueando `starlette`, `uvicorn` e `keyring`, importar `analisar_md` e rodar `analisar_md.py <amostra> --relatorio --v2`; deve funcionar (constituição, Restrições Técnicas)
- [X] T064 Em `gera_md/revisao.py`, não gravar a nova versão quando `texto_final` for igual ao original; gravar o relatório como `<origem>_revisao.md` (próximo número livre) e retornar `Revisao.destino = None` (FR-023). Em `gera_md/web/rotas_ia.py` e `gera_md/web/static/componentes/detalhes.js`/`app.js`, exibir "Nenhuma alteração; veja as pendências no relatório" sem inserir versão na lista; manter `revisar_md.py` (interface antiga) funcionando com `destino = None`. Teste em `tests/unit/test_revisao.py`
- [X] T065 Em `gera_md/web/rotas_ia.py`, salvar `provedor_padrao` só quando `p.tipo_acesso == "assinatura"`; em `gera_md/web/static/componentes/painel-ia.js`, usar `provedor_padrao` da config para a escolha inicial, nunca um provedor de API. Teste em `tests/integration/test_revisao_web.py`: revisar com `claude-api` não altera `provedor_padrao`

**Checkpoint**: `python -m pytest tests -q` passando; constituição I, IV e Restrições atendidas.

**Registro (2026-10-14)**: T059–T065 concluídas; `python -m pytest tests -q` → 104 passed. Dois testes
antigos (`test_marcador_perdido_mantem_original`, `test_revisao_completa`) foram ajustados à nova
regra do FR-023: revisão sem diferença no texto não grava versão.

---

## Phase 9: Relatórios não viram documento (clarificação 2026-10-14)

**Purpose**: impedir que um relatório de revisão seja tratado como documento (um Word foi
gerado do `tutorial-fluxo-completo_v3_revisao.md`, com as notas da IA e sem as imagens) e
deixar o relatório legível sem marcadores internos. Ver spec.md: Clarifications, FR-023, FR-030.

- [X] T066 [P] FR-030: em `gera_md/analise.py`, criar `eh_relatorio(caminho)` que reconhece, sem diferenciar maiúsculas, nomes terminados em `_revisao.md` ou `_revisao_N.md` e o nome `relatorio_analise_md.md`; `encontrar_mds` passa a ignorá-los (vale para a web, a tela Tk e a CLI). Em `gera_md/web/seguranca.py`, `validar_caminho` ganha `permitir_relatorio=False` e recusa relatórios com 400 ("Relatórios não podem ser usados como documento."); só `POST /api/abrir` em `gera_md/web/rotas_analise.py` passa `permitir_relatorio=True`. Testes: em `tests/unit/test_analise.py`, `encontrar_mds` ignora `x_revisao.md`, `x_v3_revisao.md`, `x_revisao_2.md` e `relatorio_analise_md.md` mas mantém `revisao.md` e `minha_revisao_geral.md`; em `tests/integration/test_analise_web.py`, `POST /api/word`, `/api/correcoes` e `/api/revisoes/previa` com um relatório → 400, e `POST /api/abrir` com o relatório → 200 (com `abrir_no_sistema` simulado)
- [X] T067 [P] FR-023: em `gera_md/revisao.py`, criar `descrever_bloco(bloco)`, que devolve `[imagem: <caminho>]` para linha de imagem, `[âncora: <id>]` para `<a id="...">` e `[bloco de código: <primeira linha de conteúdo, até 60 caracteres>…]` para bloco ``` (`[bloco de código]` se vazio); aplicar a troca de `⟦BLOCO_n⟧` em pendências, alterações e falhas antes de gravar o relatório e de preencher `Revisao`, deixando marcador sem bloco correspondente como `[bloco]`. Em `gera_md/provedores/simulado.py`, aceitar `pendencia=` para customizar a pendência devolvida. Teste em `tests/unit/test_revisao.py`: pendência que cita `⟦BLOCO_0⟧` (código) e `⟦BLOCO_1⟧` (imagem) sai como `[bloco de código: print(...)…]` e `[imagem: img.png]`, e o relatório gravado não contém `⟦`

**Checkpoint**: `python -m pytest tests -q` passando; numa pasta com `*_revisao.md`, eles não aparecem na lista e não podem virar Word.

**Registro (2026-10-14)**: T066–T067 concluídas; `python -m pytest tests -q` → 107 passed. Na pasta
uma pasta real de documentação, os dois `*_revisao.md` deixaram de aparecer na busca.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências. **T006 MUST rodar antes de T009–T014** (snapshots do código antigo).
- **Foundational (Phase 2)**: depende do Setup e bloqueia todas as histórias.
- **US1 (Phase 3)** e **US2 (Phase 4)**: dependem só da Phase 2 e podem andar em paralelo; T045 toca `app.js` e `detalhes.js` depois de T032.
- **US3 (Phase 5)**: depende da Phase 2; usa `rotas_analise.py` (depois de T028) e o `app.js` da US1.
- **US4 (Phase 6)**: depende de T037, T039, T043 e T044 da US2.
- **Polish (Phase 7)**: depois das histórias desejadas.
- **Remediação (Phase 8)**: depois da Phase 7; T059–T061, T063 em paralelo; T062 depois de T059–T061; T064 e T065 tocam `rotas_ia.py` (sequenciais entre si).
- **Relatórios (Phase 9)**: depois da Phase 8; T066 e T067 em paralelo (arquivos diferentes).

### Cadeia crítica

T003/T005 → T006 → T007 → T009 → T010 → T014 → T015 → T021 → T027 → T028 → T032 → (US2) T036 → T037 → T039 → T040 → T043 → T045

### Within Each User Story

- Testes escritos primeiro, falhando antes da implementação
- Núcleo (`gera_md/`) antes das rotas; rotas antes dos componentes que as chamam
- Integração em `app.js` por último

---

## Parallel Examples

```text
# Setup
T003 fixtures da amostra  |  T004 conftest.py

# Foundational (após T007)
T008 versoes.py  |  T011 relatorio.py  |  T012 config.py
# após T014
T016 test_analise  |  T017 test_correcao  |  T018 test_versoes  |  T019 test_operacoes
T023 static base  |  T024 test_seguranca  |  T025 Gera Documents.cmd

# US1
T026 teste de integração  |  T029 pasta.js  |  T030 lista.js  |  T031 detalhes.js

# US2
T033 test_provedores  |  T034 test_revisao  |  T035 test_revisao_web  |  T038 simulado.py  |  T044 painel-ia.js
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 (com os snapshots) → Phase 2 (núcleo + servidor seguro)
2. Phase 3 (US1) → **validar** com o quickstart seção 3
3. O frontend já substitui a tela Tk no fluxo sem IA

### Incremental Delivery

1. MVP (US1)
2. + US2 → revisão pela assinatura Pro/Max (escopo P1 completo; quickstart seções 4 e 5)
3. + US3 → comparação
4. + US4 → acesso por API separado (quickstart seção 6)
5. Polish → desempenho, acessibilidade, documentação e validação final

---

## Notes

- Nenhuma tarefa altera `gerar_word.py`.
- Mover código para `gera_md/` é **cópia literal + ajustes de import**: qualquer mudança de regra quebra T015 e precisa ser revertida ou virar uma feature separada (constituição II).
- Nenhuma tarefa ou teste chama o Claude real; só T058 (manual).

## Registro da implementação (2026-10-14)

- Todas as tarefas concluídas; `python -m pytest tests -q` → 97 passed.
- T012: as preferências novas ficaram em `gera_documents_config.json` (o `salvar_config` do
  `gerar_word.py` descarta chaves desconhecidas); `ultima_pasta` continua no arquivo antigo.
- T020/T027: a rota de arquivo usa `?caminho=` em vez de caminho codificado no path.
- Dependência só de teste: `httpx2` (exigida pelo `starlette.testclient` 1.2), em
  `requirements-dev.txt`.
- T056: foco visível, rótulos, `aria-live` e situação com texto + ícone + cor implementados;
  o contraste AA não foi medido com ferramenta.
- T058: ver "Resultado da validação" no quickstart.md.
