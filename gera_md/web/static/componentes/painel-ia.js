// Painel de IA: provedores com tipo de acesso e estado, skill, modelo e acesso por API opcional.
import { api, esc } from "./util.js";

const ESTADO = {
  logado: "logado",
  login_necessario: "login necessário",
  nao_instalado: "não instalado",
  chave_ausente: "chave não configurada",
  erro: "erro",
};

export function criarPainelIA({ aoRevisar, aoErro, aoMensagem }) {
  const caixa = document.getElementById("painel-ia");
  let provedores = [];
  let skills = [];
  let escolhido = null;
  let skill = "";
  let modelo = "padrão";
  let ocupado = false;
  let temSelecao = false;
  let apiAberto = false;

  let prefs = null;  // preferências salvas (provedor/modelo usados por último)

  async function carregar(atualizar = false) {
    try {
      const [p, s, c] = await Promise.all([
        api("GET", `/api/provedores${atualizar ? "?atualizar=1" : ""}`),
        skills.length ? Promise.resolve(skills) : api("GET", "/api/skills"),
        prefs ? Promise.resolve(prefs) : api("GET", "/api/config"),
      ]);
      provedores = p;
      skills = s;
      if (!prefs) {
        prefs = c;
        if (c.modelo_padrao) modelo = c.modelo_padrao;
      }
      if (!skill) skill = (s.find((x) => x.padrao) || s[0] || {}).nome || "";
      if (!escolhido || !provedores.some((x) => x.id === escolhido)) {
        // FR-025: a escolha inicial nunca é um acesso por API
        const lembrado = provedores.find((x) => x.id === prefs.provedor_padrao && x.tipo_acesso === "assinatura");
        escolhido = (lembrado || provedores.find((x) => x.padrao) || provedores.find((x) => x.tipo_acesso === "assinatura") || {}).id || null;
      }
      desenhar();
    } catch (e) {
      aoErro(e);
    }
  }

  function atual() { return provedores.find((p) => p.id === escolhido) || null; }

  function desenhar() {
    const p = atual();
    const pronto = p && p.estado === "logado";
    const lista = provedores.map((x) => {
      const seloAcesso = x.tipo_acesso === "api"
        ? '<span class="selo selo-api">API — cobrado por uso</span>'
        : '<span class="selo selo-assinatura">Assinatura</span>';
      const passos = x.estado !== "logado" && x.instrucoes_login?.length
        ? `<ol class="passos">${x.instrucoes_login.map((s) => `<li>${esc(s)}</li>`).join("")}</ol>` : "";
      // o acesso por API só aparece na lista depois de configurado (nunca é o padrão)
      if (x.tipo_acesso === "api" && x.estado === "chave_ausente") return "";
      return `<label class="provedor">
        <input type="radio" name="provedor" value="${esc(x.id)}" ${x.id === escolhido ? "checked" : ""}>
        <span><span class="nome-ia">${esc(x.nome)}</span>${seloAcesso}
          <span class="selo selo-${esc(x.estado)}">${esc(ESTADO[x.estado] || x.estado)}</span>
          <span class="det">${esc(x.detalhe || "")}</span>${passos}</span>
      </label>`;
    }).join("");
    const api_ = provedores.find((x) => x.tipo_acesso === "api");
    const p_modelos = (p?.modelos || ["padrão"]);
    if (!p_modelos.includes(modelo)) modelo = p_modelos[0];
    caixa.innerHTML = `
      <h2>Revisão de texto com IA</h2>
      ${lista || '<p class="dica">Nenhuma IA disponível.</p>'}
      <div class="ia-linha">
        <button type="button" data-verificar>Verificar de novo</button>
      </div>
      <div class="ia-linha">
        <label>Skill <select data-skill>${skills.map((s) => `<option ${s.nome === skill ? "selected" : ""}>${esc(s.nome)}</option>`).join("")}</select></label>
        <label>Modelo <select data-modelo>${p_modelos.map((m) => `<option ${m === modelo ? "selected" : ""}>${esc(m)}</option>`).join("")}</select></label>
        <button type="button" class="primario" data-revisar ${pronto && temSelecao && !ocupado ? "" : "disabled"}>Revisar texto (IA)</button>
      </div>
      <p class="dica">${!temSelecao ? "Selecione um ou mais arquivos na lista." :
        !pronto ? "A IA escolhida precisa estar logada." :
        "Corrige vícios de linguagem, redundâncias e ambiguidades em tom técnico; cria nova versão + relatório."}</p>
      ${api_ ? `<details class="api" ${apiAberto ? "open" : ""}>
        <summary>Acesso por API (opcional)</summary>
        <p class="aviso-cobranca">Será cobrado por uso na sua conta da API, separado da assinatura.
          A chave fica no cofre de credenciais do sistema, nunca em arquivo.</p>
        <div class="ia-linha">
          <input type="password" data-chave placeholder="sk-ant-..." autocomplete="off" aria-label="Chave de API" style="flex:1">
          <button type="button" data-salvar-chave>Salvar</button>
          ${api_.estado !== "chave_ausente" ? '<button type="button" data-remover-chave>Remover</button>' : ""}
        </div>
        <p class="det">${esc(api_.detalhe || "")}</p>
      </details>` : ""}`;

    caixa.querySelectorAll("input[name=provedor]").forEach((r) =>
      r.addEventListener("change", () => { escolhido = r.value; desenhar(); }));
    caixa.querySelector("[data-skill]")?.addEventListener("change", (e) => { skill = e.target.value; });
    caixa.querySelector("[data-modelo]")?.addEventListener("change", (e) => { modelo = e.target.value; });
    caixa.querySelector("[data-verificar]").addEventListener("click", () => carregar(true));
    caixa.querySelector("[data-revisar]")?.addEventListener("click", () => aoRevisar({ provedor: escolhido, skill, modelo }));
    caixa.querySelector("details.api")?.addEventListener("toggle", (e) => { apiAberto = e.target.open; });
    caixa.querySelector("[data-salvar-chave]")?.addEventListener("click", async () => {
      const campo = caixa.querySelector("[data-chave]");
      try {
        await api("PUT", "/api/provedores/claude-api/chave", { chave: campo.value });
        campo.value = "";
        aoMensagem("Chave de API salva no cofre do sistema. O acesso por API aparece como opção separada.");
        await carregar(true);
      } catch (e) { aoErro(e); }
    });
    caixa.querySelector("[data-remover-chave]")?.addEventListener("click", async () => {
      try {
        await api("DELETE", "/api/provedores/claude-api/chave");
        if (escolhido === "claude-api") escolhido = null;
        aoMensagem("Chave de API removida.");
        await carregar(true);
      } catch (e) { aoErro(e); }
    });
  }

  return {
    carregar,
    atualizarProvedor(p) {
      const i = provedores.findIndex((x) => x.id === p.id);
      if (i >= 0) provedores[i] = p; else provedores.push(p);
      desenhar();
    },
    definirSelecao(sim) { if (temSelecao !== sim) { temSelecao = sim; desenhar(); } },
    ocupado(sim) { ocupado = sim; desenhar(); },
  };
}
