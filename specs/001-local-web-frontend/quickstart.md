# Quickstart: validar o frontend web local

Roteiro para provar que a feature funciona de ponta a ponta. Contratos em
[contracts/](./contracts/) e entidades em [data-model.md](./data-model.md).

## Pré-requisitos

- Python 3.10+ e `pip install -r requirements.txt`
- Para IA por assinatura: Claude Code instalado e logado com a conta Pro/Max
  (`claude auth login`), conferindo com `claude auth status --text`
- Pasta de exemplo: `tests/fixtures/amostra/` (arquivos com problemas conhecidos)

## 1. Testes automáticos (sem IA e sem rede)

```powershell
python -m pytest tests -q
```

Esperado: tudo passa, incluindo:
- `tests/golden`: análise, `_v2` e relatório idênticos aos snapshots do código anterior (SC-003)
- `tests/unit/test_correcao.py`: corrigir uma `_v2` não gera novas correções (VII)
- `tests/unit/test_provedores.py`: modo assinatura remove variáveis de chave do ambiente e
  recusa `apiKeySource ≠ "none"` (SC-004)
- `tests/integration`: rotas sem cookie → 401; `Host` estranho → 403; revisão sem
  `confirmado` → 409; hash dos originais inalterado (SC-005)

## 2. Subir a ferramenta

```powershell
python -m gera_md.web        # ou dar dois cliques em "Gera Documents.cmd"
```

Esperado: o navegador abre em `http://127.0.0.1:<porta>/?t=...` e a tela inicial aparece em
pt-BR. Acessar a mesma porta pelo IP da máquina, a partir de outro computador, falha.

## 3. Fluxo sem IA (User Story 1)

1. Informe `tests/fixtures/amostra` e clique em **Buscar**. A lista é preenchida aos poucos
   com a situação em texto e cor.
2. Filtre por **Corrigir** e depois digite parte de um nome.
3. Selecione um arquivo. Cada problema aparece com a linha e o trecho.
4. Clique em **Criar versão corrigida** com 2 arquivos selecionados. As `_v2` aparecem
   logo abaixo dos originais com a lista de correções.
5. **Comparar** original × `_v2`: as linhas alteradas aparecem destacadas (User Story 3).
6. **Gerar Word** abre o `gerar_word.py` com o arquivo preenchido.
7. Compare com `python analisar_md.py tests/fixtures/amostra --relatorio --saida <tmp>`: os
   números de erros e avisos são iguais (FR-028).

## 4. Revisão com IA pela assinatura (User Story 2)

1. Abra o painel **IA**. "Claude (Pro/Max)" aparece como **Assinatura — logado**, com o plano.
2. Opcional, para provar FR-017: defina `ANTHROPIC_API_KEY` com um valor falso no terminal
   antes de subir a ferramenta. O painel continua mostrando **Assinatura — logado** e a
   revisão funciona sem erro de chave.
3. Selecione 1 arquivo pequeno e clique em **Revisar**. A confirmação lista o arquivo, a
   IA, "Assinatura — sem cobrança extra (consome o limite do plano)".
4. Acompanhe o progresso por trecho. Em seguida repita com um arquivo grande e clique em
   **Cancelar**: a operação para em até 5 s e nenhuma versão nova é criada.
5. Na revisão concluída: a nova versão e o `_revisao.md` existem, os blocos de código e as
   imagens estão idênticos (comparação) e os detalhes mostram alterações, pendências e a
   reanálise.

## 5. Sem IA logada

Rode `claude auth logout` (ou suba a ferramenta numa máquina sem Claude Code). O painel
mostra **Login necessário** com os passos. As seções 3.1 a 3.6 continuam funcionando.
Faça login de novo e clique em **Verificar de novo**: o estado volta a **logado** sem
reiniciar.

## 6. Acesso por API (User Story 4, opcional)

1. Em **IA → Acesso por API**, informe uma chave. Aparece a opção separada
   **"Claude — API (cobrado por uso)"**, nunca selecionada por padrão.
2. Confira que `gerar_word_config.json` não contém a chave.
3. Revise um arquivo pequeno com essa opção. A confirmação e o resultado mostram o aviso de
   cobrança e o custo.

## Resultado da validação (2026-10-14)

- `python -m pytest tests -q`: **97 passed** (Windows 11, Python 3.14, Claude Code 2.1.299).
- Servidor: login pelo link → 303 com cookie; `/api/config` sem cookie → 401.
- Seção 3 no Chrome: 28 arquivos da amostra analisados (12 erros, 16 avisos); `_v2` criada e
  comparação lado a lado destacando a linha alterada.
- Seção 4 com o Claude real: `claude-assinatura` = **logado, Plano: pro**, inclusive com
  `ANTHROPIC_API_KEY` falsa no ambiente; revisão de `riscado.md` (modelo haiku) criou
  `riscado_v2.md` + relatório, com uma pendência para o autor, sem cobrança por API.
- Bug encontrado e corrigido: a confirmação dependia do evento `close` do `<dialog>`, que o
  Chrome atrasa em aba oculta; passou a usar o `submit` do formulário.
- Não executado manualmente: `claude auth logout`/login (seção 5) e o acesso por API com
  chave real (seção 6). Ambos estão cobertos pelos testes automáticos com processos simulados.

### Após a remediação do /speckit-analyze (Phase 8)

- `python -m pytest tests -q`: **104 passed**.
- Novos comandos: `python revisar_md.py a.md b.md`, `python revisar_md.py --definir-chave-api`,
  `python -m gera_md comparar original.md versao_v2.md`.
- Revisão sem diferença no texto não grava mais `_vN`; só `nome_revisao.md`.
