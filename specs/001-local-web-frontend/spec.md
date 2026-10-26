# Feature Specification: Frontend Web Local com Várias IAs via Login

**Feature Branch**: `001-local-web-frontend`

**Created**: 2026-10-14

**Status**: Draft

**Input**: User description: "frontend web local para analisar_md com várias IAs via login, lembrando que é para utilizar Claude Pro, não uma API do Claude; se quiser utilizar API será outro tipo de acesso."

## Clarifications

### Session 2026-10-14

- Q: Como a lista de arquivos deve tratar os relatórios (`*_revisao.md` e `relatorio_analise_md.md`) encontrados na pasta? → A: Esconder da lista; abrir só pelo link "Abrir relatório" nos detalhes da revisão. (Motivo: um Word foi gerado a partir do relatório de revisão, com as notas de vício de linguagem e sem as imagens.)
- Q: Quando a IA citar um marcador interno como `⟦BLOCO_29⟧` nas pendências ou alterações, o que o relatório de revisão deve mostrar no lugar? → A: O conteúdo resumido do bloco: `[imagem: caminho.png]`, `[bloco de código: primeira linha…]` ou `[âncora: id]`.
- Q: Onde e com que nome deve ficar o Word corrigido gerado de uma versão revisada? → A: Ao lado do `.md` de origem, com o mesmo nome (`tutorial-fluxo-completo_v3.md` → `tutorial-fluxo-completo_v3.docx`); o `.docx` gerado errado não é apagado nem sobrescrito.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Analisar e corrigir uma pasta pelo navegador (Priority: P1)

O consultor abre a ferramenta no navegador da própria máquina, informa uma pasta local ou
de rede, vê a lista de arquivos `.md` com o número de erros e avisos de cada um, abre um
arquivo para ver os problemas destacados na linha em que ocorrem e cria a versão corrigida
(`_v2`) de um ou de vários arquivos. Nada disso depende de IA.

**Why this priority**: é o fluxo que já existe hoje na tela desktop e entrega valor sozinho;
sem ele o frontend não substitui a ferramenta atual.

**Independent Test**: abrir a ferramenta numa máquina sem nenhuma IA configurada, analisar
uma pasta de exemplo com problemas conhecidos e criar as versões corrigidas; conferir que os
originais ficaram intactos e que as novas versões aparecem na lista com menos problemas.

**Acceptance Scenarios**:

1. **Given** uma pasta com 20 arquivos `.md`, **When** o usuário informa a pasta e inicia a
   busca, **Then** a lista é preenchida progressivamente com arquivo, erros, avisos e
   situação (Corrigir, Revisar, OK), e o usuário pode continuar usando a tela durante a busca.
2. **Given** a lista preenchida, **When** o usuário seleciona um arquivo, **Then** vê os
   problemas agrupados por nível, cada um com a linha do arquivo e o trecho correspondente.
3. **Given** arquivos com problemas selecionados, **When** o usuário pede a versão corrigida,
   **Then** cada um ganha uma nova versão no próximo número livre, a lista mostra a nova
   versão logo abaixo do original com as correções aplicadas e o que ainda exige ajuste manual.
4. **Given** a lista preenchida, **When** o usuário filtra por situação ou digita parte do
   nome, **Then** só os arquivos correspondentes são exibidos.
5. **Given** um arquivo selecionado, **When** o usuário pede para gerar o Word, **Then** a
   geração do documento Word é iniciada com esse arquivo já preenchido.

---

### User Story 2 - Revisar texto com IA usando a assinatura logada (Priority: P1)

O consultor escolhe qual IA usar entre as que estão disponíveis e logadas na máquina (por
padrão, o Claude da assinatura Pro/Max), escolhe a skill de revisão e revisa um ou vários
arquivos. A ferramenta deixa claro que o uso consome o limite da assinatura, sem cobrança
extra, mostra o progresso de cada arquivo, permite cancelar, e no fim exibe as alterações
feitas e as pendências para o autor.

**Why this priority**: é o motivo principal do pedido — usar a assinatura que o usuário já
paga, sem chave de API.

**Independent Test**: numa máquina com o Claude logado pela assinatura e sem nenhuma chave de
API configurada, revisar um arquivo de exemplo; conferir que a nova versão e o relatório de
revisão foram criados, que nenhuma cobrança por API ocorreu e que blocos de código e imagens
continuam idênticos.

**Acceptance Scenarios**:

1. **Given** o Claude logado via assinatura, **When** o usuário abre a tela de IA, **Then** o
   Claude aparece como "Assinatura — logado", pronto para uso.
2. **Given** uma IA instalada mas não logada, **When** o usuário a seleciona, **Then** a
   ferramenta informa que é preciso fazer login e mostra o passo a passo para isso, sem
   travar as demais funções.
3. **Given** arquivos selecionados e uma IA logada, **When** o usuário pede a revisão,
   **Then** a ferramenta pede confirmação mostrando quais arquivos serão enviados, para qual
   IA e em qual tipo de acesso, e só envia após a confirmação.
4. **Given** uma revisão em andamento, **When** o usuário cancela, **Then** os trechos ainda
   não processados não são enviados, nenhuma versão parcial é apresentada como concluída e
   o original continua intacto.
5. **Given** uma revisão concluída, **When** o usuário seleciona a nova versão, **Then** vê o
   número de alterações por categoria, os trechos não revisados, as pendências para o autor e
   o resultado da análise de formatação dessa nova versão.

---

### User Story 3 - Comparar versões antes de aceitar (Priority: P2)

Depois de uma correção automática ou de uma revisão por IA, o consultor vê lado a lado (ou
com destaques) o que mudou entre o original e a nova versão, para decidir se vai usá-la.

**Why this priority**: aumenta a confiança no resultado, mas o fluxo principal funciona sem
ela (o relatório de revisão já lista as alterações).

**Independent Test**: criar uma versão corrigida de um arquivo de exemplo e abrir a
comparação; conferir que todas as linhas alteradas estão destacadas e que as não alteradas
não estão.

**Acceptance Scenarios**:

1. **Given** um original e sua nova versão, **When** o usuário abre a comparação, **Then** as
   linhas incluídas, removidas e alteradas aparecem destacadas de forma distinta.

---

### User Story 4 - Usar IA por API como tipo de acesso separado (Priority: P3)

Um usuário que prefere pagar por uso configura o acesso por API de uma IA. Esse acesso aparece
como um tipo diferente da assinatura, identificado como "API — cobrado por uso", e nunca é
escolhido automaticamente.

**Why this priority**: o pedido deixa claro que a API não é o caminho principal; é uma opção
para quem quiser, tratada como outro tipo de acesso.

**Independent Test**: configurar uma chave de API, conferir que ela aparece como tipo de
acesso separado com o aviso de cobrança, revisar um arquivo e verificar que o custo real é
exibido.

**Acceptance Scenarios**:

1. **Given** a mesma IA disponível por assinatura e por API, **When** o usuário abre a escolha
   de IA, **Then** os dois aparecem como opções distintas, com a assinatura selecionada por
   padrão.
2. **Given** o acesso por API escolhido, **When** o usuário confirma a revisão, **Then** a
   confirmação avisa explicitamente que haverá cobrança por uso e, no fim, mostra o custo.
3. **Given** uma chave de API informada, **When** o usuário fecha e reabre a ferramenta,
   **Then** a chave não aparece em nenhum arquivo de configuração em texto puro.

---

### Edge Cases

- Pasta de rede lenta ou que cai durante a busca: a busca mostra o erro, mantém os arquivos
  já analisados e permite tentar de novo.
- Pasta inexistente ou sem permissão: mensagem clara dizendo o que verificar.
- Arquivo que não está em UTF-8: aparece como erro na análise e a versão corrigida é gravada
  em UTF-8.
- Nenhuma IA instalada ou logada: as funções sem IA continuam disponíveis e a área de IA
  explica como instalar e fazer login.
- Limite de uso da assinatura atingido no meio da revisão: os trechos que falharem ficam como
  no original, marcados como "não revisado", e a mensagem informa que o limite foi atingido.
- Sessão de login expirada durante o uso: a ferramenta detecta, avisa e orienta a refazer o
  login.
- Arquivo alterado por outra pessoa entre a análise e a correção: a correção usa o conteúdo
  atual e a análise é refeita.
- Duas abas do navegador abertas na mesma ferramenta: as operações não se sobrepõem a ponto de
  sobrescrever versões (o próximo número livre é sempre recalculado).
- Outra máquina da rede tentando acessar a ferramenta: o acesso é recusado.
- Pasta com relatórios de revisões anteriores (`*_revisao.md`): eles não entram na lista nem
  podem virar Word por engano (FR-030).

## Requirements *(mandatory)*

### Functional Requirements

**Acesso e execução local**

- **FR-001**: A ferramenta MUST rodar inteiramente na máquina do usuário e ser usada pelo
  navegador dessa mesma máquina, sem depender de nenhum servidor externo para as funções sem IA.
- **FR-002**: A ferramenta MUST recusar conexões vindas de outras máquinas.
- **FR-003**: A ferramenta MUST ser iniciada com um único comando ou atalho, abrindo o
  navegador automaticamente na tela inicial.

**Análise e correção**

- **FR-004**: Usuários MUST poder informar uma pasta local ou de rede, digitando o caminho ou
  escolhendo a partir das pastas recentes, e optar por incluir subpastas.
- **FR-030**: Relatórios gerados pela ferramenta (`*_revisao.md`, `*_revisao_N.md` e
  `relatorio_analise_md.md`) MUST NOT aparecer na lista de arquivos nem ser aceitos por
  correção, revisão com IA ou geração do Word; são abertos só pelo link "Abrir relatório"
  nos detalhes da revisão.
- **FR-005**: A ferramenta MUST aplicar exatamente as mesmas regras de análise e de correção da
  ferramenta atual, com os mesmos níveis (ERRO, AVISO, INFO) e mensagens.
- **FR-006**: A lista de arquivos MUST ser preenchida progressivamente durante a busca, mostrar
  progresso e permitir cancelar a busca.
- **FR-007**: Usuários MUST poder filtrar a lista por situação e por nome, e ordená-la por
  nome, erros ou avisos.
- **FR-008**: A situação de cada arquivo MUST ser indicada por texto além da cor.
- **FR-009**: Ao selecionar um arquivo, a ferramenta MUST mostrar cada problema com a linha e o
  trecho do arquivo onde ocorre.
- **FR-010**: Usuários MUST poder criar a versão corrigida de um arquivo, de vários selecionados
  ou de todos os que têm problemas, com o resumo das correções aplicadas e do que ficou para
  ajuste manual.
- **FR-011**: Nenhuma operação MUST alterar, renomear ou apagar o arquivo original; toda saída
  é uma nova versão no próximo número livre.
- **FR-012**: Usuários MUST poder salvar o relatório de análise da pasta e abrir um arquivo no
  editor padrão do sistema.
- **FR-013**: Usuários MUST poder iniciar a geração do documento Word a partir do arquivo
  selecionado. O Word é sugerido ao lado do `.md` de origem e com o mesmo nome (ex.:
  `nome_v3.md` → `nome_v3.docx`), para que fique claro de qual versão ele veio.

**IA por login (assinatura)**

- **FR-014**: A ferramenta MUST listar as IAs disponíveis na máquina com o tipo de acesso e o
  estado de cada uma: "Assinatura — logado", "Assinatura — login necessário", "Não instalado",
  "API — cobrado por uso".
- **FR-015**: O Claude via assinatura Pro/Max, usando o login já feito na máquina, MUST ser o
  provedor e o tipo de acesso padrão.
- **FR-016**: Nesta versão, o Claude via assinatura é a única IA por login suportada. A
  escolha de IA MUST ser organizada de forma que uma nova IA por assinatura (ex.: ChatGPT
  Plus/Pro, Gemini) possa ser adicionada depois sem alterar as funções de análise, correção,
  revisão e relatório; a tela de escolha já lista a IA com seu tipo de acesso e estado
  (FR-014), mesmo havendo uma só.
- **FR-017**: O uso por assinatura MUST NOT exigir chave de API; se houver uma chave de API
  configurada no ambiente, ela MUST NOT ser usada pelo modo assinatura sem o usuário escolher
  explicitamente o tipo de acesso API.
- **FR-018**: Quando uma IA exigir login, a ferramenta MUST mostrar as instruções de login
  daquela IA e permitir verificar de novo o estado sem reiniciar.
- **FR-019**: Usuários MUST poder escolher a skill de revisão (padrão: revisão de documentação
  técnica) e, quando a IA oferecer, o modelo.
- **FR-020**: Antes de enviar qualquer conteúdo, a ferramenta MUST pedir confirmação mostrando
  os arquivos, a IA, o tipo de acesso e se haverá cobrança.
- **FR-021**: Durante a revisão, a ferramenta MUST mostrar o progresso por arquivo e por trecho
  e permitir cancelar.
- **FR-022**: Blocos de código, imagens e âncoras MUST permanecer idênticos após a revisão;
  trechos com resposta inválida, incompleta ou com erro MUST ficar como no original e ser
  listados como "não revisado".
- **FR-023**: Cada revisão MUST gerar um relatório das alterações. Quando o texto revisado
  difere do original, MUST também gerar uma nova versão, analisada de novo antes de ser
  exibida; quando não há diferença, nenhuma versão é gravada (constituição I) e o relatório
  (`nome_revisao.md`, no próximo número livre) traz as pendências e os trechos não revisados.
  O relatório MUST NOT conter marcadores internos (`⟦BLOCO_n⟧`): cada um é trocado pelo
  conteúdo resumido do bloco — `[imagem: caminho.png]`, `[bloco de código: primeira linha…]`
  ou `[âncora: id]`.
- **FR-024**: A ferramenta MUST mostrar, por arquivo e no total, o uso informado pela IA; no
  modo assinatura, com o aviso de que não há cobrança extra além do limite da assinatura.

**IA por API (acesso separado)**

- **FR-025**: O acesso por API MUST ser configurado separadamente, exibido como tipo de acesso
  próprio e nunca selecionado por padrão.
- **FR-026**: Chaves de API MUST ser guardadas no armazenamento seguro de credenciais do
  sistema operacional, nunca em arquivo de configuração em texto puro.
- **FR-027**: No acesso por API, a confirmação e o resultado MUST mostrar o aviso de cobrança e
  o custo da operação.

**Compatibilidade**

- **FR-028**: O uso pela linha de comando (relatório e versões corrigidas em lote) MUST
  continuar funcionando com o mesmo resultado.
- **FR-029**: A interface MUST estar em português do Brasil.

### Key Entities

- **Pasta analisada**: caminho local ou de rede, opção de subpastas, data da análise e lista de
  arquivos encontrados.
- **Arquivo Markdown**: caminho, versão (original, `_v2`, `_v3`...), arquivo de origem quando
  for uma versão, contagem de erros e avisos e situação.
- **Achado**: nível, linha, mensagem e trecho do arquivo.
- **Correção aplicada**: linha do original e descrição da correção automática.
- **Provedor de IA**: nome, tipo de acesso (assinatura ou API), estado (logado, login
  necessário, não instalado), modelos disponíveis e instruções de login.
- **Revisão por IA**: arquivo de origem, nova versão, provedor e tipo de acesso usados, skill,
  alterações por categoria, trechos não revisados, pendências para o autor, uso e custo.
- **Operação em andamento**: tipo (busca, correção, revisão), progresso, possibilidade de
  cancelar e resultado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário que nunca usou a ferramenta consegue analisar uma pasta, criar as
  versões corrigidas e revisar um arquivo com IA em até 5 minutos, sem consultar documentação.
- **SC-002**: Os primeiros resultados de uma pasta com 200 arquivos aparecem em até 3 segundos
  numa pasta local, e a tela continua respondendo durante toda a busca, inclusive em pasta de
  rede.
- **SC-003**: Para o mesmo conjunto de arquivos de exemplo, a análise e as versões corrigidas
  produzidas pelo frontend são 100% idênticas às da ferramenta atual.
- **SC-004**: Em 100% das revisões feitas no modo assinatura não há nenhuma cobrança por API.
- **SC-005**: Em 100% das operações nenhum arquivo original é alterado.
- **SC-006**: Em 100% das revisões, blocos de código, imagens e âncoras permanecem idênticos
  ao original.
- **SC-007**: O cancelamento de uma operação longa interrompe o envio de novos trechos em até
  5 segundos.
- **SC-008**: Com nenhuma IA logada, 100% das funções sem IA continuam disponíveis.

## Assumptions

- O usuário já tem a assinatura Claude Pro ou Max e o Claude Code instalado; o login é feito
  pela própria ferramenta da IA, não pelo frontend.
- O frontend não guarda senha de nenhuma IA: ele só detecta e usa o login já feito na máquina.
- Uso individual: uma pessoa por máquina; não há contas de usuário nem controle de acesso
  além da restrição à própria máquina.
- Outras IAs por assinatura (ChatGPT, Gemini, Copilot etc.) ficam para uma próxima feature;
  esta entrega só garante que adicioná-las não exige refazer o núcleo.
- A tela desktop atual pode continuar existindo; o frontend web não exige removê-la.
- As regras de análise e correção são as atuais; novas regras ficam fora desta feature.
- A geração do Word continua sendo feita pela ferramenta atual de geração; o frontend apenas
  a inicia com o arquivo escolhido.
- A edição do texto do Markdown dentro do frontend está fora do escopo; o arquivo é aberto no
  editor padrão do sistema.
- Windows é a plataforma principal, com uso frequente de pastas de rede.
