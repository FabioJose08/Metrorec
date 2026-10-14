"""Cálculos de rota independentes da interface gráfica."""
from collections import deque
from datetime import datetime

INDISPONIVEIS = {"Indisponível", "Interrompida"}


def _disponiveis(linhas):
    return {nome: linha for nome, linha in linhas.items()
            if linha.get("status") not in INDISPONIVEIS}


def _tempo_percurso(linha, quantidade):
    tempo = quantidade * float(linha.get("minutos_por_trecho", 3))
    if linha.get("status") in ("Operação com restrições", "Atenção", "Operação reduzida"):
        tempo *= float(linha.get("fator_tempo_restrito", 1.25))
    return tempo


def calcular_rota_na_linha(linha, origem, destino):
    if not linha or linha.get("status") in INDISPONIVEIS:
        return None
    estacoes = linha["estacoes"]
    if origem not in estacoes or destino not in estacoes or origem == destino:
        return None
    a, b = estacoes.index(origem), estacoes.index(destino)
    rota = estacoes[a:b + 1] if a < b else list(reversed(estacoes[b:a + 1]))
    quantidade = len(rota) - 1
    espera = max(0, int(linha.get("intervalo", 0)) // 2)
    return {"rota": rota, "estacoes": quantidade,
            "tempo": round(_tempo_percurso(linha, quantidade) + espera),
            "tarifa": linha["tarifa"], "trocas": 0,
            "sentido": "ida" if a < b else "volta"}


def montar_rota_integrada(linhas, origem, destino, transferencia=5, linha_inicial=None):
    """Busca caminho mínimo em estações; trocar de linha só ocorre numa estação comum."""
    ativas = _disponiveis(linhas)
    if origem == destino or not any(origem in l["estacoes"] for l in ativas.values()) \
            or not any(destino in l["estacoes"] for l in ativas.values()):
        return None
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
    tempo_percurso = sum(_tempo_percurso(ativas[p["linha"]], len(p["rota"]) - 1) for p in pernas)
    tempo_transferencia = max(0, len(pernas) - 1) * max(0, int(transferencia))
    tempo = tempo_percurso + tempo_transferencia
    espera = sum(max(0, int(ativas[p["linha"]].get("intervalo", 0)) // 2) for p in pernas[:1])
    tarifa = max(ativas[p["linha"]]["tarifa"] for p in pernas)
    result = {"rota": [estado[0] for estado in caminho], "pernas": pernas,
              "estacoes": quantidade, "tempo": round(tempo + espera),
              "tempo_transferencia": tempo_transferencia,
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
