<!--
Sync Impact Report
- Version change: (template, sem versão) → 1.0.0
- Princípios definidos (primeira ratificação):
  I. Original Intocável
  II. Fidelidade ao Conversor Word
  III. Local-First, IA por Login
  IV. Núcleo Separado da Interface
  V. IA Protegida e Auditável
  VI. Interface Responsiva e Clara
  VII. Regras Testáveis e Idempotentes
- Seções adicionadas: Restrições Técnicas; Fluxo de Desenvolvimento e Quality Gates; Governance
- Seções removidas: nenhuma
- Templates (.specify/templates/*): não alterados por este comando; leem a constituição em
  tempo de execução. Revisar manualmente o "Constitution Check" do plan-template se ele
  tiver gates fixos.
- TODOs adiados: nenhum
-->

# Gera Documents Constitution

## Core Principles

### I. Original Intocável

- O arquivo de entrada do usuário MUST NOT ser sobrescrito, renomeado ou apagado por
  nenhuma operação (correção automática, revisão por IA, conversão).
- Toda saída MUST ser gravada como nova versão (`nome_vN.md`, `nome_vN_revisao.md`,
  `.docx`) no próximo número livre; nenhuma versão existente pode ser sobrescrita.
- Arquivos temporários criados por uma operação que não produziu mudança MUST ser
  removidos ao final.

**Rationale**: os documentos são entregáveis de consultoria; perda de conteúdo é
inaceitável e o usuário precisa sempre poder comparar antes e depois.

### II. Fidelidade ao Conversor Word

- `gerar_word.py` é a fonte da verdade sobre o que o Word suporta. As regras do
  analisador MUST refletir exatamente o comportamento do conversor.
- Parsing compartilhado (tabelas, separadores, título) MUST ser importado do conversor
  ou de um módulo comum — nunca reimplementado em paralelo.
- Toda mudança no suporte do conversor (ex.: passar a aceitar links ou `~~riscado~~`)
  MUST vir acompanhada da atualização das regras de análise e correção na mesma entrega.
- Cada achado MUST ter nível (`ERRO`, `AVISO`, `INFO`), linha e mensagem que diga o que
  sai errado no Word e como corrigir.

**Rationale**: um analisador que diverge do conversor gera falsos alarmes ou deixa
passar erros, e o usuário perde a confiança no relatório.

### III. Local-First, IA por Login

- A aplicação MUST rodar inteiramente na máquina do usuário, incluindo pastas de rede
  (UNC), sem depender de servidor próprio na nuvem.
- Provedores de IA MUST ser acessados por uma camada de adaptadores com contrato único
  (disponibilidade, login, execução, uso/custo). O Claude Code logado (Pro/Max) é o
  provedor padrão; outros (ex.: CLIs de outras IAs) MAY ser adicionados como novos
  adaptadores sem alterar o núcleo.
- O uso por assinatura com login MUST ser o caminho principal; chave de API é opcional,
  MUST NOT ser gravada no repositório ou em arquivo de configuração em texto puro, e o
  usuário MUST ser avisado quando o modo escolhido gera cobrança.
- Conteúdo de documento MUST ser enviado somente ao provedor escolhido e somente após
  confirmação explícita do usuário.
- Se nenhum provedor estiver disponível, as funções sem IA (análise, v2, Word) MUST
  continuar funcionando e a interface MUST explicar como fazer login.

**Rationale**: o público usa a assinatura que já tem, em ambiente corporativo, com
documentos de clientes; privacidade e custo previsível são requisitos.

### IV. Núcleo Separado da Interface

- Análise, correção, revisão por IA, relatório e geração de Word MUST existir como
  funções de núcleo sem dependência de UI, retornando dados estruturados
  (serializáveis em JSON).
- Todas as interfaces (CLI, tela desktop, frontend web local) MUST consumir o mesmo
  núcleo; regra de negócio dentro de código de tela é proibida.
- A CLI (`--relatorio`, `--v2` e equivalentes) MUST ser mantida com paridade de
  funcionalidade com a interface gráfica.

**Rationale**: hoje a tela concentra centenas de linhas de closures com lógica; separar
permite trocar o frontend, testar o núcleo e automatizar em lote.

### V. IA Protegida e Auditável

- Blocos de código, imagens, âncoras e tabelas estruturais MUST ser protegidos antes do
  envio à IA e restaurados depois; resposta que perder marcador, vier truncada ou com
  erro MUST manter o trecho original e ser listada como "não revisado".
- Toda alteração da IA MUST constar no relatório de revisão com categoria e trecho, e as
  pendências para o autor MUST ser exibidas separadamente.
- A versão revisada MUST passar de novo pelo analisador antes de ser apresentada.
- Uso e custo equivalente informados pelo provedor MUST ser exibidos por arquivo e no
  total da operação.

**Rationale**: a IA melhora o texto, mas não pode quebrar a estrutura nem alterar o
documento sem rastro.

### VI. Interface Responsiva e Clara

- Operações de I/O, rede ou IA MUST rodar fora da thread de interface, com progresso
  visível e opção de cancelar operações longas.
- A interface MUST estar em pt-BR, mostrar o estado de cada arquivo (Corrigir, Revisar,
  OK) com cor **e** texto, permitir filtrar/ordenar a lista e mostrar os problemas no
  contexto da linha do arquivo.
- O fluxo principal (escolher pasta → analisar → corrigir → revisar → gerar Word) MUST
  ser executável sem ler documentação, e erros MUST dizer o que fazer a seguir.
- Interfaces web locais MUST escutar apenas em `127.0.0.1`.

**Rationale**: o usuário final é consultor, não desenvolvedor; travamento de tela em
pasta de rede ou revisão longa é a principal causa de abandono.

### VII. Regras Testáveis e Idempotentes

- Cada regra de análise MUST ter ao menos um caso de teste positivo e um negativo
  (arquivos `.md` de exemplo).
- Cada correção automática MUST ser idempotente: corrigir uma v2 já corrigida não gera
  novas correções, e a v2 nunca tem mais `ERRO` que o original.
- Testes do núcleo MUST rodar sem UI e sem provedor de IA (provedor simulado).

**Rationale**: as regras são heurísticas com regex; sem testes, cada ajuste reintroduz
regressões silenciosas.

## Restrições Técnicas

- Python 3.10+; Windows é a plataforma principal, Linux/macOS devem continuar
  funcionando.
- Arquivos lidos e gravados em UTF-8; arquivos em outra codificação são convertidos
  apenas na nova versão.
- Dependências novas MUST ser justificadas no plano da feature; o caminho sem IA MUST
  funcionar só com Python e `python-docx` (Node.js/`npx` permanece opcional para
  Mermaid).
- A configuração do usuário fica em arquivo JSON local ao lado dos scripts ou no perfil
  do usuário, sem segredos.
- A escolha da tecnologia do frontend é decisão de plano (`/speckit-plan`), desde que
  respeite os princípios III, IV e VI.

## Fluxo de Desenvolvimento e Quality Gates

- Toda feature segue Spec Kit: `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` →
  `/speckit-implement`, e o plano MUST conter o "Constitution Check" com os princípios
  I–VII.
- Antes de entregar: testes do núcleo passando; CLI e interface gráfica testadas
  manualmente com uma pasta local e uma de rede; nenhum original alterado.
- Mudanças em regras de análise ou correção MUST listar no resumo da entrega quais
  mensagens/níveis mudaram.
- Complexidade adicional (novo processo, servidor, banco, framework) MUST ser
  justificada no plano com a alternativa mais simples descartada.

## Governance

- Esta constituição prevalece sobre outras práticas do projeto. Conflitos são
  resolvidos alterando a constituição, não ignorando-a.
- Emendas são feitas via `/speckit-constitution`, com Sync Impact Report e revisão de
  quem mantém o projeto.
- Versionamento semântico: MAJOR para remoção ou redefinição incompatível de princípio;
  MINOR para princípio ou seção nova ou expansão material; PATCH para redação e
  esclarecimentos.
- Revisão de conformidade: todo plano e toda entrega MUST verificar os princípios; o
  descumprimento justificado MUST ficar registrado na seção de complexidade do plano.

**Version**: 1.0.0 | **Ratified**: 2026-10-14 | **Last Amended**: 2026-10-14
