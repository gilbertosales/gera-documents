// Painel de detalhes do arquivo em foco: revisão por IA, correções aplicadas e problemas.
import { esc, usd } from "./util.js";

const ORDEM = ["ERRO", "AVISO", "INFO"];
const TITULO = { ERRO: "Erros", AVISO: "Avisos", INFO: "Informações" };

function blocoRevisao(r, aoAbrirRelatorio) {
  const total = Object.values(r.contagem || {}).reduce((s, n) => s + n, 0);
  const cobranca = r.cobranca === "por_uso"
    ? `cobrado por uso (API): ${usd(r.uso?.custo_usd)}`
    : `equivalente em API ${usd(r.uso?.custo_usd)} (não cobrado no Pro/Max)`;
  const itens = Object.entries(r.contagem || {}).sort((a, b) => b[1] - a[1])
    .map(([c, n]) => `<li class="fix">✔ ${esc(c)}: ${n}</li>`).join("");
  const falhas = (r.falhas || []).map((f) => `<li class="falha">✖ Trecho não revisado (${esc(f.secao)}): ${esc(f.erro)}</li>`).join("");
  const pend = (r.pendencias || []).map((p) => `<li class="pend">? [${esc(p.secao)}] ${esc(p.texto)}</li>`).join("");
  const el = document.createElement("div");
  el.innerHTML = `
    <h3>Revisão de texto com IA</h3>
    <p class="meta">${total} alteração(ões) · ${esc(r.tipo_acesso === "api" ? "API" : "assinatura")} · ${esc(cobranca)}
      · skill ${esc(r.skill)} · modelo ${esc(r.modelo)}</p>
    ${r.destino ? "" : '<p class="dica">Nenhuma alteração no texto — nenhuma versão foi gravada. Veja as pendências no relatório.</p>'}
    <ul class="simples">${itens || (r.destino ? '<li class="dica">Nenhuma alteração sugerida.</li>' : "")}${falhas}</ul>
    ${pend ? `<h3>Pendências para o autor (${r.pendencias.length})</h3><ul class="simples">${pend}</ul>` : ""}
    ${r.relatorio ? `<p><button type="button" class="link" data-relatorio>Abrir relatório da revisão</button></p>` : ""}`;
  el.querySelector("[data-relatorio]")?.addEventListener("click", () => aoAbrirRelatorio(r.relatorio));
  return el;
}

export function criarDetalhes({ aoAbrirRelatorio }) {
  const caixa = document.getElementById("detalhes");

  function mostrar(arquivo) {
    caixa.innerHTML = "";
    if (!arquivo) {
      caixa.innerHTML = '<p class="dica">Selecione um arquivo para ver os problemas encontrados.</p>';
      return;
    }
    const cab = document.createElement("div");
    const origem = arquivo.origem ? `<p class="meta">Versão criada a partir de ${esc(arquivo.origem.split(/[\\/]/).pop())}</p>` : "";
    cab.innerHTML = `<h2>${esc(arquivo.rotulo)}</h2>${origem}`;
    caixa.append(cab);

    if (arquivo.revisao) caixa.append(blocoRevisao(arquivo.revisao, aoAbrirRelatorio));

    if (arquivo.correcoes?.length) {
      const el = document.createElement("div");
      el.innerHTML = `<h3>Correções aplicadas (${arquivo.correcoes.length})</h3><ul class="simples">${
        arquivo.correcoes.map((c) => `<li class="fix">✔ [${c.linha ? `linha ${c.linha} do original` : "geral"}] ${esc(c.descricao)}</li>`).join("")
      }</ul>`;
      caixa.append(el);
    }

    const achados = arquivo.achados || [];
    if (!achados.length) {
      caixa.insertAdjacentHTML("beforeend", '<p class="pronto">Nenhum problema encontrado — pronto para o Word. ✔</p>');
      return;
    }
    for (const nivel of ORDEM) {
      const grupo = achados.filter((a) => a.nivel === nivel);
      if (!grupo.length) continue;
      const el = document.createElement("div");
      el.innerHTML = `<h3>${TITULO[nivel]} (${grupo.length})</h3>` + grupo.map((a) => `
        <div class="achado n-${nivel}">
          <div class="cab"><span class="nivel">${nivel}</span>
            <span class="linha">${a.linha ? `linha ${a.linha}` : "arquivo inteiro"}</span>
            <span>${esc(a.mensagem)}</span></div>
          ${a.trecho != null && a.trecho !== "" ? `<pre>${esc(a.trecho)}</pre>` : ""}
        </div>`).join("");
      caixa.append(el);
    }
    const temProblema = achados.some((a) => a.nivel !== "INFO");
    if (arquivo.tipo_versao === "original" && temProblema) {
      caixa.insertAdjacentHTML("beforeend", '<p class="dica">Clique em <b>Criar versão corrigida</b> para gerar uma versão corrigida deste arquivo.</p>');
    } else if (arquivo.tipo_versao === "correcao" && temProblema) {
      caixa.insertAdjacentHTML("beforeend", '<p class="dica">Os problemas acima não têm correção automática — ajuste manualmente no arquivo.</p>');
    }
  }

  mostrar(null);
  return { mostrar };
}
