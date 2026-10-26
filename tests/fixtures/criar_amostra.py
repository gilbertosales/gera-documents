#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera tests/fixtures/amostra/: um .md por regra do analisador.

Rodar de novo recria a pasta do zero (os arquivos ficam versionados junto dos testes).
"""

import base64
import os
import shutil

AQUI = os.path.dirname(os.path.abspath(__file__))
AMOSTRA = os.path.join(AQUI, "amostra")

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
)

# nome → conteúdo. Cada arquivo isola uma regra (com H1, para não gerar o INFO
# de "sem título" fora do arquivo que testa justamente isso).
ARQUIVOS = {
    "ok.md": "# Documento OK\n\n## Seção\n\nTexto com **negrito**, *itálico* e `código`.\n\n"
             "- item 1\n- item 2\n   - subitem\n\n1. um\n2. dois\n\n"
             "| A | B |\n|---|---|\n| 1 | 2 |\n\n> citação simples\n\n"
             "![imagem](img/existe.png)\n\n<a id=\"ancora\"></a>\n\n```python\nx = [1](2)\n```\n",
    "sem_h1.md": "## Só subtítulo\n\nTexto.\n",
    "tabela_sem_separador.md": "# T\n\n| A | B |\n| 1 | 2 |\n",
    "tabela_colunas.md": "# T\n\n| A | B |\n|---|---|\n| 1 | 2 | 3 |\n| 4 |\n",
    "tabela_br.md": "# T\n\n| A | B |\n|---|---|\n| linha1<br>linha2 | x |\n",
    "mermaid.md": "# T\n\n```mermaid\ngraph TD; A-->B\n```\n",
    "titulo_nivel6.md": "# T\n\n###### Nível seis\n",
    "titulo_sem_espaco.md": "# T\n\n##Sem espaço\n",
    "lista_tab.md": "# T\n\n- item\n\t- sub com tab\n",
    "lista_4_espacos.md": "# T\n\n- item\n    - sub com 4 espaços\n",
    "lista_mais.md": "# T\n\n+ item com mais\n",
    "lista_parenteses.md": "# T\n\n1) primeiro\n2) segundo\n",
    "checklist.md": "# T\n\n- [ ] pendente\n- [x] feito\n",
    "citacao_lista.md": "# T\n\n> - item na citação\n> ## título na citação\n",
    "imagem_internet.md": "# T\n\n![logo](https://exemplo.com/logo.png)\n",
    "imagem_inexistente.md": "# T\n\n![falta](img/nao_existe.png)\n",
    "texto_apos_imagem.md": "# T\n\n![ok](img/existe.png) legenda na mesma linha\n",
    "imagem_no_meio.md": "# T\n\nVeja ![ok](img/existe.png) no meio do texto.\n",
    "links.md": "# T\n\nVeja [o site](https://exemplo.com) e [a seção](#secao).\n",
    "riscado.md": "# T\n\nTexto ~~antigo~~ novo.\n",
    "negrito_sublinhado.md": "# T\n\nTexto __forte__ aqui.\n",
    "italico_sublinhado.md": "# T\n\nTexto _ênfase_ aqui.\n",
    "html.md": "# T\n\nTexto <span>com tag</span> aqui.\n",
    "ancora.md": "# T\n\n<a id=\"topo\"></a>\n\nTexto.\n",
    "nota_rodape.md": "# T\n\nTexto com nota[^1].\n",
    "codigo_aberto.md": "# T\n\n```\ncódigo sem fim\n",
    "sub/interno.md": "# Interno\n\nTexto ~~velho~~.\n",
    "node_modules/ignorado.md": "# Ignorado\n\n~~não deve aparecer~~\n",
    ".oculta/ignorado.md": "# Ignorado\n",
}


def criar(destino=AMOSTRA):
    if os.path.isdir(destino):
        shutil.rmtree(destino)
    for nome, texto in ARQUIVOS.items():
        caminho = os.path.join(destino, nome)
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
    with open(os.path.join(destino, "cp1252.md"), "wb") as f:
        f.write("# Acentuação\n\nTexto em cp1252: ação, coração.\n".encode("cp1252"))
    os.makedirs(os.path.join(destino, "img"), exist_ok=True)
    with open(os.path.join(destino, "img", "existe.png"), "wb") as f:
        f.write(PNG_1X1)


if __name__ == "__main__":
    criar()
    print(f"Amostra criada em {AMOSTRA}")
