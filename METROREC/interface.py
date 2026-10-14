import json
from copy import deepcopy
import tkinter as tk
import unicodedata
import urllib.request
import threading
import webbrowser
from pathlib import Path
from urllib.parse import quote, urlencode
from tkinter import ttk, messagebox
import tkintermapview
from PIL import Image, ImageOps, ImageTk
from dados import LINHAS
from simulacao import SimulacaoTrens
from viagens import montar_rota_integrada, proximo_horario
from utilitarios import formatar_reais, horario_atual, data_atual, minutos_para_texto
from operacao import GestorOperacional
from painel_admin import PainelAdministracao
# Paleta de Cores do Sistema
C = {
    "fundo": "#F2F7FC",
    "topo": "#082A50",
    "texto": "#102B50",
    "sec": "#5D7190",
    "card": "#FFFFFF",
    "borda": "#DCE6F1",
    "botao": "#0B315B",
    "hover": "#174879",
    "azul": "#075BC7",
    "verde": "#0AA875",
    "amarelo": "#E6A21A",
    "laranja": "#F2781B",
    "vermelho": "#E3333F",
}
# Cores das Linhas do Metrorec
CORES_LINHAS = {
    "Jaboatão": "#E3333F",
    "Camaragibe": "#F2781B",
    "Sul": "#075BC7",
}
API_LINHAS = "https://esigportal2.recife.pe.gov.br/arcgis/rest/services/MeioAmbiente/PCR_CBTU_Mobilidade/MapServer/3/query"
API_ESTACOES = "https://esigportal2.recife.pe.gov.br/arcgis/rest/services/MeioAmbiente/PCR_CBTU_Mobilidade/MapServer/2/query"
# Fallback usado somente se a API estiver indisponível.
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
    "Cajueiro Seco": (-8.1680556, -34.9341667)
}
ROTAS_MAPA = {
    "Jaboatão": LINHAS["Jaboatão"]["estacoes"],
    "Camaragibe": LINHAS["Camaragibe"]["estacoes"],
    "Sul": list(reversed(LINHAS["Sul"]["estacoes"])),
}
class MetroRecApp:
    def __init__(self, root):
        self.root = root
        self.linhas = deepcopy(LINHAS)
        self.operacao = GestorOperacional(self.linhas)
        self.topo = self.conteudo = None
        # Atributos do Mapa Real
        self.map_widget = None
        self.marcadores_trens = {}
        self.marcadores_estacoes = {}
        self.tracos_mapa = []
        self.estado_mapa = None
        self.gis_carregado = False
        self.gis_carregando = False
        self.icones_estacoes = {}
        self.tracos_api = []
        self.tracos_api_lookup = {}
        self.simulacao_timer_id = None
        self.simulacao = SimulacaoTrens(self.linhas)
        self.operacao.ao_atualizar_linha = self.simulacao.atualizar_operacao
        self.operacao.ao_atualizar_frota = self.simulacao.sincronizar_frota
        self.operacao.validar_despacho = self.simulacao.validar_despacho
        self.simulacao.validar_maquinista = self.operacao.validar_maquinista_para_trem
        self.simulacao.ao_mudar_status = self.operacao.registrar_status_simulado
        self.simulacao.sincronizar_frota(self.operacao.trens)
        pasta_imagens = Path(__file__).parent / "assets"
        self.fotos_linhas = {
            "Jaboatão": Image.open(pasta_imagens / "linha-jaboatao.png"),
            "Camaragibe": Image.open(pasta_imagens / "linha-camaragibe.png"),
            "Sul": Image.open(pasta_imagens / "linha-sul.png"),
        }
        self.foto_cabecalho = Image.open(pasta_imagens / "cabecalho-trem.png")
        self.logo_cbtu = Image.open(pasta_imagens / "logo-cbtu.png")
        self._janela()
        self._estilos()
        self.tela_inicial()
    def _janela(self):
        self.root.title("METROREC - Sistema de Mobilidade Integrado")
        caminho_icone = Path(__file__).parent / "assets" / "metrorec-logo.png"
        if caminho_icone.is_file():
            self.icone_janela = tk.PhotoImage(file=str(caminho_icone))
            self.root.iconphoto(True, self.icone_janela)
        largura = self.root.winfo_screenwidth()
        altura = self.root.winfo_screenheight()
        minimo_largura = min(760, max(640, largura - 80))
        minimo_altura = min(560, max(440, altura - 120))
        self.root.geometry(f"{max(minimo_largura, min(1360, largura - 40))}x{max(minimo_altura, min(820, altura - 80))}")
        self.root.minsize(minimo_largura, minimo_altura)
        self.root.configure(bg=C["fundo"])
    def _estilos(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Metro.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 9),
                    foreground="white", background=C["botao"], borderwidth=0)
        s.map("Metro.TButton", background=[("active", C["hover"])])
        s.configure("Metro.Dark.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 9),
                    foreground="white", background=C["topo"], borderwidth=0)
        s.map("Metro.Dark.TButton", background=[("active", C["hover"])])
        s.configure("Metro.Nav.TButton", font=("Segoe UI", 10), padding=(13, 9),
                    foreground=C["texto"], background="#E8F0FA", borderwidth=0)
        s.map("Metro.Nav.TButton", background=[("active", "#D7E6F8")])
        s.configure("Metro.NavActive.TButton", font=("Segoe UI", 10, "bold"), padding=(13, 9),
                    foreground="white", background=C["azul"], borderwidth=0)
        s.map("Metro.NavActive.TButton", background=[("active", "#064AA3")])
        s.configure("Metro.NavSmall.TButton", font=("Segoe UI", 9), padding=(5, 7),
                    foreground=C["texto"], background="#E8F0FA", borderwidth=0)
        s.map("Metro.NavSmall.TButton", background=[("active", "#D7E6F8")])
        s.configure("Metro.NavSmallActive.TButton", font=("Segoe UI", 9, "bold"), padding=(5, 7),
                    foreground="white", background=C["azul"], borderwidth=0)
        s.map("Metro.NavSmallActive.TButton", background=[("active", "#064AA3")])
        for nome, cor, estilo in [
            ("Jaboatão", CORES_LINHAS["Jaboatão"], "Linha1.TButton"),
            ("Camaragibe", CORES_LINHAS["Camaragibe"], "Linha2.TButton"),
            ("Sul", CORES_LINHAS["Sul"], "Linha3.TButton"),
        ]:
            s.configure(estilo, font=("Segoe UI", 10, "bold"), padding=(12, 10),
                        foreground="white", background=cor, borderwidth=0)
            s.map(estilo, background=[("active", cor)])
    def _limpar(self):
        self.root.unbind_all("<MouseWheel>")
        self.root.unbind_all("<Button-4>")
        self.root.unbind_all("<Button-5>")
        self._guardar_estado_mapa()
        self._limpar_elementos_mapa()
        self.map_widget = None
        for widget in (self.topo, self.conteudo):
            if widget and widget.winfo_exists():
                widget.destroy()
        self.topo = self.conteudo = None
    def _guardar_estado_mapa(self):
        mapa = self.map_widget
        if mapa and self._mapa_existe(mapa):
            try:
                self.estado_mapa = (mapa.get_position(), mapa.zoom)
            except (AttributeError, tk.TclError):
                pass
    @staticmethod
    def _mapa_existe(mapa):
        try:
            return bool(mapa and mapa.winfo_exists())
        except tk.TclError:
            return False
    def _limpar_elementos_mapa(self):
        mapa = self.map_widget
        if self._mapa_existe(mapa):
            objetos = [*self.marcadores_trens.values(), *self.marcadores_estacoes.values(), *self.tracos_mapa]
            for objeto in objetos:
                if getattr(objeto, "map_widget", mapa) is mapa:
                    try:
                        objeto.delete()
                    except (AttributeError, tk.TclError):
                        pass
        self.marcadores_trens.clear()
        self.marcadores_estacoes.clear()
        self.tracos_mapa.clear()
    def _label(self, parent, texto="", tam=10, cor=None, peso=None, bg=None, **kw):
        return tk.Label(parent, text=texto, font=("Segoe UI", tam, peso) if peso else ("Segoe UI", tam),
                        fg=cor or C["texto"], bg=bg if bg is not None else parent.cget("bg"), **kw)
    def _card(self, parent, **kw):
        return tk.Frame(parent, bg=C["card"], bd=1, relief="solid",
                        highlightthickness=0, highlightbackground=C["borda"], **kw)
    def _botao(self, parent, texto, comando, estilo="Metro.TButton", **kw):
        return ttk.Button(parent, text=texto, command=comando, style=estilo, **kw)
    def _cabecalho(self, titulo, subtitulo="", destaque=False):
        self._limpar()
        altura = 145 if destaque else 80
        self.topo = tk.Frame(self.root, bg=C["topo"], height=altura)
        self.topo.pack(fill="x")
        self.topo.pack_propagate(False)
        relogio = self._label(self.topo, "", 12, "#F1F5F9", "bold", C["topo"], justify="right")
        relogio.place(relx=0.89, rely=0.38, anchor="nw")
        def atualizar():
            if relogio.winfo_exists():
                relogio.config(text=f"{horario_atual()}  •  {data_atual()}")
                relogio.after(1000, atualizar)
        atualizar()
        if destaque:
            marca = tk.Frame(self.topo, bg=C["topo"])
            marca.place(x=108, y=37)
            linha_marca = tk.Frame(marca, bg=C["topo"])
            linha_marca.pack(anchor="w")
            self._label(linha_marca, "METRO", 26, "white", "bold", C["topo"]).pack(side="left")
            self._label(linha_marca, "REC", 26, "#19A5F8", "bold", C["topo"]).pack(side="left")
            self._label(marca, "Sistema de Mobilidade Integrado", 9, "#D5E5F7", bg=C["topo"]).pack(anchor="w")
            divisor_marca = tk.Frame(self.topo, bg="#496987", width=1, height=58)
            divisor_marca.place(x=350, y=43)
            frase = tk.Frame(self.topo, bg=C["topo"])
            frase.place(x=372, y=47)
            self._label(frase, "Mais mobilidade", 13, "white", "bold", C["topo"]).pack(anchor="w")
            self._label(frase, "para uma Recife melhor.", 10, "#BBD2EB", bg=C["topo"]).pack(anchor="w")
            banner = tk.Label(self.topo, bg=C["topo"], bd=0)
            banner.place(relx=0.49, y=0, relwidth=0.34, height=145)
            banner.bind("<Configure>", lambda e: self._ajustar_imagem(e.widget, self.foto_cabecalho, e.width, e.height))
            logo_cbtu = ImageOps.contain(self.logo_cbtu, (36, 42), method=Image.Resampling.LANCZOS)
            self.imagem_logo_cbtu = ImageTk.PhotoImage(logo_cbtu)
            logo_cbtu = tk.Label(self.topo, image=self.imagem_logo_cbtu, bg=C["topo"], bd=0)
            logo_cbtu.place(relx=0.85, y=49)
            divisor_cbtu = tk.Frame(self.topo, bg="#496987", width=1, height=54)
            divisor_cbtu.place(relx=0.88, y=45)
            self._partes_cabecalho = (marca, divisor_marca, frase, banner, logo_cbtu, divisor_cbtu, relogio)
            self.topo.bind("<Configure>", self._adaptar_cabecalho)
        else:
            esquerda = tk.Frame(self.topo, bg=C["topo"])
            esquerda.pack(side="left", padx=30, fill="y")
            self._label(esquerda, "METROREC", 16, "white", "bold", C["topo"]).pack(anchor="w", pady=(14, 0))
            self._label(esquerda, titulo, 9, "#BBD2EB", bg=C["topo"]).pack(anchor="w")
        self.conteudo = tk.Frame(self.root, bg=C["fundo"])
        self.conteudo.pack(fill="both", expand=True)
        self.pagina_canvas = tk.Canvas(self.conteudo, bg=C["fundo"], highlightthickness=0)
        self.pagina_scrollbar = ttk.Scrollbar(self.conteudo, orient="vertical", command=self.pagina_canvas.yview)
        self.pagina_canvas.configure(yscrollcommand=self.pagina_scrollbar.set)
        self.pagina_scrollbar.pack(side="right", fill="y")
        self.pagina_canvas.pack(side="left", fill="both", expand=True)
        area_conteudo = tk.Frame(self.pagina_canvas, bg=C["fundo"])
        self.pagina_window = self.pagina_canvas.create_window((0, 0), window=area_conteudo, anchor="nw")
        def ajustar_area(_evento=None):
            altura = max(self.pagina_canvas.winfo_height(), area_conteudo.winfo_reqheight())
            self.pagina_canvas.itemconfigure(self.pagina_window,
                                             width=self.pagina_canvas.winfo_width(), height=altura)
            self.pagina_canvas.configure(scrollregion=self.pagina_canvas.bbox("all"))
        area_conteudo.bind("<Configure>", ajustar_area)
        self.pagina_canvas.bind("<Configure>", ajustar_area)
        self.root.bind_all("<MouseWheel>", self._rolar_pagina)
        self.root.bind_all("<Button-4>", self._rolar_pagina)
        self.root.bind_all("<Button-5>", self._rolar_pagina)
        area = tk.Frame(area_conteudo, bg=C["fundo"])
        area.pack(fill="both", expand=True, padx=16, pady=(12, 12) if destaque else (16, 16))
        if subtitulo and not destaque:
            self._label(area, subtitulo, 11, C["sec"], bg=C["fundo"]).pack(anchor="w", pady=(0, 16))
        return area
    def _adaptar_cabecalho(self, evento):
        if not getattr(self, "_partes_cabecalho", None):
            return
        marca, divisor, frase, banner, logo, divisor_cbtu, relogio = self._partes_cabecalho
        largura = evento.width
        if largura >= 1120:
            marca.place_configure(x=108, y=37)
            divisor.place(x=350, y=43)
            frase.place(x=372, y=47)
            banner.place(relx=0.49, y=0, relwidth=0.34, height=145)
            logo.place(relx=0.85, y=49)
            divisor_cbtu.place(relx=0.88, y=45)
            relogio.place(relx=0.89, rely=0.38, anchor="nw")
            relogio.configure(font=("Segoe UI", 12, "bold"))
        elif largura >= 840:
            marca.place(x=24, y=37)
            divisor.place(x=263, y=43)
            frase.place_forget()
            banner.place_forget()
            logo.place(relx=0.73, y=49)
            divisor_cbtu.place(relx=0.79, y=45)
            relogio.place(relx=0.81, rely=0.38, anchor="nw")
            relogio.configure(font=("Segoe UI", 10, "bold"))
        else:
            marca.place(x=16, y=37)
            divisor.place_forget()
            frase.place_forget()
            banner.place_forget()
            logo.place_forget()
            divisor_cbtu.place_forget()
            relogio.place(relx=0.72, rely=0.38, anchor="nw")
            relogio.configure(font=("Segoe UI", 9, "bold"))
    def _rolar_pagina(self, evento):
        if getattr(evento, "num", None) == 4:
            unidades = -3
        elif getattr(evento, "num", None) == 5:
            unidades = 3
        else:
            unidades = -int(evento.delta / 120) or (-1 if evento.delta > 0 else 1)
        widget = evento.widget
        canvas_interno = None
        while widget and widget is not self.pagina_canvas:
            if widget is self.map_widget or isinstance(widget, (tk.Text, ttk.Treeview)):
                return
            if isinstance(widget, tk.Canvas):
                canvas_interno = widget
            widget = getattr(widget, "master", None)
        if widget is not self.pagina_canvas:
            return
        if canvas_interno:
            canvas_interno.yview_scroll(unidades, "units")
            return "break"
        self.pagina_canvas.yview_scroll(unidades, "units")
        return "break"
    def _ajustar_imagem(self, widget, imagem, largura, altura):
        if largura < 1 or altura < 1:
            return
        ajustada = ImageOps.contain(imagem, (largura, altura), method=Image.Resampling.LANCZOS)
        widget.imagem = ImageTk.PhotoImage(ajustada)
        widget.configure(image=widget.imagem)
    def _nav(self, parent, ativo=None):
        barra = tk.Frame(parent, bg=C["fundo"])
        barra.pack(fill="x", pady=(0, 18))
        botoes = [
            ("⌂  Início", "Início", self.tela_inicial),
            ("▤  Mapa Real Interativo", "Mapa Real Interativo", self.tela_mapa_rede),
            ("▥  Dashboard", "Dashboard", self.tela_dashboard),
            ("▣  Linhas", "Linhas", self.tela_todas_linhas),
            ("⌖  Planejar Rota", "Planejar Rota", self.janela_planejamento_global),
        ]
        botoes_criados = []
        for texto, chave, comando in botoes:
            estilo = "Metro.NavActive.TButton" if chave == ativo else "Metro.Nav.TButton"
            botao = self._botao(barra, texto, comando, estilo)
            botao.pack(side="left", padx=(0, 6), ipady=1)
            botoes_criados.append((botao, texto, chave == ativo))
        compactos = ("Início", "Mapa", "Painel", "Linhas", "Planejar")
        def adaptar(evento):
            pequeno = evento.width < 980
            for (botao, texto, selecionado), compacto in zip(botoes_criados, compactos):
                botao.configure(text=compacto if pequeno else texto,
                                style=("Metro.NavSmallActive.TButton" if selecionado else "Metro.NavSmall.TButton")
                                if pequeno else ("Metro.NavActive.TButton" if selecionado else "Metro.Nav.TButton"))
        barra.bind("<Configure>", adaptar)
    def _janela_nova(self, titulo, largura, altura):
        w = tk.Toplevel(self.root)
        w.title(f"METROREC - {titulo}")
        largura = min(largura, self.root.winfo_screenwidth() - 60)
        altura = min(altura, self.root.winfo_screenheight() - 100)
        w.geometry(f"{largura}x{altura}")
        w.minsize(min(400, largura), min(300, altura))
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
            "Operação com restrições": C["laranja"],
            "Interrompida": C["vermelho"],
            "Indisponível": C["vermelho"],
            "Operação com restrições": C["laranja"]
        }.get(status, C["sec"])
    def todas_estacoes(self):
        return list(dict.fromkeys(e for l in self.linhas.values() for e in l["estacoes"]))
    def _cartao_linha(self, parent, nome, linha):
        cor = CORES_LINHAS.get(nome, C["azul"])
        card = self._card(parent, height=405)
        card.configure(bd=0, highlightthickness=1, highlightbackground=C["borda"])
        card.pack(side="left", fill="x", expand=True, padx=8, pady=2)
        card.pack_propagate(False)
        tk.Frame(card, bg=cor, height=7).pack(fill="x")
        corpo = tk.Frame(card, bg="white")
        corpo.pack(fill="both", expand=True, padx=16, pady=12)
        topo = tk.Frame(corpo, bg="white")
        topo.pack(fill="x")
        selo = tk.Canvas(topo, width=68, height=68, bg="white", highlightthickness=0)
        selo.pack(side="left", padx=(0, 14))
        selo.create_oval(3, 3, 65, 65, fill=cor, outline=cor)
        selo.create_text(34, 34, text=linha["codigo"], fill="white", font=("Segoe UI", 21, "bold"))
        descricoes = {
            "Jaboatão": "Conectando pessoas e regiões.",
            "Camaragibe": "Integração que aproxima.",
            "Sul": "Mais conexão para o seu destino.",
        }
        nome_texto = "Linha Sul" if nome == "Sul" else f"Linha {nome}"
        textos = tk.Frame(topo, bg="white")
        textos.pack(side="left", fill="x", expand=True)
        self._label(textos, nome_texto, 19, C["texto"], "bold", "white").pack(anchor="w", pady=(5, 2))
        self._label(textos, descricoes.get(nome, "Rede de transporte metropolitano"),
                    9, C["sec"], bg="white").pack(anchor="w")
        self._label(corpo, f"●  {linha['status']}", 9, self.status_cor(linha["status"]),
                    "bold", "white").pack(anchor="w", pady=(10, 8))
        info = tk.Frame(corpo, bg="white")
        info.pack(fill="x", pady=(0, 8))
        primeiro, ultimo = linha["estacoes"][0], linha["estacoes"][-1]
        itens = [
            ("▣", str(len(linha["estacoes"])), "Estações"),
            ("◷", formatar_reais(linha["tarifa"]), "Tarifa"),
            ("⌁", f"{primeiro} → {ultimo}", "(terminal a terminal)"),
        ]
        for i, (icone, valor, legenda) in enumerate(itens):
            celula = tk.Frame(info, bg="white")
            celula.pack(side="left", fill="both", expand=True, padx=(0 if i == 0 else 8, 0))
            tk.Label(celula, text=icone, font=("Segoe UI Symbol", 18), fg=C["topo"], bg="white").pack(side="left", padx=(0, 7))
            textos_info = tk.Frame(celula, bg="white")
            textos_info.pack(side="left", fill="x", expand=True)
            self._label(textos_info, valor, 10 if i == 2 else 12, C["texto"], "bold", "white",
                        wraplength=95 if i == 2 else 70, justify="left").pack(anchor="w", pady=(2, 1))
            self._label(textos_info, legenda, 8, C["sec"], bg="white",
                        wraplength=100).pack(anchor="w")
            if i < 2:
                tk.Frame(info, bg=C["borda"], width=1).pack(side="left", fill="y", padx=7)
        visual = tk.Label(corpo, bg="white", height=135, bd=0)
        visual.pack(fill="x", pady=(0, 13))
        visual.bind("<Configure>", lambda e, n=nome: self._enquadrar_foto_linha(e.widget, e.width, e.height, n))
        estilos = {"Jaboatão": "Linha1.TButton", "Camaragibe": "Linha2.TButton", "Sul": "Linha3.TButton"}
        self._botao(corpo, "➜  Ver detalhes da linha  ›", lambda n=nome: self.tela_linha(n),
                    estilos.get(nome, "Metro.TButton")).pack(fill="x", ipady=2)
    def _adaptar_cartoes_inicio(self, evento, quadro):
        compacto = evento.width < 1000
        modo = "vertical" if compacto else "horizontal"
        if getattr(quadro, "_modo_cartoes", None) == modo:
            return
        quadro._modo_cartoes = modo
        for cartao in quadro.winfo_children():
            cartao.pack_forget()
            cartao.pack(side="top" if compacto else "left", fill="x" if compacto else "both",
                        expand=not compacto, padx=8, pady=8 if compacto else 2)
    def _enquadrar_foto_linha(self, widget, largura, altura, nome):
        if largura < 1 or altura < 1:
            return
        foto = ImageOps.fit(self.fotos_linhas[nome], (largura, altura), method=Image.Resampling.LANCZOS,
                            centering=(0.5, 0.5))
        widget.imagem = ImageTk.PhotoImage(foto)
        widget.configure(image=widget.imagem)
    def tela_inicial(self):
        area = self._cabecalho("Painel Geral", destaque=True)
        self._nav(area, "Início")
        boas_vindas = tk.Frame(area, bg=C["fundo"], height=105)
        boas_vindas.pack(fill="x", pady=(0, 16))
        boas_vindas.pack_propagate(False)
        tk.Frame(boas_vindas, bg=C["azul"], width=5).pack(side="left", fill="y", padx=(0, 16))
        mensagem = tk.Frame(boas_vindas, bg=C["fundo"])
        mensagem.pack(side="left", fill="both", expand=True, pady=4)
        self._label(mensagem, "BEM-VINDO AO METROREC", 10, C["azul"], "bold", C["fundo"]).pack(anchor="w")
        self._label(mensagem, "Escolha uma linha para começar", 23, C["texto"], "bold", C["fundo"]).pack(anchor="w", pady=(0, 2))
        self._label(mensagem, "Acesse as estações, consulte horários, veja o mapa e planeje sua rota.",
                    10, C["sec"], bg=C["fundo"]).pack(anchor="w")
        cards = tk.Frame(area, bg=C["fundo"])
        cards.pack(fill="both", expand=True)
        for nome, linha in self.linhas.items():
            self._cartao_linha(cards, nome, linha)
        cards.bind("<Configure>", lambda evento: self._adaptar_cartoes_inicio(evento, cards))
        rodape = tk.Frame(area, bg=C["fundo"])
        rodape.pack(fill="x", pady=(14, 0))
        self._botao(rodape, "⚙  Painel de Administração", self.tela_admin,
                    "Metro.Dark.TButton").pack(side="right")
    def tela_linha(self, nome):
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
        total = len(self.todas_estacoes())
        normais = sum(l["status"] == "Operação normal" for l in self.linhas.values())
        ativas = sum(l["status"] not in ("Interrompida", "Indisponível") for l in self.linhas.values())
        cards = tk.Frame(area, bg=C["fundo"])
        cards.pack(fill="x", pady=8)
        indicadores = [
            ("Linhas Ativas", ativas, "Metrorec"),
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
        if linha["status"] in ("Interrompida", "Indisponível"):
            self._label(w, "Serviço interrompido; consulte o painel para atualizações.",
                        11, C["vermelho"], "bold", C["fundo"]).pack(anchor="w", padx=20, pady=12)
            return
        box, area = self._area_rolavel(w)
        box.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        for i, horario in enumerate(linha["horarios"]):
            tk.Label(area, text=horario, font=("Segoe UI", 10, "bold"), bg="#F1F5F9", fg=C["texto"],
                     width=10, pady=8).grid(row=i // 5, column=i % 5, padx=6, pady=6, sticky="ew")
    def mostrar_proximo(self, nome):
        linha = self.linhas[nome]
        horario, falta = proximo_horario(linha)
        msg = (f"Linha {nome} indisponível." if linha["status"] in ("Interrompida", "Indisponível") else
               f"Linha {nome}\n\nPróxima saída: {horario}\nEstimativa: {minutos_para_texto(falta)}"
               if horario else "Sem mais saídas hoje.")
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
        selecao_linha = tk.StringVar(value=nome_linha or "Rede completa")
        combo_linha = self._campo(dentro, "Linha", ["Rede completa", *self.linhas], selecao_linha)
        origem = self._campo(dentro, "Estação de Origem", [])
        destino = self._campo(dentro, "Estação de Destino", [])
        def atualizar_estacoes(_evento=None):
            nome = selecao_linha.get()
            estacoes = (self.todas_estacoes() if nome == "Rede completa"
                        else list(self.linhas.get(nome, {}).get("estacoes", [])))
            origem.configure(values=estacoes)
            destino.configure(values=estacoes)
            origem.set("")
            destino.set("")
        combo_linha.bind("<<ComboboxSelected>>", atualizar_estacoes)
        atualizar_estacoes()
        resultado = tk.Text(w, height=10, font=("Segoe UI", 10), bg="white", fg=C["texto"], bd=1, relief="solid", padx=10, pady=10)
        resultado.pack(fill="both", expand=True, padx=24)
        resultado.config(state="disabled")
        def calcular():
            o, d = origem.get(), destino.get()
            if not o or not d or o == d:
                messagebox.showwarning("Aviso", "Selecione estações válidas e diferentes.")
                return
            linha_inicio = None if selecao_linha.get() == "Rede completa" else selecao_linha.get()
            rota = montar_rota_integrada(self.linhas, o, d, linha_inicial=linha_inicio)
            if not rota:
                msg = "Rota não encontrada."
            else:
                pernas = rota.get("pernas", [])
                detalhe = "\n".join(
                    f"{perna['linha']} ({perna['sentido']}): " + " → ".join(perna["rota"])
                    for perna in pernas) if pernas else " → ".join(rota.get("rota", []))
                msg = (
                    f"Origem: {o}  →  Destino: {d}\n"
                    f"Linhas: {rota.get('linha', selecao_linha.get())}\n"
                    f"Estações percorridas: {rota.get('estacoes')}  |  Integrações: {rota.get('trocas')}\n"
                    f"Tempo estimado: {rota.get('tempo')} min\n"
                    f"Tempo de transferência: {rota.get('tempo_transferencia', 0)} min\n"
                    f"Tarifa acadêmica: {formatar_reais(rota.get('tarifa', self.operacao.tarifa))}\n\n"
                    f"Itinerário:\n{detalhe}"
                )
            resultado.config(state="normal")
            resultado.delete("1.0", "end")
            resultado.insert("1.0", msg)
            resultado.config(state="disabled")
        self._botao(w, "Calcular Rota", calcular).pack(fill="x", padx=24, pady=16)
    def tela_admin(self):
        area = self._cabecalho("Administração do Sistema", "Gerenciar linhas")
        self._nav(area)
        self._label(area, "Painel de demonstração: os dados são salvos neste computador e não alteram sistemas reais da CBTU.",
                    9, C["sec"], bg=C["fundo"]).pack(anchor="w", pady=(0, 8))
        PainelAdministracao(area, self).pack(fill="both", expand=True)
    # ==============================================================================
    # MAPA REAL INTERATIVO COM TKINTERMAPVIEW
    # ==============================================================================
    def tela_mapa_rede(self):
        area = self._cabecalho("Mapa da Rede Metroviária", "Traçado real baseado em dados GIS da Prefeitura/CBTU")
        self._nav(area)
        bar = tk.Frame(area, bg=C["fundo"])
        bar.pack(fill="x", pady=(0, 10))
        for txt, cmd in [("▶ Iniciar Simulação", self.simulacao_iniciar), ("⏸ Pausar", self.simulacao_pausar),
                         ("⏹ Parar", self.simulacao_parar), ("↻ Reiniciar", self.simulacao_reiniciar)]:
            self._botao(bar, txt, cmd).pack(side="left", padx=(0, 6))
        self._botao(bar, "🛰 Visão Satélite",
                    lambda: self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"),
                    "Metro.Nav.TButton").pack(side="right", padx=(6, 0))
        self._botao(bar, "🗺 Visão Ruas",
                    lambda: self.map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"),
                    "Metro.Nav.TButton").pack(side="right")
        caixa = tk.Frame(area, bg=C["fundo"])
        caixa.pack(fill="both", expand=True)
        self.map_widget = tkintermapview.TkinterMapView(caixa, corner_radius=8)
        self.map_widget.pack(fill="both", expand=True)
        if self.estado_mapa:
            posicao, zoom = self.estado_mapa
            self.map_widget.set_position(*posicao)
            self.map_widget.set_zoom(zoom)
        else:
            self.map_widget.set_position(-8.10, -34.94)
            self.map_widget.set_zoom(12)
        mapa = self.map_widget
        mapa.after_idle(lambda: self._preparar_mapa(mapa))
        if self.estado_mapa is None:
            self.root.after(250, lambda: self._ajustar_mapa(mapa))
    def _preparar_mapa(self, mapa):
        if mapa is not self.map_widget or not self._mapa_existe(mapa):
            return
        if not self.gis_carregado:
            self._desenhar_linhas_e_estacoes_reais()
            self._carregar_gis()
        else:
            self._desenhar_linhas_e_estacoes_reais()
        self._atualizar_trens_no_mapa()
        self._agendar_simulacao()
    @staticmethod
    def _normalizar(texto):
        texto = unicodedata.normalize("NFD", str(texto)).encode("ascii", "ignore").decode().lower()
        return "".join(c for c in texto if c.isalnum())
    def _api(self, url, campos):
        q = urlencode({"where": "1=1", "outFields": campos, "returnGeometry": "true",
                       "outSR": "4326", "f": "geojson", "returnTrueCurves": "false"})
        try:
            with urllib.request.urlopen(f"{url}?{q}", timeout=8) as r:
                return json.loads(r.read().decode())
        except Exception:
            return None
    def _carregar_gis(self):
        if self.gis_carregando or self.gis_carregado:
            return
        self.gis_carregando = True
        threading.Thread(target=self._buscar_gis, daemon=True).start()

    def _buscar_gis(self):
        estacoes = self._api(API_ESTACOES, "name")
        linhas = self._api(API_LINHAS, "name")
        try:
            self.root.after(0, lambda: self._aplicar_gis(estacoes, linhas))
        except tk.TclError:
            pass

    def _aplicar_gis(self, estacoes, linhas):
        self.gis_carregando = False
        self.gis_carregado = True
        if estacoes:
            nomes = {self._normalizar(n): n for n in COORDENADAS_ESTACOES}
            for f in estacoes.get("features", []):
                bruto = f.get("properties", {}).get("name", "").replace("estacao", "")
                nome = self._normalizar(bruto)
                c = f.get("geometry", {}).get("coordinates", [])
                alvo = next((n for k, n in nomes.items() if k == nome or k in nome or nome in k), None)
                if alvo and len(c) >= 2:
                    COORDENADAS_ESTACOES[alvo] = (float(c[1]), float(c[0]))
        self.tracos_api = []
        self.tracos_api_lookup = {}
        if not linhas:
            if self._mapa_existe(self.map_widget):
                self._desenhar_linhas_e_estacoes_reais()
                self._atualizar_trens_no_mapa()
            return
        partes = []
        for f in linhas.get("features", []):
            g = f.get("geometry", {})
            c = g.get("coordinates", [])
            partes.extend([c] if g.get("type") == "LineString" else c)
        for nome, rota in ROTAS_MAPA.items():
            for origem, destino in zip(rota, rota[1:]):
                trecho = self._melhor_trecho(origem, destino, partes)
                if trecho:
                    self.tracos_api.append((nome, origem, destino, trecho))
        self.tracos_api_lookup = {(n, o, d): trecho for n, o, d, trecho in self.tracos_api}
        if self._mapa_existe(self.map_widget):
            self._desenhar_linhas_e_estacoes_reais()
            self._atualizar_trens_no_mapa()
    @staticmethod
    def _melhor_trecho(origem, destino, partes):
        a, b = COORDENADAS_ESTACOES[origem], COORDENADAS_ESTACOES[destino]
        melhor = None
        for parte in partes:
            if len(parte) < 2:
                continue
            p = [(float(y), float(x)) for x, y, *resto in parte]
            ia = min(range(len(p)), key=lambda i: (p[i][0] - a[0]) ** 2 + (p[i][1] - a[1]) ** 2)
            ib = min(range(len(p)), key=lambda i: (p[i][0] - b[0]) ** 2 + (p[i][1] - b[1]) ** 2)
            da = (p[ia][0] - a[0]) ** 2 + (p[ia][1] - a[1]) ** 2
            db = (p[ib][0] - b[0]) ** 2 + (p[ib][1] - b[1]) ** 2
            if max(da, db) > 0.006 ** 2 or ia == ib:
                continue
            trecho = p[ia:ib + 1] if ia < ib else p[ib:ia + 1][::-1]
            erro = da + db
            tamanho = sum((y[0] - x[0]) ** 2 + (y[1] - x[1]) ** 2 for x, y in zip(trecho, trecho[1:]))
            candidato = (erro, tamanho, trecho)
            if melhor is None or candidato[:2] < melhor[:2]:
                melhor = candidato
        return melhor[2] if melhor else None
    def _icone_estacao(self, cor, integracao=False):
        chave = (cor, integracao)
        if chave in self.icones_estacoes:
            return self.icones_estacoes[chave]
        tamanho, raio = (9, 3) if integracao else (7, 2)
        imagem = tk.PhotoImage(master=self.root, width=tamanho, height=tamanho)
        centro = (tamanho - 1) / 2
        for y in range(tamanho):
            for x in range(tamanho):
                if ((x - centro) ** 2 + (y - centro) ** 2) ** .5 <= raio:
                    imagem.put(cor, (x, y))
        self.icones_estacoes[chave] = imagem
        return imagem
    def _desenhar_linhas_e_estacoes_reais(self):
        if not self._mapa_existe(self.map_widget):
            return
        self._limpar_elementos_mapa()
        api_pares = self.tracos_api_lookup
        for nome, rota in ROTAS_MAPA.items():
            for origem, destino in zip(rota, rota[1:]):
                a, b = COORDENADAS_ESTACOES[origem], COORDENADAS_ESTACOES[destino]
                cor = C["sec"] if self.linhas[nome]["status"] in ("Interrompida", "Indisponível") else CORES_LINHAS[nome]
                caminho = self.map_widget.set_path(api_pares.get((nome, origem, destino), [a, b]), color=cor, width=3)
                self.tracos_mapa.append(caminho)
        mostradas = set()
        for nome, estacoes in ROTAS_MAPA.items():
            for estacao in estacoes:
                if estacao in mostradas:
                    continue
                marcador = self.map_widget.set_marker(
                    *COORDENADAS_ESTACOES[estacao], text=f"  {estacao}",
                    icon=self._icone_estacao(CORES_LINHAS[nome], estacao in {"Recife", "Joana Bezerra", "Coqueiral"}),
                    icon_anchor="center", text_color="#334155",
                    font=("Segoe UI", 8 if estacao in {"Recife", "Joana Bezerra", "Coqueiral"} else 7, "bold"),
                    command=lambda m, e=estacao: self.abrir_google_maps_estacao(e)
                )
                self.marcadores_estacoes[estacao] = marcador
                mostradas.add(estacao)
    def _ajustar_mapa(self, mapa=None):
        mapa = mapa or self.map_widget
        if mapa is not self.map_widget or self.estado_mapa is not None or not self._mapa_existe(mapa):
            return
        if mapa.winfo_width() < 320 or mapa.winfo_height() < 260:
            mapa.after(150, lambda: self._ajustar_mapa(mapa))
            return
        lats, lons = zip(*COORDENADAS_ESTACOES.values())
        self.map_widget.fit_bounding_box((max(lats) + .008, min(lons) - .008),
                                         (min(lats) - .008, max(lons) + .008))
    def abrir_google_maps_estacao(self, estacao):
        lat, lon = COORDENADAS_ESTACOES[estacao]
        webbrowser.open(f"https://www.google.com/maps/search/?api=1&query={quote(f'{lat},{lon}')}")
    def _simulacao_ativa(self):
        return self.simulacao.ativo and not self.simulacao.paused and not self.simulacao.parado
    def _agendar_simulacao(self):
        if self.simulacao_timer_id is None and self._simulacao_ativa():
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
        self._limpar_trens_do_mapa()
    def simulacao_reiniciar(self):
        self._cancelar_simulacao()
        self._limpar_trens_do_mapa()
        self.simulacao.reiniciar()
        self._agendar_simulacao()
    def _limpar_trens_do_mapa(self):
        for marker in self.marcadores_trens.values():
            if getattr(marker, "map_widget", None) is self.map_widget and self._mapa_existe(self.map_widget):
                try:
                    marker.delete()
                except tk.TclError:
                    pass
        self.marcadores_trens.clear()
    def simulacao_tick(self):
        self.simulacao_timer_id = None
        if self._simulacao_ativa():
            self.simulacao.atualizar(0.04 * self.simulacao.config["escala_minutos_por_segundo"])
            if self._mapa_existe(self.map_widget):
                self._atualizar_trens_no_mapa()
            self._agendar_simulacao()
    def _ponto_no_traco(self, linha, origem, destino, progresso):
        trecho = self.tracos_api_lookup.get((linha, origem, destino))
        if trecho is None:
            trecho = self.tracos_api_lookup.get((linha, destino, origem))
            if trecho:
                trecho = trecho[::-1]
        if not trecho:
            a, b = COORDENADAS_ESTACOES[origem], COORDENADAS_ESTACOES[destino]
            return a[0] + (b[0] - a[0]) * progresso, a[1] + (b[1] - a[1]) * progresso
        dist = [0.0]
        for a, b in zip(trecho, trecho[1:]):
            dist.append(dist[-1] + ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** .5)
        alvo = dist[-1] * progresso
        for i in range(1, len(dist)):
            if alvo <= dist[i]:
                a, b = trecho[i - 1], trecho[i]
                t = (alvo - dist[i - 1]) / max(dist[i] - dist[i - 1], 1e-12)
                return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        return trecho[-1]
    def _atualizar_trens_no_mapa(self):
        ids_ativos = {f"trem_{trem.id}" for trem in self.simulacao.trens}
        for chave in set(self.marcadores_trens) - ids_ativos:
            marker = self.marcadores_trens.pop(chave)
            try:
                marker.delete()
            except tk.TclError:
                pass
        for trem in self.simulacao.trens:
            linha = self.linhas.get(trem.linha)
            if not linha:
                continue
            estacoes = linha["estacoes"]
            idx = estacoes.index(trem.estacao_atual)
            direcao = 1 if trem.sentido == "ida" else -1
            proximo = idx + direcao
            if 0 <= proximo < len(estacoes):
                lat, lon = self._ponto_no_traco(trem.linha, trem.estacao_atual, estacoes[proximo], trem.progresso)
            else:
                lat, lon = COORDENADAS_ESTACOES[trem.estacao_atual]
            chave = f"trem_{trem.id}"
            if chave in self.marcadores_trens:
                self.marcadores_trens[chave].set_position(lat, lon)
            else:
                self.marcadores_trens[chave] = self.map_widget.set_marker(lat, lon, text=f"🚆 {trem.linha}")
