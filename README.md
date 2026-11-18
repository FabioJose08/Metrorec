# 🚇 MetroREC — Sistema de Mobilidade Integrado

O **MetroREC** é um projeto acadêmico desenvolvido em Python que simula o funcionamento do sistema metroviário da Região Metropolitana do Recife. A aplicação apresenta uma interface gráfica com mapa interativo, simulação de circulação dos trens, planejamento de viagens e gerenciamento operacional.

O objetivo é demonstrar, de forma visual e interativa, como funciona a organização de uma rede de transporte ferroviário.

## ✨ Funcionalidades

- **Mapa interativo:** visualização das linhas ferroviárias e estações.
- **Simulação de trens:** movimentação das composições e representação da operação da rede.
- **Planejamento de viagens:** consulta de trajetos, conexões e estimativas de tempo.
- **Painel administrativo:** gerenciamento de tarifas, linhas, frota e maquinistas.
- **Controle operacional:** registro e acompanhamento de ocorrências.
- **Persistência local:** armazenamento das configurações operacionais.

## 🚆 Linhas disponíveis

O projeto contempla três linhas do sistema:

| Linha | Trajeto |
|---|---|
| Jaboatão | Jaboatão ↔ Recife |
| Camaragibe | Camaragibe ↔ Recife |
| Sul | Cajueiro Seco ↔ Recife |

As estações Recife e Joana Bezerra funcionam como pontos de conexão entre as linhas.

## 🛠️ Tecnologias utilizadas

- **Python:** linguagem principal do projeto.
- **Tkinter:** construção da interface gráfica.
- **TkinterMapView:** implementação do mapa interativo.
- **Pillow:** manipulação de imagens.
- **Requests:** comunicação com serviços externos.
- **SQLite:** armazenamento local do cache de mapas.
- **PyInstaller:** geração do executável para Windows.
- **OpenStreetMap:** referência para os dados cartográficos.

## 📂 Estrutura do projeto

```text
Metrorec/
├── README.md
├── LICENSE
└── METROREC/
    ├── main.py
    ├── interface.py
    ├── dados.py
    ├── viagens.py
    ├── simulacao.py
    ├── operacao.py
    ├── painel_admin.py
    ├── map_tiles.py
    ├── utilitarios.py
    ├── operacao.json
    ├── requirements.txt
    ├── requirements-build.txt
    ├── build_exe.ps1
    ├── assets/
    └── tests/
```

## ▶️ Como executar

**1. Clone o repositório:**

```bash
git clone https://github.com/FabioJose08/Metrorec.git
```

**2. Entre na pasta do projeto:**

```bash
cd Metrorec/METROREC
```

**3. Crie um ambiente virtual:**

```bash
python -m venv .venv
```

**4. Ative o ambiente virtual no Windows:**

```bash
.venv\Scripts\activate
```

**5. Instale as dependências:**

```bash
python -m pip install -r requirements.txt
```

**6. Execute a aplicação:**

```bash
python main.py
```

## 📦 Gerar executável

O projeto também permite gerar uma versão executável para Windows.

Instale as dependências de compilação:

```bash
python -m pip install -r requirements-build.txt
```

Execute o script de compilação:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_exe.ps1
```

O executável será gerado em:

```text
dist/MetroREC.exe
```

## ⚠️ Observação

O MetroREC é um simulador acadêmico e demonstrativo. Tarifas, intervalos, velocidades e tempos de viagem são parâmetros utilizados para a simulação, não representando necessariamente os dados oficiais da operação real.

O sistema não possui integração com os sistemas operacionais da CBTU.

Os dados cartográficos do OpenStreetMap são utilizados conforme seus termos de atribuição: https://www.openstreetmap.org/copyright.

## 🎓 Projeto acadêmico

Desenvolvido como parte das atividades acadêmicas do curso de Ciência da Computação, com foco em programação, organização de sistemas, interfaces gráficas e simulação de processos.

---

**Desenvolvido por Fábio José.**
