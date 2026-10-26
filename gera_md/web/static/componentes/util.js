// Utilitários compartilhados pelos componentes.

export class ErroApi extends Error {
  constructor(status, erro, acao, dados) {
    super(erro);
    this.status = status;
    this.acao = acao || "";
    this.dados = dados || {};
  }
}

export async function api(metodo, url, corpo) {
  const opcoes = { method: metodo, headers: {}, credentials: "same-origin" };
  if (corpo !== undefined) {
    opcoes.headers["Content-Type"] = "application/json";
    opcoes.body = JSON.stringify(corpo);
  }
  let resp;
  try {
    resp = await fetch(url, opcoes);
  } catch {
    throw new ErroApi(0, "Sem conexão com o servidor local.",
      "Confira se a janela do Gera Documents ainda está aberta e recarregue a página.");
  }
  const texto = await resp.text();
  let dados = {};
  try { dados = texto ? JSON.parse(texto) : {}; } catch { dados = { erro: texto }; }
  if (!resp.ok) throw new ErroApi(resp.status, dados.erro || `Erro ${resp.status}`, dados.acao, dados);
  return dados;
}

const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ESC[c]);

export function h(html) {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

export const nomeArquivo = (p) => String(p).split(/[\\/]/).pop();

export const ICONE_SITUACAO = { Corrigir: "✖", Revisar: "!", OK: "✔" };

export function seloSituacao(sit) {
  return `<span class="sit sit-${esc(sit)}"><span aria-hidden="true">${ICONE_SITUACAO[sit] || ""}</span>${esc(sit)}</span>`;
}

export const usd = (v) => `US$ ${Number(v || 0).toFixed(2)}`;
