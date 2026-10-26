// Tela principal: liga a barra da pasta, a lista, os detalhes, o painel de IA e a comparação
// à API local e aos eventos (SSE) das operações longas.
import { api, esc, nomeArquivo, usd } from "./componentes/util.js";
import { criarBarraPasta } from "./componentes/pasta.js";
import { criarLista } from "./componentes/lista.js";
import { criarDetalhes } from "./componentes/detalhes.js";
import { criarPainelIA } from "./componentes/painel-ia.js";
import { criarComparacao } from "./componentes/comparacao.js";

const $ = (id) => document.getElementById(id);
const estado = { analiseId: null, pasta: "" };
const ops = new Map();        // operacao_id → { tipo, aoFim }
const pendentes = new Map();  // eventos que chegaram antes do id da operação

// ── Status, erros e diálogos ─────────────────────────────────────────────────
function status(msg, { erro = false } = {}) {
  $("status").textContent = msg;
  $("status").style.color = erro ? "var(--erro)" : "";
}

function mostrarErro(e) {
  const acao = e.acao ? ` — ${e.acao}` : "";
  status(`${e.message}${acao}`, { erro: true });
}

function dialogo(titulo, html, { confirmar = "Confirmar", cancelar = "Cancelar" } = {}) {
  const dlg = $("dlg-confirmar");
  $("dlg-titulo").textContent = titulo;
  $("dlg-corpo").innerHTML = html;
  $("dlg-sim").textContent = confirmar;
  const btnNao = dlg.querySelector('button[value="nao"]');
  btnNao.hidden = !cancelar;
  btnNao.textContent = cancelar || "";
  dlg.returnValue = "";
  dlg.showModal();
  // O "submit" do form é síncrono com o clique; o evento "close" pode atrasar (ex.: aba oculta).
  const form = dlg.querySelector("form");
  return new Promise((ok) => {
    let feito = false;
    const fim = (sim) => {
      if (feito) return;
      feito = true;
      form.removeEventListener("submit", aoEnviar);
      dlg.removeEventListener("cancel", aoCancelar);
      dlg.removeEventListener("close", aoCancelar);
      ok(sim);
    };
    const aoEnviar = (ev) => fim(ev.submitter?.value === "sim");
    const aoCancelar = () => fim(false);
    form.addEventListener("submit", aoEnviar);
    dlg.addEventListener("cancel", aoCancelar);
    dlg.addEventListener("close", aoCancelar);
  });
}

const avisar = (titulo, html) => dialogo(titulo, html, { confirmar: "OK", cancelar: null });

// ── Operações longas ─────────────────────────────────────────────────────────
function atualizarOcupado() {
  const rodando = [...ops.values()];
  const temBusca = rodando.some((o) => o.tipo === "busca");
  const temRevisao = rodando.some((o) => o.tipo === "revisao");
  barraPasta.buscando(temBusca);
  painel.ocupado(temRevisao);
  $("btn-corrigir").disabled = rodando.some((o) => o.tipo === "correcao");
  $("btn-cancelar").hidden = !rodando.length;
  $("barra").hidden = !rodando.length;
  if (!rodando.length) $("barra").removeAttribute("value");
}

function registrarOperacao(id, tipo, aoFim) {
  ops.set(id, { tipo, aoFim });
  atualizarOcupado();
  for (const [ev, dados] of pendentes.get(id) || []) tratarEvento(ev, dados);
  pendentes.delete(id);
}

async function cancelarUltima() {
  const ids = [...ops.keys()];
  const id = ids[ids.length - 1];
  if (!id) return;
  status("Cancelando...");
  try { await api("POST", `/api/operacoes/${id}/cancelar`); } catch (e) { mostrarErro(e); }
}

function tratarEvento(ev, dados) {
  if (ev === "provedor") {
    painel.atualizarProvedor(dados.provedor);
    if (dados.provedor.estado !== "logado") status(`${dados.provedor.nome}: sessão expirada — faça login de novo.`, { erro: true });
    return;
  }
  const id = dados.operacao_id;
  const op = ops.get(id);
  if (!op) {
    if (!pendentes.has(id)) pendentes.set(id, []);
    pendentes.get(id).push([ev, dados]);
    return;
  }
  if (ev === "arquivo") {
    if (dados.analise_id === estado.analiseId) lista.receber(dados.arquivo, dados.indice);
  } else if (ev === "progresso") {
    status(dados.mensagem);
    const barra = $("barra");
    if (dados.total) { barra.max = dados.total; barra.value = dados.feito; } else barra.removeAttribute("value");
  } else if (ev === "concluido" || ev === "erro" || ev === "cancelado") {
    ops.delete(id);
    atualizarOcupado();
    op.aoFim(ev, dados);
  }
}

function conectarEventos() {
  const fonte = new EventSource("/api/eventos");
  for (const ev of ["arquivo", "progresso", "concluido", "erro", "cancelado", "provedor"]) {
    fonte.addEventListener(ev, (m) => tratarEvento(ev, JSON.parse(m.data)));
  }
  fonte.onerror = () => {
    if (fonte.readyState === EventSource.CLOSED) {
      status("Conexão com o servidor local perdida — recarregue a página.", { erro: true });
    }
  };
}

// ── Componentes ─────────────────────────────────────────────────────────────
const detalhes = criarDetalhes({ aoAbrirRelatorio: (c) => abrir(c) });
const comparacao = criarComparacao({ aoErro: mostrarErro });

const lista = criarLista({
  aoFocar(arquivo) {
    detalhes.mostrar(arquivo);
    $("btn-comparar").disabled = !arquivo?.origem;
    painel.definirSelecao(lista.selecionados.length > 0 || !!arquivo);
  },
  aoAbrir: (c) => abrir(c),
});

const barraPasta = criarBarraPasta({ aoBuscar: buscar, aoCancelar: cancelarUltima, aoErro: mostrarErro });

const painel = criarPainelIA({ aoRevisar: revisar, aoErro: mostrarErro, aoMensagem: (m) => status(m) });

// seleção efetiva: marcados; senão o arquivo em foco
function alvo() {
  const sel = lista.selecionados;
  if (sel.length) return sel;
  return lista.foco ? [lista.foco] : [];
}

// ── Busca ───────────────────────────────────────────────────────────────────
async function buscar(pasta, subpastas) {
  if ([...ops.values()].some((o) => o.tipo === "busca")) return;
  try {
    const r = await api("POST", "/api/analises", { pasta, subpastas });
    estado.analiseId = r.analise_id;
    estado.pasta = pasta;
    lista.limpar("Analisando...");
    status("Buscando...");
    registrarOperacao(r.operacao_id, "busca", (ev, d) => {
      const res = d.resultado || {};
      if (ev === "erro") return mostrarErro({ message: `Falha ao ler a pasta: ${d.erro}`, acao: d.acao });
      const n = lista.arquivos.length;
      const e = lista.arquivos.reduce((s, a) => s + a.erros, 0);
      const w = lista.arquivos.reduce((s, a) => s + a.avisos, 0);
      const resumo = n ? `${n} arquivo(s) .md · ${e} erro(s) · ${w} aviso(s)` : "Nenhum arquivo .md encontrado nessa pasta.";
      status(ev === "cancelado" ? `Busca cancelada — ${resumo}` : resumo);
      if (!n) lista.limpar("Nenhum arquivo .md encontrado nessa pasta.");
      if (n && !lista.foco) lista.focar(lista.arquivos[0].caminho);
      if (res.falhas?.length) {
        avisar("Algumas pastas não puderam ser lidas",
          `<p>Os arquivos já analisados continuam na lista. Confira a conexão com a rede e clique em <b>Buscar .md</b> de novo.</p>
           <ul>${res.falhas.slice(0, 10).map((f) => `<li>${esc(f)}</li>`).join("")}</ul>`);
      }
    });
    api("GET", "/api/config").then((c) => barraPasta.definirRecentes(c.pastas_recentes)).catch(() => {});
  } catch (e) {
    mostrarErro(e);
  }
}

// ── Correção ────────────────────────────────────────────────────────────────
async function corrigir() {
  if (!estado.analiseId) return status("Faça uma busca primeiro.");
  let caminhos = lista.selecionados.map((a) => a.caminho);
  if (!caminhos.length) {
    const comProblema = lista.arquivos.filter((a) => a.situacao !== "OK");
    if (!comProblema.length) return avisar("Criar versão corrigida", "<p>Nenhum arquivo com problemas para corrigir.</p>");
    const ok = await dialogo("Criar versão corrigida",
      `<p>Nenhum arquivo selecionado.</p><p>Criar a versão corrigida dos <b>${comProblema.length}</b> arquivo(s) com problemas?</p>
       <p class="dica">Os originais não são alterados: cada um ganha uma nova versão (_v2, _v3...).</p>`);
    if (!ok) return;
    caminhos = "todos_com_problema";
  }
  try {
    const r = await api("POST", "/api/correcoes", { analise_id: estado.analiseId, caminhos });
    registrarOperacao(r.operacao_id, "correcao", (ev, d) => {
      if (ev === "erro") return mostrarErro({ message: d.erro, acao: d.acao });
      const res = d.resultado || { criados: [], sem_mudanca: [] };
      if (res.criados.length) {
        const ultimo = res.criados[res.criados.length - 1];
        lista.focar(ultimo.caminho);
        let msg = `<p>${res.criados.length} versão(ões) corrigida(s) criada(s):</p><ul>${
          res.criados.slice(0, 10).map((c) => `<li>${esc(nomeArquivo(c.caminho))}</li>`).join("")}${res.criados.length > 10 ? "<li>...</li>" : ""}</ul>`;
        if (res.restantes) msg += `<p>Ainda há <b>${res.restantes}</b> problema(s) sem correção automática (ex.: imagem que não existe) — veja os detalhes de cada versão.</p>`;
        status(`${res.criados.length} versão(ões) corrigida(s) criada(s).`);
        avisar("Versões corrigidas", msg);
      } else if (res.sem_mudanca.length) {
        avisar("Criar versão corrigida", "<p>Nada a corrigir automaticamente nos arquivos selecionados — os problemas restantes precisam de ajuste manual.</p>");
        status("Nada a corrigir automaticamente.");
      } else {
        status("Nenhum arquivo precisava de correção.");
      }
    });
  } catch (e) {
    mostrarErro(e);
  }
}

// ── Revisão com IA ───────────────────────────────────────────────────────────
async function revisar({ provedor, skill, modelo }) {
  const arquivos = alvo();
  if (!arquivos.length) return status("Selecione um ou mais arquivos na lista.");
  const caminhos = arquivos.map((a) => a.caminho);
  try {
    const p = await api("POST", "/api/revisoes/previa", { analise_id: estado.analiseId, caminhos, provedor, skill, modelo });
    const cobrado = p.cobranca === "por_uso";
    const totalTrechos = p.arquivos.reduce((s, a) => s + a.trechos, 0);
    const ok = await dialogo("Revisar texto com IA", `
      <p>Enviar <b>${p.arquivos.length}</b> arquivo(s) (${totalTrechos} trecho(s)) para <b>${esc(p.nome)}</b>
         com a skill <b>${esc(p.skill)}</b> (modelo ${esc(p.modelo)})?</p>
      <ul>${p.arquivos.slice(0, 12).map((a) => `<li>${esc(a.rotulo)} — ${a.trechos} trecho(s)</li>`).join("")}${p.arquivos.length > 12 ? "<li>...</li>" : ""}</ul>
      <p class="destaque${cobrado ? " cobrado" : ""}">${esc(p.aviso)}</p>
      <p class="dica">Blocos de código, imagens e âncoras não são enviados para alteração. Cada arquivo gera uma
         nova versão e um relatório _revisao.md; o original não é alterado.</p>`,
      { confirmar: cobrado ? "Enviar (cobrado por uso)" : "Enviar para revisão" });
    if (!ok) return;
    const r = await api("POST", "/api/revisoes", { analise_id: estado.analiseId, caminhos, provedor, skill, modelo, confirmado: true });
    status("Revisando com IA...");
    registrarOperacao(r.operacao_id, "revisao", (ev, d) => fimRevisao(ev, d));
  } catch (e) {
    if (e.dados?.provedor) painel.atualizarProvedor(e.dados.provedor);
    mostrarErro(e);
  }
}

function fimRevisao(ev, d) {
  if (ev === "erro") return mostrarErro({ message: d.erro, acao: d.acao });
  const res = d.resultado || { feitos: [], erros: [], uso: {} };
  const cobrado = res.cobranca === "por_uso";
  const custo = cobrado ? `Cobrado por uso (API): ${usd(res.uso?.custo_usd)}`
    : `Equivalente em API: ${usd(res.uso?.custo_usd)} — não cobrado no Pro/Max (consome só o limite da assinatura)`;
  if (ev === "cancelado") {
    status("Revisão cancelada — nenhuma versão parcial foi gravada para o arquivo em andamento.");
    if (!res.feitos?.length) return;
  }
  if (res.feitos?.length) {
    const ultimo = res.feitos[res.feitos.length - 1];
    lista.focar(ultimo.destino || ultimo.origem);
    status(`Revisão concluída: ${res.feitos.length} arquivo(s) · ${custo}`);
  }
  const itens = (res.feitos || []).map((r) => {
    const total = Object.values(r.contagem || {}).reduce((s, n) => s + n, 0);
    const resumo = r.destino ? `${esc(nomeArquivo(r.destino))} — ${total} alteração(ões)`
      : `${esc(nomeArquivo(r.origem))} — sem alterações no texto (nenhuma versão gravada)`;
    return `<li>${resumo}, ${r.pendencias.length} pendência(s)${r.falhas.length ? `, ${r.falhas.length} trecho(s) não revisado(s)` : ""}</li>`;
  }).join("");
  const erros = (res.erros || []).map((e) => `<li>${esc(nomeArquivo(e.caminho))}: ${esc(e.erro)}</li>`).join("");
  avisar(ev === "cancelado" ? "Revisão cancelada" : "Revisão concluída", `
    ${itens ? `<p>Arquivo(s) revisado(s):</p><ul>${itens}</ul>` : ""}
    ${erros ? `<p>Falhas:</p><ul>${erros}</ul>` : ""}
    <p class="destaque${cobrado ? " cobrado" : ""}">${esc(custo)}</p>`);
}

// ── Ações simples ────────────────────────────────────────────────────────────
async function abrir(caminho) {
  if (!caminho) return;
  try { await api("POST", "/api/abrir", { analise_id: estado.analiseId, caminho }); } catch (e) { mostrarErro(e); }
}

function exigirFoco() {
  const f = lista.foco;
  if (!f) status("Selecione um arquivo na lista.");
  return f;
}

$("btn-corrigir").addEventListener("click", corrigir);
$("btn-abrir").addEventListener("click", () => { const f = exigirFoco(); if (f) abrir(f.caminho); });
$("btn-word").addEventListener("click", async () => {
  const f = exigirFoco();
  if (!f) return;
  try {
    await api("POST", "/api/word", { analise_id: estado.analiseId, caminho: f.caminho });
    status(`Abrindo o gerador de Word com ${nomeArquivo(f.caminho)}...`);
  } catch (e) { mostrarErro(e); }
});
$("btn-comparar").addEventListener("click", () => {
  const f = lista.foco;
  if (f?.origem) comparacao.abrir(estado.analiseId, f.origem, f.caminho);
});
$("btn-relatorio").addEventListener("click", async () => {
  if (!estado.analiseId) return status("Faça uma busca primeiro.");
  try {
    const { caminho } = await api("POST", "/api/relatorios", { analise_id: estado.analiseId });
    estado.ultimoRelatorio = caminho;
    if (await dialogo("Relatório salvo", `<p>${esc(caminho)}</p>`, { confirmar: "Abrir agora", cancelar: "Fechar" })) abrir(caminho);
  } catch (e) { mostrarErro(e); }
});
$("btn-cancelar").addEventListener("click", cancelarUltima);

// ── Início ──────────────────────────────────────────────────────────────────
conectarEventos();
api("GET", "/api/config").then((c) => barraPasta.definir(c.ultima_pasta, c.pastas_recentes)).catch(mostrarErro);
painel.carregar();
