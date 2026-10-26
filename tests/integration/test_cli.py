"""FR-028: a linha de comando continua produzindo o mesmo resultado."""

import os
import subprocess
import sys

from tests.conftest import RAIZ
from tests.golden.gerar_snapshots import SNAPSHOTS, normalizar_relatorio


def _rodar(*args):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, *args], cwd=RAIZ, capture_output=True, text=True,
                          encoding="utf-8", env=env, timeout=120)


def test_relatorio_cli_igual_ao_snapshot(amostra, tmp_path):
    saida = str(tmp_path / "rel.md")
    r = _rodar("analisar_md.py", amostra, "--relatorio", "--saida", saida)
    assert r.returncode == 0, r.stderr
    with open(saida, encoding="utf-8") as f:
        obtido = normalizar_relatorio(f.read(), amostra)
    with open(os.path.join(SNAPSHOTS, "relatorio.md"), encoding="utf-8") as f:
        esperado = f.read()
    # o Mermaid depende de haver Node.js na máquina; o resto precisa ser idêntico
    filtrar = lambda t: [l for l in t.splitlines() if "mermaid" not in l.lower() and "Mermaid" not in l]
    assert filtrar(obtido)[4:] == filtrar(esperado)[4:]


def test_cli_v2(amostra, tmp_path):
    r = _rodar("analisar_md.py", amostra, "--relatorio", "--v2", "--saida", str(tmp_path / "r.md"))
    assert r.returncode == 0, r.stderr
    assert os.path.exists(os.path.join(amostra, "links_v2.md"))
    assert "→ links_v2.md" in r.stdout


def test_revisar_md_help_mostra_provedor():
    r = _rodar("revisar_md.py", "--help")
    assert r.returncode == 0 and "--provedor" in r.stdout and "claude-assinatura" in r.stdout


def test_revisar_varios_arquivos(amostra, simulado, capsys):
    """T059: revisar_md.py aceita vários arquivos (provedor simulado no lugar do Claude)."""
    import revisar_md
    a = os.path.join(amostra, "ok.md")
    b = os.path.join(amostra, "links.md")
    with open(a, "a", encoding="utf-8") as f:
        f.write("\nO resultado foi muito bom.\n")
    revisar_md.main([a, b, "--provedor", "claude-assinatura", "--skill", "technical-documentation"])
    saida = capsys.readouterr().out
    assert "[1/2]" in saida and "[2/2]" in saida and "Total: 2 arquivo(s)" in saida
    assert os.path.exists(os.path.join(amostra, "ok_v2.md"))  # mudou → versão
    assert "sem alterações (nenhuma versão gravada)" in saida  # links.md não mudou
    assert simulado.chamadas == 2


def test_comparar_cli(amostra):
    """T060: python -m gera_md comparar."""
    a = os.path.join(amostra, "riscado.md")
    b = os.path.join(amostra, "riscado_copia.md")
    with open(a, encoding="utf-8") as f:
        texto = f.read()
    with open(b, "w", encoding="utf-8") as f:
        f.write(texto.replace("~~antigo~~ ", ""))
    r = _rodar("-m", "gera_md", "comparar", a, b)
    assert r.returncode == 1, r.stderr
    assert "@@ alterado" in r.stdout and "-    3 | Texto ~~antigo~~ novo." in r.stdout
    assert "+    3 | Texto novo." in r.stdout
    assert _rodar("-m", "gera_md", "comparar", a, a).returncode == 0


def test_chave_api_cli(monkeypatch, capsys):
    """T061: --definir-chave-api lê pelo getpass e grava no cofre; nunca ecoa a chave."""
    import types
    import revisar_md
    guardado = {}
    kr = types.SimpleNamespace(get_password=lambda s, u: guardado.get((s, u)),
                               set_password=lambda s, u, v: guardado.__setitem__((s, u), v),
                               delete_password=lambda s, u: guardado.pop((s, u), None))
    monkeypatch.setitem(sys.modules, "keyring", kr)
    chave = "sk-ant-api03-" + "q" * 40
    monkeypatch.setattr(revisar_md.getpass, "getpass", lambda prompt="": chave)
    revisar_md.main(["--definir-chave-api"])
    assert list(guardado.values()) == [chave]
    assert chave not in capsys.readouterr().out
    revisar_md.main(["--remover-chave-api"])
    assert guardado == {}
