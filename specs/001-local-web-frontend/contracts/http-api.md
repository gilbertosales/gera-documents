# Contrato: API HTTP do servidor local

Base: `http://127.0.0.1:<porta>`. Todas as rotas `/api/*` exigem o cookie de sessão (ver
research R4). JSON em UTF-8. Erros seguem `{"erro": "<mensagem em pt-BR>", "acao": "<o que
fazer>"}`.

| Código | Quando |
|---|---|
| 400 | entrada inválida (pasta inexistente, caminho fora da análise, arquivo não `.md`) |
| 401 | sem cookie de sessão válido |
| 403 | `Host` ou `Origin` não permitido |
| 404 | análise, arquivo ou operação não encontrados |
| 409 | conflito: revisão sem `confirmado: true`, outra revisão em andamento, provedor não logado |

## Sessão

- `GET /?t=<token>` → define o cookie e redireciona para `/`. Sem token válido → 401.

## Pastas e análise

- `GET /api/config` → `{pastas_recentes, ultima_pasta, provedor_padrao, skill_padrao, modelo_padrao}`
- `POST /api/pastas/escolher` → abre o seletor nativo; `{pasta: str | null}`
- `POST /api/analises` `{pasta, subpastas}` → 202 `{analise_id, operacao_id}`; os arquivos
  chegam pelos eventos.
- `GET /api/analises/{id}` → `Analise` completa (ver data-model).
- `GET /api/analises/{id}/arquivo?caminho=<caminho>` → `ResultadoArquivo` com `achados[].trecho`
  (caminho como parâmetro de consulta: caminhos do Windows com `\` e `:` não cabem bem no path).

## Correção, relatório e ações locais

- `POST /api/correcoes` `{analise_id, caminhos: [str] | "todos_com_problema"}` → 202
  `{operacao_id}`; o resultado traz `criados: [ResultadoArquivo]`, `sem_mudanca: [str]`.
- `POST /api/relatorios` `{analise_id, destino?}` → `{caminho}`
- `POST /api/abrir` `{analise_id, caminho}` → abre no editor padrão; 200
- `POST /api/word` `{analise_id, caminho}` → inicia `gerar_word.py` com o arquivo; 200
- `GET /api/comparacao?analise_id=<id>&a=<caminho>&b=<caminho>` →
  `{blocos: [{tipo: "igual"|"inserido"|"removido"|"alterado", a: [ini, fim], b: [ini, fim], linhas_a: [str], linhas_b: [str]}]}`

## IA

- `GET /api/provedores` → `[ProvedorIA]` (ver data-model); `?atualizar=1` refaz a verificação de login.
- `GET /api/skills` → `[{nome, padrao: bool}]`
- `PUT /api/provedores/claude-api/chave` `{chave}` → grava no cofre do sistema e devolve o `ProvedorIA` atualizado.
  `DELETE` remove (mesma resposta). A chave nunca é devolvida em nenhuma resposta.
- `POST /api/revisoes/previa` `{caminhos, provedor, skill, modelo}` →
  `{arquivos: [{caminho, trechos}], provedor, tipo_acesso, cobranca, aviso}`. Texto para a
  confirmação (FR-020).
- `POST /api/revisoes` `{analise_id, caminhos, provedor, skill, modelo, confirmado: true}` →
  202 `{operacao_id}`. Sem `confirmado: true` → 409.
  No resultado, cada item de `feitos` é uma `Revisao`; `destino: null` quando o texto não mudou
  (só o relatório `nome_revisao.md` é gravado e a revisão fica ligada ao arquivo original).

## Operações

- `GET /api/operacoes/{id}` → `Operacao`
- `POST /api/operacoes/{id}/cancelar` → 202
- `GET /api/eventos` → `text/event-stream`. Eventos:

| `event` | `data` |
|---|---|
| `progresso` | `{operacao_id, feito, total, mensagem}` |
| `arquivo` | `{operacao_id, analise_id, arquivo: ResultadoArquivo, depois_de: str \| null, indice: int}` |
| `concluido` | `{operacao_id, tipo, resultado}` |
| `erro` | `{operacao_id, erro, acao}` |
| `cancelado` | `{operacao_id}` |
| `provedor` | `ProvedorIA` (ex.: sessão expirada durante a revisão) |
