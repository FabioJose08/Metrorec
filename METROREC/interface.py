import os
import math
import tkinter as tk
import webbrowser
from urllib.parse import quote
from tkinter import ttk, messagebox
import tkintermapview

from dados import LINHAS, STATUS_DISPONIVEIS
from simulacao import SimulacaoTrens
from viagens import calcular_rota_na_linha, montar_rota_integrada, proximo_horario
from utilitarios import formatar_reais, horario_atual, data_atual, minutos_para_texto


# Paleta de Cores do Sistema
C = {
    "fundo": "#F4F6F9",
    "topo": "#0F172A",
    "texto": "#1E293B",
    "sec": "#64748B",
    "card": "#FFFFFF",
    "borda": "#E2E8F0",
    "botao": "#0F172A",
    "hover": "#1E293B",
    "verde": "#10B981",
    "amarelo": "#F59E0B",
    "laranja": "#F97316",
    "vermelho": "#EF4444",
}

# Cores das Linhas do Metrorec
CORES_LINHAS = {
    "Jaboatão": "#DC2626",    # Vermelho
    "Camaragibe": "#EA580C",  # Laranja
    "Sul": "#2563EB"          # Azul
}

# Coordenadas Reais de Latitude e Longitude de Cada Estação
COORDENADAS_ESTACOES = {
    # Linha Camaragibe
    "Camaragibe": (-8.0211, -34.9818),
    "Cosme e Damião": (-8.0322, -34.9669),
    "Rodoviária": (-8.0428, -34.9582),
    "Curado": (-8.0673, -34.9721),
    "Alto do Céu": (-8.0776, -34.9625),
    "Coqueiral": (-8.0837, -34.9542),

    # Linha Jaboatão
    "Jaboatão": (-8.1132, -35.0152),
    "Engenho Velho": (-8.1068, -35.0035),
    "Floriano": (-8.1009, -34.9904),
    "Cavaleiro": (-8.0932, -34.9687),

    # Tronco Comum (Centro)
    "Tejipió": (-8.0858, -34.9458),
    "Barro": (-8.0812, -34.9351),
    "Werneck": (-8.0782, -34.9221),
    "Santa Luzia": (-8.0772, -34.9123),
    "Mangueira": (-8.0771, -34.9031),
    "Ipiranga": (-8.0768, -34.8953),
    "Afogados": (-8.0735, -34.8872),
    "Joana Bezerra": (-8.0701, -34.8805),
    "Recife": (-8.0671, -34.8722),

    # Linha Sul
    "Largo da Paz": (-8.0815, -34.8885),
    "Imbiribeira": (-8.0941, -34.8942),
    "Antônio Falcão": (-8.1022, -34.8988),
    "Shopping": (-8.1132, -34.9035),
    "Tancredo Neves": (-8.1221, -34.9068),
    "Aeroporto": (-8.1332, -34.9112),
    "Porta Larga": (-8.1435, -34.9162),
    "Monte dos Guararapes": (-8.1541, -34.9198),
    "Prazeres": (-8.1638, -34.9232),
    "Cajueiro Seco": (-8.1752, -34.9281)
}


class MetroRecApp:
    def __init__(self, root):
        self.root = root
        self.linhas = LINHAS
        self.linha_atual = None
        self.topo = self.conteudo = None
        
        # Atributos do Mapa Real
        self.map_widget = None
        self.marcadores_trens = {}
        self.simulacao_timer_id = None
        self.simulacao = SimulacaoTrens(self.linhas)
        self.anim_step = 0.0

        self._janela()
        self._estilos()
        self.tela_inicial()

    def _janela(self):
        self.root.title("METROREC - Sistema de Mobilidade Integrado")
        self.root.geometry("1280x820")
        self.root.minsize(1024, 700)
        self.root.configure(bg=C["fundo"])

    def _estilos(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Metro.TButton", font=("Segoe UI", 10, "bold"), padding=(16, 9),
                    foreground="white", background=C["botao"], borderwidth=0)
        s.map("Metro.TButton", background=[("active", C["hover"])])
        s.configure("Metro.Nav.TButton", font=("Segoe UI", 9, "bold"), padding=(12, 7),
                    foreground="#334155", background="#E2E8F0")
        s.map("Metro.Nav.TButton", background=[("active", "#CBD5E1")])

    def _limpar(self):
        self._cancelar_simulacao()
        for widget in (self.topo, self.conteudo):
            if widget and widget.winfo_exists():
                widget.destroy()
        self.topo = self.conteudo = None

    def _label(self, parent, texto="", tam=10, cor=None, peso=None, bg=None, **kw):
        return tk.Label(parent, text=texto, font=("Segoe UI", tam, peso) if peso else ("Segoe UI", tam),
                        fg=cor or C["texto"], bg=bg if bg is not None else parent.cget("bg"), **kw)

    def _card(self, parent, **kw):
        return tk.Frame(parent, bg=C["card"], bd=1, relief="solid",
                        highlightthickness=0, highlightbackground=C["borda"], **kw)

    def _botao(self, parent, texto, comando, estilo="Metro.TButton", **kw):
        return ttk.Button(parent, text=texto, command=comando, style=estilo, **kw)

    def _cabecalho(self, titulo, subtitulo=""):
        self._limpar()
        self.topo = tk.Frame(self.root, bg=C["topo"], height=80)
        self.topo.pack(fill="x")
        self.topo.pack_propagate(False)
        
        esquerda = tk.Frame(self.topo, bg=C["topo"])
        esquerda.pack(side="left", padx=28, fill="y")
        self._label(esquerda, "🚇 METROREC", 16, "white", "bold", C["topo"]).pack(anchor="w", pady=(14, 0))
        self._label(esquerda, titulo, 9, "#94A3B8", bg=C["topo"]).pack(anchor="w")
        
        relogio = self._label(self.topo, "", 13, "#F1F5F9", "bold", C["topo"])
        relogio.pack(side="right", padx=28)

        def atualizar():
            if relogio.winfo_exists():
                relogio.config(text=f"{horario_atual()}  •  {data_atual()}")
                relogio.after(1000, atualizar)
        atualizar()

        self.conteudo = tk.Frame(self.root, bg=C["fundo"])
        self.conteudo.pack(fill="both", expand=True)
        area = tk.Frame(self.conteudo, bg=C["fundo"])
        area.pack(fill="both", expand=True, padx=32, pady=24)
        
        if subtitulo:
            self._label(area, subtitulo, 11, C["sec"], bg=C["fundo"]).pack(anchor="w", pady=(0, 16))
        return area

    def _nav(self, parent):
        barra = tk.Frame(parent, bg=C["fundo"])
        barra.pack(fill="x", pady=(0, 16))
        botoes = [
            ("Início", self.tela_inicial),
            ("Mapa Real Interativo", self.tela_mapa_rede),
            ("Dashboard", self.tela_dashboard),
            ("Linhas", self.tela_todas_linhas),
            ("Planejar Rota", self.janela_planejamento_global)
        ]
        for texto, comando in botoes:
            self._botao(barra, texto, comando, "Metro.Nav.TButton").pack(side="left", padx=(0, 6))

    def _janela_nova(self, titulo, largura, altura):
        w = tk.Toplevel(self.root)
        w.title(f"METROREC - {titulo}")
        w.geometry(f"{largura}x{altura}")
        w.minsize(400, 300)
        w.configure(bg=C["fundo"])
        w.transient(self.root)
        w.grab_set()
        return w

    def _campo(self, parent, rotulo, valores, variavel=None):
        self._label(parent, rotulo, 10, C["texto"], "bold", "white").pack(anchor="w")
        combo = ttk.Combobox(parent, values=valores, textvariable=variavel, state="readonly")
        combo.pack(fill="x", pady=(4, 12))
        return combo

    def _area_rolavel(self, parent):
        box = tk.Frame(parent, bg="white", bd=1, relief="solid", highlightbackground=C["borda"])
        canvas = tk.Canvas(box, bg="white", highlightthickness=0)
        barra = ttk.Scrollbar(box, orient="vertical", command=canvas.yview)
        area = tk.Frame(canvas, bg="white")
        area.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=area, anchor="nw")
        canvas.configure(yscrollcommand=barra.set)
        canvas.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        return box, area

    def status_cor(self, status):
        return {
            "Operação normal": C["verde"],
            "Atenção": C["amarelo"],
            "Operação reduzida": C["laranja"],
            "Interrompida": C["vermelho"]
        }.get(status, C["sec"])

    def todas_estacoes(self):
        return sorted({e for l in self.linhas.values() for e in l["estacoes"]})

    def tela_inicial(self):
        self.linha_atual = None
        area = self._cabecalho("Painel Geral", "Selecione uma linha ou acompanhe o mapa da rede")
        self._nav(area)

        cards = tk.Frame(area, bg=C["fundo"])
        cards.pack(fill="x", pady=8)

        for nome, linha in self.linhas.items():
            card = self._card(cards, width=320, height=220)
            card.pack(side="left", fill="both", expand=True, padx=6)
            card.pack_propagate(False)
            
            tk.Frame(card, bg=CORES_LINHAS.get(nome, C["botao"]), height=6).pack(fill="x")
            self._label(card, linha["codigo"], 10, C["sec"], "bold", "white").pack(anchor="w", padx=20, pady=(16, 0))
            self._label(card, f"Linha {nome}", 18, C["texto"], "bold", "white").pack(anchor="w", padx=20)
            self._label(card, linha["status"], 10, self.status_cor(linha["status"]), "bold", "white").pack(anchor="w", padx=20, pady=(4, 2))
            self._label(card, f"{len(linha['estacoes'])} Estações  •  {formatar_reais(linha['tarifa'])}", 9, C["sec"], bg="white").pack(anchor="w", padx=20)
            self._botao(card, "Detalhes da Linha", lambda n=nome: self.tela_linha(n)).pack(fill="x", padx=20, pady=(16, 0))

        rodape = tk.Frame(area, bg=C["fundo"])
        rodape.pack(fill="x", pady=24)
        self._botao(rodape, "⚙ Painel de Administração", self.tela_admin).pack(side="right")

    def tela_linha(self, nome):
        self.linha_atual = nome
        linha = self.linhas[nome]
        area = self._cabecalho(
            f"{linha['codigo']} • Linha {nome}",
            f"Status: {linha['status']}  |  Tarifa: {formatar_reais(linha['tarifa'])}  |  Intervalo: {linha['intervalo']} min"
        )
        self._nav(area)
        
        grid = tk.Frame(area, bg=C["fundo"])
        grid.pack(fill="both", expand=True)
        for col in range(4):
            grid.columnconfigure(col, weight=1)
            
        opcoes = [
            ("🗺", "Ver no Mapa Real", self.tela_mapa_rede),
            ("🧭", "Planejar Rota", lambda: self.janela_planejamento(nome)),
            ("📍", "Lista de Estações", lambda: self.janela_estacoes(nome)),
            ("🕐", "Quadro de Horários", lambda: self.janela_horarios(nome)),
            ("🚇", "Próxima Partida", lambda: self.mostrar_proximo(nome)),
            ("⚠", "Status Operacional", lambda: self.janela_status(nome)),
            ("ℹ", "Informações Gerais", lambda: self.janela_informacoes(nome))
        ]
        
        for i, (icone, titulo, comando) in enumerate(opcoes):
            card = self._card(grid)
            card.grid(row=i // 4, column=i % 4, sticky="nsew", padx=6, pady=6)
            self._label(card, icone, 24, bg="white").pack(pady=(20, 6))
            self._label(card, titulo, 11, C["texto"], "bold", "white").pack()
            self._botao(card, "Acessar", comando).pack(fill="x", padx=20, pady=16)

    def tela_dashboard(self):
        area = self._cabecalho("Dashboard Operacional", "Indicadores da Região Metropolitana do Recife")
        self._nav(area)
        
        total = sum(len(l["estacoes"]) for l in self.linhas.values())
        normais = sum(l["status"] == "Operação normal" for l in self.linhas.values())
        
        cards = tk.Frame(area, bg=C["fundo"])
        cards.pack(fill="x", pady=8)
        
        indicadores = [
            ("Linhas Ativas", len(self.linhas), "Metrorec"),
            ("Estações Totais", total, "Com integrações"),
            ("Operação Normal", normais, "Linhas regulares"),
            ("Alertas Operacionais", len(self.linhas) - normais, "Atenção necessária")
        ]
        
        for titulo, valor, detalhe in indicadores:
            card = self._card(cards)
            card.pack(side="left", fill="both", expand=True, padx=5)
            self._label(card, titulo, 10, C["sec"], "bold", "white").pack(anchor="w", padx=16, pady=(14, 0))
            self._label(card, str(valor), 22, C["texto"], "bold", "white").pack(anchor="w", padx=16)
            self._label(card, detalhe, 9, C["sec"], bg="white").pack(anchor="w", padx=16, pady=(0, 14))

    def tela_todas_linhas(self):
        area = self._cabecalho("Linhas da Rede", "Itinerários do Metrorec")
        self._nav(area)
        
        for nome, linha in self.linhas.items():
            card = self._card(area)
            card.pack(fill="x", pady=6)
            
            esq = tk.Frame(card, bg="white")
            esq.pack(side="left", fill="both", expand=True, padx=16, pady=14)
            
            self._label(esq, f"{linha['codigo']} • Linha {nome}", 14, C["texto"], "bold", "white").pack(anchor="w")
            self._label(esq, f"{len(linha['estacoes'])} Estações  |  Terminal: {linha['estacoes'][0]} ↔ {linha['estacoes'][-1]}", 10, C["sec"], bg="white").pack(anchor="w", pady=2)
            
            self._label(card, linha["status"], 10, self.status_cor(linha["status"]), "bold", "white").pack(side="left", padx=16)
            self._botao(card, "Acessar Linha", lambda n=nome: self.tela_linha(n)).pack(side="right", padx=16)

    def janela_estacoes(self, nome):
        linha = self.linhas[nome]
        w = self._janela_nova(f"Estações - Linha {nome}", 550, 550)
        self._label(w, f"Estações da Linha {nome}", 16, C["texto"], "bold", C["fundo"]).pack(anchor="w", padx=20, pady=(16, 4))
        
        box, area = self._area_rolavel(w)
        box.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        
        for i, estacao in enumerate(linha["estacoes"], 1):
            item = tk.Frame(area, bg="white")
            item.pack(fill="x", pady=2, padx=4)
            self._label(item, f"{i:02d}", 10, C["sec"], "bold", "white", width=4).pack(side="left", padx=8, pady=8)
            self._label(item, estacao, 10, C["texto"], "bold", "white").pack(side="left")

    def janela_horarios(self, nome):
        linha = self.linhas[nome]
        w = self._janela_nova("Horários", 650, 500)
        self._label(w, f"Horários - Linha {nome}", 16, C["texto"], "bold", C["fundo"]).pack(anchor="w", padx=20, pady=(16, 4))
        
        box, area = self._area_rolavel(w)
        box.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        
        for i, horario in enumerate(linha["horarios"]):
            tk.Label(area, text=horario, font=("Segoe UI", 10, "bold"), bg="#F1F5F9", fg=C["texto"],
                     width=10, pady=8).grid(row=i // 5, column=i % 5, padx=6, pady=6, sticky="ew")

    def mostrar_proximo(self, nome):
        linha = self.linhas[nome]
        horario, falta = proximo_horario(linha)
        msg = f"Linha {nome}\n\nPróxima saída: {horario}\nEstimativa: {minutos_para_texto(falta)}" if horario else "Sem mais saídas hoje."
        messagebox.showinfo("Próximo Comboio", msg)

    def janela_status(self, nome):
        linha = self.linhas[nome]
        messagebox.showinfo("Status Operacional", f"Linha {nome}\n\nSituação: {linha['status']}\nIntervalo: {linha['intervalo']} min")

    def janela_informacoes(self, nome):
        linha = self.linhas[nome]
        info = f"Linha {nome} ({linha['codigo']})\nEstações: {len(linha['estacoes'])}\nTarifa: {formatar_reais(linha['tarifa'])}"
        messagebox.showinfo("Informações", info)

    def janela_planejamento_global(self):
        self.janela_planejamento()

    def janela_planejamento(self, nome_linha=None):
        w = self._janela_nova("Planeador de Viagem", 650, 600)
        self._label(w, "Calcular Rota de Viagem", 16, C["texto"], "bold", C["fundo"]).pack(anchor="w", padx=24, pady=(20, 8))
        
        card = self._card(w)
        card.pack(fill="x", padx=24, pady=(0, 12))
        dentro = tk.Frame(card, bg="white")
        dentro.pack(fill="x", padx=16, pady=16)
        
        origem = self._campo(dentro, "Estação de Origem", self.todas_estacoes())
        destino = self._campo(dentro, "Estação de Destino", self.todas_estacoes())
        
        resultado = tk.Text(w, height=10, font=("Segoe UI", 10), bg="white", fg=C["texto"], bd=1, relief="solid", padx=10, pady=10)
        resultado.pack(fill="both", expand=True, padx=24)
        resultado.config(state="disabled")

        def calcular():
            o, d = origem.get(), destino.get()
            if not o or not d or o == d:
                messagebox.showwarning("Aviso", "Selecione estações válidas e diferentes.")
                return
            
            rota = montar_rota_integrada(self.linhas, o, d)
            if not rota:
                rota = calcular_rota_na_linha(self.linhas.get(nome_linha or "Jaboatão"), o, d)
                
            if not rota:
                msg = "Rota não encontrada."
            else:
                msg = (
                    f"Origem: {o}  →  Destino: {d}\n"
                    f"Tempo estimado: {rota.get('tempo')} min\n"
                    f"Tarifa: {formatar_reais(rota.get('tarifa', 4.25))}\n\n"
                    f"Itinerário:\n" + " ➔ ".join(rota.get("rota", []))
                )
            resultado.config(state="normal")
            resultado.delete("1.0", "end")
            resultado.insert("1.0", msg)
            resultado.config(state="disabled")

        self._botao(w, "Calcular Rota", calcular).pack(fill="x", padx=24, pady=16)

    def tela_admin(self):
        area = self._cabecalho("Administração do Sistema", "Gerenciar linhas")
        self._nav(area)
        card = self._card(area)
        card.pack(fill="both", expand=True)
        self._label(card, "Configuração de Linhas", 14, C["texto"], "bold", "white").pack(anchor="w", padx=20, pady=16)

    # ==============================================================================
    # MAPA REAL INTERATIVO COM TKINTERMAPVIEW
    # ==============================================================================
    def tela_mapa_rede(self):
        area = self._cabecalho("Mapa da Rede Metroviária", "Simulação sobre mapa geográfico real")
        self._nav(area)
        
        # Barra de Controles da Simulação e Tipo de Mapa
        bar = tk.Frame(area, bg=C["fundo"])
        bar.pack(fill="x", pady=(0, 10))
        
        for txt, cmd in [("▶ Iniciar Simulação", self.simulacao_iniciar),
                         ("⏸ Pausar", self.simulacao_pausar),
                         ("⏹ Parar", self.simulacao_parar),
                         ("↻ Reiniciar", self.simulacao_reiniciar)]:
            self._botao(bar, txt, cmd).pack(side="left", padx=(0, 6))

        # Alternador do estilo de mapa (OpenStreetMap vs Satélite)
        btn_sat = self._botao(bar, "🛰 Visão Satélite", lambda: self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"), "Metro.Nav.TButton")
        btn_sat.pack(side="right", padx=(6, 0))
        
        btn_rua = self._botao(bar, "🗺 Visão Ruas", lambda: self.map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"), "Metro.Nav.TButton")
        btn_rua.pack(side="right")

        # Widget do Mapa Real
        caixa = tk.Frame(area, bg=C["fundo"])
        caixa.pack(fill="both", expand=True)

        self.map_widget = tkintermapview.TkinterMapView(caixa, corner_radius=8)
        self.map_widget.pack(fill="both", expand=True)

        # Centralizar na Região Metropolitana do Recife
        self.map_widget.set_position(-8.0800, -34.9200)
        self.map_widget.set_zoom(12)

        self._desenhar_linhas_e_estacoes_reais()

    def _desenhar_linhas_e_estacoes_reais(self):
        """Desenha os traçados das linhas e os marcadores de cada estação no mapa real."""
        self.marcadores_trens.clear()
        
        for nome, linha in self.linhas.items():
            cor = CORES_LINHAS.get(nome, "#333333")
            caminho_coords = []

            for estacao in linha["estacoes"]:
                if estacao in COORDENADAS_ESTACOES:
                    lat, lon = COORDENADAS_ESTACOES[estacao]
                    caminho_coords.append((lat, lon))

                    # Adiciona Marcador na Estação Real
                    self.map_widget.set_marker(
                        lat, lon,
                        text=estacao,
                        command=lambda m, e=estacao: self.abrir_google_maps_estacao(e)
                    )

            # Desenha a linha conectando as estações
            if len(caminho_coords) > 1:
                self.map_widget.set_path(caminho_coords, color=cor, width=4)

    def _simulacao_ativa(self):
        return self.simulacao.ativo and not self.simulacao.paused and not self.simulacao.parado

    def _agendar_simulacao(self):
        self._cancelar_simulacao()
        if self.map_widget and self._simulacao_ativa():
            self.simulacao_timer_id = self.root.after(40, self.simulacao_tick)

    def _cancelar_simulacao(self):
        if self.simulacao_timer_id is not None:
            try:
                self.root.after_cancel(self.simulacao_timer_id)
            except tk.TclError:
                pass
            self.simulacao_timer_id = None

    def simulacao_iniciar(self):
        self.simulacao.iniciar()
        self._agendar_simulacao()

    def simulacao_pausar(self):
        self.simulacao.pausar()
        self._cancelar_simulacao()

    def simulacao_parar(self):
        self.simulacao.parar()
        self._cancelar_simulacao()
        self.anim_step = 0.0
        self._limpar_trens_do_mapa()

    def simulacao_reiniciar(self):
        self._cancelar_simulacao()
        self.simulacao.reiniciar()
        self.anim_step = 0.0
        self._agendar_simulacao()

    def _limpar_trens_do_mapa(self):
        for marker in self.marcadores_trens.values():
            marker.delete()
        self.marcadores_trens.clear()

    def simulacao_tick(self):
        if self._simulacao_ativa():
            self.anim_step += 0.03
            if self.anim_step >= 1.0:
                self.anim_step = 0.0
                self.simulacao.avancar()
            
            self._atualizar_trens_no_mapa()
            self._agendar_simulacao()

    def _atualizar_trens_no_mapa(self):
        """Atualiza a posição dos trens interpolando coordenadas de latitude e longitude."""
        for i, trem in enumerate(self.simulacao.trens):
            est_atual = trem.estacao_atual
            linha_obj = self.linhas.get(trem.linha)

            if not linha_obj or est_atual not in COORDENADAS_ESTACOES:
                continue

            estacoes = linha_obj["estacoes"]
            idx = estacoes.index(est_atual) if est_atual in estacoes else -1
            sentido = getattr(trem, "sentido", 1)
            prox_idx = idx + sentido

            # Interpolação Geográfica entre Estações
            if 0 <= prox_idx < len(estacoes):
                lat1, lon1 = COORDENADAS_ESTACOES[est_atual]
                lat2, lon2 = COORDENADAS_ESTACOES[estacoes[prox_idx]]

                lat_atual = lat1 + (lat2 - lat1) * self.anim_step
                lon_atual = lon1 + (lon2 - lon1) * self.anim_step
            else:
                lat_atual, lon_atual = COORDENADAS_ESTACOES[est_atual]

            # Atualizar ou Criar Marcador do Trem
            chave_trem = f"trem_{i}"
            rotulo = f"🚆 {trem.linha}"

            if chave_trem in self.marcadores_trens:
                self.marcadores_trens[chave_trem].set_position(lat_atual, lon_atual)
            else:
                marcador = self.map_widget.set_marker(lat_atual, lon_atual, text=rotulo)
                self.marcadores_trens[chave_trem] = marcador