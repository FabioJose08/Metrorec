import time
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
    """Motor pequeno de simulação para os três trens da rede METROREC."""

    def __init__(self, linhas):
        self.linhas = linhas
        self.trens = []
        self.velocidade = 1.0
        self.ativo = False
        self.paused = False
        self.parado = False
        self.eventos = []
        self.tempo_inicial = time.strftime("%H:%M")
        self._montar_trens()

    def _montar_trens(self):
        self.trens = []
        configuracao = [
            (1, "Jaboatão", "Jaboatão"),
            (2, "Camaragibe", "Camaragibe"),
            (3, "Sul", "Cajueiro Seco"),
        ]

        for idx, nome_linha, terminal in configuracao:
            linha = self.linhas[nome_linha]
            codigo = linha["codigo"]
            estacoes = linha["estacoes"]
            idx_atual = estacoes.index(terminal)
            proxima = estacoes[idx_atual + 1] if idx_atual + 1 < len(estacoes) else terminal
            trem = Trem(
                id=idx,
                linha=nome_linha,
                codigo_linha=codigo,
                estacao_atual=terminal,
                proxima_estacao=proxima,
                sentido="ida",
                status="Em movimento",
                progresso=0.0,
            )
            self.trens.append(trem)

    def iniciar(self):
        self.ativo = True
        self.paused = False
        self.parado = False
        self.eventos.append(f"{self.tempo_inicial} — Simulação iniciada.")

    def pausar(self):
        self.paused = True
        self.ativo = False
        self.eventos.append(f"{self.tempo_inicial} — Simulação pausada.")

    def parar(self):
        self.paused = False
        self.ativo = False
        self.parado = True
        self.eventos.append(f"{self.tempo_inicial} — Simulação parada.")

    def reiniciar(self):
        self._montar_trens()
        self.ativo = True
        self.paused = False
        self.parado = False
        self.eventos = []
        self.eventos.append(f"{self.tempo_inicial} — Simulação reiniciada.")

    def avancar(self):
        if not self.ativo or self.paused or self.parado:
            return

        for trem in self.trens:
            linha = self.linhas[trem.linha]
            estacoes = linha["estacoes"]
            atual_idx = estacoes.index(trem.estacao_atual)

            if trem.sentido == "ida":
                if atual_idx == len(estacoes) - 1:
                    trem.sentido = "volta"
                    trem.status = "Retornando"
                    trem.proxima_estacao = estacoes[-2]
                    trem.eventos.append(f"{self.tempo_inicial} — Trem {trem.id:02d} chegou ao terminal {estacoes[-1]}.")
                    continue

                proxima_idx = atual_idx + 1
                proxima_estacao = estacoes[proxima_idx]
                trem.estacao_atual = proxima_estacao
                trem.proxima_estacao = estacoes[proxima_idx + 1] if proxima_idx + 1 < len(estacoes) else "Terminal"
                trem.status = "Em movimento"
                trem.progresso = min(100, round((proxima_idx / max(len(estacoes) - 1, 1)) * 100, 2))
                trem.eventos.append(f"{self.tempo_inicial} — Trem {trem.id:02d} chegou à estação {proxima_estacao}.")

            elif trem.sentido == "volta":
                if atual_idx == 0:
                    trem.sentido = "ida"
                    trem.status = "Em movimento"
                    trem.proxima_estacao = estacoes[1]
                    trem.eventos.append(f"{self.tempo_inicial} — Trem {trem.id:02d} retornou ao terminal {estacoes[0]}.")
                    continue

                proxima_idx = atual_idx - 1
                proxima_estacao = estacoes[proxima_idx]
                trem.estacao_atual = proxima_estacao
                trem.proxima_estacao = estacoes[proxima_idx - 1] if proxima_idx - 1 >= 0 else "Terminal"
                trem.status = "Em movimento"
                trem.progresso = min(100, round(((len(estacoes) - proxima_idx) / max(len(estacoes), 1)) * 100, 2))
                trem.eventos.append(f"{self.tempo_inicial} — Trem {trem.id:02d} retornou à estação {proxima_estacao}.")

        self.eventos.extend([f"{self.tempo_inicial} — Trem {trem.id:02d} em {trem.estacao_atual}." for trem in self.trens])

    def alterar_velocidade(self, valor):
        self.velocidade = float(valor)

    def painel(self):
        texto = []
        for trem in self.trens:
            texto.append(
                f"TREM {trem.id:02d}\n"
                f"Linha: {trem.linha}\n"
                f"Estação atual: {trem.estacao_atual}\n"
                f"Próxima: {trem.proxima_estacao}\n"
                f"Status: {trem.status}\n"
                f"Sentido: {trem.sentido}\n"
                f"Progresso: {int(trem.progresso)}%"
            )
        return "\n\n".join(texto)
