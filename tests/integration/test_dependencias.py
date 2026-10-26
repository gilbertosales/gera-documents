"""Constituição (Restrições Técnicas): o caminho sem IA funciona só com Python + python-docx.

Roda a CLI em subprocesso com starlette, uvicorn e keyring bloqueados.
"""

import os
import subprocess
import sys

from tests.conftest import RAIZ

BLOQUEAR = (
    "import sys\n"
    "for m in ('starlette', 'uvicorn', 'keyring', 'httpx', 'httpx2'):\n"
    "    sys.modules[m] = None  # import m → ImportError\n"
    "sys.argv = ['analisar_md.py'] + sys.argv[1:]\n"
    "import runpy\n"
    "runpy.run_path('analisar_md.py', run_name='__main__')\n"
    "assert 'starlette' not in [k for k, v in sys.modules.items() if v is not None]\n"
)


def test_cli_sem_dependencias_web(amostra, tmp_path):
    saida = str(tmp_path / "rel.md")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, "-c", BLOQUEAR, amostra, "--relatorio", "--v2", "--saida", saida],
                       cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
    assert r.returncode == 0, r.stderr
    assert os.path.exists(saida)
    assert os.path.exists(os.path.join(amostra, "links_v2.md"))
