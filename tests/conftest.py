import hashlib
import os
import shutil
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

AMOSTRA = os.path.join(RAIZ, "tests", "fixtures", "amostra")


@pytest.fixture
def amostra(tmp_path):
    """Cópia descartável de tests/fixtures/amostra."""
    destino = tmp_path / "amostra"
    shutil.copytree(AMOSTRA, destino)
    return str(destino)


def hash_arquivos(pasta):
    """{caminho relativo: sha256} de todos os arquivos da pasta."""
    out = {}
    for raiz, _dirs, arquivos in os.walk(pasta):
        for nome in arquivos:
            p = os.path.join(raiz, nome)
            with open(p, "rb") as f:
                out[os.path.relpath(p, pasta)] = hashlib.sha256(f.read()).hexdigest()
    return out


@pytest.fixture(name="hash_arquivos")
def _hash_arquivos():
    return hash_arquivos
