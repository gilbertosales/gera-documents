// Lista de arquivos: preenchida aos poucos, com filtro, ordenação, seleção múltipla e teclado.
import { esc, seloSituacao } from "./util.js";

const TIPO = { correcao: "correção", revisao_ia: "revisão IA" };

export function criarLista({ aoFocar, aoAbrir }) {
  const tbody = document.querySelector("#lista tbody");
  const vazio = document.getElementById("lista-vazia");
  const chkTodos = document.getElementById("chk-todos");
  const campoBusca = document.getElementById("campo-busca");
  const selOrdem = document.getElementById("sel-ordem");
  const chips = [...document.querySelectorAll(".chips [data-filtro]")];

  let arquivos = [];          // ordem do servidor
  let visiveis = [];          // após filtro/ordem
  const selecionados = new Set();
  let foco = null;
  let ancora = null;          // para Shift+clique
  let filtro = "";
  let busca = "";
  let ordem = "";
  let agendado = false;
  let textoVazio = vazio.innerHTML;

  function agendar() {
    if (agendado) return;
    agendado = true;
    requestAnimationFrame(() => { agendado = false; desenhar(); });
  }

  function calcularVisiveis() {
    const termo = busca.toLowerCase();
    let v = arquivos.filter((a) => (!filtro || a.situacao === filtro) &&
      (!termo || a.rotulo.toLowerCase().includes(termo)));
    if (ordem === "nome") v = [...v].sort((a, b) => a.rotulo.localeCompare(b.rotulo, "pt-BR"));
    else if (ordem === "erros") v = [...v].sort((a, b) => b.erros - a.erros || b.avisos - a.avisos);
    else if (ordem === "avisos") v = [...v].sort((a, b) => b.avisos - a.avisos || b.erros - a.erros);
    return v;
  }

  function desenhar() {
    visiveis = calcularVisiveis();
    const contas = { "": arquivos.length, Corrigir: 0, Revisar: 0, OK: 0 };
    for (const a of arquivos) contas[a.situacao]++;
    for (const c of chips) {
      c.querySelector("[data-conta]").textContent = contas[c.dataset.filtro] ? `(${contas[c.dataset.filtro]})` : "";
      c.setAttribute("aria-checked", String(c.dataset.filtro === filtro));
    }
    tbody.innerHTML = visiveis.map((a) => {
      const versao = a.origem ? " versao" : "";
      const tipo = TIPO[a.tipo_versao] ? `<span class="tipo-versao">v${a.versao ?? ""} · ${TIPO[a.tipo_versao]}</span>` : "";
      const sel = selecionados.has(a.caminho);
      return `<tr data-caminho="${esc(a.caminho)}" class="${sel ? "selecionado" : ""}${a.caminho === foco ? " foco" : ""}" aria-selected="${sel}">
        <td class="c-sel"><input type="checkbox" tabindex="-1" ${sel ? "checked" : ""} aria-label="Selecionar ${esc(a.rotulo)}"></td>
        <td class="nome${versao}">${esc(a.rotulo)}${tipo}</td>
        <td class="c-num">${a.erros}</td>
        <td class="c-num">${a.avisos}</td>
        <td>${seloSituacao(a.situacao)}</td>
      </tr>`;
    }).join("");
    vazio.hidden = visiveis.length > 0;
    if (!visiveis.length) vazio.innerHTML = arquivos.length ? "Nenhum arquivo com esse filtro." : textoVazio;
    chkTodos.checked = visiveis.length > 0 && visiveis.every((a) => selecionados.has(a.caminho));
    tbody.querySelector("tr.foco")?.scrollIntoView({ block: "nearest" });
  }

  function focar(caminho, { selecionarSo = false } = {}) {
    foco = caminho;
    if (selecionarSo) { selecionados.clear(); if (caminho) selecionados.add(caminho); }
    ancora = caminho;
    desenhar();
    aoFocar(arquivos.find((a) => a.caminho === caminho) || null);
  }

  tbody.addEventListener("click", (ev) => {
    const tr = ev.target.closest("tr[data-caminho]");
    if (!tr) return;
    const c = tr.dataset.caminho;
    if (ev.target.matches("input[type=checkbox]") || ev.ctrlKey || ev.metaKey) {
      selecionados.has(c) ? selecionados.delete(c) : selecionados.add(c);
      foco = c; ancora = c;
      desenhar();
      aoFocar(arquivos.find((a) => a.caminho === c));
    } else if (ev.shiftKey && ancora) {
      const i = visiveis.findIndex((a) => a.caminho === ancora);
      const j = visiveis.findIndex((a) => a.caminho === c);
      selecionados.clear();
      for (const a of visiveis.slice(Math.min(i, j), Math.max(i, j) + 1)) selecionados.add(a.caminho);
      foco = c;
      desenhar();
      aoFocar(arquivos.find((a) => a.caminho === c));
    } else {
      focar(c, { selecionarSo: true });
    }
  });
  tbody.addEventListener("dblclick", (ev) => {
    const tr = ev.target.closest("tr[data-caminho]");
    if (tr) aoAbrir(tr.dataset.caminho);
  });
  tbody.addEventListener("keydown", (ev) => {
    if (!visiveis.length) return;
    const i = Math.max(0, visiveis.findIndex((a) => a.caminho === foco));
    if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
      ev.preventDefault();
      const j = Math.min(visiveis.length - 1, Math.max(0, i + (ev.key === "ArrowDown" ? 1 : -1)));
      const c = visiveis[j].caminho;
      if (ev.shiftKey) { selecionados.add(c); foco = c; desenhar(); aoFocar(visiveis[j]); }
      else focar(c, { selecionarSo: true });
    } else if (ev.key === " ") {
      ev.preventDefault();
      const c = visiveis[i].caminho;
      selecionados.has(c) ? selecionados.delete(c) : selecionados.add(c);
      foco = c; desenhar();
    } else if (ev.key === "Enter") {
      ev.preventDefault();
      focar(visiveis[i].caminho);
    } else if (ev.key.toLowerCase() === "a" && (ev.ctrlKey || ev.metaKey)) {
      ev.preventDefault();
      for (const a of visiveis) selecionados.add(a.caminho);
      desenhar();
    }
  });
  chkTodos.addEventListener("change", () => {
    if (chkTodos.checked) for (const a of visiveis) selecionados.add(a.caminho);
    else for (const a of visiveis) selecionados.delete(a.caminho);
    desenhar();
  });
  for (const c of chips) c.addEventListener("click", () => { filtro = c.dataset.filtro; desenhar(); });
  campoBusca.addEventListener("input", () => { busca = campoBusca.value.trim(); desenhar(); });
  selOrdem.addEventListener("change", () => { ordem = selOrdem.value; desenhar(); });

  return {
    limpar(mensagem) {
      arquivos = []; selecionados.clear(); foco = null; ancora = null;
      if (mensagem) textoVazio = mensagem;
      desenhar();
      aoFocar(null);
    },
    /** Insere/atualiza na posição informada pelo servidor. */
    receber(arquivo, indice) {
      const atual = arquivos.findIndex((a) => a.caminho === arquivo.caminho);
      if (atual >= 0) arquivos.splice(atual, 1);
      const pos = Number.isInteger(indice) ? Math.min(indice, arquivos.length) : arquivos.length;
      arquivos.splice(pos, 0, arquivo);
      if (arquivo.caminho === foco) aoFocar(arquivo);
      agendar();
    },
    focar(caminho) { focar(caminho, { selecionarSo: true }); },
    selecionar(caminhos) { selecionados.clear(); caminhos.forEach((c) => selecionados.add(c)); desenhar(); },
    get arquivos() { return arquivos; },
    get selecionados() { return arquivos.filter((a) => selecionados.has(a.caminho)); },
    get foco() { return arquivos.find((a) => a.caminho === foco) || null; },
    obter(caminho) { return arquivos.find((a) => a.caminho === caminho) || null; },
  };
}
