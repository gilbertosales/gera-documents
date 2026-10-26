# Research: Frontend Web Local com Várias IAs via Login

**Feature**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Date**: 2026-10-14

Todas as incógnitas do Technical Context estão resolvidas abaixo.

## R1. Como usar o Claude Pro/Max sem API (modo assinatura)

**Decision**: chamar o Claude Code em modo não interativo (`claude -p`), como o
`revisar_md.py` já faz, com três salvaguardas novas:

1. **Ambiente limpo**: o processo filho é iniciado sem `ANTHROPIC_API_KEY`,
   `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `CLAUDE_CODE_USE_BEDROCK`,
   `CLAUDE_CODE_USE_VERTEX` e `CLAUDE_CODE_USE_FOUNDRY`. Sem isso, uma chave presente no
   Windows faria o Claude Code cobrar por API sem o usuário perceber (FR-017).
2. **Verificação antes**: `claude auth status --json` (com o mesmo ambiente limpo) MUST
   retornar `loggedIn: true` e `authMethod: "claude.ai"`; `subscriptionType` (ex.: `pro`,
   `max`) é exibido na tela. Esse comando não consome uso. Na máquina de desenvolvimento,
   o Claude Code 2.1.299 retornou exatamente esses campos.
3. **Verificação durante**: usar `--output-format stream-json --verbose` e ler a mensagem
   inicial `system/init`; se `apiKeySource` for diferente de `"none"`, o processo é
   encerrado antes de qualquer resposta e o trecho fica como "não revisado" com a mensagem
   "o Claude Code tentou usar chave de API no modo assinatura". A mensagem final `result`
   fornece `result`, `total_cost_usd` e `usage`.

Flags mantidas: `--tools ""` (sem ferramentas), `--no-session-persistence`,
`--append-system-prompt-file`, `--model`, `cwd` = pasta temporária. **Nunca** usar `--bare`:
nesse modo o Claude Code não lê o login OAuth/keychain, só chave de API.

**Rationale**: é o único caminho oficial para usar a assinatura Pro/Max fora do app; o
contrato atual já funciona; as salvaguardas garantem SC-004 por construção, não por
convenção.

**Alternatives considered**:
- SDK/API da Anthropic com OAuth da assinatura: não é suportado para uso de terceiros.
- Automatizar o claude.ai pelo navegador: frágil e contra os termos de uso.
- Claude Agent SDK: exige chave de API, não serve para o modo assinatura.

## R2. Modo API como tipo de acesso separado

**Decision**: o mesmo adaptador do Claude Code com `modo="api"`: o processo filho recebe
`ANTHROPIC_API_KEY` lida do Gerenciador de Credenciais do Windows (pacote `keyring`) só no
momento da chamada; `auth status` deve retornar método de chave de API e `apiKeySource`
diferente de `"none"`. O custo `total_cost_usd` passa a ser cobrança real e é exibido assim.

**Rationale**: reaproveita proteção de blocos, divisão em trechos e o parsing já testados;
uma única dependência nova (`keyring`) cobre FR-026 no Windows, macOS e Linux.

**Alternatives considered**: SDK `anthropic` direto (mais uma dependência e um segundo
caminho de prompt/parsing para manter); guardar a chave no `gerar_word_config.json`
(proibido pela constituição III).

## R3. Servidor local e frontend

**Decision**: **Starlette + uvicorn** (já instalados) servindo uma API JSON, um canal de
eventos SSE e arquivos estáticos. Frontend em **HTML + CSS + JavaScript puro (ES modules)**,
sem etapa de build e sem Node.js.

**Rationale**: o projeto é Python e roda em máquinas de consultores; zero build e duas
dependências pequenas. SSE cobre progresso e logs unidirecionais sem WebSocket. As telas
(lista, detalhes, comparação, painel de IA) são poucas e não justificam framework SPA.

**Alternatives considered**:
- FastAPI: traz pydantic e mais peso, sem ganho real para cerca de 20 rotas.
- Flask: síncrono; SSE e cancelamento com threads ficam mais trabalhosos.
- React/Vite: exige Node.js e build, contrariando a restrição técnica de dependências mínimas.
- NiceGUI/Streamlit: pouco controle sobre layout, filtros e segurança local.

## R4. Segurança do servidor local

**Decision**:
- Bind exclusivo em `127.0.0.1`, em porta livre escolhida ao iniciar (preferência 8765).
- **Token de sessão** aleatório (`secrets.token_urlsafe(32)`) gerado ao iniciar; o navegador
  é aberto em `http://127.0.0.1:<porta>/?t=<token>`, o token vira cookie `HttpOnly`,
  `SameSite=Strict`, e toda rota `/api/*` exige o cookie.
- Verificação de `Host` (`127.0.0.1:<porta>` ou `localhost:<porta>`) contra DNS rebinding, e
  de `Origin` nas requisições que alteram estado.
- Caminhos de arquivo recebidos pela API são resolvidos e validados (precisam ser `.md` e
  estar dentro da pasta analisada) antes de qualquer leitura ou escrita.

**Rationale**: FR-002 pede recusar outras máquinas; o token também impede que um site
aberto no mesmo navegador dispare revisões (CSRF) ou leia documentos de clientes.

**Alternatives considered**: só `127.0.0.1` (não protege contra páginas maliciosas no
navegador local); autenticação com senha (atrito desnecessário para uso individual).

## R5. Operações longas, progresso e cancelamento

**Decision**: um **gerenciador de operações** no núcleo, com um `threading.Event` de
cancelamento por operação e uma fila de eventos (`progresso`, `arquivo`, `concluido`,
`erro`, `cancelado`) consumida pelo SSE. Na revisão, o executor só envia um trecho novo se a
operação não foi cancelada; processos `claude` em execução são encerrados (`Popen.kill`)
no cancelamento. Uma operação de IA por vez; buscas e correções podem rodar em paralelo.

**Rationale**: atende FR-006, FR-021 e SC-007 (≤ 5 s); o mesmo mecanismo serve CLI, Tk e web.

**Alternatives considered**: asyncio de ponta a ponta (exigiria reescrever o núcleo síncrono
de I/O de arquivos); fila de tarefas externa (excesso para uso local).

## R6. Escolha de pasta no navegador

**Decision**: campo de caminho com pastas recentes (até 10, no arquivo de configuração
existente) + botão "Procurar..." que abre o seletor nativo do sistema pelo servidor
(`tkinter.filedialog.askdirectory` em subprocesso), já que servidor e navegador estão na
mesma máquina.

**Rationale**: navegadores não revelam o caminho real de pastas; o diálogo nativo funciona
com pastas de rede e unidades mapeadas.

**Alternatives considered**: navegador de pastas próprio na web (mais código, pior em UNC);
File System Access API (não expõe o caminho e não funciona em todos os navegadores).

## R7. Separar o núcleo sem mudar resultados (SC-003)

**Decision**: criar o pacote `gera_md/` com as funções de análise, correção, versões,
relatório e revisão movidas **sem alterar a lógica**; `analisar_md.py` e `revisar_md.py`
passam a importar do pacote e mantêm as mesmas funções públicas, CLI e tela Tk.
Antes de mover, gerar **snapshots dourados** (achados, `_v2` e relatório) de um conjunto
de arquivos de exemplo com o código atual; os testes comparam o núcleo novo com esses
snapshots.

Unificações seguras: `proximo_v2` e `proxima_versao` (idênticas) viram uma só função em
`versoes.py`, com criação exclusiva do arquivo (`open(..., "x")`) para que duas abas nunca
gravem o mesmo número.

**Rationale**: constituição II e IV; os snapshots tornam a refatoração verificável.

## R8. Comparação de versões

**Decision**: `difflib.SequenceMatcher` no servidor, retornando blocos
`igual/inserido/removido/alterado` com números de linha; o frontend exibe lado a lado (ou
em coluna única em telas estreitas).

**Rationale**: biblioteca padrão; o volume (documentos de até alguns milhares de linhas)
é trivial.

## R9. Testes

**Decision**: `pytest` (já instalado). `tests/unit` para regras de análise (positivo e
negativo por regra), correção (idempotência), versões e proteção de blocos;
`tests/integration` para as rotas com `starlette.testclient` e um **provedor simulado**
(sem rede, sem Claude); `tests/golden` para os snapshots de R7. Um teste manual opcional
com o Claude real fica no quickstart.

## R10. Extensibilidade para outras IAs

**Decision**: interface `ProvedorIA` (ver [contracts/provedor-ia.md](./contracts/provedor-ia.md))
e um registro de provedores. Nesta versão: `claude-assinatura` e `claude-api`, ambos sobre
o mesmo adaptador. Uma IA futura (ex.: ChatGPT via Codex CLI, Gemini CLI) é uma nova
classe registrada, sem tocar em análise, correção, revisão ou relatório (FR-016).
