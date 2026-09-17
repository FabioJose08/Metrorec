from datetime import datetime


def formatar_reais(valor):
    return f"R$ {valor:.2f}".replace(".", ",")


def horario_atual():
    return datetime.now().strftime("%H:%M")


def data_atual():
    return datetime.now().strftime("%d/%m/%Y")


def minutos_para_texto(minutos):
    if minutos is None:
        return ""
    if minutos <= 0:
        return "agora"
    if minutos == 1:
        return "em 1 minuto"
    return f"em {minutos} minutos"
