// Barra da pasta: caminho, pastas recentes, "Procurar...", subpastas e Buscar/Cancelar.
import { api, esc } from "./util.js";

export function criarBarraPasta({ aoBuscar, aoCancelar, aoErro }) {
  const form = document.getElementById("form-pasta");
  const campo = document.getElementById("campo-pasta");
  const lista = document.getElementById("pastas-recentes");
  const chk = document.getElementById("chk-subpastas");
  const btnBuscar = document.getElementById("btn-buscar");
  const btnProcurar = document.getElementById("btn-procurar");
  let buscando = false;

  function definirRecentes(pastas) {
    lista.innerHTML = (pastas || []).map((p) => `<option value="${esc(p)}"></option>`).join("");
  }

  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    if (buscando) aoCancelar();
    else aoBuscar(campo.value.trim(), chk.checked);
  });

  btnProcurar.addEventListener("click", async () => {
    btnProcurar.disabled = true;
    try {
      const { pasta } = await api("POST", "/api/pastas/escolher", { inicial: campo.value.trim() });
      if (pasta) {
        campo.value = pasta;
        aoBuscar(pasta, chk.checked);
      }
    } catch (e) {
      aoErro(e);
    } finally {
      btnProcurar.disabled = false;
    }
  });

  return {
    definir(pasta, recentes) {
      if (pasta && !campo.value) campo.value = pasta;
      definirRecentes(recentes);
    },
    definirRecentes,
    buscando(sim) {
      buscando = sim;
      btnBuscar.textContent = sim ? "Cancelar busca" : "Buscar .md";
      btnBuscar.classList.toggle("primario", !sim);
      btnProcurar.disabled = sim;
    },
    get pasta() { return campo.value.trim(); },
  };
}
