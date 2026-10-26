# Análise de arquivos Markdown para o Word

**Pasta:** `<PASTA>`  
**Data:** <DATA>  
**Arquivos:** 28 · **Erros:** 12 · **Avisos:** 16

## Resumo

| Arquivo | Erros | Avisos | Situação |
|---|---|---|---|
| ancora.md | 0 | 0 | OK |
| checklist.md | 0 | 2 | Revisar |
| citacao_lista.md | 0 | 2 | Revisar |
| codigo_aberto.md | 1 | 0 | Corrigir |
| cp1252.md | 1 | 0 | Corrigir |
| html.md | 0 | 1 | Revisar |
| imagem_inexistente.md | 1 | 0 | Corrigir |
| imagem_internet.md | 1 | 0 | Corrigir |
| imagem_no_meio.md | 1 | 0 | Corrigir |
| italico_sublinhado.md | 0 | 1 | Revisar |
| links.md | 0 | 1 | Revisar |
| lista_4_espacos.md | 1 | 0 | Corrigir |
| lista_mais.md | 1 | 0 | Corrigir |
| lista_parenteses.md | 2 | 0 | Corrigir |
| lista_tab.md | 1 | 0 | Corrigir |
| mermaid.md | 0 | 0 | OK |
| negrito_sublinhado.md | 0 | 1 | Revisar |
| nota_rodape.md | 0 | 1 | Revisar |
| ok.md | 0 | 0 | OK |
| riscado.md | 0 | 1 | Revisar |
| sem_h1.md | 0 | 0 | OK |
| tabela_br.md | 0 | 1 | Revisar |
| tabela_colunas.md | 2 | 0 | Corrigir |
| tabela_sem_separador.md | 0 | 1 | Revisar |
| texto_apos_imagem.md | 0 | 1 | Revisar |
| titulo_nivel6.md | 0 | 1 | Revisar |
| titulo_sem_espaco.md | 0 | 1 | Revisar |
| sub/interno.md | 0 | 1 | Revisar |

## checklist.md

| Nível | Linha | Problema |
|---|---|---|
| AVISO | 3 | Checklist ([ ] / [x]) sai com os colchetes como texto. |
| AVISO | 4 | Checklist ([ ] / [x]) sai com os colchetes como texto. |

## citacao_lista.md

| Nível | Linha | Problema |
|---|---|---|
| AVISO | 3 | Lista/título dentro de citação (>) sai como texto literal. |
| AVISO | 4 | Lista/título dentro de citação (>) sai como texto literal. |

## codigo_aberto.md

| Nível | Linha | Problema |
|---|---|---|
| ERRO | 3 | Bloco de código ``` aberto e nunca fechado — todo o resto do documento vira código. |

## cp1252.md

| Nível | Linha | Problema |
|---|---|---|
| ERRO | - | Arquivo não está em UTF-8 — o gerar_word.py falha ao ler. |

## html.md

| Nível | Linha | Problema |
|---|---|---|
| AVISO | 3 | HTML (<span>) sai como texto literal. |

## imagem_inexistente.md

| Nível | Linha | Problema |
|---|---|---|
| ERRO | 3 | Imagem não encontrada: img/nao_existe.png |

## imagem_internet.md

| Nível | Linha | Problema |
|---|---|---|
| ERRO | 3 | Imagem da internet (https://exemplo.com/logo.png) não é baixada — salve a imagem na pasta e aponte para o arquivo local. |

## imagem_no_meio.md

| Nível | Linha | Problema |
|---|---|---|
| ERRO | 3 | Imagem no meio do texto não é inserida — sai como texto. |

## italico_sublinhado.md

| Nível | Linha | Problema |
|---|---|---|
| AVISO | 3 | _itálico_ com sublinhado não é suportado — o certo é *itálico*. |

## links.md

| Nível | Linha | Problema |
|---|---|---|
| AVISO | 3 | Link [texto](url) sai literal, com colchetes e URL. |

## lista_4_espacos.md

| Nível | Linha | Problema |
|---|---|---|
| ERRO | 4 | Sublista com 4+ espaços de recuo é colada no texto do item anterior. |

## lista_mais.md

| Nível | Linha | Problema |
|---|---|---|
| ERRO | 3 | Marcador "+" não é reconhecido — é colado no item anterior. |

## lista_parenteses.md

| Nível | Linha | Problema |
|---|---|---|
| ERRO | 3 | Lista numerada com "1)" não é reconhecida — o certo é "1." |
| ERRO | 4 | Lista numerada com "1)" não é reconhecida — o certo é "1." |

## lista_tab.md

| Nível | Linha | Problema |
|---|---|---|
| ERRO | 4 | Item de lista recuado com TAB não é reconhecido. |

## negrito_sublinhado.md

| Nível | Linha | Problema |
|---|---|---|
| AVISO | 3 | __negrito__ com sublinhado não é suportado — o certo é **negrito**. |

## nota_rodape.md

| Nível | Linha | Problema |
|---|---|---|
| AVISO | 3 | Nota de rodapé [^n] não é suportada — sai como texto. |

## riscado.md

| Nível | Linha | Problema |
|---|---|---|
| AVISO | 3 | ~~riscado~~ não é suportado — sai com os ~~. |

## sem_h1.md

| Nível | Linha | Problema |
|---|---|---|
| INFO | - | Sem título "# ..." — a tela do gerar_word vai sugerir "sem h1" como nome do relatório. |

## tabela_br.md

| Nível | Linha | Problema |
|---|---|---|
| AVISO | 5 | <br> dentro de célula aparece como texto literal no Word. |

## tabela_colunas.md

| Nível | Linha | Problema |
|---|---|---|
| ERRO | 5 | Linha da tabela com 3 colunas, cabeçalho tem 2 — células ficam desalinhadas/vazias no Word. |
| ERRO | 6 | Linha da tabela com 1 colunas, cabeçalho tem 2 — células ficam desalinhadas/vazias no Word. |

## tabela_sem_separador.md

| Nível | Linha | Problema |
|---|---|---|
| AVISO | 3 | Tabela sem a linha separadora (/---/---/) após o cabeçalho. |

## texto_apos_imagem.md

| Nível | Linha | Problema |
|---|---|---|
| AVISO | 3 | Texto depois da imagem na mesma linha é descartado. |

## titulo_nivel6.md

| Nível | Linha | Problema |
|---|---|---|
| AVISO | 3 | Título ###### (nível 6) não é suportado — sai como texto com os #. |

## titulo_sem_espaco.md

| Nível | Linha | Problema |
|---|---|---|
| AVISO | 3 | Título sem espaço após o # (ex.: "##Título") — sai como texto. |

## sub/interno.md

| Nível | Linha | Problema |
|---|---|---|
| AVISO | 3 | ~~riscado~~ não é suportado — sai com os ~~. |
