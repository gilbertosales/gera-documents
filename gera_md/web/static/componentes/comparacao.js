// Comparação lado a lado (coluna única em telas estreitas) entre a origem e uma versão.
import { api, esc, nomeArquivo } from "./util.js";

const CONTEXTO = 3;     // linhas iguais mantidas ao redor das mudanças
const RECOLHER = 10;    // blocos iguais maiores que isso são recolhidos

function linhaLado(tipo, na, ta, nb, tb) {
  const cls = tipo === "igual" ? "" : `t-${tipo}`;
  return `<tr>
    <td class="n">${na ?? ""}</td><td class="${na != null ? cls : ""}">${na != null ? esc(ta) : ""}</td>
    <td class="n">${nb ?? ""}</td><td class="${nb != null ? cls : ""}">${nb != null ? esc(tb) : ""}</td></tr>`;
}

function linhaUnica(tipo, n, texto, marca) {
  return `<tr><td class="n">${n ?? ""}</td><td class="${tipo === "igual" ? "" : `t-${tipo}`}">${marca} ${esc(texto)}</td></tr>`;
}

function desenhar(blocos, lado) {
  const linhas = [];
  blocos.forEach((b, idx) => {
    if (b.tipo === "igual") {
      const n = b.linhas_a.length;
      const mostrar = (i) => lado
        ? linhaLado("igual", b.a[0] + i, b.linhas_a[i], b.b[0] + i, b.linhas_b[i])
        : linhaUnica("igual", b.b[0] + i, b.linhas_b[i], " ");
      if (n > RECOLHER) {
        const ini = idx === 0 ? 0 : CONTEXTO;
        const fim = idx === blocos.length - 1 ? 0 : CONTEXTO;
        for (let i = 0; i < ini; i++) linhas.push(mostrar(i));
        const ocultas = n - ini - fim;
        const conteudo = [];
        for (let i = ini; i < n - fim; i++) conteudo.push(mostrar(i));
        linhas.push(`<tr class="recolhido" data-conteudo="${esc(conteudo.join(""))}"><td colspan="${lado ? 4 : 2}">⋯ ${ocultas} linha(s) iguais — clique para mostrar</td></tr>`);
        for (let i = n - fim; i < n; i++) linhas.push(mostrar(i));
      } else {
        for (let i = 0; i < n; i++) linhas.push(mostrar(i));
      }
      return;
    }
    const la = b.linhas_a, lb = b.linhas_b;
    if (lado) {
      for (let i = 0; i < Math.max(la.length, lb.length); i++) {
        linhas.push(linhaLado(b.tipo, i < la.length ? b.a[0] + i : null, la[i], i < lb.length ? b.b[0] + i : null, lb[i]));
      }
    } else {
      la.forEach((t, i) => linhas.push(linhaUnica(b.tipo === "inserido" ? "inserido" : "removido", b.a[0] + i, t, "−")));
      lb.forEach((t, i) => linhas.push(linhaUnica(b.tipo === "removido" ? "removido" : "inserido", b.b[0] + i, t, "+")));
    }
  });
  return linhas.join("");
}

export function criarComparacao({ aoErro }) {
  const dlg = document.getElementById("dlg-comparacao");
  const corpo = document.getElementById("cmp-corpo");
  const titulo = document.getElementById("cmp-titulo");
  document.getElementById("cmp-fechar").addEventListener("click", () => dlg.close());
  corpo.addEventListener("click", (ev) => {
    const tr = ev.target.closest("tr.recolhido");
    if (tr) tr.outerHTML = tr.dataset.conteudo;
  });

  return {
    async abrir(analiseId, origem, versao) {
      try {
        const q = new URLSearchParams({ analise_id: analiseId, a: origem, b: versao });
        const { blocos } = await api("GET", `/api/comparacao?${q}`);
        const lado = window.innerWidth >= 900;
        const mudancas = blocos.filter((b) => b.tipo !== "igual").length;
        titulo.textContent = `${nomeArquivo(origem)} → ${nomeArquivo(versao)} · ${mudancas} trecho(s) diferente(s)`;
        corpo.innerHTML = `<table class="cmp">${lado
          ? `<colgroup><col style="width:48px"><col><col style="width:48px"><col></colgroup>
             <thead><tr><th colspan="2">${esc(nomeArquivo(origem))}</th><th colspan="2">${esc(nomeArquivo(versao))}</th></tr></thead>`
          : `<colgroup><col style="width:40px"><col></colgroup>`}
          <tbody>${mudancas ? desenhar(blocos, lado) : `<tr><td colspan="4" class="dica" style="padding:16px">Os dois arquivos são idênticos.</td></tr>`}</tbody></table>`;
        dlg.showModal();
        corpo.querySelector(".t-inserido, .t-removido, .t-alterado")?.scrollIntoView({ block: "center" });
      } catch (e) {
        aoErro(e);
      }
    },
  };
}
