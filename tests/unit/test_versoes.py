import threading

from gera_md.versoes import gravar_nova_versao, numero_versao, proxima_versao


def test_proxima_versao(tmp_path):
    a = tmp_path / "a.md"
    assert proxima_versao(str(a)).endswith("a_v2.md")
    assert proxima_versao(str(tmp_path / "a_v2.md")).endswith("a_v3.md")
    (tmp_path / "a_v2.md").write_text("x")
    (tmp_path / "a_v3.md").write_text("x")
    assert proxima_versao(str(a)).endswith("a_v4.md")


def test_numero_versao():
    assert numero_versao("c:/x/doc_v12.md") == 12
    assert numero_versao("c:/x/doc.md") is None


def test_gravacao_concorrente_nunca_sobrescreve(tmp_path):
    a = str(tmp_path / "a.md")
    criados, barreira = [], threading.Barrier(8)

    def gravar(i):
        barreira.wait()
        criados.append(gravar_nova_versao(a, f"conteúdo {i}\n"))

    ts = [threading.Thread(target=gravar, args=(i,)) for i in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert len(set(criados)) == 8
    conteudos = {open(c, encoding="utf-8").read() for c in criados}
    assert len(conteudos) == 8
