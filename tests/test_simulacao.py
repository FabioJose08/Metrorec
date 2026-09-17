import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dados import LINHAS
from simulacao import SimulacaoTrens


def test_simulacao_cria_tres_trens_nas_posicoes_iniciais():
    simulacao = SimulacaoTrens(LINHAS)

    assert len(simulacao.trens) == 3
    assert simulacao.trens[0].linha == "Jaboatão"
    assert simulacao.trens[0].estacao_atual == "Jaboatão"
    assert simulacao.trens[1].linha == "Camaragibe"
    assert simulacao.trens[1].estacao_atual == "Camaragibe"
    assert simulacao.trens[2].linha == "Sul"
    assert simulacao.trens[2].estacao_atual == "Cajueiro Seco"


def test_simulacao_avanca_trens_entre_estacoes():
    simulacao = SimulacaoTrens(LINHAS)
    trem = simulacao.trens[0]

    simulacao.iniciar()
    simulacao.avancar()

    assert trem.estacao_atual == "Engenho Velho"
    assert trem.proxima_estacao == "Floriano"
