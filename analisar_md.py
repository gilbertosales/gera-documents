#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analisar_md.py
==============
Busca arquivos .md numa pasta (local ou de rede), aponta o que vai sair errado
ao converter para Word com gerar_word.py e cria uma versão corrigida de cada
arquivo (nome_v2.md) — o original nunca é alterado.

Uso:
    python -m gera_md.web                         → frontend web local (recomendado;
                                                    ou "Gera Documents.cmd")
    python analisar_md.py                         → abre a tela
    python analisar_md.py "\\\\servidor\\docs"        → abre a tela já com a pasta
    python analisar_md.py pasta --relatorio       → sem tela: só gera o relatório
    python analisar_md.py pasta --relatorio --v2  → sem tela: relatório + cria as v2

Na tela:
    1. Escolha a pasta e clique em "Buscar" — a lista mostra cada .md com o
       número de erros/avisos; clique num arquivo para ver os problemas.
    2. "Criar v2 corrigido" grava nome_v2.md ao lado do original com as
       correções automáticas e mostra o que foi corrigido e o que ainda
       precisa de ajuste manual (ex.: imagem que não existe).
    3. "Revisar texto (IA)" passa a skill escolhida (pasta .claude/skills,
       padrão technical-documentation) ao Claude Code logado com a assinatura
       Pro/Max (sem chave de API; confira com `claude auth status --text`) para corrigir vícios de
       linguagem, redundâncias e ambiguidades em tom técnico/de consultoria.
       Grava nova versão + relatório _revisao.md (ver revisar_md.py).
    4. "Gerar Word" abre o gerar_word.py já com o arquivo selecionado.

A lógica de análise e correção fica em gera_md/ (núcleo sem interface),
compartilhada com o frontend web.

Níveis:
    ERRO   → conteúdo some ou aparece quebrado no Word
    AVISO  → aparece como texto literal (ex.: [link](url), ~~riscado~~)
    INFO   → funciona, mas vale saber
"""


import argparse
import os
import queue
import subprocess
import sys
import threading

from gerar_word import carregar_config, salvar_config
import revisar_md

# Núcleo sem interface (gera_md/): a tela e a CLI abaixo só o consomem.
from gera_md.analise import PASTAS_IGNORADAS, analisar_arquivo, contar, encontrar_mds  # noqa: F401
from gera_md.correcao import corrigir_md
from gera_md.relatorio import escrever_relatorio
from gera_md.versoes import proxima_versao as proximo_v2  # noqa: F401 — nome antigo

if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GERAR_WORD = os.path.join(SCRIPT_DIR, "gerar_word.py")
RELATORIO_PADRAO = os.path.join(SCRIPT_DIR, "relatorio_analise_md.md")


# ── Utilitários ───────────────────────────────────────────────────────────────


def _abrir(path):
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])


# ── Tela ──────────────────────────────────────────────────────────────────────


def abrir_tela(pasta_inicial=""):
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    cfg = carregar_config()
    root = tk.Tk()
    root.title("Analisar Markdown (.md) para Word")
    root.geometry("1050x680")
    root.minsize(780, 500)

    resultados = {}  # caminho → achados
    correcoes = {}  # caminho da v2 → correções aplicadas
    var_pasta = tk.StringVar(value=pasta_inicial or cfg.get("ultima_pasta", ""))
    var_rec = tk.BooleanVar(value=True)
    status = tk.StringVar(value="Escolha a pasta (local ou de rede) e clique em Buscar.")

    # ── Barra da pasta ────────────────────────────────────────────────────
    topo = ttk.Frame(root, padding=(12, 12, 12, 6))
    topo.pack(fill="x")
    ttk.Label(topo, text="Pasta:").pack(side="left")
    ttk.Entry(topo, textvariable=var_pasta).pack(side="left", fill="x", expand=True, padx=6)

    def escolher_pasta():
        p = filedialog.askdirectory(title="Pasta com os arquivos .md (local ou de rede)",
                                    initialdir=var_pasta.get() or SCRIPT_DIR)
        if p:
            var_pasta.set(os.path.normpath(p))

    ttk.Button(topo, text="Procurar...", command=escolher_pasta).pack(side="left")
    ttk.Checkbutton(topo, text="Subpastas", variable=var_rec).pack(side="left", padx=8)
    btn_buscar = ttk.Button(topo, text="Buscar .md")
    btn_buscar.pack(side="left")

    # ── Lista de arquivos (cima) + detalhes (baixo) ──────────────────────
    painel = ttk.PanedWindow(root, orient="vertical")
    painel.pack(fill="both", expand=True, padx=12)

    f_lista = ttk.Frame(painel)
    cols = ("erros", "avisos", "situacao")
    lista = ttk.Treeview(f_lista, columns=cols, selectmode="extended")
    lista.heading("#0", text="Arquivo .md", anchor="w")
    lista.heading("erros", text="Erros")
    lista.heading("avisos", text="Avisos")
    lista.heading("situacao", text="Situação")
    lista.column("#0", width=620, anchor="w")
    for c, w in (("erros", 70), ("avisos", 70), ("situacao", 110)):
        lista.column(c, width=w, anchor="center", stretch=False)
    lista.tag_configure("Corrigir", foreground="#b42318")
    lista.tag_configure("Revisar", foreground="#9a6700")
    lista.tag_configure("OK", foreground="#1a7f37")
    sb1 = ttk.Scrollbar(f_lista, orient="vertical", command=lista.yview)
    lista.configure(yscrollcommand=sb1.set)
    lista.pack(side="left", fill="both", expand=True)
    sb1.pack(side="right", fill="y")
    painel.add(f_lista, weight=3)

    f_det = ttk.Frame(painel)
    det = tk.Text(f_det, wrap="word", height=10, relief="flat", padx=8, pady=6,
                  font=("Segoe UI", 10), background="#fafafa")
    det.tag_configure("titulo", font=("Segoe UI", 10, "bold"))
    det.tag_configure("ERRO", foreground="#b42318")
    det.tag_configure("AVISO", foreground="#9a6700")
    det.tag_configure("INFO", foreground="#555555")
    det.tag_configure("FIX", foreground="#1a7f37")
    sb2 = ttk.Scrollbar(f_det, orient="vertical", command=det.yview)
    det.configure(yscrollcommand=sb2.set, state="disabled")
    det.pack(side="left", fill="both", expand=True)
    sb2.pack(side="right", fill="y")
    painel.add(f_det, weight=2)

    # ── Botões ────────────────────────────────────────────────────────────
    base = ttk.Frame(root, padding=12)
    base.pack(fill="x")
    btn_v2 = ttk.Button(base, text="Criar v2 corrigido")
    btn_v2.pack(side="left")
    btn_abrir = ttk.Button(base, text="Abrir .md")
    btn_abrir.pack(side="left", padx=6)
    btn_word = ttk.Button(base, text="Gerar Word...")
    btn_word.pack(side="left")
    btn_rel = ttk.Button(base, text="Salvar relatório")
    btn_rel.pack(side="left", padx=6)
    ttk.Label(base, textvariable=status, foreground="#555").pack(side="left", padx=10)

    # ── Revisão de texto com IA (skill do .claude/skills) ─────────────────
    ia = ttk.LabelFrame(root, text="Revisão de texto com IA (Claude + skill)", padding=(12, 6))
    ia.pack(fill="x", padx=12, pady=(0, 12))
    skills = revisar_md.listar_skills()
    var_skill = tk.StringVar(value=revisar_md.SKILL_PADRAO if revisar_md.SKILL_PADRAO in skills
                             else (skills[0] if skills else ""))
    var_modelo = tk.StringVar(value="padrão")
    ttk.Label(ia, text="Skill:").pack(side="left")
    ttk.Combobox(ia, textvariable=var_skill, values=skills, state="readonly",
                 width=28).pack(side="left", padx=(4, 12))
    ttk.Label(ia, text="Modelo:").pack(side="left")
    ttk.Combobox(ia, textvariable=var_modelo, values=revisar_md.MODELOS, state="readonly",
                 width=10).pack(side="left", padx=(4, 12))
    btn_ia = ttk.Button(ia, text="Revisar texto (IA)")
    btn_ia.pack(side="left")
    ttk.Label(ia, text="Vícios de linguagem, redundâncias, ambiguidades e tom técnico/consultoria "
                       "→ cria nova versão + relatório", foreground="#555").pack(side="left", padx=10)
    revisoes = {}  # caminho da versão revisada → resumo de revisar_md.revisar_md

    def rotulo(path):
        try:
            return os.path.relpath(path, var_pasta.get())
        except ValueError:
            return path

    def mostrar_linha(path, depois_de=None):
        e, w, sit = contar(resultados[path])
        valores = (e, w, sit)
        if lista.exists(path):
            lista.item(path, values=valores, tags=(sit,))
        else:
            idx = lista.index(depois_de) + 1 if depois_de and lista.exists(depois_de) else "end"
            lista.insert("", idx, iid=path, text=rotulo(path), values=valores, tags=(sit,))

    def mostrar_detalhes(_evt=None):
        sel = lista.selection()
        det.configure(state="normal")
        det.delete("1.0", "end")
        if sel:
            path = sel[0]
            det.insert("end", rotulo(path) + "\n", "titulo")
            if path in revisoes:
                r = revisoes[path]
                total = sum(r["contagem"].values())
                det.insert("end", f"\nRevisão de texto com IA — {total} alteração(ões), "
                                  f"equivalente em API US$ {r['custo']:.2f} "
                                  f"(não cobrado no Pro/Max):\n", "titulo")
                for c, n in sorted(r["contagem"].items(), key=lambda x: -x[1]):
                    det.insert("end", f"  ✔ {c}: {n}\n", "FIX")
                for cab, erro in r["falhas"]:
                    det.insert("end", f"  ✖ Trecho não revisado ({cab}): {erro}\n", "ERRO")
                if r["pendencias"]:
                    det.insert("end", f"\nPendências para o autor ({len(r['pendencias'])}):\n",
                               "titulo")
                    for cab, txt in r["pendencias"]:
                        det.insert("end", f"  ? [{cab}] {txt}\n", "AVISO")
                det.insert("end", f"\nDetalhes de cada alteração: {r['relatorio']}\n", "INFO")
            if path in correcoes:
                det.insert("end", f"\nCorreções aplicadas ao criar este arquivo "
                                  f"({len(correcoes[path])}):\n", "titulo")
                for n, msg in correcoes[path]:
                    ref = f"linha {n} do original" if n else "geral"
                    det.insert("end", f"  ✔ [{ref}] {msg}\n", "FIX")
            achados = resultados.get(path, [])
            if achados:
                det.insert("end", f"\nProblemas ({len(achados)}):\n", "titulo")
                for nivel, n, msg in achados:
                    det.insert("end", f"  {nivel:<5}  linha {n or '-':>4}   {msg}\n", nivel)
                if path not in correcoes and any(a[0] != "INFO" for a in achados):
                    det.insert("end", "\nClique em \"Criar v2 corrigido\" para gerar uma "
                                      "versão corrigida deste arquivo.\n", "INFO")
                elif path in correcoes:
                    det.insert("end", "\nOs problemas acima não têm correção automática — "
                                      "ajuste manualmente no arquivo.\n", "INFO")
            else:
                det.insert("end", "\nNenhum problema encontrado — pronto para o Word. ✔\n", "FIX")
        det.configure(state="disabled")

    lista.bind("<<TreeviewSelect>>", mostrar_detalhes)
    lista.bind("<Double-1>", lambda e: abrir_md())

    def buscar():
        pasta = os.path.normpath(var_pasta.get().strip()) if var_pasta.get().strip() else ""
        var_pasta.set(pasta)
        if not pasta or not os.path.isdir(pasta):
            messagebox.showwarning("Atenção", f"Pasta não encontrada ou sem acesso:\n{pasta}")
            return
        cfg["ultima_pasta"] = pasta
        salvar_config(cfg)
        lista.delete(*lista.get_children())
        resultados.clear()
        correcoes.clear()
        mostrar_detalhes()
        btn_buscar.state(["disabled"])
        status.set("Buscando...")
        recursivo = var_rec.get()
        fila = queue.Queue()

        # A thread só lê arquivos (pasta de rede pode ser lenta); a tela é
        # atualizada pela thread principal, lendo a fila — tkinter não é thread-safe.
        def trabalho():
            try:
                for md in encontrar_mds(pasta, recursivo):
                    fila.put(("arquivo", md, analisar_arquivo(md)))
            except OSError as exc:
                fila.put(("erro", str(exc), None))
            fila.put(("fim", None, None))

        def ler_fila():
            try:
                while True:
                    tipo, a, b = fila.get_nowait()
                    if tipo == "arquivo":
                        resultados[a] = b
                        mostrar_linha(a)
                        status.set(f"Analisando... {len(resultados)} arquivo(s)")
                    elif tipo == "erro":
                        messagebox.showerror("Erro", f"Falha ao ler a pasta:\n{a}")
                    else:
                        fim_busca(len(resultados))
                        return
            except queue.Empty:
                pass
            root.after(100, ler_fila)

        threading.Thread(target=trabalho, daemon=True).start()
        root.after(100, ler_fila)

    def fim_busca(n):
        btn_buscar.state(["!disabled"])
        e = sum(contar(a)[0] for a in resultados.values())
        w = sum(contar(a)[1] for a in resultados.values())
        status.set(f"{n} arquivo(s) .md · {e} erro(s) · {w} aviso(s)"
                   if n else "Nenhum arquivo .md encontrado nessa pasta.")
        filhos = lista.get_children()
        if filhos:
            lista.selection_set(filhos[0])

    def criar_v2():
        sel = list(lista.selection())
        if not sel:
            com_problema = [p for p, a in resultados.items() if contar(a)[2] != "OK"]
            if not com_problema:
                messagebox.showinfo("Criar v2", "Nenhum arquivo com problemas para corrigir.")
                return
            if not messagebox.askyesno(
                "Criar v2", f"Nenhum arquivo selecionado.\n\nCriar a versão v2 corrigida dos "
                            f"{len(com_problema)} arquivo(s) com problemas?"):
                return
            sel = com_problema
        criados, sem_mudanca, restantes = [], [], 0
        for path in sel:
            if contar(resultados.get(path, []))[2] == "OK" and len(sel) > 1:
                continue
            try:
                v2, fixes = corrigir_md(path)
            except OSError as exc:
                messagebox.showerror("Erro", f"Não foi possível criar a v2 de\n{path}\n\n{exc}")
                continue
            if not fixes:
                os.remove(v2)
                sem_mudanca.append(path)
                continue
            correcoes[v2] = fixes
            resultados[v2] = analisar_arquivo(v2)
            restantes += sum(contar(resultados[v2])[:2])
            mostrar_linha(v2, depois_de=path)
            criados.append(v2)
        if criados:
            lista.selection_set(criados[-1])
            lista.see(criados[-1])
            msg = (f"{len(criados)} arquivo(s) v2 criado(s):\n"
                   + "\n".join("  " + os.path.basename(c) for c in criados[:10])
                   + ("\n  ..." if len(criados) > 10 else ""))
            if restantes:
                msg += (f"\n\nAinda há {restantes} problema(s) sem correção automática "
                        "(ex.: imagem que não existe) — veja os detalhes de cada v2.")
            messagebox.showinfo("Criar v2", msg)
        elif sem_mudanca:
            messagebox.showinfo("Criar v2", "Nada a corrigir automaticamente nos arquivos "
                                            "selecionados — os problemas restantes precisam "
                                            "de ajuste manual.")

    def revisar_ia():
        sel = list(lista.selection())
        if not sel:
            messagebox.showinfo("Revisar texto", "Selecione um ou mais arquivos na lista.")
            return
        if not revisar_md.claude_disponivel():
            messagebox.showerror("Revisar texto", "Comando 'claude' não encontrado.\n\n"
                                 "Instale o Claude Code e faça login (claude → /login).")
            return
        if not var_skill.get():
            messagebox.showerror("Revisar texto", f"Nenhuma skill encontrada em\n"
                                                  f"{revisar_md.SKILLS_DIR}")
            return
        nomes = "\n".join("  " + os.path.basename(p) for p in sel[:8])
        if not messagebox.askyesno(
            "Revisar texto com IA",
            f"Revisar {len(sel)} arquivo(s) com a skill \"{var_skill.get()}\"?\n{nomes}\n\n"
            "Cada arquivo gera uma nova versão (_v2, _v3...) e um relatório _revisao.md.\n"
            "Usa o Claude Code logado nesta máquina: no plano Pro/Max consome o limite "
            "de uso da assinatura, sem cobrança extra."):
            return

        skill, modelo = var_skill.get(), var_modelo.get()
        fila = queue.Queue()
        for b in (btn_ia, btn_v2, btn_buscar):
            b.state(["disabled"])

        def trabalho():
            for k, path in enumerate(sel, 1):
                prefixo = f"[{k}/{len(sel)}] {os.path.basename(path)}: "
                try:
                    r = revisar_md.revisar_md(
                        path, skill, modelo,
                        progresso=lambda msg, p=prefixo: fila.put(("status", p + msg, None)))
                    achados = analisar_arquivo(r["destino"]) if r["destino"] else None
                    fila.put(("ok", path, (r, achados)))
                except Exception as exc:  # noqa: BLE001 — erro exibido ao usuário
                    fila.put(("erro", path, exc))
            fila.put(("fim", None, None))

        feitos, erros = [], []

        def ler_fila():
            try:
                while True:
                    tipo, a, b = fila.get_nowait()
                    if tipo == "status":
                        status.set(a)
                    elif tipo == "ok":
                        r, achados = b
                        if r["destino"]:
                            revisoes[r["destino"]] = r
                            resultados[r["destino"]] = achados
                            mostrar_linha(r["destino"], depois_de=a)
                        else:  # sem alterações: só o relatório, ligado ao original
                            revisoes[a] = r
                        feitos.append(r)
                    elif tipo == "erro":
                        erros.append(f"{os.path.basename(a)}: {b}")
                    else:
                        fim_revisao(feitos, erros)
                        return
            except queue.Empty:
                pass
            root.after(200, ler_fila)

        threading.Thread(target=trabalho, daemon=True).start()
        root.after(200, ler_fila)

    def fim_revisao(feitos, erros):
        for b in (btn_ia, btn_v2, btn_buscar):
            b.state(["!disabled"])
        custo = sum(r["custo"] for r in feitos)
        status.set(f"Revisão concluída: {len(feitos)} arquivo(s) · "
                   f"equivalente em API US$ {custo:.2f} (não cobrado no Pro/Max)")
        if feitos:
            alvo = feitos[-1]["destino"] or feitos[-1]["origem"]
            lista.selection_set(alvo)
            lista.see(alvo)
        msg = ""
        if feitos:
            msg += f"{len(feitos)} arquivo(s) revisado(s):\n" + "\n".join(
                f"  {os.path.basename(r['destino'] or r['origem'])} — "
                + (f"{sum(r['contagem'].values())} alteração(ões)" if r["destino"]
                   else "sem alterações (nenhuma versão gravada)")
                + f", {len(r['pendencias'])} pendência(s)" for r in feitos)
            msg += (f"\n\nEquivalente em API: US$ {custo:.2f}\n"
                    "No plano Pro/Max esse valor não é cobrado; a revisão só consome "
                    "o limite de uso da assinatura.")
        if erros:
            msg += "\n\nFalhas:\n" + "\n".join("  " + e for e in erros)
        if feitos and len(feitos) == 1 and not erros:
            if messagebox.askyesno("Revisão concluída",
                                   msg + "\n\nAbrir o relatório de revisão?"):
                _abrir(feitos[0]["relatorio"])
        elif msg:
            (messagebox.showwarning if erros else messagebox.showinfo)("Revisão concluída", msg)

    def selecionado():
        sel = lista.selection()
        if not sel:
            messagebox.showinfo("Atenção", "Selecione um arquivo na lista.")
            return None
        return sel[0]

    def abrir_md():
        path = selecionado()
        if path:
            _abrir(path)

    def gerar_word():
        path = selecionado()
        if path:
            subprocess.Popen([sys.executable, GERAR_WORD, path], cwd=SCRIPT_DIR)

    def salvar_relatorio():
        if not resultados:
            messagebox.showinfo("Relatório", "Faça uma busca primeiro.")
            return
        saida = filedialog.asksaveasfilename(
            title="Salvar relatório", initialdir=SCRIPT_DIR,
            initialfile=os.path.basename(RELATORIO_PADRAO), defaultextension=".md",
            filetypes=[("Markdown", "*.md")])
        if not saida:
            return
        ordem = [p for p in lista.get_children()]
        escrever_relatorio(var_pasta.get(), [(p, resultados[p]) for p in ordem], saida)
        if messagebox.askyesno("Relatório", f"Relatório salvo:\n{saida}\n\nAbrir agora?"):
            _abrir(saida)

    btn_buscar.configure(command=buscar)
    btn_v2.configure(command=criar_v2)
    btn_abrir.configure(command=abrir_md)
    btn_word.configure(command=gerar_word)
    btn_rel.configure(command=salvar_relatorio)
    btn_ia.configure(command=revisar_ia)

    if pasta_inicial and os.path.isdir(pasta_inicial):
        root.after(100, buscar)
    root.mainloop()


# ── Execução ──────────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser(description="Analisa .md para conversão com gerar_word.py")
    ap.add_argument("pasta", nargs="?", default="", help="pasta local ou de rede")
    ap.add_argument("--relatorio", action="store_true", help="sem tela: só gera o relatório")
    ap.add_argument("--v2", action="store_true", help="com --relatorio: cria também as v2")
    ap.add_argument("--saida", default=RELATORIO_PADRAO, help="arquivo .md do relatório")
    args = ap.parse_args()

    if not args.relatorio:
        abrir_tela(args.pasta)
        return

    if not os.path.isdir(args.pasta):
        print(f"ERRO: pasta não encontrada ou sem acesso: {args.pasta}")
        sys.exit(1)
    pasta = os.path.abspath(args.pasta)
    resultados = []
    for md in encontrar_mds(pasta):
        achados = analisar_arquivo(md)
        resultados.append((md, achados))
        print(f"  {contar(achados)[2]:<8} {os.path.relpath(md, pasta)}")
        if args.v2 and contar(achados)[2] != "OK":
            v2, fixes = corrigir_md(md)
            if fixes:
                resultados.append((v2, analisar_arquivo(v2)))
                print(f"           → {os.path.basename(v2)} ({len(fixes)} correção(ões))")
            else:
                os.remove(v2)
    escrever_relatorio(pasta, resultados, args.saida)
    print(f"\nRelatório: {args.saida}")


if __name__ == "__main__":
    main()
