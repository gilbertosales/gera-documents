import time

from gera_md.comparacao import comparar, comparar_linhas


def test_identicos():
    assert [b["tipo"] for b in comparar_linhas(["a", "b"], ["a", "b"])] == ["igual"]


def test_tipos_e_intervalos():
    blocos = comparar_linhas(["a", "b", "c", "d"], ["a", "B", "c", "d", "e"])
    tipos = [(b["tipo"], b["a"], b["b"]) for b in blocos]
    assert ("alterado", [2, 3], [2, 3]) in tipos
    assert ("inserido", [5, 5], [5, 6]) in tipos
    rem = comparar_linhas(["a", "x", "b"], ["a", "b"])
    assert ("removido", [2, 3], [2, 2]) in [(b["tipo"], b["a"], b["b"]) for b in rem]


def test_arquivos_e_desempenho(tmp_path):
    a = [f"linha {i}" for i in range(5000)]
    b = list(a)
    b[100], b[2500] = "mudou", "mudou também"
    b.insert(4000, "nova")
    (tmp_path / "a.md").write_text("\n".join(a), encoding="utf-8")
    (tmp_path / "b.md").write_text("\n".join(b), encoding="utf-8")
    t0 = time.perf_counter()
    blocos = comparar(str(tmp_path / "a.md"), str(tmp_path / "b.md"))
    assert time.perf_counter() - t0 < 1
    assert sum(b["tipo"] != "igual" for b in blocos) == 3
