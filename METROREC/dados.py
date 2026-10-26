TARIFA_PADRAO = 4.25  # valor acadêmico inicial, centralizado para toda a rede

# Referências aproximadas de tempo dentro do metrô, sem espera ou transferência.
# São médias de calibração do planejador, não horários de composições.
DURACOES_REFERENCIA_LINHAS = {
    "Jaboatão": 26,
    "Camaragibe": 28,
    "Sul": 22,
}

# Coordenadas de referência para ancorar estações nas geometrias ferroviárias locais.
COORDENADAS_ESTACOES = {
    "Camaragibe": (-8.0247222, -34.9950000), "Cosme e Damião": (-8.0355556, -34.9888889),
    "Rodoviária": (-8.0644444, -34.9811111), "Curado": (-8.0758333, -34.9786111),
    "Alto do Céu": (-8.0847222, -34.9747222), "Coqueiral": (-8.0911111, -34.9647222),
    "Jaboatão": (-8.1108333, -35.0150000), "Engenho Velho": (-8.1077778, -35.0050000),
    "Floriano": (-8.1066667, -34.9930556), "Cavaleiro": (-8.0941667, -34.9727778),
    "Tejipió": (-8.0902778, -34.9563889), "Barro": (-8.0886111, -34.9455556),
    "Werneck": (-8.0858333, -34.9361111), "Santa Luzia": (-8.0838889, -34.9300000),
    "Mangueira": (-8.0791667, -34.9211111), "Ipiranga": (-8.0775000, -34.9133333),
    "Afogados": (-8.0772222, -34.9061111), "Joana Bezerra": (-8.0730556, -34.8952778),
    "Recife": (-8.0683333, -34.8847222), "Largo da Paz": (-8.0813889, -34.9047222),
    "Imbiribeira": (-8.0900000, -34.9075000), "Antônio Falcão": (-8.1097222, -34.9088889),
    "Shopping": (-8.1158333, -34.9102778), "Tancredo Neves": (-8.1219444, -34.9116667),
    "Aeroporto": (-8.1341667, -34.9144444), "Porta Larga": (-8.1469444, -34.9175000),
    "Monte dos Guararapes": (-8.1541667, -34.9200000), "Prazeres": (-8.1608333, -34.9266667),
    "Cajueiro Seco": (-8.1680556, -34.9341667),
}

LINHAS = {
    "Jaboatão": {
        "codigo": "L1",
        "status": "Operação normal",
        "tarifa": TARIFA_PADRAO,
        "intervalo": 20,
        "estacoes": [
            "Jaboatão",
            "Engenho Velho",
            "Floriano",
            "Cavaleiro",
            "Coqueiral",
            "Tejipió",
            "Barro",
            "Werneck",
            "Santa Luzia",
            "Mangueira",
            "Ipiranga",
            "Afogados",
            "Joana Bezerra",
            "Recife",
        ],
        "horarios": [
            "05:30", "05:50", "06:10", "06:30", "06:50",
            "07:10", "07:30", "07:50", "08:10", "08:30",
            "09:00", "09:30", "10:00", "10:30", "11:00",
            "11:30", "12:00", "12:30", "13:00", "13:30",
            "14:00", "14:30", "15:00", "15:30", "16:00",
            "16:30", "17:00", "17:30", "18:00", "18:30",
            "19:00", "19:20", "19:40", "20:00", "20:20",
            "20:40", "21:00", "21:20", "21:40", "22:00",
        ],
    },
    "Camaragibe": {
        "codigo": "L2",
        "status": "Operação normal",
        "tarifa": TARIFA_PADRAO,
        "intervalo": 20,
        "estacoes": [
            "Camaragibe",
            "Cosme e Damião",
            "Rodoviária",
            "Curado",
            "Alto do Céu",
            "Coqueiral",
            "Tejipió",
            "Barro",
            "Werneck",
            "Santa Luzia",
            "Mangueira",
            "Ipiranga",
            "Afogados",
            "Joana Bezerra",
            "Recife",
        ],
        "horarios": [
            "05:40", "06:00", "06:20", "06:40", "07:00",
            "07:20", "07:40", "08:00", "08:20", "08:40",
            "09:10", "09:40", "10:10", "10:40", "11:10",
            "11:40", "12:10", "12:40", "13:10", "13:40",
            "14:10", "14:40", "15:10", "15:40", "16:10",
            "16:40", "17:10", "17:40", "18:10", "18:40",
            "19:10", "19:30", "19:50", "20:10", "20:30",
            "20:50", "21:10", "21:30", "21:50", "22:10",
        ],
    },
    "Sul": {
        "codigo": "L3",
        "status": "Operação normal",
        "tarifa": TARIFA_PADRAO,
        "intervalo": 20,
        "estacoes": [
           "Cajueiro Seco",
           "Prazeres",
           "Monte dos Guararapes",
           "Porta Larga",
           "Aeroporto",
           "Tancredo Neves",
           "Shopping",
           "Antônio Falcão",
           "Imbiribeira",
           "Largo da Paz",
           "Joana Bezerra",
           "Recife",
        ],
        "horarios": [
            "05:35", "05:55", "06:15", "06:35", "06:55",
            "07:15", "07:35", "07:55", "08:15", "08:35",
            "09:05", "09:35", "10:05", "10:35", "11:05",
            "11:35", "12:05", "12:35", "13:05", "13:35",
            "14:05", "14:35", "15:05", "15:35", "16:05",
            "16:35", "17:05", "17:35", "18:05", "18:35",
            "19:05", "19:25", "19:45", "20:05", "20:25",
            "20:45", "21:05", "21:25", "21:45", "22:05",
        ],
    },
}

STATUS_DISPONIVEIS = [
    "Operação normal",
    "Operação com restrições",
    "Indisponível",
]

CONEXOES = ["Recife", "Joana Bezerra"]
