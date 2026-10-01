from dataclasses import dataclass, field


@dataclass
class Trem:
    id: int
    linha: str
    codigo_linha: str
    estacao_atual: str
    proxima_estacao: str
    sentido: str = "ida"
    status: str = "Em movimento"
    progresso: float = 0.0
    eventos: list = field(default_factory=list)


class SimulacaoTrens:
    """Motor simples: cada trem percorre continuamente o trecho atual."""

    def __init__(self, linhas):
        self.linhas = linhas
        self.velocidade = 1.0
        self.ativo = self.paused = self.parado = False
        self.eventos = []
        self._montar_trens()

    def _montar_trens(self):
        terminais = [(1, "Jaboatão", "Jaboatão"), (2, "Camaragibe", "Camaragibe"), (3, "Sul", "Cajueiro Seco")]
        self.trens = []
        for idx, linha, terminal in terminais:
            dados = self.linhas[linha]
            pos = dados["estacoes"].index(terminal)
            self.trens.append(Trem(idx, linha, dados["codigo"], terminal, dados["estacoes"][pos + 1] if pos + 1 < len(dados["estacoes"]) else terminal))

    def iniciar(self):
        self.ativo, self.paused, self.parado = True, False, False

    def pausar(self):
        self.paused, self.ativo = True, False

    def parar(self):
        self.paused, self.ativo, self.parado = False, False, True

    def reiniciar(self):
        self._montar_trens()
        self.eventos.clear()
        self.ativo, self.paused, self.parado = True, False, False

    def _mover(self, trem):
        estacoes = self.linhas[trem.linha]["estacoes"]
        atual = estacoes.index(trem.estacao_atual)
        direcao = 1 if trem.sentido == "ida" else -1
        proximo = atual + direcao

        if not 0 <= proximo < len(estacoes):
            trem.sentido = "volta" if direcao == 1 else "ida"
            direcao *= -1
            proximo = atual + direcao
            trem.status = "Retornando"

        trem.progresso = 0.0
        trem.estacao_atual = estacoes[proximo]
        seguinte = proximo + direcao
        trem.proxima_estacao = estacoes[seguinte] if 0 <= seguinte < len(estacoes) else "Terminal"
        if trem.proxima_estacao != "Terminal":
            trem.status = "Em movimento"

    def atualizar(self, passo=0.03):
        if not self.ativo or self.paused or self.parado:
            return
        for trem in self.trens:
            trem.progresso += passo * self.velocidade * 100
            while trem.progresso >= 100:
                trem.progresso -= 100
                self._mover(trem)

    def avancar(self):
        """Avança um trecho inteiro, mantendo compatibilidade com os testes existentes."""
        if self.ativo and not self.paused and not self.parado:
            for trem in self.trens:
                self._mover(trem)

    def alterar_velocidade(self, valor):
        self.velocidade = max(0.1, float(valor))

    def painel(self):
        return "\n\n".join(
            f"TREM {t.id:02d}\nLinha: {t.linha}\nEstação atual: {t.estacao_atual}\n"
            f"Próxima: {t.proxima_estacao}\nStatus: {t.status}\nSentido: {t.sentido}\n"
            f"Progresso: {int(t.progresso)}%" for t in self.trens
        )
