import copy
import json
import math
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from dados import COORDENADAS_ESTACOES, DURACOES_REFERENCIA_LINHAS, LINHAS
from interface import MetroRecApp
from viagens import (
    _tempo_percurso,
    calcular_rota_na_linha,
    montar_rota_integrada,
)


class CalculoDeViagensTests(unittest.TestCase):
    def test_percurso_completo_tem_duracao_de_referencia_nos_dois_sentidos(self):
        for nome, linha in LINHAS.items():
            with self.subTest(linha=nome):
                ida = calcular_rota_na_linha(linha, linha["estacoes"][0], linha["estacoes"][-1])
                volta = calcular_rota_na_linha(linha, linha["estacoes"][-1], linha["estacoes"][0])
                referencia = DURACOES_REFERENCIA_LINHAS[nome]
                self.assertEqual(ida["tempo_percurso"], referencia)
                self.assertEqual(volta["tempo_percurso"], referencia)
                self.assertEqual(ida["tempo_percurso"], volta["tempo_percurso"])

    def test_vizinha_soma_somente_um_trecho_e_espera_fica_separada(self):
        linha = LINHAS["Jaboatão"]
        viagem = calcular_rota_na_linha(linha, "Jaboatão", "Engenho Velho")
        self.assertEqual(viagem["estacoes"], 1)
        self.assertGreater(viagem["tempo_percurso"], 0)
        self.assertLess(viagem["tempo_percurso"], DURACOES_REFERENCIA_LINHAS["Jaboatão"])
        self.assertEqual(viagem["espera_inicial"], 10)
        self.assertEqual(viagem["tempo_total_estimado"], viagem["tempo_percurso"] + 10)

    def test_percurso_intermediario_soma_os_trechos_escolhidos(self):
        linha = LINHAS["Jaboatão"]
        origem, destino = "Cavaleiro", "Barro"
        esperado = round(_tempo_percurso("Jaboatão", linha, origem, destino))
        viagem = calcular_rota_na_linha(linha, origem, destino)
        self.assertEqual(viagem["rota"], ["Cavaleiro", "Coqueiral", "Tejipió", "Barro"])
        self.assertEqual(viagem["estacoes"], 3)
        self.assertEqual(viagem["tempo_percurso"], esperado)

    def test_percursos_intermediarios_das_outras_linhas_usam_somente_seus_trechos(self):
        casos = (
            ("Camaragibe", "Curado", "Coqueiral", ["Curado", "Alto do Céu", "Coqueiral"]),
            ("Sul", "Aeroporto", "Imbiribeira",
             ["Aeroporto", "Tancredo Neves", "Shopping", "Antônio Falcão", "Imbiribeira"]),
        )
        for nome, origem, destino, rota_esperada in casos:
            with self.subTest(linha=nome):
                viagem = calcular_rota_na_linha(LINHAS[nome], origem, destino)
                self.assertEqual(viagem["rota"], rota_esperada)
                self.assertEqual(viagem["estacoes"], len(rota_esperada) - 1)
                self.assertLess(viagem["tempo_percurso"], DURACOES_REFERENCIA_LINHAS[nome])
                inversa = calcular_rota_na_linha(LINHAS[nome], destino, origem)
                self.assertEqual(viagem["tempo_percurso"], inversa["tempo_percurso"])

    def test_viagem_na_mesma_estacao_tem_tempo_zero(self):
        viagem = calcular_rota_na_linha(LINHAS["Sul"], "Recife", "Recife")
        self.assertEqual(viagem["tempo_percurso"], 0)
        self.assertEqual(viagem["espera_inicial"], 0)
        self.assertEqual(viagem["tempo_total_estimado"], 0)
        rede = montar_rota_integrada(LINHAS, "Recife", "Recife")
        self.assertEqual(rede["tempo_percurso"], 0)
        self.assertEqual(rede["tempo_total_estimado"], 0)

    def test_tempo_integrado_separa_percurso_espera_e_transferencia(self):
        viagem = montar_rota_integrada(LINHAS, "Jaboatão", "Cajueiro Seco", transferencia=5)
        self.assertIsNotNone(viagem)
        self.assertEqual(viagem["trocas"], 1)
        self.assertEqual(viagem["tempo_transferencia"], 5)
        self.assertEqual(viagem["espera_inicial"], 10)
        soma_pernas = sum(
            round(_tempo_percurso(perna["linha"], LINHAS[perna["linha"]],
                                  perna["rota"][0], perna["rota"][-1]))
            for perna in viagem["pernas"]
        )
        self.assertEqual(viagem["tempo_percurso"], soma_pernas)
        self.assertEqual(viagem["tempo_total_estimado"], soma_pernas + 15)
        self.assertEqual(viagem["estacoes"], sum(len(perna["rota"]) - 1 for perna in viagem["pernas"]))

    def test_status_com_restricoes_mantem_fator_existente(self):
        linha = copy.deepcopy(LINHAS["Camaragibe"])
        linha["status"] = "Operação com restrições"
        completa = calcular_rota_na_linha(LINHAS["Camaragibe"], "Camaragibe", "Recife")
        restrita = calcular_rota_na_linha(linha, "Camaragibe", "Recife")
        self.assertEqual(restrita["tempo_percurso"], round(completa["tempo_percurso"] * 1.25))

    def test_marcador_de_trem_usa_tracado_local_quando_api_nao_tem_trecho(self):
        asset = PROJECT / "assets" / "trilhos_metrorec.json"
        pontos = json.loads(asset.read_text(encoding="utf-8"))["routes"]["Jaboatão"]
        app = object.__new__(MetroRecApp)
        app.tracos_api_lookup = {}
        app.tracos_osm = {"Jaboatão": pontos}
        origem, destino = "Jaboatão", "Engenho Velho"
        a, b = COORDENADAS_ESTACOES[origem], COORDENADAS_ESTACOES[destino]
        ia = min(range(len(pontos)), key=lambda i: math.dist(pontos[i], a))
        ib = min(range(len(pontos)), key=lambda i: math.dist(pontos[i], b))
        trecho = pontos[ia:ib + 1] if ia < ib else pontos[ib:ia + 1][::-1]
        distancias = [0.0]
        for p1, p2 in zip(trecho, trecho[1:]):
            distancias.append(distancias[-1] + math.dist(p1, p2))
        alvo = distancias[-1] / 2
        for i in range(1, len(distancias)):
            if alvo <= distancias[i]:
                proporcao = (alvo - distancias[i - 1]) / (distancias[i] - distancias[i - 1])
                esperado = tuple(trecho[i - 1][e] + (trecho[i][e] - trecho[i - 1][e]) * proporcao
                                 for e in range(2))
                break
        atual = app._ponto_no_traco("Jaboatão", origem, destino, 0.5)
        self.assertAlmostEqual(atual[0], esperado[0])
        self.assertAlmostEqual(atual[1], esperado[1])
        ponto_reto = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        self.assertGreater(math.dist(atual, ponto_reto) * 111_000, 20)


if __name__ == "__main__":
    unittest.main()
