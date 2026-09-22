import tkinter as tk
import webbrowser
from urllib.parse import quote
from tkinter import ttk, messagebox

from dados import LINHAS, STATUS_DISPONIVEIS
from simulacao import SimulacaoTrens
from viagens import calcular_rota_na_linha, montar_rota_integrada, proximo_horario
from utilitarios import formatar_reais, horario_atual, data_atual, minutos_para_texto


C = {
    "fundo": "#eef2f6", "topo": "#15283f", "texto": "#172b40", "sec": "#667587",
    "card": "white", "borda": "#d9e1ea", "botao": "#071b2f", "hover": "#0d4d76", "mapa": "#f8fafc",
    "verde": "#198754", "amarelo": "#b77900", "laranja": "#d97706", "vermelho": "#c0392b",
}
CORES_LINHAS = {"Jaboatão": "#d81010", "Camaragibe": "#e67f18", "Sul": "#0b1aec"}
POSICOES = {
    "Camaragibe": (120,120), "Cosme e Damião": (180,160), "Rodoviária": (260,180),
    "Curado": (340,240), "Alto do Céu": (420,280), "Coqueiral": (500,320), "Tejipió": (560,350),
    "Barro": (620,390), "Werneck": (680,420), "Santa Luzia": (750,460), "Mangueira": (800,500),
    "Ipiranga": (850,530), "Afogados": (900,560), "Joana Bezerra": (940,590), "Recife": (1030,620),
    "Jaboatão": (160,680), "Engenho Velho": (260,640), "Floriano": (340,600), "Cavaleiro": (420,560),
    "Cajueiro Seco": (180,170), "Prazeres": (260,230), "Monte dos Guararapes": (340,280),
    "Porta Larga": (420,330), "Aeroporto": (500,380), "Tancredo Neves": (570,420),
    "Shopping": (640,480), "Antônio Falcão": (720,530), "Imbiribeira": (780,570), "Largo da Paz": (860,610)
}


class MetroRecApp:
    def __init__(self, root):
        self.root, self.linhas = root, LINHAS
        self.linha_atual = None
        self.topo = self.conteudo = self.mapa_canvas = None
        self.mapa_zoom, self.simulacao_timer_id = 1.0, None
        self.simulacao = SimulacaoTrens(self.linhas)
        self._janela()
        self._estilos()
        self.tela_inicial()

    def _janela(self):
        self.root.title("METROREC - Sistema de Informações e Planejamento")
        self.root.geometry("1200x760")
        self.root.minsize(1000, 650)
        self.root.configure(bg=C["fundo"])
        self.root.option_add("*Font", ("Segoe UI", 10))

    def _estilos(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Metro.TButton", font=("Segoe UI", 11, "bold"), padding=(16,10),
                    foreground="white", background=C["botao"], borderwidth=2, relief="raised")
        s.map("Metro.TButton", background=[("active", C["hover"]), ("pressed", "#020710")])
        s.configure("Metro.Nav.TButton", font=("Segoe UI", 10, "bold"), padding=(14,8),
                    foreground="white", background="#102b4f")
        s.map("Metro.Nav.TButton", background=[("active", "#0b5a8a")])
        s.configure("Metro.TCombobox", font=("Segoe UI",11), padding=6,
                    fieldbackground="white", foreground=C["texto"])
        s.configure("Metro.TEntry", font=("Segoe UI",11), padding=6)
        s.configure("Treeview", font=("Segoe UI",10), rowheight=34)
        s.configure("Treeview.Heading", font=("Segoe UI",10,"bold"), padding=7)

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
                        highlightthickness=1, highlightbackground=C["borda"], **kw)

    def _botao(self, parent, texto, comando, estilo="Metro.TButton", **kw):
        return ttk.Button(parent, text=texto, command=comando, style=estilo, **kw)

    def _cabecalho(self, titulo, subtitulo=""):
        self._limpar()
        self.topo = tk.Frame(self.root, bg=C["topo"], height=88)
        self.topo.pack(fill="x")
        self.topo.pack_propagate(False)
        esquerda = tk.Frame(self.topo, bg=C["topo"])
        esquerda.pack(side="left", padx=28, fill="y")
        self._label(esquerda, "🚇 METROREC", 18, "white", "bold", C["topo"]).pack(anchor="w", pady=(12,0))
        self._label(esquerda, titulo, 10, "#bdc9d7", bg=C["topo"]).pack(anchor="w")
        relogio = self._label(self.topo, "", 16, "white", "bold", C["topo"])
        relogio.pack(side="right", padx=28)

        def atualizar():
            if relogio.winfo_exists():
                relogio.config(text=f"{horario_atual()}  |  {data_atual()}")
                relogio.after(1000, atualizar)
        atualizar()

        self.conteudo = tk.Frame(self.root, bg=C["fundo"])
        self.conteudo.pack(fill="both", expand=True)
        area = tk.Frame(self.conteudo, bg=C["fundo"])
        area.pack(fill="both", expand=True, padx=30, pady=25)
        self._label(area, titulo, 26, C["texto"], "bold", C["fundo"]).pack(anchor="w")
        if subtitulo:
            self._label(area, subtitulo, 11, C["sec"], bg=C["fundo"]).pack(anchor="w", pady=(4,20))
        return area

    def _nav(self, parent):
        barra = tk.Frame(parent, bg=C["fundo"])
        barra.pack(fill="x", pady=(0,8))
        botoes = [
            ("Início", self.tela_inicial),
            ("Dashboard", self.tela_dashboard),
            ("Linhas", self.tela_todas_linhas),
            ("Mapa da Rede", self.tela_mapa_rede),
            ("Planejar viagem", self.janela_planejamento_global)
        ]
        for texto, comando in botoes:
            self._botao(barra, texto, comando, "Metro.Nav.TButton").pack(side="left", padx=4)

    def _janela_nova(self, titulo, largura, altura):
        w = tk.Toplevel(self.root)
        w.title(f"METROREC - {titulo}")
        w.geometry(f"{largura}x{altura}")
        w.minsize(max(450, largura-80), max(350, altura-100))
        w.configure(bg=C["fundo"])
        w.transient(self.root)
        w.grab_set()
        return w

    def _campo(self, parent, rotulo, valores, variavel=None):
        self._label(parent, rotulo, 10, C["texto"], "bold", "white").pack(anchor="w")
        combo = ttk.Combobox(parent, values=valores, textvariable=variavel,
                             state="readonly", style="Metro.TCombobox")
        combo.pack(fill="x", pady=(5,15))
        return combo

    def _campo_grid(self, parent, rotulo, variavel, valores, row, col):
        padx = (0,10) if col == 0 else (10,0)
        self._label(parent, rotulo, 10, C["texto"], "bold", "white").grid(
            row=row, column=col, sticky="w", padx=padx, pady=6)
        if valores is None:
            item = ttk.Entry(parent, textvariable=variavel, style="Metro.TEntry")
        else:
            item = ttk.Combobox(parent, values=valores, textvariable=variavel,
                                state="readonly", style="Metro.TCombobox")
        item.grid(row=row+1, column=col, sticky="ew", padx=padx, pady=(0,15))
        return item

    def _area_rolavel(self, parent):
        box = tk.Frame(parent, bg="white", bd=1, relief="solid",
                       highlightthickness=1, highlightbackground=C["borda"])
        canvas = tk.Canvas(box, bg="white", highlightthickness=0)
        barra = ttk.Scrollbar(box, orient="vertical", command=canvas.yview)
        area = tk.Frame(canvas, bg="white")
        area.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=area, anchor="nw")
        canvas.configure(yscrollcommand=barra.set)
        canvas.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        return box, area

    def status_cor(self, status):
        return {
            "Operação normal": C["verde"], "Atenção": C["amarelo"],
            "Operação reduzida": C["laranja"], "Interrompida": C["vermelho"]
        }.get(status, "#68737d")

    def todas_estacoes(self):
        return sorted({e for l in self.linhas.values() for e in l["estacoes"]})

    def tela_inicial(self):
        self.linha_atual = None
        area = self._cabecalho(
            "Sistema de Informações do Metrô",
            "Consulte linhas, horários, estações e planeje sua viagem")
        self._nav(area)
        self._label(area, "Informações das linhas Jaboatão, Camaragibe e Sul.", 12, "#425466", bg=C["fundo"]).pack(
            anchor="w", pady=(0,18))

        cards = tk.Frame(area, bg=C["fundo"])
        cards.pack(fill="x")

        for nome, linha in self.linhas.items():
            card = self._card(cards, width=330, height=250)
            card.pack(side="left", fill="both", expand=True, padx=7)
            card.pack_propagate(False)
            tk.Frame(card, bg="#1f5fa8", height=8).pack(fill="x")
            self._label(card, linha["codigo"], 11, C["sec"], "bold", "white").pack(anchor="w", padx=22, pady=(18,0))
            self._label(card, nome, 20, C["texto"], "bold", "white").pack(anchor="w", padx=22)
            self._label(card, linha["status"], 10, self.status_cor(linha["status"]), "bold", "white").pack(
                anchor="w", padx=22, pady=(5,3))
            self._label(card, f"{len(linha['estacoes'])} estações • {formatar_reais(linha['tarifa'])}",
                        10, C["sec"], bg="white").pack(anchor="w", padx=22)
            self._botao(card, "Acessar linha", lambda n=nome: self.tela_linha(n)).pack(
                fill="x", padx=22, pady=(12,18))

        rodape = tk.Frame(area, bg=C["fundo"])
        rodape.pack(fill="x", pady=20)
        self._botao(rodape, "⚙ Controle do sistema", self.tela_admin).pack(side="right", padx=4)

    def tela_linha(self, nome):
        self.linha_atual = nome
        linha = self.linhas[nome]
        area = self._cabecalho(
            f"{linha['codigo']} • Linha {nome}",
            f"{linha['status']} • Tarifa: {formatar_reais(linha['tarifa'])} • Intervalo: {linha['intervalo']} min")
        self._nav(area)
        grid = tk.Frame(area, bg=C["fundo"])
        grid.pack(fill="both", expand=True)
        for col in range(4):
            grid.columnconfigure(col, weight=1)
        opcoes = [
            ("🧭","Planejar viagem",lambda:self.janela_planejamento(nome)),
            ("📍","Estações",lambda:self.janela_estacoes(nome)),
            ("🕐","Horários",lambda:self.janela_horarios(nome)),
            ("🚇","Próximo metrô",lambda:self.mostrar_proximo(nome)),
            ("⚠","Status da linha",lambda:self.janela_status(nome)),
            ("💰","Tarifa",lambda:self.mostrar_tarifa(nome)),
            ("ℹ","Informações",lambda:self.janela_informacoes(nome))
        ]
        for i, (icone, titulo, comando) in enumerate(opcoes):
            card = self._card(grid)
            card.grid(row=i//4, column=i%4, sticky="nsew", padx=7, pady=7)
            self._label(card, icone, 27, bg="white").pack(pady=(24,8))
            self._label(card, titulo, 12, C["texto"], "bold", "white").pack()
            self._botao(card, "Abrir", comando).pack(fill="x", padx=25, pady=20)

    def tela_dashboard(self):
        area = self._cabecalho("Visão geral", "Resumo rápido do sistema METROREC")
        self._nav(area)
        total = sum(len(l["estacoes"]) for l in self.linhas.values())
        normais = sum(l["status"]=="Operação normal" for l in self.linhas.values())
        indicadores = [
            ("Linhas", len(self.linhas), "Linhas cadastradas"),
            ("Estações", total, "Somando as três linhas"),
            ("Operação normal", normais, "Linhas em situação normal"),
            ("Atenção", len(self.linhas)-normais, "Linhas fora do padrão normal")
        ]
        cards = tk.Frame(area, bg=C["fundo"])
        cards.pack(fill="x", pady=10)
        for titulo, valor, detalhe in indicadores:
            card = self._card(cards)
            card.pack(side="left", fill="both", expand=True, padx=5)
            self._label(card, titulo, 10, C["sec"], "bold", "white").pack(anchor="w", padx=20, pady=(18,0))
            self._label(card, str(valor), 25, C["texto"], "bold", "white").pack(anchor="w", padx=20)
            self._label(card, detalhe, 9, "#8a98a8", bg="white").pack(anchor="w", padx=20, pady=(0,18))

        baixo = tk.Frame(area, bg=C["fundo"])
        baixo.pack(fill="both", expand=True, pady=10)
        esquerda = self._card(baixo)
        direita = self._card(baixo)
        esquerda.pack(side="left", fill="both", expand=True, padx=(0,7))
        direita.pack(side="right", fill="both", expand=True, padx=(7,0))
        self._label(esquerda, "Situação das linhas", 15, C["texto"], "bold", "white").pack(anchor="w", padx=20, pady=18)
        for nome, linha in self.linhas.items():
            item = tk.Frame(esquerda, bg="#f6f8fa")
            item.pack(fill="x", padx=18, pady=5)
            self._label(item, f"{linha['codigo']} • {nome}", 10, C["texto"], "bold", "#f6f8fa").pack(side="left", padx=12, pady=12)
            self._label(item, linha["status"], 9, self.status_cor(linha["status"]), "bold", "#f6f8fa").pack(side="right", padx=12)

        self._label(direita, "Próximo metrô disponível", 15, C["texto"], "bold", "white").pack(anchor="w", padx=20, pady=18)
        prox = self.proximo_global()
        if prox:
            nome, horario, falta = prox
            self._label(direita, nome, 20, "#1f5fa8", "bold", "white").pack(anchor="w", padx=20)
            self._label(direita, f"Horário: {horario}", 12, "#425466", bg="white").pack(anchor="w", padx=20, pady=4)
            self._label(direita, minutos_para_texto(falta), 11, C["verde"], "bold", "white").pack(anchor="w", padx=20)
        else:
            self._label(direita, "Não há mais horários cadastrados hoje.", 11, C["sec"], bg="white").pack(anchor="w", padx=20)
        self._botao(direita, "Atualizar", self.tela_dashboard).pack(fill="x", padx=20, pady=25)

    def proximo_global(self):
        itens = []
        for nome, linha in self.linhas.items():
            horario, falta = proximo_horario(linha)
            if horario is not None:
                itens.append((nome, horario, falta))
        return min(itens, key=lambda x:x[2]) if itens else None

    def tela_todas_linhas(self):
        area = self._cabecalho("Todas as linhas", "Escolha uma linha para consultar seus detalhes")
        self._nav(area)
        lista = tk.Frame(area, bg=C["fundo"])
        lista.pack(fill="both", expand=True)
        for nome, linha in self.linhas.items():
            card = self._card(lista)
            card.pack(fill="x", pady=7)
            esquerda = tk.Frame(card, bg="white")
            esquerda.pack(side="left", fill="both", expand=True, padx=20, pady=17)
            self._label(esquerda, f"{linha['codigo']} • {nome}", 16, C["texto"], "bold", "white").pack(anchor="w")
            self._label(esquerda, f"{len(linha['estacoes'])} estações • {linha['estacoes'][0]} → {linha['estacoes'][-1]}",
                        10, C["sec"], bg="white").pack(anchor="w", pady=4)
            self._label(card, linha["status"], 10, self.status_cor(linha["status"]), "bold", "white").pack(side="left", padx=15)
            self._botao(card, "Acessar", lambda n=nome:self.tela_linha(n)).pack(side="right", padx=20)

    def janela_estacoes(self, nome):
        linha = self.linhas[nome]
        w = self._janela_nova("Estações", 600, 600)
        self._cabecalho_janela(w, f"Estações • {nome}", f"{len(linha['estacoes'])} estações na linha {linha['codigo']}")
        box, area = self._area_rolavel(w)
        box.pack(fill="both", expand=True, padx=30, pady=(0,20))
        for i, estacao in enumerate(linha["estacoes"], 1):
            bg = "#eef6ff" if i%2 else "white"
            item = tk.Frame(area, bg=bg, bd=1, relief="solid", highlightthickness=1, highlightbackground=C["borda"])
            item.pack(fill="x", pady=4)
            self._label(item, f"{i:02d}", 10, "#1f5fa8", "bold", bg, width=5).pack(side="left", padx=10, pady=11)
            self._label(item, estacao, 11, C["texto"], "bold", bg).pack(side="left", pady=11)
            if estacao in ("Recife","Joana Bezerra"):
                tk.Label(item,text="CONEXÃO",font=("Segoe UI",8,"bold"),bg="#102b4f",fg="white").pack(side="right",padx=12,pady=11)

    def _cabecalho_janela(self, w, titulo, subtitulo):
        box = tk.Frame(w, bg=C["fundo"])
        box.pack(fill="x", padx=30, pady=(20,8))
        self._label(box,titulo,21,C["texto"],"bold",C["fundo"]).pack(anchor="w")
        self._label(box,subtitulo,10,C["sec"],bg=C["fundo"]).pack(anchor="w",pady=(4,0))

    def janela_horarios(self, nome):
        linha = self.linhas[nome]
        w = self._janela_nova("Horários", 720, 570)
        self._cabecalho_janela(w, f"Horários • Linha {linha['codigo']}", f"{len(linha['horarios'])} horários cadastrados")
        box, area = self._area_rolavel(w)
        box.pack(fill="both", expand=True, padx=30, pady=(0,20))
        for i, horario in enumerate(linha["horarios"]):
            tk.Label(area,text=horario,font=("Segoe UI",11,"bold"),bg="#eff6ff",fg="#102b4f",
                     width=12,pady=10,bd=1,relief="solid").grid(row=i//5,column=i%5,padx=7,pady=7,sticky="ew")

    def mostrar_proximo(self, nome):
        linha = self.linhas[nome]
        horario, falta = proximo_horario(linha)
        msg = (f"Linha {linha['codigo']} • {nome}\n\nPróximo metrô: {horario}\nTempo: {minutos_para_texto(falta)}"
               if horario else f"Linha {linha['codigo']}\n\nNão há mais horários cadastrados para hoje.")
        messagebox.showinfo("Próximo metrô", msg)

    def janela_status(self, nome):
        linha = self.linhas[nome]
        w = self._janela_nova("Status da linha", 500, 360)
        card = self._card(w)
        card.pack(fill="both", expand=True, padx=30, pady=30)
        self._label(card,"Status da linha",21,C["texto"],"bold","white").pack(pady=(25,8))
        self._label(card,f"{linha['codigo']} • {nome}",12,C["sec"],bg="white").pack()
        self._label(card,linha["status"],15,self.status_cor(linha["status"]),"bold","white").pack(pady=20)
        self._label(card,f"Intervalo médio: {linha['intervalo']} minutos",11,"#425466",bg="white").pack(pady=(0,25))

    def mostrar_tarifa(self, nome):
        linha = self.linhas[nome]
        messagebox.showinfo("Tarifa",f"Linha {linha['codigo']} • {nome}\n\nTarifa atual: {formatar_reais(linha['tarifa'])}")

    def janela_informacoes(self, nome):
        linha = self.linhas[nome]
        texto = "\n".join([
            f"Linha: {nome}", f"Código: {linha['codigo']}", f"Estações: {len(linha['estacoes'])}",
            f"Horários: {len(linha['horarios'])}", f"Tarifa: {formatar_reais(linha['tarifa'])}",
            f"Intervalo médio: {linha['intervalo']} min", f"Status: {linha['status']}",
            f"Primeira estação: {linha['estacoes'][0]}", f"Última estação: {linha['estacoes'][-1]}"
        ])
        messagebox.showinfo("Informações da linha",texto)

    def janela_planejamento_global(self):
        self.janela_planejamento()

    def janela_planejamento(self, nome_linha=None):
        w = self._janela_nova("Planejar viagem",700,650)
        self._cabecalho_janela(w,"Planejar viagem","Escolha a origem e o destino para calcular a rota")
        card = self._card(w); card.pack(fill="x",padx=30,pady=(0,12))
        dentro = tk.Frame(card,bg="white"); dentro.pack(fill="x",padx=24,pady=20)
        origem = self._campo(dentro,"Origem",self.todas_estacoes())
        destino = self._campo(dentro,"Destino",self.todas_estacoes())
        linha_var = tk.StringVar(value=nome_linha or "Todas as linhas")
        if nome_linha:
            self._label(dentro,f"Linha atual: {nome_linha}",10,C["texto"],"bold","white").pack(anchor="w")
        else:
            self._campo(dentro,"Priorizar linha",["Todas as linhas"]+list(self.linhas),linha_var)

        resultado = tk.Text(w,height=10,font=("Segoe UI",10),bg="white",fg=C["texto"],bd=1,relief="solid",padx=12,pady=12,wrap="word")
        resultado.pack(fill="both",expand=True,padx=30); resultado.config(state="disabled")

        def mostrar(texto):
            resultado.config(state="normal"); resultado.delete("1.0","end"); resultado.insert("1.0",texto); resultado.config(state="disabled")

        def calcular():
            o,d = origem.get(),destino.get()
            if not o or not d:
                messagebox.showwarning("Atenção","Selecione a origem e o destino."); return
            if o == d:
                messagebox.showwarning("Atenção","Origem e destino não podem ser iguais."); return
            nome = linha_var.get()
            if nome == "Todas as linhas":
                rota = montar_rota_integrada(self.linhas,o,d)
            else:
                rota = calcular_rota_na_linha(self.linhas[nome],o,d)
                if rota: rota["linha"] = nome
            if not rota:
                mostrar("Não foi possível encontrar uma rota com os dados cadastrados."); return
            texto = (
                f"ORIGEM: {o}\nDESTINO: {d}\n\nLINHA: {rota['linha']}\n"
                f"ESTAÇÕES PERCORRIDAS: {rota['estacoes']}\nTEMPO ESTIMADO: {rota['tempo']} minutos\n"
                f"TARIFA: {formatar_reais(rota['tarifa'])}\n"
            )
            if rota.get("trocas"): texto += f"INTEGRAÇÃO: 1 troca em {rota.get('conexao','estação de conexão')}\n"
            mostrar(texto + "\nROTA:\n" + " → ".join(rota["rota"]))

        self._botao(w,"Calcular viagem",calcular).pack(fill="x",padx=30,pady=14)

    def tela_admin(self):
        area = self._cabecalho("Controle do sistema","Área acadêmica para simular alterações durante a execução")
        self._nav(area)
        card = self._card(area); card.pack(fill="both",expand=True)
        self._label(card,"Alterar informações da linha",16,C["texto"],"bold","white").pack(anchor="w",padx=25,pady=(25,5))
        self._label(card,"As alterações ficam apenas enquanto o programa estiver aberto.",10,C["sec"],bg="white").pack(anchor="w",padx=25,pady=(0,20))
        form = tk.Frame(card,bg="white"); form.pack(fill="x",padx=25)
        form.columnconfigure(0,weight=1); form.columnconfigure(1,weight=1)
        linha_var,status_var,tarifa_var,intervalo_var = [tk.StringVar() for _ in range(4)]
        linha_var.set(next(iter(self.linhas)))
        linha_combo = self._campo_grid(form,"Linha",linha_var,list(self.linhas),0,0)
        self._campo_grid(form,"Status",status_var,STATUS_DISPONIVEIS,0,1)
        self._campo_grid(form,"Tarifa",tarifa_var,None,2,0)
        self._campo_grid(form,"Intervalo médio (min)",intervalo_var,None,2,1)

        area_h = tk.Frame(card,bg="white"); area_h.pack(fill="both",expand=True,padx=25,pady=10)
        self._label(area_h,"Horários cadastrados",11,C["texto"],"bold","white").pack(anchor="w")
        horarios = tk.Text(area_h,height=8,font=("Segoe UI",10),bg="#f7f9fb",bd=1,relief="solid")
        horarios.pack(fill="both",expand=True,pady=7)

        def carregar():
            l = self.linhas[linha_var.get()]
            status_var.set(l["status"]); tarifa_var.set(str(l["tarifa"])); intervalo_var.set(str(l["intervalo"]))
            horarios.delete("1.0","end"); horarios.insert("1.0",", ".join(l["horarios"]))

        def validar_horarios():
            lista = [h.strip() for h in horarios.get("1.0","end").split(",") if h.strip()]
            for h in lista:
                try:
                    hora,minuto = map(int,h.split(":"))
                    if not (0<=hora<=23 and 0<=minuto<=59): raise ValueError
                except ValueError:
                    messagebox.showerror("Erro",f"Horário inválido: {h}"); return None
            return lista

        def salvar():
            try:
                tarifa = float(tarifa_var.get().replace(",","."))
                intervalo = int(intervalo_var.get())
            except ValueError:
                messagebox.showerror("Erro","Tarifa e intervalo precisam ser numéricos."); return
            lista = validar_horarios()
            if lista is None or tarifa <= 0 or intervalo <= 0:
                if lista is not None: messagebox.showwarning("Atenção","Tarifa e intervalo devem ser maiores que zero.")
                return
            self.linhas[linha_var.get()].update(status=status_var.get(),tarifa=tarifa,intervalo=intervalo,horarios=lista)
            messagebox.showinfo("Sucesso","Informações atualizadas com sucesso.")

        linha_combo.bind("<<ComboboxSelected>>",lambda _:carregar())
        botoes = tk.Frame(card,bg="white"); botoes.pack(fill="x",padx=25,pady=(3,25))
        self._botao(botoes,"Carregar dados",carregar).pack(side="left")
        self._botao(botoes,"Salvar alterações",salvar).pack(side="left",padx=8)
        self._botao(botoes,"Voltar",self.tela_inicial).pack(side="right")
        carregar()

    def abrir_google_maps_estacao(self, estacao):
        q = quote(f"Metrorec {estacao} Recife Pernambuco")
        webbrowser.open(f"https://www.google.com/maps/search/?api=1&query={q}")

    def tela_mapa_rede(self):
        area = self._cabecalho("Mapa da Rede","Mapa da rede METROREC com referência visual de Recife")
        self._nav(area)
        self._controles_mapa(area)
        caixa = tk.Frame(area,bg=C["fundo"])
        caixa.pack(fill="both",expand=True)
        self.mapa_canvas = tk.Canvas(caixa,width=1000,height=550,bg=C["mapa"],highlightthickness=1,highlightbackground=C["borda"])
        self.mapa_canvas.configure(scrollregion=(0,0,1500,760),xscrollincrement=30,yscrollincrement=30)
        xb = ttk.Scrollbar(caixa,orient="horizontal",command=self.mapa_canvas.xview)
        yb = ttk.Scrollbar(caixa,orient="vertical",command=self.mapa_canvas.yview)
        self.mapa_canvas.configure(xscrollcommand=xb.set,yscrollcommand=yb.set)
        xb.pack(side="bottom",fill="x")
        yb.pack(side="right",fill="y")
        self.mapa_canvas.pack(side="left",fill="both",expand=True)
        self.mapa_zoom = 1.0
        self.mapa_canvas.bind("<ButtonPress-1>",self.iniciar_arraste_mapa)
        self.mapa_canvas.bind("<B1-Motion>",self.arrastar_mapa)
        self._desenhar_mapa()

        legenda=tk.Frame(area,bg=C["fundo"])
        legenda.pack(fill="x",pady=(8,0))
        for texto,cor in [("● Estação",C["texto"]),("━ L1 – Jaboatão",CORES_LINHAS["Jaboatão"]),("━ L2 – Camaragibe",CORES_LINHAS["Camaragibe"]),("━ L3 – Sul",CORES_LINHAS["Sul"])]:
            self._label(legenda,texto,10,cor,"bold",C["fundo"]).pack(side="left",padx=8)

    def _controles_mapa(self, area):
        sim = tk.Frame(area, bg=C["fundo"])
        sim.pack(fill="x", pady=(0,8))
        for texto, comando in [("▶ Iniciar", self.simulacao_iniciar), ("⏸ Pausar", self.simulacao_pausar), ("⏹ Parar", self.simulacao_parar), ("↻ Reiniciar", self.simulacao_reiniciar)]:
            self._botao(sim, texto, comando).pack(side="left", padx=4)
        self._label(sim, "Velocidade:", 10, C["texto"], "bold", C["fundo"]).pack(side="left", padx=(18,6))
        for v in (0.5, 1):
            self._botao(sim, f"{v:g}x", lambda valor=v: self.simulacao_alterar_velocidade(valor)).pack(side="left", padx=2)

    def _simulacao_ativa(self):
        return self.simulacao.ativo and not self.simulacao.paused and not self.simulacao.parado

    def _agendar_simulacao(self):
        self._cancelar_simulacao()
        if self.mapa_canvas and self._simulacao_ativa():
            self.simulacao_timer_id = self.mapa_canvas.after(int(1000/self.simulacao.velocidade),self.simulacao_tick)

    def _cancelar_simulacao(self):
        if self.mapa_canvas and self.simulacao_timer_id is not None:
            try:self.mapa_canvas.after_cancel(self.simulacao_timer_id)
            except tk.TclError:pass
        self.simulacao_timer_id=None

    def _desenhar_mapa(self):
        if self.mapa_canvas:
            self.desenhar_mapa_rede(self.mapa_canvas)

    def simulacao_iniciar(self):
        self.simulacao.iniciar(); self._desenhar_mapa(); self._agendar_simulacao()

    def simulacao_pausar(self):
        self.simulacao.pausar(); self._cancelar_simulacao(); self._desenhar_mapa()

    def simulacao_parar(self):
        self.simulacao.parar(); self._cancelar_simulacao(); self._desenhar_mapa()

    def simulacao_reiniciar(self):
        self._cancelar_simulacao(); self.simulacao.reiniciar(); self._desenhar_mapa(); self._agendar_simulacao()

    def simulacao_tick(self):
        if self._simulacao_ativa():
            self.simulacao.avancar(); self._desenhar_mapa(); self._agendar_simulacao()
        else:
            self._cancelar_simulacao()

    def simulacao_alterar_velocidade(self, valor):
        self.simulacao.alterar_velocidade(valor); self._agendar_simulacao()

    def iniciar_arraste_mapa(self, event):
        if self.mapa_canvas: self.mapa_canvas.scan_mark(event.x,event.y)

    def arrastar_mapa(self, event):
        if self.mapa_canvas: self.mapa_canvas.scan_dragto(event.x,event.y,gain=1)

    def desenhar_mapa_base(self, canvas):
        canvas.create_rectangle(0,0,1500,760,fill="#eef2f6",outline="#eef2f6")
        canvas.create_rectangle(70,70,1420,690,fill="#dce8ee",outline="#8ca3b7")
        canvas.create_polygon(80,120,180,90,300,120,390,150,530,120,700,110,830,140,980,120,1180,160,1320,170,
                             1400,260,1370,430,1400,590,1280,660,1010,640,840,680,640,640,480,650,270,620,130,620,80,500,
                             fill="#eef6f9",outline="#8fa8b7",width=2)
        for x in range(100,1400,80): canvas.create_line(x,80,x+40,700,fill="#b9c9d8",dash=(2,4))
        for y in range(100,700,70): canvas.create_line(80,y,1420,y+30,fill="#b9c9d8",dash=(2,4))

    def _desenhar_trens(self, canvas, pos):
        for trem in self.simulacao.trens:
            if trem.estacao_atual in pos:
                x,y=pos[trem.estacao_atual]; cor=CORES_LINHAS.get(trem.linha,C["botao"])
                canvas.create_text(x+24,y-12,text="🚇",font=("Segoe UI Emoji",14),fill=cor)
                canvas.create_text(x+30,y+16,text=f"T{trem.id:02d}",font=("Segoe UI",7,"bold"),fill=C["texto"])

    def desenhar_mapa_rede(self, canvas):
        canvas.delete("all"); self.desenhar_mapa_base(canvas)
        pos={n:(x*self.mapa_zoom,y*self.mapa_zoom) for n,(x,y) in POSICOES.items()}
        
        for nome, linha in self.linhas.items():
            cor=CORES_LINHAS[nome]
            for a,b in zip(linha["estacoes"],linha["estacoes"][1:]):
                x1,y1=pos[a]; x2,y2=pos[b]
                canvas.create_line(x1,y1,x2,y2,fill=cor,width=5,capstyle="round",smooth=True)

        mostradas=set()
        for nome, linha in self.linhas.items():
            cor=CORES_LINHAS[nome]
            for estacao in linha["estacoes"]:
                if estacao in mostradas: continue
                x,y=pos[estacao]
                item=canvas.create_oval(x-6,y-6,x+6,y+6,fill="white",outline=cor,width=3)
                canvas.create_text(x+12,y-8,text=estacao,anchor="w",font=("Segoe UI",8,"bold"),fill=C["texto"])
                canvas.tag_bind(item,"<Button-1>",lambda _,e=estacao:self.abrir_info_estacao(e))
                mostradas.add(estacao)

        for estacao in ("Joana Bezerra","Recife"):
            x,y=pos[estacao]; item=canvas.create_oval(x-13,y-13,x+13,y+13,fill=C["botao"],outline="white",width=3)
            canvas.tag_bind(item,"<Button-1>",lambda _,e=estacao:self.abrir_info_estacao(e))
        self._desenhar_trens(canvas,pos)
        canvas.create_text(50,30,text="Mapa da Rede METROREC",anchor="w",font=("Segoe UI",16,"bold"),fill=C["texto"])

    def abrir_info_estacao(self, estacao, linha_nome=None):
        disponiveis=[nome for nome,linha in self.linhas.items() if estacao in linha["estacoes"]]
        if not disponiveis:
            messagebox.showwarning("Atenção",f"A estação {estacao} não está cadastrada na rede."); return
        nome=linha_nome if linha_nome in disponiveis else disponiveis[0]
        linha=self.linhas[nome]; i=linha["estacoes"].index(estacao)
        proxima=linha["estacoes"][i+1] if i+1<len(linha["estacoes"]) else "Fim de linha"
        w=self._janela_nova(f"Estação • {estacao}",440,300)
        tk.Frame(w,bg=C["botao"],height=55).pack(fill="x")
        self._label(w,estacao,18,"white","bold",C["botao"]).place(x=16,y=10)
        info=tk.Frame(w,bg=C["fundo"]); info.pack(fill="both",expand=True,padx=16,pady=10)
        for texto in [f"Linha: {nome}",f"Status: {linha['status']}",f"Próxima estação: {proxima}",f"Linhas disponíveis: {', '.join(disponiveis)}"]:
            self._label(info,texto,10,C["texto"],bg=C["fundo"]).pack(anchor="w")
        botoes=tk.Frame(w,bg=C["fundo"]); botoes.pack(fill="x",padx=16,pady=(0,16))
        self._botao(botoes,"Ver no Google Maps",lambda:self.abrir_google_maps_estacao(estacao)).pack(side="left",padx=(0,8))
        self._botao(botoes,"Planejar viagem",lambda:(w.destroy(),self.janela_planejamento())).pack(side="left")