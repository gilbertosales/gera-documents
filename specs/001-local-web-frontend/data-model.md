# Data Model: Frontend Web Local com Várias IAs via Login

Entidades do núcleo (`gera_md/modelos.py`), todas serializáveis em JSON. Não há banco de
dados: o estado durável são os arquivos no disco e o arquivo de configuração. O estado da
sessão (análise atual, operações) vive em memória no servidor.

## Analise (pasta analisada)

| Campo | Tipo | Regras |
|---|---|---|
| `id` | str | gerado por análise |
| `pasta` | str | caminho absoluto normalizado; precisa existir e ser legível |
| `subpastas` | bool | padrão `true`; ignora `node_modules`, `venv`, `__pycache__` e pastas com `.` |
| `iniciada_em` | datetime | |
| `arquivos` | list[ResultadoArquivo] | ordem de descoberta; versões criadas entram logo após a origem |

Relação: 1 Analise → N ResultadoArquivo. Todo caminho aceito pela API precisa estar dentro
de `pasta`.

## ResultadoArquivo (arquivo Markdown)

| Campo | Tipo | Regras |
|---|---|---|
| `caminho` | str | absoluto; extensão `.md` ou `.markdown` |
| `rotulo` | str | caminho relativo à pasta |
| `versao` | int \| null | `null` para original; N para `_vN` |
| `origem` | str \| null | caminho do arquivo do qual esta versão foi criada |
| `tipo_versao` | `original` \| `correcao` \| `revisao_ia` | |
| `achados` | list[Achado] | ordenados por nível (ERRO, AVISO, INFO) e linha |
| `erros`, `avisos` | int | derivados de `achados` |
| `situacao` | `Corrigir` \| `Revisar` \| `OK` | `Corrigir` se erros > 0; `Revisar` se avisos > 0; senão `OK` |
| `correcoes` | list[Correcao] | só quando `tipo_versao = correcao` |
| `revisao` | Revisao \| null | só quando `tipo_versao = revisao_ia` |
| `modificado_em` | float | mtime na análise; se mudar, a análise é refeita antes de corrigir |

## Achado

| Campo | Tipo | Regras |
|---|---|---|
| `nivel` | `ERRO` \| `AVISO` \| `INFO` | |
| `linha` | int | 0 = arquivo inteiro |
| `mensagem` | str | idêntica à da ferramenta atual |
| `trecho` | str \| null | conteúdo da linha (até 200 caracteres) para exibição no contexto |

## Correcao

| Campo | Tipo | Regras |
|---|---|---|
| `linha` | int | linha do original; 0 = geral |
| `descricao` | str | idêntica à da ferramenta atual |

## ProvedorIA (estado exibido)

| Campo | Tipo | Regras |
|---|---|---|
| `id` | str | ex.: `claude-assinatura`, `claude-api` |
| `nome` | str | ex.: "Claude (Pro/Max)" |
| `tipo_acesso` | `assinatura` \| `api` | |
| `estado` | `logado` \| `login_necessario` \| `nao_instalado` \| `chave_ausente` \| `erro` | |
| `detalhe` | str | ex.: "Plano: pro"; nunca inclui e-mail ou token |
| `cobranca` | `limite_assinatura` \| `por_uso` | |
| `padrao` | bool | `true` só para `claude-assinatura` |
| `modelos` | list[str] | `padrão`, `sonnet`, `opus`, `haiku` |
| `instrucoes_login` | list[str] | passos exibidos quando `estado ≠ logado` |

Transições de `estado`: `nao_instalado` → (instala) → `login_necessario` → (login externo
+ "Verificar de novo") → `logado`. Uma resposta de sessão expirada durante o uso leva
`logado` → `login_necessario`.

## Revisao (revisão por IA)

| Campo | Tipo | Regras |
|---|---|---|
| `origem` | str | arquivo revisado |
| `destino` | str | nova versão `_vN` |
| `relatorio` | str | `<destino>_revisao.md` |
| `provedor`, `tipo_acesso`, `skill`, `modelo` | str | |
| `contagem` | dict[str, int] | alterações por categoria |
| `pendencias` | list[{secao, texto}] | |
| `falhas` | list[{secao, erro}] | trechos mantidos como no original |
| `trechos` | int | total de trechos |
| `uso` | {custo_usd: float, tokens_entrada: int, tokens_saida: int} | `custo_usd` é equivalente (assinatura) ou cobrado (API) |
| `cancelada` | bool | se `true`, não é gravada nenhuma versão |

## Operacao

| Campo | Tipo | Regras |
|---|---|---|
| `id` | str | |
| `tipo` | `busca` \| `correcao` \| `revisao` | |
| `estado` | `executando` \| `concluida` \| `cancelando` \| `cancelada` \| `erro` | |
| `progresso` | {feito: int, total: int \| null, mensagem: str} | |
| `resultado` | objeto conforme o tipo | |

Transições: `executando` → `concluida` \| `erro`; `executando` → (cancelar) → `cancelando`
→ `cancelada`. Só uma operação `revisao` pode estar `executando` por vez.

## Configuracao

Campos existentes mantidos em `gerar_word_config.json` (`template`, `subtitulo`, `versao`,
`rodape`, `ultima_pasta`). Os novos ficam em `gera_documents_config.json`, porque o
`salvar_config` do `gerar_word.py` descarta chaves que não conhece: `pastas_recentes`
(list[str], máx. 10), `provedor_padrao` (str; **só provedores com `tipo_acesso = "assinatura"`**,
FR-025), `skill_padrao` (str), `modelo_padrao` (str). **Nunca** contém chave de API.
