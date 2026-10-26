"""Cálculos de rota independentes da interface gráfica."""
from collections import deque
from datetime import datetime
from functools import lru_cache
import json
import math
from pathlib import Path

from dados import COORDENADAS_ESTACOES, DURACOES_REFERENCIA_LINHAS, LINHAS

INDISPONIVEIS = {"Indisponível", "Interrompida"}


def _disponiveis(linhas):
    return {nome: linha for nome, linha in linhas.items()
            if linha.get("status") not in INDISPONIVEIS}


@lru_cache(maxsize=1)
def _geometrias_linhas():
    """Carrega os traçados ferroviários locais; não depende de APIs geográficas."""
    caminho = Path(__file__).parent / "assets" / "trilhos_metrorec.json"
    try:
        with caminho.open(encoding="utf-8") as arquivo:
            return json.load(arquivo).get("routes", {})
    except (OSError, ValueError, TypeError):
        return {}


def _distancia_km(a, b):
    """Distância haversine entre pontos (latitude, longitude)."""
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(min(1.0, math.sqrt(h)))


def _comprimentos_trechos(nome_linha, estacoes):
    """Retorna comprimentos por trecho usando as geometrias locais quando coerentes."""
    pontos = _geometrias_linhas().get(nome_linha)
    if not pontos or len(pontos) < 2 or len(estacoes) < 2:
        return None
    pontos = [tuple(map(float, ponto)) for ponto in pontos]
    indices = []
    for estacao in estacoes:
        coordenada = _coordenada_estacao(estacao)
        if coordenada is None:
            return None
        indice = min(range(len(pontos)), key=lambda i: _distancia_km(pontos[i], coordenada))
        # Descarta dados que não estejam próximos das estações cadastradas.
        if _distancia_km(pontos[indice], coordenada) > 1.0:
            return None
        indices.append(indice)
    diferencas = [b - a for a, b in zip(indices, indices[1:])]
    if not (all(delta > 0 for delta in diferencas) or all(delta < 0 for delta in diferencas)):
        return None
    comprimentos = []
    for a, b in zip(indices, indices[1:]):
        inicio, fim = sorted((a, b))
        comprimento = sum(_distancia_km(p1, p2) for p1, p2 in zip(pontos[inicio:fim], pontos[inicio + 1:fim + 1]))
        if comprimento <= 0:
            return None
        comprimentos.append(comprimento)
    return comprimentos


def _nome_da_linha(linha):
    codigo = linha.get("codigo")
    return next((nome for nome, dados in LINHAS.items() if dados.get("codigo") == codigo), None)


def _coordenada_estacao(estacao):
    coordenada = COORDENADAS_ESTACOES.get(estacao)
    return tuple(coordenada) if coordenada else None


def _tempo_percurso(nome_linha, linha, origem, destino):
    """Soma os trechos da rota e calibra a linha para sua duração de referência."""
    estacoes = linha["estacoes"]
    if origem == destino:
        return 0.0
    i_origem, i_destino = estacoes.index(origem), estacoes.index(destino)
    primeiro, ultimo = sorted((i_origem, i_destino))
    comprimentos = _comprimentos_trechos(nome_linha, estacoes)
    referencia = float(DURACOES_REFERENCIA_LINHAS.get(nome_linha, linha.get("tempo_referencia_minutos", 0)))
    if comprimentos and len(comprimentos) == len(estacoes) - 1 and sum(comprimentos) > 0:
        fracao_percorrida = sum(comprimentos[primeiro:ultimo]) / sum(comprimentos)
        tempo = referencia * fracao_percorrida
    else:
        # Fallback transparente: distribuição uniforme da média total por trecho.
        quantidade_total = max(1, len(estacoes) - 1)
        tempo = referencia * (ultimo - primeiro) / quantidade_total
    if linha.get("status") in ("Operação com restrições", "Atenção", "Operação reduzida"):
        tempo *= float(linha.get("fator_tempo_restrito", 1.25))
    return tempo


def _espera_inicial(linha):
    """Espera estimada como metade do intervalo; separada do tempo dentro do trem."""
    return max(0.0, float(linha.get("intervalo", 0)) / 2)


def calcular_rota_na_linha(linha, origem, destino):
    if not linha or linha.get("status") in INDISPONIVEIS:
        return None
    estacoes = linha["estacoes"]
    if origem not in estacoes or destino not in estacoes:
        return None
    a, b = estacoes.index(origem), estacoes.index(destino)
    rota = estacoes[a:b + 1] if a < b else list(reversed(estacoes[b:a + 1]))
    quantidade = len(rota) - 1
    nome_linha = _nome_da_linha(linha)
    tempo_percurso = _tempo_percurso(nome_linha, linha, origem, destino)
    espera = _espera_inicial(linha) if quantidade else 0.0
    tempo_percurso_exibido = round(tempo_percurso)
    espera_exibida = round(espera)
    total = tempo_percurso_exibido + espera_exibida
    return {"rota": rota, "estacoes": quantidade,
            "tempo_percurso": tempo_percurso_exibido,
            "espera_inicial": espera_exibida,
            "tempo_transferencia": 0,
            "tempo_total_estimado": total,
            "tempo": total,
            "tarifa": linha["tarifa"], "trocas": 0,
            "sentido": "ida" if a <= b else "volta"}


def montar_rota_integrada(linhas, origem, destino, transferencia=5, linha_inicial=None):
    """Busca caminho mínimo em estações; trocar de linha só ocorre numa estação comum."""
    ativas = _disponiveis(linhas)
    if not any(origem in l["estacoes"] for l in ativas.values()) \
            or not any(destino in l["estacoes"] for l in ativas.values()):
        return None
    if origem == destino:
        linhas_origem = [nome for nome, linha in ativas.items() if origem in linha["estacoes"]]
        if linha_inicial in linhas_origem:
            linhas_origem = [linha_inicial]
        nome = linhas_origem[0]
        return {"rota": [origem], "pernas": [], "estacoes": 0,
                "tempo_percurso": 0, "espera_inicial": 0,
                "tempo_transferencia": 0, "tempo_total_estimado": 0,
                "tempo": 0, "tarifa": ativas[nome]["tarifa"], "trocas": 0,
                "linha": nome}
    inicio = [(origem, nome) for nome, linha in ativas.items()
              if origem in linha["estacoes"] and (linha_inicial is None or nome == linha_inicial)]
    if not inicio:
        return None
    fila = deque((estado, [estado]) for estado in inicio)
    vistos = set(inicio)
    caminho = None
    while fila:
        (estacao, nome), estados = fila.popleft()
        if estacao == destino:
            caminho = estados
            break
        rota = ativas[nome]["estacoes"]
        pos = rota.index(estacao)
        vizinhos = []
        if pos > 0:
            vizinhos.append((rota[pos - 1], nome))
        if pos + 1 < len(rota):
            vizinhos.append((rota[pos + 1], nome))
        vizinhos.extend((estacao, outra) for outra, linha in ativas.items()
                        if outra != nome and estacao in linha["estacoes"])
        for seguinte in vizinhos:
            if seguinte not in vistos:
                vistos.add(seguinte)
                fila.append((seguinte, estados + [seguinte]))
    if not caminho:
        return None

    pernas, estacoes_perna = [], [caminho[0][0]]
    nome_atual = caminho[0][1]
    for (estacao, linha), (proxima, proxima_linha) in zip(caminho, caminho[1:]):
        if linha != proxima_linha:
            pernas.append({"linha": nome_atual, "rota": estacoes_perna})
            nome_atual, estacoes_perna = proxima_linha, [estacao]
        else:
            estacoes_perna.append(proxima)
    pernas.append({"linha": nome_atual, "rota": estacoes_perna})
    for perna in pernas:
        ordem = ativas[perna["linha"]]["estacoes"]
        perna["sentido"] = "ida" if ordem.index(perna["rota"][0]) < ordem.index(perna["rota"][-1]) else "volta"
    quantidade = sum(len(perna["rota"]) - 1 for perna in pernas)
    tempo_percurso = sum(
        _tempo_percurso(perna["linha"], ativas[perna["linha"]], perna["rota"][0], perna["rota"][-1])
        for perna in pernas
    )
    tempo_transferencia = max(0, len(pernas) - 1) * max(0, int(transferencia))
    espera = _espera_inicial(ativas[pernas[0]["linha"]]) if pernas else 0.0
    tempo_percurso_exibido = round(tempo_percurso)
    espera_exibida = round(espera)
    tempo_transferencia_exibido = round(tempo_transferencia)
    tempo_total = tempo_percurso_exibido + tempo_transferencia_exibido + espera_exibida
    tarifa = max(ativas[p["linha"]]["tarifa"] for p in pernas)
    result = {"rota": [estado[0] for estado in caminho], "pernas": pernas,
              "estacoes": quantidade,
              "tempo_percurso": tempo_percurso_exibido,
              "espera_inicial": espera_exibida,
              "tempo_total_estimado": tempo_total,
              "tempo": tempo_total,
              "tempo_transferencia": tempo_transferencia_exibido,
              "tarifa": tarifa, "trocas": len(pernas) - 1,
              "linha": " + ".join(p["linha"] for p in pernas)}
    if len(pernas) > 1:
        result["conexao"] = pernas[0]["rota"][-1]
    return result


def proximo_horario(linha, agora=None):
    if not linha or linha.get("status") in INDISPONIVEIS:
        return None, None
    agora = agora or datetime.now()
    atual = agora.hour * 60 + agora.minute
    for horario in linha["horarios"]:
        hora, minuto = map(int, horario.split(":"))
        minutos = hora * 60 + minuto
        if minutos >= atual:
            return horario, minutos - atual
    return None, None
