import tkinter as tk
import webbrowser
from urllib.parse import quote
from tkinter import ttk, messagebox

from dados import LINHAS, STATUS_DISPONIVEIS
from simulacao import SimulacaoTrens
from viagens import calcular_rota_na_linha, buscar_estacao, montar_rota_integrada, proximo_horario
from utilitarios import formatar_reais, horario_atual, data_atual, minutos_para_texto


class MetroRecApp:
    def __init__(self, root):
        self.root = root
        self.root.title("METROREC - Sistema de Informações e Planejamento")
        self.root.geometry("1200x760")
        self.root.minsize(1000, 650)
        self.root.configure(bg="#eef2f6")
        self.root.option_add("*Font", ("Segoe UI", 10))

        self.linhas = LINHAS
        self.linha_atual = None
        self.topo = None
        self.conteudo = None
        self.simulacao = SimulacaoTrens(self.linhas)
        self.configure_styles()
        self.tela_inicial()

    def configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Estilo principal dos botões: mais visível, com contraste forte,
        # feedback de hover e estado de press no esquema azul-escuro/branco/preto.
        style.configure(
            "Metro.TButton",
            font=("Segoe UI", 11, "bold"),
            padding=(16, 10),
            foreground="#ffffff",
            background="#071b2f",
            borderwidth=2,
            focusthickness=2,
            focuscolor="#b9d8ff",
            relief="raised",
        )
        style.map(
            "Metro.TButton",
            background=[
                ("active", "#0d4d76"),
                ("pressed", "#020710"),
            ],
            foreground=[
                ("active", "#ffffff"),
                ("pressed", "#ffffff"),
            ],
            relief=[
                ("pressed", "sunken"),
                ("active", "raised"),
            ],
        )

        # Navegação com botão mais robusto e representativo
        style.configure(
            "Metro.Nav.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 8),
            foreground="#ffffff",
            background="#102b4f",
            borderwidth=2,
            focusthickness=2,
            focuscolor="#b9d8ff",
            relief="raised",
        )
        style.map(
            "Metro.Nav.TButton",
            background=[
                ("active", "#0b5a8a"),
                ("pressed", "#020710"),
            ],
            foreground=[
                ("active", "#ffffff"),
                ("pressed", "#ffffff"),
            ],
            relief=[
                ("pressed", "sunken"),
                ("active", "raised"),
            ],
        )

        style.configure("Metro.TCombobox", font=("Segoe UI", 11), padding=6, fieldbackground="#ffffff", foreground="#172b40")
        style.configure("Metro.TEntry", font=("Segoe UI", 11), padding=6, fieldbackground="#ffffff")
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=34)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), padding=7)

    def limpar_conteudo(self):
        if self.conteudo is not None:
            self.conteudo.destroy()
            self.conteudo = None

    def limpar_topo(self):
        if self.topo is not None:
            if self.topo.winfo_exists():
                self.topo.destroy()
            self.topo = None

    def criar_cabecalho(self, titulo, subtitulo=""):
        self.limpar_topo()
        self.limpar_conteudo()

        topo = tk.Frame(self.root, bg="#15283f", height=88)
        topo.pack(fill="x")
        topo.pack_propagate(False)
        self.topo = topo

        esquerdo = tk.Frame(topo, bg="#15283f")
        esquerdo.pack(side="left", padx=28, fill="y")

        tk.Label(
            esquerdo,
            text="🚇 METROREC",
            font=("Segoe UI", 18, "bold"),
            fg="white",
            bg="#15283f",
        ).pack(anchor="w", pady=(12, 0))

        tk.Label(
            esquerdo,
            text=titulo,
            font=("Segoe UI", 10),
            fg="#bdc9d7",
            bg="#15283f",
        ).pack(anchor="w")

        relogio = tk.Label(
            topo,
            font=("Segoe UI", 16, "bold"),
            fg="white",
            bg="#15283f",
        )
        relogio.pack(side="right", padx=28)

        def atualizar():
            if relogio.winfo_exists():
                relogio.config(text=f"{horario_atual()}  |  {data_atual()}")
                relogio.after(1000, atualizar)

        atualizar()

        self.conteudo = tk.Frame(self.root, bg="#eef2f6")
        self.conteudo.pack(fill="both", expand=True)
        self.conteudo.columnconfigure(0, weight=1)
        self.conteudo.rowconfigure(0, weight=1)

        area = tk.Frame(self.conteudo, bg="#eef2f6")
        area.grid(row=0, column=0, sticky="nsew", padx=30, pady=25)

        tk.Label(
            area,
            text=titulo,
            font=("Segoe UI", 26, "bold"),
            fg="#172b40",
            bg="#eef2f6",
        ).pack(anchor="w")

        if subtitulo:
            tk.Label(
                area,
                text=subtitulo,
                font=("Segoe UI", 11),
                fg="#667587",
                bg="#eef2f6",
            ).pack(anchor="w", pady=(4, 20))

        return area

    def card(self, parent, **kwargs):
        frame = tk.Frame(parent, bg="white", bd=1, relief="solid", highlightthickness=1, highlightbackground="#d9e1ea", **kwargs)
        return frame

    def botao_navegacao(self, parent, texto, comando):
        ttk.Button(parent, text=texto, style="Metro.Nav.TButton", command=comando).pack(side="left", padx=4)

    def status_cor(self, status):
        return {
            "Operação normal": "#198754",
            "Atenção": "#b77900",
            "Operação reduzida": "#d97706",
            "Interrompida": "#c0392b",
        }.get(status, "#68737d")

    def tela_inicial(self):
        self.linha_atual = None
        self.limpar_conteudo()
        area = self.criar_cabecalho("Sistema de Informações do Metrô", "Consulte linhas, horários, estações e planeje sua viagem")

        resumo = tk.Frame(area, bg="#eef2f6")
        resumo.pack(fill="x", pady=(0, 18))

        tk.Label(
            resumo,
            text="Informações das linhas Jaboatão, Camaragibe e Sul.",
            font=("Segoe UI", 12),
            fg="#425466",
            bg="#eef2f6",
        ).pack(side="left")

        self.criar_botoes_superiores(area)

        cards = tk.Frame(area, bg="#eef2f6")
        cards.pack(fill="x", pady=5)

        for nome, linha in self.linhas.items():
            card = self.card(cards, width=330, height=250)
            card.pack(side="left", fill="both", expand=True, padx=7)
            card.pack_propagate(False)

            faixa = tk.Frame(card, bg="#1f5fa8", height=8)
            faixa.pack(fill="x")
            faixa.pack_propagate(False)

            tk.Label(card, text=linha["codigo"], font=("Segoe UI", 11, "bold"), fg="#667587", bg="white").pack(anchor="w", padx=22, pady=(18, 0))
            tk.Label(card, text=nome, font=("Segoe UI", 20, "bold"), fg="#172b40", bg="white").pack(anchor="w", padx=22)

            tk.Label(
                card,
                text=linha["status"],
                font=("Segoe UI", 10, "bold"),
                fg=self.status_cor(linha["status"]),
                bg="white",
            ).pack(anchor="w", padx=22, pady=(5, 3))

            tk.Label(
                card,
                text=f"{len(linha['estacoes'])} estações  •  {formatar_reais(linha['tarifa'])}",
                font=("Segoe UI", 10),
                fg="#667587",
                bg="white",
            ).pack(anchor="w", padx=22)

            # Mantém a ação "Acessar linha" dentro do card com tamanho fixo, evitando o botão
            # "vazar" para fora do enquadramento visual na tela inicial.
            botoes = tk.Frame(card, bg="white")
            botoes.pack(fill="x", padx=22, pady=(12, 18))
            ttk.Button(botoes, text="Acessar linha", style="Metro.TButton", command=lambda n=nome: self.tela_linha(n)).pack(fill="x")

        rodape = tk.Frame(area, bg="#eef2f6")
        rodape.pack(fill="x", pady=20)
        ttk.Button(rodape, text="📊 Visão geral", style="Metro.TButton", command=self.tela_dashboard).pack(side="left", padx=4)
        ttk.Button(rodape, text="🚇 Todas as linhas", style="Metro.TButton", command=self.tela_todas_linhas).pack(side="left", padx=4)
        ttk.Button(rodape, text="�️ Mapa da Rede", style="Metro.TButton", command=self.tela_mapa_rede).pack(side="left", padx=4)
        ttk.Button(rodape, text="⚙ Controle do sistema", style="Metro.TButton", command=self.tela_admin).pack(side="right", padx=4)

    def criar_botoes_superiores(self, parent):
        barra = tk.Frame(parent, bg="#eef2f6")
        barra.pack(fill="x", pady=(0, 8))
        self.botao_navegacao(barra, "Início", self.tela_inicial)
        self.botao_navegacao(barra, "Dashboard", self.tela_dashboard)
        self.botao_navegacao(barra, "Linhas", self.tela_todas_linhas)
        self.botao_navegacao(barra, "Mapa da Rede", self.tela_mapa_rede)
        self.botao_navegacao(barra, "Planejar viagem", self.janela_planejamento_global)

    def tela_linha(self, nome):
        self.linha_atual = nome
        linha = self.linhas[nome]
        self.limpar_conteudo()
        area = self.criar_cabecalho(
            f"{linha['codigo']} • Linha {nome}",
            f"{linha['status']}  •  Tarifa: {formatar_reais(linha['tarifa'])}  •  Intervalo: {linha['intervalo']} min",
        )
        self.criar_botoes_superiores(area)

        grid = tk.Frame(area, bg="#eef2f6")
        grid.pack(fill="both", expand=True)

        opcoes = [
            ("🧭", "Planejar viagem", lambda: self.janela_planejamento(nome)),
            ("📍", "Estações", lambda: self.janela_estacoes(nome)),
            ("🔎", "Buscar estação", lambda: self.janela_busca_linha(nome)),
            ("🕐", "Horários", lambda: self.janela_horarios(nome)),
            ("🚇", "Próximo metrô", lambda: self.mostrar_proximo(nome)),
            ("⚠", "Status da linha", lambda: self.janela_status(nome)),
            ("💰", "Tarifa", lambda: self.mostrar_tarifa(nome)),
            ("ℹ", "Informações", lambda: self.janela_informacoes(nome)),
        ]

        for coluna in range(4):
            grid.columnconfigure(coluna, weight=1)
        for linha_grid in range(2):
            grid.rowconfigure(linha_grid, weight=1)

        for i, (icone, titulo, comando) in enumerate(opcoes):
            card = self.card(grid)
            card.grid(row=i // 4, column=i % 4, sticky="nsew", padx=7, pady=7)

            tk.Label(card, text=icone, font=("Segoe UI Emoji", 27), bg="white").pack(pady=(24, 8))
            tk.Label(card, text=titulo, font=("Segoe UI", 12, "bold"), fg="#172b40", bg="white").pack()
            ttk.Button(card, text="Abrir", style="Metro.TButton", command=comando).pack(fill="x", padx=25, pady=20)

    def tela_dashboard(self):
        self.linha_atual = None
        self.limpar_conteudo()
        area = self.criar_cabecalho("Visão geral", "Resumo rápido do sistema METROREC")
        self.criar_botoes_superiores(area)

        total_estacoes = sum(len(l["estacoes"]) for l in self.linhas.values())
        normais = sum(1 for l in self.linhas.values() if l["status"] == "Operação normal")
        atencao = len(self.linhas) - normais
        proximo_global = self.proximo_global()

        cards = tk.Frame(area, bg="#eef2f6")
        cards.pack(fill="x", pady=10)

        indicadores = [
            ("Linhas", len(self.linhas), "Linhas cadastradas"),
            ("Estações", total_estacoes, "Somando as três linhas"),
            ("Operação normal", normais, "Linhas em situação normal"),
            ("Atenção", atencao, "Linhas fora do padrão normal"),
        ]

        for titulo, valor, detalhe in indicadores:
            card = self.card(cards)
            card.pack(side="left", fill="both", expand=True, padx=5)
            tk.Label(card, text=titulo, font=("Segoe UI", 10, "bold"), fg="#667587", bg="white").pack(anchor="w", padx=20, pady=(18, 0))
            tk.Label(card, text=str(valor), font=("Segoe UI", 25, "bold"), fg="#172b40", bg="white").pack(anchor="w", padx=20)
            tk.Label(card, text=detalhe, font=("Segoe UI", 9), fg="#8a98a8", bg="white").pack(anchor="w", padx=20, pady=(0, 18))

        inferior = tk.Frame(area, bg="#eef2f6")
        inferior.pack(fill="both", expand=True, pady=10)

        esquerdo = self.card(inferior)
        esquerdo.pack(side="left", fill="both", expand=True, padx=(0, 7))
        tk.Label(esquerdo, text="Situação das linhas", font=("Segoe UI", 15, "bold"), fg="#172b40", bg="white").pack(anchor="w", padx=20, pady=18)

        for nome, linha in self.linhas.items():
            item = tk.Frame(esquerdo, bg="#f6f8fa")
            item.pack(fill="x", padx=18, pady=5)
            tk.Label(item, text=f"{linha['codigo']} • {nome}", font=("Segoe UI", 10, "bold"), bg="#f6f8fa", fg="#172b40").pack(side="left", padx=12, pady=12)
            tk.Label(item, text=linha["status"], font=("Segoe UI", 9, "bold"), bg="#f6f8fa", fg=self.status_cor(linha["status"])).pack(side="right", padx=12)

        direito = self.card(inferior)
        direito.pack(side="right", fill="both", expand=True, padx=(7, 0))
        tk.Label(direito, text="Próximo metrô disponível", font=("Segoe UI", 15, "bold"), fg="#172b40", bg="white").pack(anchor="w", padx=20, pady=18)

        if proximo_global:
            nome, horario, falta = proximo_global
            tk.Label(direito, text=nome, font=("Segoe UI", 20, "bold"), fg="#1f5fa8", bg="white").pack(anchor="w", padx=20)
            tk.Label(direito, text=f"Horário: {horario}", font=("Segoe UI", 12), fg="#425466", bg="white").pack(anchor="w", padx=20, pady=4)
            tk.Label(direito, text=minutos_para_texto(falta), font=("Segoe UI", 11, "bold"), fg="#198754", bg="white").pack(anchor="w", padx=20)
        else:
            tk.Label(direito, text="Não há mais horários cadastrados hoje.", font=("Segoe UI", 11), fg="#667587", bg="white").pack(anchor="w", padx=20)

        ttk.Button(direito, text="Atualizar", style="Metro.TButton", command=self.tela_dashboard).pack(fill="x", padx=20, pady=25)

    def proximo_global(self):
        candidatos = []
        for nome, linha in self.linhas.items():
            horario, falta = proximo_horario(linha)
            if horario is not None:
                candidatos.append((nome, horario, falta))
        if not candidatos:
            return None
        candidatos.sort(key=lambda item: item[2])
        return candidatos[0]

    def tela_todas_linhas(self):
        self.linha_atual = None
        self.limpar_conteudo()
        area = self.criar_cabecalho("Todas as linhas", "Escolha uma linha para consultar seus detalhes")
        self.criar_botoes_superiores(area)

        lista = tk.Frame(area, bg="#eef2f6")
        lista.pack(fill="both", expand=True)

        for nome, linha in self.linhas.items():
            card = self.card(lista)
            card.pack(fill="x", pady=7)

            esquerda = tk.Frame(card, bg="white")
            esquerda.pack(side="left", fill="both", expand=True, padx=20, pady=17)
            tk.Label(esquerda, text=f"{linha['codigo']} • {nome}", font=("Segoe UI", 16, "bold"), fg="#172b40", bg="white").pack(anchor="w")
            tk.Label(esquerda, text=f"{len(linha['estacoes'])} estações • {linha['estacoes'][0]} → {linha['estacoes'][-1]}", font=("Segoe UI", 10), fg="#667587", bg="white").pack(anchor="w", pady=4)

            tk.Label(card, text=linha["status"], font=("Segoe UI", 10, "bold"), fg=self.status_cor(linha["status"]), bg="white").pack(side="left", padx=15)
            ttk.Button(card, text="Acessar", style="Metro.TButton", command=lambda n=nome: self.tela_linha(n)).pack(side="right", padx=20)

    def janela_estacoes(self, nome):
        linha = self.linhas[nome]
        janela = self.nova_janela("Estações", 600, 600)
        janela.configure(bg="#eef2f6")

        cabecalho = tk.Frame(janela, bg="#eef2f6")
        cabecalho.pack(fill="x", padx=30, pady=(20, 8))

        tk.Label(cabecalho, text=f"Estações • {nome}", font=("Segoe UI", 21, "bold"), bg="#eef2f6", fg="#172b40").pack(anchor="w")
        tk.Label(cabecalho, text=f"{len(linha['estacoes'])} estações na linha {linha['codigo']}", font=("Segoe UI", 10), bg="#eef2f6", fg="#667587").pack(anchor="w", pady=(4, 0))

        container = tk.Frame(janela, bg="#ffffff", bd=1, relief="solid", highlightthickness=1, highlightbackground="#d9e1ea")
        container.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        canvas = tk.Canvas(container, bg="#ffffff", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        lista = tk.Frame(canvas, bg="#ffffff")
        lista.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=lista, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for i, estacao in enumerate(linha["estacoes"], start=1):
            item = tk.Frame(lista, bg="#eef6ff" if i % 2 else "white", bd=1, relief="solid", highlightthickness=1, highlightbackground="#d9e1ea")
            item.pack(fill="x", pady=4)
            tk.Label(item, text=f"{i:02d}", width=5, font=("Segoe UI", 10, "bold"), bg="#eef6ff" if i % 2 else "white", fg="#1f5fa8").pack(side="left", padx=10, pady=11)
            tk.Label(item, text=estacao, font=("Segoe UI", 11, "bold"), bg="#eef6ff" if i % 2 else "white", fg="#172b40").pack(side="left", pady=11)
            if estacao in ("Recife", "Joana Bezerra"):
                tk.Label(item, text="CONEXÃO", font=("Segoe UI", 8, "bold"), bg="#102b4f", fg="#ffffff").pack(side="right", padx=12, pady=11)

    def janela_horarios(self, nome):
        linha = self.linhas[nome]
        janela = self.nova_janela("Horários", 720, 570)
        janela.configure(bg="#eef2f6")

        cabecalho = tk.Frame(janela, bg="#eef2f6")
        cabecalho.pack(fill="x", padx=30, pady=(20, 8))

        tk.Label(cabecalho, text=f"Horários • Linha {linha['codigo']}", font=("Segoe UI", 21, "bold"), bg="#eef2f6", fg="#172b40").pack(anchor="w")
        tk.Label(cabecalho, text=f"{len(linha['horarios'])} horários cadastrados", font=("Segoe UI", 10), bg="#eef2f6", fg="#667587").pack(anchor="w", pady=(4, 0))

        container = tk.Frame(janela, bg="#ffffff", bd=1, relief="solid", highlightthickness=1, highlightbackground="#d9e1ea")
        container.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        canvas = tk.Canvas(container, bg="#ffffff", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        lista = tk.Frame(canvas, bg="#ffffff")
        lista.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=lista, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        colunas = 5
        for i, horario in enumerate(linha["horarios"]):
            item = tk.Label(lista, text=horario, font=("Segoe UI", 11, "bold"), bg="#eff6ff", fg="#102b4f", width=12, pady=10, bd=1, relief="solid")
            item.grid(row=i // colunas, column=i % colunas, padx=7, pady=7)

    def mostrar_proximo(self, nome):
        linha = self.linhas[nome]
        horario, falta = proximo_horario(linha)
        if horario:
            messagebox.showinfo("Próximo metrô", f"Linha {linha['codigo']} • {nome}\n\nPróximo metrô: {horario}\nTempo: {minutos_para_texto(falta)}")
        else:
            messagebox.showinfo("Próximo metrô", f"Linha {linha['codigo']}\n\nNão há mais horários cadastrados para hoje.")

    def janela_status(self, nome):
        linha = self.linhas[nome]
        janela = self.nova_janela("Status da linha", 500, 360)
        janela.configure(bg="#eef2f6")

        card = tk.Frame(janela, bg="#ffffff", bd=1, relief="solid", highlightthickness=1, highlightbackground="#d9e1ea")
        card.pack(fill="both", expand=True, padx=30, pady=30)

        tk.Label(card, text="Status da linha", font=("Segoe UI", 21, "bold"), bg="#ffffff", fg="#172b40").pack(pady=(25, 8))
        tk.Label(card, text=f"{linha['codigo']} • {nome}", font=("Segoe UI", 12), bg="#ffffff", fg="#667587").pack()
        tk.Label(card, text=linha["status"], font=("Segoe UI", 15, "bold"), fg=self.status_cor(linha["status"]), bg="#ffffff").pack(pady=20)
        tk.Label(card, text=f"Intervalo médio: {linha['intervalo']} minutos", font=("Segoe UI", 11), bg="#ffffff", fg="#425466").pack(pady=(0, 25))

    def mostrar_tarifa(self, nome):
        linha = self.linhas[nome]
        messagebox.showinfo("Tarifa", f"Linha {linha['codigo']} • {nome}\n\nTarifa atual: {formatar_reais(linha['tarifa'])}")

    def janela_informacoes(self, nome):
        linha = self.linhas[nome]
        texto = (
            f"Linha: {nome}\n"
            f"Código: {linha['codigo']}\n"
            f"Estações: {len(linha['estacoes'])}\n"
            f"Horários: {len(linha['horarios'])}\n"
            f"Tarifa: {formatar_reais(linha['tarifa'])}\n"
            f"Intervalo médio: {linha['intervalo']} min\n"
            f"Status: {linha['status']}\n"
            f"Primeira estação: {linha['estacoes'][0]}\n"
            f"Última estação: {linha['estacoes'][-1]}"
        )
        messagebox.showinfo("Informações da linha", texto)

    def janela_busca_linha(self, nome):
        janela = self.nova_janela("Buscar estação", 560, 520)
        self.criar_busca(janela, lambda termo: [r for r in buscar_estacao(self.linhas, termo) if r["linha"] == nome])

    def abrir_google_maps_estacao(self, estacao):
        query = quote(f"Metrorec {estacao} Recife Pernambuco")
        webbrowser.open(f"https://www.google.com/maps/search/?api=1&query={query}")

    def tela_mapa_rede(self):
        self.linha_atual = None
        self.limpar_conteudo()
        area = self.criar_cabecalho("Mapa da Rede", "Mapa da rede METROREC com referência visual de Recife")
        self.criar_botoes_superiores(area)

        toolbar = tk.Frame(area, bg="#eef2f6")
        toolbar.pack(fill="x", pady=(4, 10))

        opcoes = ["Todas", "L1 – Jaboatão", "L2 – Camaragibe", "L3 – Sul"]
        for label in opcoes:
            ttk.Button(toolbar, text=label, style="Metro.TButton", command=lambda value=label: self.mostrar_mapa_filtrado(value)).pack(side="left", padx=4)

        controls = tk.Frame(area, bg="#eef2f6")
        controls.pack(fill="x", pady=(0, 8))
        ttk.Button(controls, text="+ Zoom", style="Metro.TButton", command=self.zoom_mapa_mais).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="− Zoom", style="Metro.TButton", command=self.zoom_mapa_menos).pack(side="left", padx=8)

        # Painel operacional compacto da simulação dos trens.
        # Mantém o mapa limpo e reduz a duplicação de botões de navegação.
        simulacao = tk.Frame(area, bg="#eef2f6")
        simulacao.pack(fill="x", pady=(0, 8))

        comandos = tk.Frame(simulacao, bg="#eef2f6")
        comandos.pack(side="left", fill="y")
        ttk.Button(comandos, text="▶ Iniciar", style="Metro.TButton", command=self.simulacao_iniciar).pack(side="left", padx=(0, 6))
        ttk.Button(comandos, text="⏸ Pausar", style="Metro.TButton", command=self.simulacao_pausar).pack(side="left", padx=6)
        ttk.Button(comandos, text="⏹ Parar", style="Metro.TButton", command=self.simulacao_parar).pack(side="left", padx=6)
        ttk.Button(comandos, text="↻ Reiniciar", style="Metro.TButton", command=self.simulacao_reiniciar).pack(side="left", padx=6)

        velocidade = tk.Frame(simulacao, bg="#eef2f6")
        velocidade.pack(side="right", fill="y")
        ttk.Label(velocidade, text="Velocidade:", font=("Segoe UI", 10, "bold"), background="#eef2f6").pack(side="left", padx=(10, 6))
        ttk.Button(velocidade, text="0.5x", style="Metro.TButton", command=lambda: self.simulacao_alterar_velocidade(0.5)).pack(side="left", padx=4)
        ttk.Button(velocidade, text="1x", style="Metro.TButton", command=lambda: self.simulacao_alterar_velocidade(1)).pack(side="left", padx=4)
        ttk.Button(velocidade, text="2x", style="Metro.TButton", command=lambda: self.simulacao_alterar_velocidade(2)).pack(side="left", padx=4)
        ttk.Button(velocidade, text="4x", style="Metro.TButton", command=lambda: self.simulacao_alterar_velocidade(4)).pack(side="left", padx=4)

        mapa_container = tk.Frame(area, bg="#eef2f6")
        mapa_container.pack(fill="both", expand=True)

        self.mapa_canvas = tk.Canvas(mapa_container, width=1000, height=550, bg="#f8fafc", highlightthickness=1, highlightbackground="#d9e1ea")
        self.mapa_canvas.configure(scrollregion=(0, 0, 1500, 760))
        self.mapa_canvas.configure(xscrollincrement=30, yscrollincrement=30)

        xbar = ttk.Scrollbar(mapa_container, orient="horizontal", command=self.mapa_canvas.xview)
        ybar = ttk.Scrollbar(mapa_container, orient="vertical", command=self.mapa_canvas.yview)
        self.mapa_canvas.configure(xscrollcommand=xbar.set, yscrollcommand=ybar.set)

        xbar.pack(side="bottom", fill="x")
        ybar.pack(side="right", fill="y")
        self.mapa_canvas.pack(side="left", fill="both", expand=True)

        self.mapa_zoom = 1.0
        self.mapa_filtro = "Todas"
        self.mapa_canvas.bind("<MouseWheel>", self.rolagem_mapa)
        self.mapa_canvas.bind("<ButtonPress-1>", self.iniciar_arraste_mapa)
        self.mapa_canvas.bind("<B1-Motion>", self.arrastar_mapa)

        # Exibe o mapa de Recife como base visual funcional e a rede METROREC por cima.
        self.desenhar_mapa_rede(self.mapa_canvas, filtro=self.mapa_filtro)

        legenda = tk.Frame(area, bg="#eef2f6")
        legenda.pack(fill="x", pady=(8, 0))
        tk.Label(legenda, text="● Estação", font=("Segoe UI", 10, "bold"), bg="#eef2f6", fg="#172b40").pack(side="left")
        tk.Label(legenda, text="━ L1 – Jaboatão", font=("Segoe UI", 10, "bold"), bg="#eef2f6", fg="#1f5fa8").pack(side="left", padx=(12, 8))
        tk.Label(legenda, text="━ L2 – Camaragibe", font=("Segoe UI", 10, "bold"), bg="#eef2f6", fg="#b96b1b").pack(side="left", padx=8)
        tk.Label(legenda, text="━ L3 – Sul", font=("Segoe UI", 10, "bold"), bg="#eef2f6", fg="#2c8c6f").pack(side="left", padx=8)

    def simulacao_iniciar(self):
        if hasattr(self, "simulacao"):
            self.simulacao.iniciar()
            self.simulacao_agendar_tick()
            self.desenhar_mapa_rede(self.mapa_canvas, filtro=self.mapa_filtro)

    def simulacao_pausar(self):
        if hasattr(self, "simulacao"):
            self.simulacao.pausar()
            self.simulacao_cancelar_tick()
            self.desenhar_mapa_rede(self.mapa_canvas, filtro=self.mapa_filtro)

    def simulacao_parar(self):
        if hasattr(self, "simulacao"):
            self.simulacao.parar()
            self.simulacao_cancelar_tick()
            self.desenhar_mapa_rede(self.mapa_canvas, filtro=self.mapa_filtro)

    def simulacao_reiniciar(self):
        if hasattr(self, "simulacao"):
            self.simulacao_cancelar_tick()
            self.simulacao.reiniciar()
            self.simulacao.iniciar()
            self.simulacao_agendar_tick()
            self.desenhar_mapa_rede(self.mapa_canvas, filtro=self.mapa_filtro)

    def simulacao_cancelar_tick(self):
        if hasattr(self, "simulacao_timer_id"):
            try:
                self.mapa_canvas.after_cancel(self.simulacao_timer_id)
            except Exception:
                pass
            self.simulacao_timer_id = None

    def simulacao_agendar_tick(self):
        self.simulacao_cancelar_tick()
        if not hasattr(self, "simulacao") or not hasattr(self, "mapa_canvas"):
            return
        if not self.simulacao.ativo or self.simulacao.paused or self.simulacao.parado:
            return
        delay = int(1000 / self.simulacao.velocidade)
        self.simulacao_timer_id = self.mapa_canvas.after(delay, self.simulacao_tick)

    def simulacao_tick(self):
        if not hasattr(self, "simulacao") or not hasattr(self, "mapa_canvas"):
            return
        if self.simulacao.ativo and not self.simulacao.paused and not self.simulacao.parado:
            self.simulacao.avancar()
            self.desenhar_mapa_rede(self.mapa_canvas, filtro=self.mapa_filtro)
            self.simulacao_agendar_tick()

    def simulacao_alterar_velocidade(self, valor):
        if hasattr(self, "simulacao"):
            self.simulacao.alterar_velocidade(valor)
            if self.simulacao.ativo and not self.simulacao.paused and not self.simulacao.parado:
                self.simulacao_agendar_tick()

    def rolagem_mapa(self, event):
        if not hasattr(self, "mapa_canvas"):
            return
        if event.delta > 0:
            self.zoom_mapa_mais()
        else:
            self.zoom_mapa_menos()

    def iniciar_arraste_mapa(self, event):
        if not hasattr(self, "mapa_canvas"):
            return
        self.mapa_canvas.scan_mark(event.x, event.y)

    def arrastar_mapa(self, event):
        if not hasattr(self, "mapa_canvas"):
            return
        self.mapa_canvas.scan_dragto(event.x, event.y, gain=1)

    def zoom_mapa_mais(self):
        if hasattr(self, "mapa_canvas"):
            self.mapa_zoom = min(self.mapa_zoom + 0.10, 1.60)
            self.redesenhar_mapa()

    def zoom_mapa_menos(self):
        if hasattr(self, "mapa_canvas"):
            self.mapa_zoom = max(self.mapa_zoom - 0.10, 0.80)
            self.redesenhar_mapa()

    def redesenhar_mapa(self):
        if hasattr(self, "mapa_canvas"):
            self.mapa_canvas.delete("all")
            filtro = getattr(self, "mapa_filtro", "Todas")
            self.desenhar_mapa_rede(self.mapa_canvas, filtro=filtro)

    def mostrar_mapa_filtrado(self, value):
        if not hasattr(self, "mapa_canvas"):
            return
        self.mapa_filtro = value
        self.mapa_canvas.delete("all")
        self.desenhar_mapa_rede(self.mapa_canvas, filtro=value)

    def desenhar_base_mapa_recife(self, canvas):
        """Cria uma base funcional visual de Recife, como fundo do mapa da rede."""
        canvas.create_rectangle(0, 0, 1500, 760, fill="#eef2f6", outline="#eef2f6")

        # área territorial principal
        canvas.create_rectangle(70, 70, 1420, 690, fill="#dce8ee", outline="#8ca3b7", width=1)

        # base da cidade com limites aproximados
        canvas.create_polygon(
            80, 120,
            180, 90,
            300, 120,
            390, 150,
            530, 120,
            700, 110,
            830, 140,
            980, 120,
            1180, 160,
            1320, 170,
            1400, 260,
            1370, 430,
            1400, 590,
            1280, 660,
            1010, 640,
            840, 680,
            640, 640,
            480, 650,
            270, 620,
            130, 620,
            80, 500,
            fill="#eef6f9",
            outline="#8fa8b7",
            width=2,
        )

        # rios/linha de água ou bairro de costa de Recife
        canvas.create_line(80, 500, 200, 460, 280, 420, 360, 460, 420, 480, 500, 460, fill="#a8c4d4", width=4, smooth=True)
        canvas.create_line(530, 120, 620, 170, 680, 180, 760, 220, 800, 260, fill="#a8c4d4", width=3, smooth=True)
        canvas.create_line(960, 120, 1010, 180, 1070, 220, 1120, 270, fill="#a8c4d4", width=3, smooth=True)

        # malha urbana - linhas de rua
        for x in range(100, 1400, 80):
            canvas.create_line(x, 80, x+40, 700, fill="#b9c9d8", dash=(2, 4), width=1)
        for y in range(100, 700, 70):
            canvas.create_line(80, y, 1420, y+30, fill="#b9c9d8", dash=(2, 4), width=1)

        # base cartográfica de Recife sem duplicar nomes de estações
        # mantém apenas a textura e a malha urbana como referência visual.

        # linha de limites geográficos e linhas de base
        canvas.create_line(70, 120, 1420, 680, fill="#8ca3b7", dash=(4, 2), width=1)

    def desenhar_mapa_rede(self, canvas, filtro="Todas"):
        canvas.delete("all")
        self.desenhar_base_mapa_recife(canvas)

        # Coordenadas organizadas em uma grade visual com padrão de rede e com
        # desenho espacial coerente para as estações reais do Recife.
        coordenadas = {
            "Camaragibe": (120, 120),
            "Cosme e Damião": (180, 160),
            "Rodoviária": (260, 180),
            "Curado": (340, 240),
            "Alto do Céu": (420, 280),
            "Coqueiral": (500, 320),
            "Tejipió": (560, 350),
            "Barro": (620, 390),
            "Werneck": (680, 420),
            "Santa Luzia": (750, 460),
            "Mangueira": (800, 500),
            "Ipiranga": (850, 530),
            "Afogados": (900, 560),
            "Joana Bezerra": (940, 590),
            "Recife": (1030, 620),
            "Jaboatão": (160, 680),
            "Engenho Velho": (260, 640),
            "Floriano": (340, 600),
            "Cavaleiro": (420, 560),
            "Cajueiro Seco": (180, 170),
            "Prazeres": (260, 230),
            "Monte dos Guararapes": (340, 280),
            "Porta Larga": (420, 330),
            "Aeroporto": (500, 380),
            "Tancredo Neves": (570, 420),
            "Shopping": (640, 480),
            "Antônio Falcão": (720, 530),
            "Imbiribeira": (780, 570),
            "Largo da Paz": (860, 610),
        }

        escala = getattr(self, "mapa_zoom", 1.0)
        coordenadas = {estacao: (x * escala, y * escala) for estacao, (x, y) in coordenadas.items()}

        # Compensa os nomes visíveis para a camada de texto não ficar empilhada.
        offsets = {
            "Camaragibe": (14, -14),
            "Cosme e Damião": (16, -14),
            "Rodoviária": (14, -14),
            "Curado": (16, -12),
            "Alto do Céu": (16, -14),
            "Coqueiral": (12, -12),
            "Tejipió": (12, -12),
            "Barro": (14, -14),
            "Werneck": (14, -14),
            "Santa Luzia": (14, -12),
            "Mangueira": (14, -12),
            "Ipiranga": (14, -12),
            "Afogados": (14, -12),
            "Joana Bezerra": (16, -12),
            "Recife": (14, -12),
            "Jaboatão": (14, -14),
            "Engenho Velho": (14, -12),
            "Floriano": (14, -12),
            "Cavaleiro": (14, -12),
            "Cajueiro Seco": (14, -12),
            "Prazeres": (14, -12),
            "Monte dos Guararapes": (14, -12),
            "Porta Larga": (14, -12),
            "Aeroporto": (14, -12),
            "Tancredo Neves": (14, -12),
            "Shopping": (14, -12),
            "Antônio Falcão": (14, -12),
            "Imbiribeira": (14, -12),
            "Largo da Paz": (14, -12),
        }

        # Ajustando a divisão cartográfica para parecer mapa real de RJ/Recife.
        linhas = {
            "L1 – Jaboatão": {
                "color": "#d81010",
                "estacoes": [
                    "Jaboatão", "Engenho Velho", "Floriano", "Cavaleiro", "Coqueiral",
                    "Tejipió", "Barro", "Werneck", "Santa Luzia", "Mangueira",
                    "Ipiranga", "Afogados", "Joana Bezerra", "Recife"
                ],
            },
            "L2 – Camaragibe": {
                "color": "#e67f18",
                "estacoes": [
                    "Camaragibe", "Cosme e Damião", "Rodoviária", "Curado", "Alto do Céu",
                    "Coqueiral", "Tejipió", "Barro", "Werneck", "Santa Luzia",
                    "Mangueira", "Ipiranga", "Afogados", "Joana Bezerra", "Recife"
                ],
            },
            "L3 – Sul": {
                "color": "#0b1aec",
                "estacoes": [
                    "Cajueiro Seco", "Prazeres", "Monte dos Guararapes", "Porta Larga",
                    "Aeroporto", "Tancredo Neves", "Shopping", "Antônio Falcão",
                    "Imbiribeira", "Largo da Paz", "Joana Bezerra", "Recife"
                ],
            },
        }

        for nome_linha, linha in linhas.items():
            if filtro != "Todas" and filtro != nome_linha:
                continue

            color = linha["color"]
            estacoes = linha["estacoes"]
            for i in range(len(estacoes) - 1):
                origem = estacoes[i]
                destino = estacoes[i + 1]
                x1, y1 = coordenadas[origem]
                x2, y2 = coordenadas[destino]
                canvas.create_line(x1, y1, x2, y2, fill=color, width=5, capstyle="round", smooth=True)

        # Rótulos únicos por estação e deslocados para fora do ponto.
        desenhadas = set()
        for nome_linha, linha in linhas.items():
            if filtro != "Todas" and filtro != nome_linha:
                continue
            color = linha["color"]
            for estacao in linha["estacoes"]:
                if estacao in desenhadas:
                    continue
                if estacao not in coordenadas:
                    continue
                x, y = coordenadas[estacao]
                r = 6
                item = canvas.create_oval(x-r, y-r, x+r, y+r, fill="white", outline=color, width=3)
                dx, dy = offsets.get(estacao, (12, -8))
                canvas.create_text(x+dx, y+dy, text=estacao, anchor="w", font=("Segoe UI", 8, "bold"), fill="#172b40")
                canvas.tag_bind(item, "<Enter>", lambda e, est=estacao, l=nome_linha: self.destaque_estacao(e, est, l))
                canvas.tag_bind(item, "<Leave>", lambda e, est=estacao: self.remover_destaque(e, est))
                canvas.tag_bind(item, "<Button-1>", lambda e, est=estacao, l=nome_linha: self.abrir_painel_estacao(e, est, l))
                desenhadas.add(estacao)

        # ressalta a interseção no centro da cidade com o desenho entre linhas.
        # Esses pontos precisam receber o mesmo bind de clique do restante das estações
        # para abrir o painel com as ações de estação e o link para o Google Maps.
        for estacao in ["Joana Bezerra", "Recife"]:
            x, y = coordenadas[estacao]
            item = canvas.create_oval(x-13, y-13, x+13, y+13, fill="#071b2f", outline="#ffffff", width=3)
            canvas.tag_bind(item, "<Button-1>", lambda e, est=estacao: self.abrir_painel_estacao(e, est, None))

        # Renderização dos trens na simulação, usando os mesmos nomes de estação do mapa.
        if hasattr(self, "simulacao"):
            for trem in self.simulacao.trens:
                if trem.linha == "Jaboatão":
                    x, y = coordenadas[trem.estacao_atual]
                    tag = canvas.create_text(x + 24, y - 12, text="🚇", font=("Segoe UI Emoji", 14), fill="#d81010")
                    canvas.create_text(x + 30, y + 16, text=f"T01", font=("Segoe UI", 7, "bold"), fill="#172b40")
                elif trem.linha == "Camaragibe":
                    x, y = coordenadas[trem.estacao_atual]
                    tag = canvas.create_text(x + 24, y - 12, text="🚇", font=("Segoe UI Emoji", 14), fill="#e67f18")
                    canvas.create_text(x + 30, y + 16, text=f"T02", font=("Segoe UI", 7, "bold"), fill="#172b40")
                elif trem.linha == "Sul":
                    x, y = coordenadas[trem.estacao_atual]
                    tag = canvas.create_text(x + 24, y - 12, text="🚇", font=("Segoe UI Emoji", 14), fill="#0b1aec")
                    canvas.create_text(x + 30, y + 16, text=f"T03", font=("Segoe UI", 7, "bold"), fill="#172b40")

        canvas.create_text(50, 30, text="Mapa da Rede METROREC", anchor="w", font=("Segoe UI", 16, "bold"), fill="#172b40")

        # Painel textual de trens na própria tela do mapa.
        if hasattr(self, "simulacao"):
            painel = tk.Frame(canvas.master, bg="#eef2f6")
            # O painel é desenhado apenas com contexto textual, ligado ao motor de simulação.
            # Isso evita aumentar a complexidade de uso com widgets a mais no canvas.

        # A simulação só precisa alimentar o painel de texto em memória e pode ser expandida depois.

    def destaque_estacao(self, event, estacao, linha):
        pass

    def remover_destaque(self, event, estacao):
        pass

    def abrir_painel_estacao(self, event, estacao, linha_nome=None):
        self.abrir_info_estacao(estacao, linha_nome)

    def abrir_info_estacao(self, estacao, linha_nome=None):
        linhas_na_estacao = [nome for nome, l in self.linhas.items() if estacao in l["estacoes"]]
        if not linhas_na_estacao:
            messagebox.showwarning("Atenção", f"A estação {estacao} não está cadastrada na rede.")
            return

        nomes_linhas = {
            "L1 – Jaboatão": "Jaboatão",
            "L2 – Camaragibe": "Camaragibe",
            "L3 – Sul": "Sul",
        }
        nome_linha = None
        linha = None

        if linha_nome:
            nome_linha = nomes_linhas.get(linha_nome, linha_nome)
            if nome_linha in self.linhas:
                linha = self.linhas[nome_linha]

        if linha is None:
            nome_linha = linhas_na_estacao[0]
            linha = self.linhas[nome_linha]

        proxima = None
        estacoes_linha = linha["estacoes"]
        if estacao in estacoes_linha:
            idx = estacoes_linha.index(estacao)
            if idx + 1 < len(estacoes_linha):
                proxima = estacoes_linha[idx + 1]
            else:
                proxima = "Fim de linha"
        else:
            proxima = "Estação fora da linha selecionada"

        painel = tk.Toplevel(self.root)
        painel.title(f"Estação • {estacao}")
        painel.geometry("440x300")
        painel.configure(bg="#eef2f6")
        painel.transient(self.root)
        painel.grab_set()

        topo = tk.Frame(painel, bg="#071b2f")
        topo.pack(fill="x")
        tk.Label(topo, text=estacao, font=("Segoe UI", 18, "bold"), bg="#071b2f", fg="#ffffff").pack(anchor="w", padx=16, pady=10)

        info = tk.Frame(painel, bg="#eef2f6")
        info.pack(fill="both", expand=True, padx=16, pady=10)

        tk.Label(info, text=f"Linha: {nome_linha}", font=("Segoe UI", 10), bg="#eef2f6", fg="#172b40").pack(anchor="w")
        tk.Label(info, text=f"Status: {linha['status']}", font=("Segoe UI", 10), bg="#eef2f6", fg="#172b40").pack(anchor="w")
        tk.Label(info, text=f"Próxima estação: {proxima}", font=("Segoe UI", 10), bg="#eef2f6", fg="#172b40").pack(anchor="w")
        tk.Label(info, text=f"Linhas disponíveis: {', '.join(linhas_na_estacao)}", font=("Segoe UI", 10), bg="#eef2f6", fg="#172b40").pack(anchor="w")

        botoes = tk.Frame(painel, bg="#eef2f6")
        botoes.pack(fill="x", padx=16, pady=(0, 16))
        ttk.Button(botoes, text="Ver no Google Maps", style="Metro.TButton", command=lambda: self.abrir_google_maps_estacao(estacao)).pack(side="left", padx=(0, 8))
        ttk.Button(botoes, text="Planejar viagem", style="Metro.TButton", command=lambda: (painel.destroy(), self.janela_planejamento(None))).pack(side="left")

    def janela_busca_global(self):
        janela = self.nova_janela("Buscar estação", 620, 560)
        self.criar_busca(janela, lambda termo: buscar_estacao(self.linhas, termo))

    def criar_busca(self, janela, funcao):
        tk.Label(janela, text="Buscar estação", font=("Segoe UI", 21, "bold"), bg="#eef2f6", fg="#172b40").pack(pady=(25, 5))
        tk.Label(janela, text="Digite parte do nome da estação", font=("Segoe UI", 10), bg="#eef2f6", fg="#667587").pack()

        entrada = ttk.Entry(janela, style="Metro.TEntry")
        entrada.pack(fill="x", padx=40, pady=15)
        entrada.focus()

        resultados = tk.Frame(janela, bg="#eef2f6")
        resultados.pack(fill="both", expand=True, padx=40, pady=10)

        def pesquisar():
            for widget in resultados.winfo_children():
                widget.destroy()

            termo = entrada.get().strip()
            if not termo:
                messagebox.showwarning("Atenção", "Digite o nome de uma estação.")
                return

            encontrados = funcao(termo)
            if not encontrados:
                tk.Label(resultados, text="Nenhuma estação encontrada.", font=("Segoe UI", 11), bg="#eef2f6", fg="#667587").pack(pady=20)
                return

            for resultado in encontrados:
                item = self.card(resultados)
                item.pack(fill="x", pady=4)
                item.configure(bg="#ffffff", highlightbackground="#d9e1ea", bd=1, relief="solid")
                tk.Label(item, text=resultado["estacao"], font=("Segoe UI", 12, "bold"), bg="white", fg="#172b40").pack(side="left", padx=15, pady=12)
                tk.Label(item, text=f"{resultado['codigo']} • {resultado['linha']} • posição {resultado['posicao']}", font=("Segoe UI", 9), bg="white", fg="#667587").pack(side="right", padx=15)

        ttk.Button(janela, text="Pesquisar", style="Metro.TButton", command=pesquisar).pack(fill="x", padx=40, pady=(0, 20))
        entrada.bind("<Return>", lambda event: pesquisar())

    def janela_planejamento_global(self):
        self.janela_planejamento(None)

    def janela_planejamento(self, nome_linha=None):
        janela = self.nova_janela("Planejar viagem", 700, 650)
        janela.configure(bg="#eef2f6")

        # Cabeçalho visual profissional da janela
        cabecalho = tk.Frame(janela, bg="#eef2f6")
        cabecalho.pack(fill="x", padx=30, pady=(20, 10))

        tk.Label(cabecalho, text="Planejar viagem", font=("Segoe UI", 22, "bold"), bg="#eef2f6", fg="#172b40").pack(anchor="w")
        tk.Label(cabecalho, text="Escolha a origem e o destino para calcular a rota", font=("Segoe UI", 10), bg="#eef2f6", fg="#667587").pack(anchor="w", pady=(4, 0))

        # Formulário com visual mais organizado
        campos = tk.Frame(janela, bg="#ffffff", bd=1, relief="solid", highlightthickness=1, highlightbackground="#d9e1ea")
        campos.pack(fill="both", expand=True, padx=30, pady=(0, 12))

        campos_inner = tk.Frame(campos, bg="#ffffff")
        campos_inner.pack(fill="both", expand=True, padx=24, pady=20)

        todas_estacoes = []
        for linha in self.linhas.values():
            for estacao in linha["estacoes"]:
                if estacao not in todas_estacoes:
                    todas_estacoes.append(estacao)

        tk.Label(campos_inner, text="Origem", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#172b40").pack(anchor="w")
        origem = ttk.Combobox(campos_inner, values=todas_estacoes, state="readonly", style="Metro.TCombobox")
        origem.pack(fill="x", pady=(5, 15))

        tk.Label(campos_inner, text="Destino", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#172b40").pack(anchor="w")
        destino = ttk.Combobox(campos_inner, values=todas_estacoes, state="readonly", style="Metro.TCombobox")
        destino.pack(fill="x", pady=(5, 15))

        linha_var = tk.StringVar(value=nome_linha or "Todas as linhas")
        if nome_linha:
            tk.Label(campos_inner, text=f"Linha atual: {nome_linha}", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#172b40").pack(anchor="w", pady=(0, 10))
        else:
            tk.Label(campos_inner, text="Priorizar linha", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg="#172b40").pack(anchor="w")
            seletor = ttk.Combobox(campos_inner, values=["Todas as linhas"] + list(self.linhas.keys()), textvariable=linha_var, state="readonly", style="Metro.TCombobox")
            seletor.pack(fill="x", pady=(5, 12))

        # Botão principal mais visível e posicionado com o restante do formulário
        botoes = tk.Frame(janela, bg="#eef2f6")
        botoes.pack(fill="x", padx=30, pady=(0, 14))

        # Área de resultado com fundo branco e borda marcada
        resultado = tk.Text(janela, height=10, font=("Segoe UI", 10), bg="#ffffff", fg="#172b40", bd=1, relief="solid", padx=12, pady=12, wrap="word")
        resultado.pack(fill="both", expand=True, padx=30)
        resultado.config(state="disabled")

        def mostrar(texto):
            resultado.config(state="normal")
            resultado.delete("1.0", "end")
            resultado.insert("1.0", texto)
            resultado.config(state="disabled")

        def calcular():
            origem_valor = origem.get()
            destino_valor = destino.get()

            if not origem_valor or not destino_valor:
                messagebox.showwarning("Atenção", "Selecione a origem e o destino.")
                return

            if origem_valor == destino_valor:
                messagebox.showwarning("Atenção", "Origem e destino não podem ser iguais.")
                return

            nome_escolhido = linha_var.get()
            rota = None

            if nome_escolhido != "Todas as linhas":
                linha = self.linhas[nome_escolhido]
                resultado_linha = calcular_rota_na_linha(linha, origem_valor, destino_valor)
                if resultado_linha:
                    resultado_linha["linha"] = nome_escolhido
                rota = resultado_linha
            else:
                rota = montar_rota_integrada(self.linhas, origem_valor, destino_valor)

            if not rota:
                mostrar("Não foi possível encontrar uma rota com os dados cadastrados.")
                return

            caminho = " → ".join(rota["rota"])
            texto = (
                f"ORIGEM: {origem_valor}\n"
                f"DESTINO: {destino_valor}\n\n"
                f"LINHA: {rota['linha']}\n"
                f"ESTAÇÕES PERCORRIDAS: {rota['estacoes']}\n"
                f"TEMPO ESTIMADO: {rota['tempo']} minutos\n"
                f"TARIFA: {formatar_reais(rota['tarifa'])}\n"
            )

            if rota.get("trocas"):
                texto += f"INTEGRAÇÃO: 1 troca em {rota.get('conexao', 'estação de conexão')}\n"

            texto += f"\nROTA:\n{caminho}"
            mostrar(texto)

        ttk.Button(botoes, text="Calcular viagem", style="Metro.TButton", command=calcular).pack(fill="x", pady=(0, 6))

    def tela_admin(self):
        self.linha_atual = None
        self.limpar_conteudo()
        area = self.criar_cabecalho("Controle do sistema", "Área acadêmica para simular alterações durante a execução")
        self.criar_botoes_superiores(area)

        card = self.card(area)
        card.pack(fill="both", expand=True)

        tk.Label(card, text="Alterar informações da linha", font=("Segoe UI", 16, "bold"), bg="white", fg="#172b40").pack(anchor="w", padx=25, pady=(25, 5))
        tk.Label(card, text="As alterações ficam apenas enquanto o programa estiver aberto.", font=("Segoe UI", 10), bg="white", fg="#667587").pack(anchor="w", padx=25, pady=(0, 20))

        formulario = tk.Frame(card, bg="white")
        formulario.pack(fill="x", padx=25)

        tk.Label(formulario, text="Linha", font=("Segoe UI", 10, "bold"), bg="white", fg="#172b40").grid(row=0, column=0, sticky="w", pady=6)
        linha_var = tk.StringVar(value=list(self.linhas.keys())[0])
        linha_combo = ttk.Combobox(formulario, values=list(self.linhas.keys()), textvariable=linha_var, state="readonly", style="Metro.TCombobox")
        linha_combo.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(0, 15))

        tk.Label(formulario, text="Status", font=("Segoe UI", 10, "bold"), bg="white", fg="#172b40").grid(row=0, column=1, sticky="w", pady=6)
        status_var = tk.StringVar()
        status_combo = ttk.Combobox(formulario, values=STATUS_DISPONIVEIS, textvariable=status_var, state="readonly", style="Metro.TCombobox")
        status_combo.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(0, 15))

        tk.Label(formulario, text="Tarifa", font=("Segoe UI", 10, "bold"), bg="white", fg="#172b40").grid(row=2, column=0, sticky="w", pady=6)
        tarifa_var = tk.StringVar()
        tarifa_entry = ttk.Entry(formulario, textvariable=tarifa_var, style="Metro.TEntry")
        tarifa_entry.grid(row=3, column=0, sticky="ew", padx=(0, 10), pady=(0, 15))

        tk.Label(formulario, text="Intervalo médio (min)", font=("Segoe UI", 10, "bold"), bg="white", fg="#172b40").grid(row=2, column=1, sticky="w", pady=6)
        intervalo_var = tk.StringVar()
        intervalo_entry = ttk.Entry(formulario, textvariable=intervalo_var, style="Metro.TEntry")
        intervalo_entry.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=(0, 15))

        formulario.columnconfigure(0, weight=1)
        formulario.columnconfigure(1, weight=1)

        horarios_frame = tk.Frame(card, bg="white")
        horarios_frame.pack(fill="both", expand=True, padx=25, pady=10)
        tk.Label(horarios_frame, text="Horários cadastrados", font=("Segoe UI", 11, "bold"), bg="white", fg="#172b40").pack(anchor="w")
        horarios_entry = tk.Text(horarios_frame, height=8, font=("Segoe UI", 10), bg="#f7f9fb", bd=1, relief="solid")
        horarios_entry.pack(fill="both", expand=True, pady=7)

        def carregar():
            linha = self.linhas[linha_var.get()]
            status_var.set(linha["status"])
            tarifa_var.set(str(linha["tarifa"]))
            intervalo_var.set(str(linha["intervalo"]))
            horarios_entry.delete("1.0", "end")
            horarios_entry.insert("1.0", ", ".join(linha["horarios"]))

        def salvar():
            linha = self.linhas[linha_var.get()]
            try:
                tarifa = float(tarifa_var.get().replace(",", "."))
                intervalo = int(intervalo_var.get())
            except ValueError:
                messagebox.showerror("Erro", "Tarifa e intervalo precisam ser numéricos.")
                return

            horarios = [h.strip() for h in horarios_entry.get("1.0", "end").split(",") if h.strip()]
            for h in horarios:
                try:
                    hora, minuto = map(int, h.split(":"))
                    if not (0 <= hora <= 23 and 0 <= minuto <= 59):
                        raise ValueError
                except ValueError:
                    messagebox.showerror("Erro", f"Horário inválido: {h}")
                    return

            if tarifa <= 0 or intervalo <= 0:
                messagebox.showwarning("Atenção", "Tarifa e intervalo devem ser maiores que zero.")
                return

            linha["status"] = status_var.get()
            linha["tarifa"] = tarifa
            linha["intervalo"] = intervalo
            linha["horarios"] = horarios
            messagebox.showinfo("Sucesso", "Informações atualizadas com sucesso.")

        linha_combo.bind("<<ComboboxSelected>>", lambda event: carregar())
        botoes = tk.Frame(card, bg="white")
        botoes.pack(fill="x", padx=25, pady=(3, 25))
        ttk.Button(botoes, text="Carregar dados", style="Metro.TButton", command=carregar).pack(side="left")
        ttk.Button(botoes, text="Salvar alterações", style="Metro.TButton", command=salvar).pack(side="left", padx=8)
        ttk.Button(botoes, text="Voltar", style="Metro.TButton", command=self.tela_inicial).pack(side="right")

        carregar()

    def nova_janela(self, titulo, largura, altura):
        janela = tk.Toplevel(self.root)
        janela.title(f"METROREC - {titulo}")
        janela.geometry(f"{largura}x{altura}")
        janela.minsize(max(450, largura - 80), max(350, altura - 100))
        janela.configure(bg="#eef2f6")
        janela.transient(self.root)
        janela.grab_set()
        return janela
