from datetime import datetime


def calcular_rota_na_linha(linha, origem, destino):
    estacoes = linha["estacoes"]

    if origem not in estacoes or destino not in estacoes or origem == destino:
        return None

    origem_idx = estacoes.index(origem)
    destino_idx = estacoes.index(destino)

    if origem_idx <= destino_idx:
        rota = estacoes[origem_idx:destino_idx + 1]
    else:
        rota = list(reversed(estacoes[destino_idx:origem_idx + 1]))

    quantidade = len(rota) - 1
    tempo = quantidade * 3

    return {
        "rota": rota,
        "estacoes": quantidade,
        "tempo": tempo,
        "tarifa": linha["tarifa"],
        "trocas": 0,
    }


def encontrar_linhas_da_estacao(linhas, estacao):
    resultado = []
    for nome, linha in linhas.items():
        if estacao in linha["estacoes"]:
            resultado.append(nome)
    return resultado


def buscar_estacao(linhas, termo):
    termo = termo.strip().lower()
    resultados = []

    if not termo:
        return resultados

    for nome, linha in linhas.items():
        for posicao, estacao in enumerate(linha["estacoes"], start=1):
            if termo in estacao.lower():
                resultados.append({
                    "estacao": estacao,
                    "linha": nome,
                    "codigo": linha["codigo"],
                    "posicao": posicao,
                })
    return resultados


def montar_rota_integrada(linhas, origem, destino):
    for nome, linha in linhas.items():
        rota = calcular_rota_na_linha(linha, origem, destino)
        if rota:
            rota["linha"] = nome
            return rota

    linhas_origem = encontrar_linhas_da_estacao(linhas, origem)
    linhas_destino = encontrar_linhas_da_estacao(linhas, destino)

    for linha_origem_nome in linhas_origem:
        for linha_destino_nome in linhas_destino:
            if linha_origem_nome == linha_destino_nome:
                continue

            linha_origem = linhas[linha_origem_nome]
            linha_destino = linhas[linha_destino_nome]

            conexoes = [
                estacao for estacao in linha_origem["estacoes"]
                if estacao in linha_destino["estacoes"]
            ]

            if not conexoes:
                continue

            conexao = conexoes[0]
            parte1 = calcular_rota_na_linha(linha_origem, origem, conexao)
            parte2 = calcular_rota_na_linha(linha_destino, conexao, destino)

            if parte1 and parte2:
                rota_completa = parte1["rota"] + parte2["rota"][1:]
                return {
                    "rota": rota_completa,
                    "estacoes": len(rota_completa) - 1,
                    "tempo": parte1["tempo"] + parte2["tempo"] + 5,
                    "tarifa": max(parte1["tarifa"], parte2["tarifa"]),
                    "trocas": 1,
                    "linha": f"{linha_origem_nome} + {linha_destino_nome}",
                    "conexao": conexao,
                }

    return None


def proximo_horario(linha):
    agora = datetime.now()
    atual_minutos = agora.hour * 60 + agora.minute

    for horario in linha["horarios"]:
        hora, minuto = map(int, horario.split(":"))
        minutos = hora * 60 + minuto
        if minutos >= atual_minutos:
            falta = minutos - atual_minutos
            return horario, falta

    return None, None
