"""Revisão com IA usando o provedor simulado: proteção de blocos, falhas, cancelamento (SC-006)."""

import os
import re
import threading

from gera_md.provedores.simulado import ProvedorSimulado
from gera_md.revisao import revisar_md

DOC = """# Relatório

## Contexto

O resultado foi muito bom e o prazo é curto.

```python
print("muito bom")  # código não pode mudar
```

![diagrama](img.png)

<a id="ancora"></a>

## Conclusão

Tudo muito bom.
"""


def _doc(tmp_path, texto=DOC):
    p = tmp_path / "doc.md"
    p.write_text(texto, encoding="utf-8")
    (tmp_path / "img.png").write_bytes(b"png")
    return str(p)


def test_blocos_protegidos_identicos(tmp_path):
    md = _doc(tmp_path)
    rev, novo = revisar_md(md, ProvedorSimulado(), "technical-documentation")
    texto = open(rev.destino, encoding="utf-8").read()
    assert 'print("muito bom")  # código não pode mudar' in texto
    assert "![diagrama](img.png)" in texto and '<a id="ancora"></a>' in texto
    assert "O resultado foi adequado" in texto
    assert open(md, encoding="utf-8").read() == DOC  # original intocado
    assert rev.contagem == {"Vício de linguagem": 1}
    assert rev.pendencias and rev.pendencias[0]["texto"].startswith('"prazo"')
    assert novo.tipo_versao == "revisao_ia" and novo.origem == md and novo.revisao is rev
    assert rev.uso.custo_usd > 0 and rev.uso.tokens_entrada == 100


def test_marcador_perdido_mantem_original(tmp_path):
    md = _doc(tmp_path)
    rev, _ = revisar_md(md, ProvedorSimulado(perder_marcador_em={1, 2}), "technical-documentation")
    assert rev.falhas and "blocos protegidos" in rev.falhas[0]["erro"]
    # trecho mantido como no original → texto igual → nenhuma versão, só o relatório (FR-023)
    assert rev.destino is None and open(md, encoding="utf-8").read() == DOC
    assert "Trechos não revisados" in open(rev.relatorio, encoding="utf-8").read()


def test_falha_tenta_de_novo(tmp_path):
    md = _doc(tmp_path)
    rev, _ = revisar_md(md, ProvedorSimulado(falhar_em={1}), "technical-documentation")
    assert not rev.falhas


def test_limite_atingido_para_os_demais(tmp_path):
    md = _doc(tmp_path, "# T\n\n" + "\n\n".join(f"## S{i}\n\n" + "muito bom. " * 800 for i in range(4)))
    prov = ProvedorSimulado(limite_em={1, 2, 3, 4, 5, 6, 7, 8})
    rev, _ = revisar_md(md, prov, "technical-documentation")
    assert rev.erro_fatal and "Limite" in rev.erro_fatal
    assert len(rev.falhas) == rev.trechos
    assert prov.chamadas <= 3  # só as chamadas que já estavam em paralelo


def test_cancelar_nao_grava_versao(tmp_path):
    md = _doc(tmp_path, "# T\n\n" + "\n\n".join(f"## S{i}\n\n" + "muito bom. " * 800 for i in range(6)))
    cancelar = threading.Event()
    threading.Timer(0.1, cancelar.set).start()
    rev, novo = revisar_md(md, ProvedorSimulado(atraso=0.5), "technical-documentation", cancelar=cancelar)
    assert rev.cancelada and novo is None and rev.destino is None
    assert sorted(os.listdir(tmp_path)) == ["doc.md", "img.png"]


def test_relatorio_tipo_de_acesso(tmp_path):
    md = _doc(tmp_path)
    rev, _ = revisar_md(md, ProvedorSimulado(), "technical-documentation")
    rel = open(rev.relatorio, encoding="utf-8").read()
    assert "não cobrado no plano Pro/Max" in rel and "Assinatura" in rel
    api = ProvedorSimulado()
    api.tipo_acesso, api.cobranca = "api", "por_uso"
    rev2, _ = revisar_md(md, api, "technical-documentation")
    rel2 = open(rev2.relatorio, encoding="utf-8").read()
    assert "Cobrado por uso (API)" in rel2 and "não cobrado" not in rel2
    assert re.search(r"doc_v3\.md$", rev2.destino)


def test_sem_alteracao_nao_grava_versao(tmp_path):
    """FR-023: texto igual ao original → só o relatório (nome_revisao.md), nenhuma versão."""
    md = _doc(tmp_path, "# Relatório\n\nTexto já adequado.\n")
    rev, novo = revisar_md(md, ProvedorSimulado(), "technical-documentation")
    assert novo is None and rev.destino is None and not rev.cancelada
    assert rev.relatorio.endswith("doc_revisao.md") and os.path.exists(rev.relatorio)
    assert rev.pendencias  # as pendências continuam no relatório
    assert "nenhuma versão foi gravada" in open(rev.relatorio, encoding="utf-8").read()
    assert not [n for n in os.listdir(tmp_path) if "_v" in n]
    rev2, _ = revisar_md(md, ProvedorSimulado(), "technical-documentation")
    assert rev2.relatorio.endswith("doc_revisao_2.md")  # nunca sobrescreve


def test_relatorio_sem_marcadores_internos(tmp_path):
    """FR-023: ⟦BLOCO_n⟧ citado pela IA vira o conteúdo resumido do bloco."""
    from gera_md.revisao import descrever_bloco
    md = _doc(tmp_path)  # BLOCO_0 = código python, BLOCO_1 = imagem, BLOCO_2 = âncora
    prov = ProvedorSimulado(pendencia='"Resultado" — confirmar o comando antes de ⟦BLOCO_0⟧, '
                                      "a captura ⟦BLOCO_1⟧, a âncora ⟦BLOCO_2⟧ e ⟦BLOCO_99⟧")
    rev, _ = revisar_md(md, prov, "technical-documentation")
    texto = rev.pendencias[0]["texto"]
    assert '[bloco de código: print("muito bom")  # código não pode mudar…]' in texto
    assert "[imagem: img.png]" in texto and "[âncora: ancora]" in texto and "[bloco]" in texto
    rel = open(rev.relatorio, encoding="utf-8").read()
    assert "⟦" not in rel and "[imagem: img.png]" in rel
    assert descrever_bloco("```\n```") == "[bloco de código]"
