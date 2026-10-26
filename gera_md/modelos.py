# -*- coding: utf-8 -*-
"""Entidades do núcleo (ver specs/001-local-web-frontend/data-model.md).

Todas serializáveis com to_dict(); nenhuma depende de interface.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

NIVEIS = ("ERRO", "AVISO", "INFO")
ORDEM_NIVEL = {n: i for i, n in enumerate(NIVEIS)}
TAM_TRECHO_ACHADO = 200


def situacao(erros: int, avisos: int) -> str:
    """`Corrigir` se erros > 0; `Revisar` se avisos > 0; senão `OK`."""
    return "Corrigir" if erros else ("Revisar" if avisos else "OK")


class _Dict:
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)  # type: ignore[call-overload]


@dataclass
class Achado(_Dict):
    nivel: str  # ERRO | AVISO | INFO
    linha: int  # 0 = arquivo inteiro
    mensagem: str
    trecho: str | None = None  # até 200 caracteres


@dataclass
class Correcao(_Dict):
    linha: int  # linha do original; 0 = geral
    descricao: str


@dataclass
class Uso(_Dict):
    custo_usd: float = 0.0
    tokens_entrada: int = 0
    tokens_saida: int = 0

    def somar(self, outro: "Uso") -> None:
        self.custo_usd += outro.custo_usd
        self.tokens_entrada += outro.tokens_entrada
        self.tokens_saida += outro.tokens_saida


@dataclass
class Revisao(_Dict):
    origem: str
    destino: str | None
    relatorio: str | None
    provedor: str
    tipo_acesso: str  # assinatura | api
    cobranca: str  # limite_assinatura | por_uso
    skill: str
    modelo: str
    contagem: dict[str, int] = field(default_factory=dict)
    pendencias: list[dict[str, str]] = field(default_factory=list)  # {secao, texto}
    falhas: list[dict[str, str]] = field(default_factory=list)  # {secao, erro}
    trechos: int = 0
    uso: Uso = field(default_factory=Uso)
    cancelada: bool = False
    erro_fatal: str | None = None  # login expirado / limite atingido no meio da revisão
    login_expirado: bool = False


@dataclass
class ResultadoArquivo(_Dict):
    caminho: str
    rotulo: str
    achados: list[Achado] = field(default_factory=list)
    versao: int | None = None
    origem: str | None = None
    tipo_versao: str = "original"  # original | correcao | revisao_ia
    correcoes: list[Correcao] = field(default_factory=list)
    revisao: Revisao | None = None
    modificado_em: float = 0.0

    @property
    def erros(self) -> int:
        return sum(1 for a in self.achados if a.nivel == "ERRO")

    @property
    def avisos(self) -> int:
        return sum(1 for a in self.achados if a.nivel == "AVISO")

    @property
    def situacao(self) -> str:
        return situacao(self.erros, self.avisos)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.update(erros=self.erros, avisos=self.avisos, situacao=self.situacao)
        return d


@dataclass
class Analise(_Dict):
    id: str
    pasta: str
    subpastas: bool = True
    iniciada_em: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    arquivos: list[ResultadoArquivo] = field(default_factory=list)

    def obter(self, caminho: str) -> ResultadoArquivo | None:
        return next((a for a in self.arquivos if a.caminho == caminho), None)

    def inserir(self, arquivo: ResultadoArquivo, depois_de: str | None = None) -> None:
        """Substitui se já existe; senão insere após `depois_de` (ou no fim)."""
        for i, a in enumerate(self.arquivos):
            if a.caminho == arquivo.caminho:
                self.arquivos[i] = arquivo
                return
        idx = next((i for i, a in enumerate(self.arquivos) if a.caminho == depois_de), None)
        if idx is None:
            self.arquivos.append(arquivo)
        else:
            # depois da origem e das versões que já vieram dela
            j = idx + 1
            while j < len(self.arquivos) and self.arquivos[j].origem == depois_de:
                j += 1
            self.arquivos.insert(j, arquivo)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "pasta": self.pasta, "subpastas": self.subpastas,
                "iniciada_em": self.iniciada_em,
                "arquivos": [a.to_dict() for a in self.arquivos]}


@dataclass
class Progresso(_Dict):
    feito: int = 0
    total: int | None = None
    mensagem: str = ""


@dataclass
class Operacao(_Dict):
    id: str
    tipo: str  # busca | correcao | revisao
    estado: str = "executando"  # executando | concluida | cancelando | cancelada | erro
    progresso: Progresso = field(default_factory=Progresso)
    resultado: Any = None
    erro: str | None = None
    criada_em: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "tipo": self.tipo, "estado": self.estado,
                "progresso": self.progresso.to_dict(), "resultado": self.resultado,
                "erro": self.erro}
