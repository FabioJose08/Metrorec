import tkinter as tk
from tkinter import ttk, messagebox

from operacao import STATUS_LINHA, STATUS_MAQUINISTA, STATUS_TREM, TIPOS_OCORRENCIA


class PainelAdministracao(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#F2F7FC")
        self.app = app
        self.gestor = app.operacao
        abas = ttk.Notebook(self)
        abas.pack(fill="both", expand=True)
        self.configuracao = ttk.Frame(abas, padding=12)
        self.equipe = ttk.Frame(abas, padding=12)
        self.frota = ttk.Frame(abas, padding=12)
        self.ocorrencias = ttk.Frame(abas, padding=12)
        for frame, titulo in ((self.configuracao, "Tarifa e linhas"), (self.equipe, "Maquinistas"),
                              (self.frota, "Trens"), (self.ocorrencias, "Ocorrências")):
            abas.add(frame, text=titulo)
        self._montar_configuracao()
        self._montar_equipe()
        self._montar_frota()
        self._montar_ocorrencias()
        self._atualizar_tudo()

    @staticmethod
    def _tabela(parent, colunas, larguras):
        quadro = ttk.Frame(parent)
        quadro.pack(fill="both", expand=True)
        tabela = ttk.Treeview(quadro, columns=colunas, show="headings", height=9)
        for nome, largura in zip(colunas, larguras):
            tabela.heading(nome, text=nome.capitalize())
            tabela.column(nome, width=largura, minwidth=45, anchor="w", stretch=False)
        barra_y = ttk.Scrollbar(quadro, orient="vertical", command=tabela.yview)
        barra_x = ttk.Scrollbar(quadro, orient="horizontal", command=tabela.xview)
        tabela.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)
        tabela.grid(row=0, column=0, sticky="nsew")
        barra_y.grid(row=0, column=1, sticky="ns")
        barra_x.grid(row=1, column=0, sticky="ew")
        quadro.rowconfigure(0, weight=1)
        quadro.columnconfigure(0, weight=1)
        return tabela

    @staticmethod
    def _botao(parent, texto, comando):
        ttk.Button(parent, text=texto, command=comando).pack(side="left", padx=(0, 8), pady=8)

    @staticmethod
    def _selecionado(tabela):
        selecao = tabela.selection()
        return tabela.item(selecao[0], "values") if selecao else None

    @staticmethod
    def _limpar_tabela(tabela):
        itens = tabela.get_children()
        if itens:
            tabela.delete(*itens)

    def _montar_configuracao(self):
        topo = ttk.LabelFrame(self.configuracao, text="Tarifa padrão da rede", padding=10)
        topo.pack(fill="x", pady=(0, 12))
        self.tarifa = tk.StringVar()
        ttk.Label(topo, text="Valor (R$)").pack(side="left")
        ttk.Entry(topo, textvariable=self.tarifa, width=12).pack(side="left", padx=8)
        self._botao(topo, "Aplicar às três linhas", self._salvar_tarifa)
        quadro = ttk.Frame(self.configuracao)
        quadro.pack(fill="both", expand=True)
        self.tabela_linhas = self._tabela(quadro, ("linha", "status", "intervalo", "tarifa"),
                                         (210, 210, 130, 130))
        self.tabela_linhas.bind("<<TreeviewSelect>>", self._selecionar_linha)
        form = ttk.LabelFrame(self.configuracao, text="Operação por linha", padding=10)
        form.pack(fill="x", pady=(10, 0))
        self.linha = tk.StringVar()
        self.status_linha = tk.StringVar()
        self.intervalo = tk.StringVar()
        ttk.Label(form, text="Linha").grid(row=0, column=0, sticky="w")
        ttk.Combobox(form, textvariable=self.linha, values=list(self.gestor.linhas),
                     state="readonly", width=18).grid(row=1, column=0, padx=(0, 12), sticky="ew")
        ttk.Label(form, text="Status operacional").grid(row=0, column=1, sticky="w")
        ttk.Combobox(form, textvariable=self.status_linha, values=STATUS_LINHA,
                     state="readonly", width=22).grid(row=1, column=1, padx=(0, 12), sticky="ew")
        ttk.Label(form, text="Intervalo de referência (min)").grid(row=0, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.intervalo, width=12).grid(row=1, column=2, padx=(0, 12))
        ttk.Button(form, text="Salvar operação", command=self._salvar_linha).grid(row=1, column=3)
        ttk.Label(form, text="Referência usada para estimar a espera; os horários cadastrados permanecem fixos.",
                  foreground="#5D7190").grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 0))

    def _selecionar_linha(self, _evento=None):
        valores = self._selecionado(self.tabela_linhas)
        if valores:
            self.linha.set(valores[0])
            self.status_linha.set(valores[1])
            self.intervalo.set(valores[2])

    def _salvar_tarifa(self):
        try:
            self.gestor.atualizar_tarifa(self.tarifa.get())
            self._atualizar_tudo()
            messagebox.showinfo("Tarifa", "A tarifa foi atualizada nas três linhas.", parent=self)
        except (ValueError, OSError) as erro:
            messagebox.showerror("Tarifa inválida", str(erro), parent=self)

    def _salvar_linha(self):
        try:
            self.gestor.atualizar_linha(self.linha.get(), self.status_linha.get(), self.intervalo.get())
            self._atualizar_tudo()
            messagebox.showinfo("Operação", "Configuração da linha salva.", parent=self)
        except (ValueError, OSError) as erro:
            messagebox.showerror("Dados inválidos", str(erro), parent=self)

    def _montar_equipe(self):
        barra = ttk.Frame(self.equipe)
        barra.pack(fill="x")
        self._botao(barra, "Adicionar maquinista", self._novo_maquinista)
        self._botao(barra, "Editar selecionado", self._editar_selecionado)
        self._botao(barra, "Remover selecionado", self._remover_maquinista)
        quadro = ttk.Frame(self.equipe)
        quadro.pack(fill="both", expand=True)
        self.tabela_equipe = self._tabela(quadro, ("id", "nome", "matrícula", "status", "trem"),
                                          (60, 240, 150, 150, 220))

    def _novo_maquinista(self):
        self._form_maquinista()

    def _editar_selecionado(self):
        valores = self._selecionado(self.tabela_equipe)
        if not valores:
            messagebox.showwarning("Maquinistas", "Selecione um maquinista.", parent=self)
            return
        registro = next(m for m in self.gestor.maquinistas if m["id"] == int(valores[0]))
        self._form_maquinista(registro)

    def _form_maquinista(self, registro=None):
        janela = tk.Toplevel(self.app.root)
        janela.title("Cadastro de maquinista")
        janela.geometry("430x310")
        janela.resizable(False, False)
        janela.transient(self.app.root)
        janela.grab_set()
        corpo = ttk.Frame(janela, padding=18)
        corpo.pack(fill="both", expand=True)
        nome = tk.StringVar(value=registro.get("nome", "") if registro else "")
        matricula = tk.StringVar(value=registro.get("matricula", "") if registro else "")
        status = tk.StringVar(value=registro.get("status", "Disponível") if registro else "Disponível")
        designacoes = {"Sem designação": None}
        designacoes.update({f'Trem {t["id"]:02} — {t["linha"]}': t["id"] for t in self.gestor.trens})
        atual = next((label for label, tid in designacoes.items()
                      if registro and tid == registro.get("trem_id")), "Sem designação")
        trem = tk.StringVar(value=atual)
        campos = (("Nome", nome), ("Matrícula", matricula))
        for i, (rotulo, variavel) in enumerate(campos):
            ttk.Label(corpo, text=rotulo).grid(row=i * 2, column=0, sticky="w", pady=(0, 3))
            ttk.Entry(corpo, textvariable=variavel).grid(row=i * 2 + 1, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(corpo, text="Status").grid(row=4, column=0, sticky="w")
        ttk.Combobox(corpo, textvariable=status, values=STATUS_MAQUINISTA,
                     state="readonly").grid(row=5, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(corpo, text="Trem designado").grid(row=6, column=0, sticky="w")
        ttk.Combobox(corpo, textvariable=trem, values=list(designacoes),
                     state="readonly").grid(row=7, column=0, sticky="ew", pady=(0, 12))
        corpo.columnconfigure(0, weight=1)

        def salvar():
            try:
                self.gestor.salvar_maquinista(
                    nome.get(), matricula.get(), status.get(), designacoes[trem.get()],
                    registro.get("id") if registro else None)
                self._atualizar_tudo()
                janela.destroy()
            except (ValueError, OSError) as erro:
                messagebox.showerror("Cadastro inválido", str(erro), parent=janela)

        ttk.Button(corpo, text="Salvar", command=salvar).grid(row=8, column=0, sticky="e")

    def _remover_maquinista(self):
        valores = self._selecionado(self.tabela_equipe)
        if not valores:
            messagebox.showwarning("Maquinistas", "Selecione um maquinista.", parent=self)
            return
        if not messagebox.askyesno("Remover maquinista", "Confirma a remoção do cadastro?", parent=self):
            return
        try:
            self.gestor.remover_maquinista(int(valores[0]))
            self._atualizar_tudo()
        except (ValueError, OSError) as erro:
            messagebox.showerror("Não foi possível remover", str(erro), parent=self)

    def _montar_frota(self):
        barra = ttk.Frame(self.frota)
        barra.pack(fill="x")
        self._botao(barra, "Adicionar trem", self._novo_trem)
        self._botao(barra, "Editar trem selecionado", self._editar_trem)
        self._botao(barra, "Remover trem selecionado", self._remover_trem)
        quadro = ttk.Frame(self.frota)
        quadro.pack(fill="both", expand=True)
        self.tabela_frota = self._tabela(quadro, ("trem", "linha", "estação", "status", "maquinista"),
                                         (80, 160, 200, 150, 220))
        controles = ttk.Frame(self.frota)
        controles.pack(fill="x", pady=(10, 0))
        self.status_trem = tk.StringVar(value="Disponível")
        ttk.Label(controles, text="Novo status").pack(side="left", padx=(0, 8))
        ttk.Combobox(controles, textvariable=self.status_trem, values=STATUS_TREM,
                     state="readonly", width=18).pack(side="left")
        self._botao(controles, "Atualizar trem selecionado", self._salvar_trem)

    def _novo_trem(self):
        self._form_trem()

    def _editar_trem(self):
        valores = self._selecionado(self.tabela_frota)
        if not valores:
            messagebox.showwarning("Frota", "Selecione um trem.", parent=self)
            return
        trem = next(t for t in self.gestor.trens if t["id"] == int(valores[0]))
        self._form_trem(trem)

    def _remover_trem(self):
        valores = self._selecionado(self.tabela_frota)
        if not valores:
            messagebox.showwarning("Frota", "Selecione um trem.", parent=self)
            return
        if not messagebox.askyesno("Remover trem", "Confirma a remoção deste trem da frota?", parent=self):
            return
        try:
            self.gestor.remover_trem(int(valores[0]))
            self._atualizar_tudo()
        except (ValueError, OSError) as erro:
            messagebox.showerror("Não foi possível remover", str(erro), parent=self)

    def _form_trem(self, registro=None):
        janela = tk.Toplevel(self.app.root)
        janela.title("Cadastro de trem")
        janela.geometry("420x230")
        janela.transient(self.app.root)
        janela.grab_set()
        corpo = ttk.Frame(janela, padding=18)
        corpo.pack(fill="both", expand=True)
        linha = tk.StringVar(value=registro["linha"] if registro else next(iter(self.gestor.linhas)))
        estacoes = tk.StringVar(value=registro.get("estacao", self.gestor.linhas[linha.get()]["estacoes"][0]) if registro else self.gestor.linhas[linha.get()]["estacoes"][0])
        ttk.Label(corpo, text="Linha").grid(row=0, column=0, sticky="w")
        seletor_linha = ttk.Combobox(corpo, textvariable=linha, values=list(self.gestor.linhas), state="readonly")
        seletor_linha.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(corpo, text="Estação atual").grid(row=2, column=0, sticky="w")
        seletor_estacao = ttk.Combobox(corpo, textvariable=estacoes, state="readonly")
        seletor_estacao.grid(row=3, column=0, sticky="ew", pady=(0, 12))

        def atualizar_estacoes(_evento=None):
            opcoes = self.gestor.linhas[linha.get()]["estacoes"]
            seletor_estacao.configure(values=opcoes)
            if estacoes.get() not in opcoes:
                estacoes.set(opcoes[0])

        seletor_linha.bind("<<ComboboxSelected>>", atualizar_estacoes)
        atualizar_estacoes()

        def salvar():
            try:
                if registro:
                    self.gestor.editar_trem(registro["id"], linha.get(), estacoes.get())
                else:
                    self.gestor.adicionar_trem(linha.get(), estacoes.get())
                self._atualizar_tudo()
                janela.destroy()
            except (ValueError, OSError) as erro:
                messagebox.showerror("Cadastro de trem", str(erro), parent=janela)

        corpo.columnconfigure(0, weight=1)
        ttk.Button(corpo, text="Salvar", command=salvar).grid(row=4, column=0, sticky="e")

    def _salvar_trem(self):
        valores = self._selecionado(self.tabela_frota)
        if not valores:
            messagebox.showwarning("Frota", "Selecione um trem.", parent=self)
            return
        try:
            self.gestor.atualizar_trem(int(valores[0]), self.status_trem.get())
            self._atualizar_tudo()
        except (ValueError, OSError) as erro:
            messagebox.showerror("Frota", str(erro), parent=self)

    def _montar_ocorrencias(self):
        barra = ttk.Frame(self.ocorrencias)
        barra.pack(fill="x")
        self._botao(barra, "Registrar ocorrência", self._nova_ocorrencia)
        self._botao(barra, "Marcar como resolvida", self._resolver_ocorrencia)
        quadro = ttk.Frame(self.ocorrencias)
        quadro.pack(fill="both", expand=True)
        self.tabela_ocorrencias = self._tabela(
            quadro, ("id", "data", "linha", "tipo", "descrição", "status"),
            (55, 140, 150, 150, 430, 110))

    def _nova_ocorrencia(self):
        janela = tk.Toplevel(self.app.root)
        janela.title("Registrar ocorrência")
        janela.geometry("440x300")
        janela.transient(self.app.root)
        janela.grab_set()
        corpo = ttk.Frame(janela, padding=18)
        corpo.pack(fill="both", expand=True)
        linha = tk.StringVar(value=next(iter(self.gestor.linhas)))
        tipo = tk.StringVar(value=TIPOS_OCORRENCIA[0])
        descricao = tk.StringVar()
        for row, rotulo, variavel, valores in (
            (0, "Linha", linha, list(self.gestor.linhas)),
            (2, "Tipo", tipo, TIPOS_OCORRENCIA),
        ):
            ttk.Label(corpo, text=rotulo).grid(row=row, column=0, sticky="w")
            ttk.Combobox(corpo, textvariable=variavel, values=valores,
                         state="readonly").grid(row=row + 1, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(corpo, text="Descrição").grid(row=4, column=0, sticky="w")
        ttk.Entry(corpo, textvariable=descricao).grid(row=5, column=0, sticky="ew", pady=(0, 10))
        corpo.columnconfigure(0, weight=1)

        def salvar():
            try:
                self.gestor.registrar_ocorrencia(linha.get(), tipo.get(), descricao.get())
                self._atualizar_tudo()
                janela.destroy()
            except (ValueError, OSError) as erro:
                messagebox.showerror("Ocorrência", str(erro), parent=janela)

        ttk.Button(corpo, text="Registrar", command=salvar).grid(row=6, column=0, sticky="e")

    def _resolver_ocorrencia(self):
        valores = self._selecionado(self.tabela_ocorrencias)
        if not valores:
            messagebox.showwarning("Ocorrências", "Selecione uma ocorrência.", parent=self)
            return
        try:
            self.gestor.resolver_ocorrencia(int(valores[0]))
            self._atualizar_tudo()
        except (ValueError, OSError) as erro:
            messagebox.showerror("Ocorrências", str(erro), parent=self)

    def _atualizar_tudo(self):
        self.tarifa.set(f"{self.gestor.tarifa:.2f}".replace(".", ","))
        self._limpar_tabela(self.tabela_linhas)
        for nome, linha in self.gestor.linhas.items():
            self.tabela_linhas.insert("", "end", iid=nome,
                                      values=(nome, linha["status"], linha["intervalo"],
                                              f'R$ {linha["tarifa"]:.2f}'.replace(".", ",")))
        if not self.linha.get() and self.gestor.linhas:
            self.linha.set(next(iter(self.gestor.linhas)))
            self._selecionar_linha_da_config()
        self._limpar_tabela(self.tabela_equipe)
        for m in self.gestor.maquinistas:
            trem = next((t for t in self.gestor.trens if t["id"] == m.get("trem_id")), None)
            designacao = f'Trem {trem["id"]:02} — {trem["linha"]}' if trem else "Sem designação"
            self.tabela_equipe.insert("", "end", values=(
                m["id"], m["nome"], m.get("matricula", ""), m["status"], designacao))
        self._limpar_tabela(self.tabela_frota)
        equipe = {m["id"]: m["nome"] for m in self.gestor.maquinistas}
        for t in self.gestor.trens:
            self.tabela_frota.insert("", "end", values=(
                t["id"], t["linha"], t.get("estacao", self.gestor.linhas[t["linha"]]["estacoes"][0]),
                t["status"], equipe.get(t.get("maquinista_id"), "Sem designação")))
        self._limpar_tabela(self.tabela_ocorrencias)
        for o in self.gestor.ocorrencias:
            self.tabela_ocorrencias.insert("", "end", values=(
                o["id"], o["data"], o["linha"], o["tipo"], o["descricao"], o["status"]))

    def _selecionar_linha_da_config(self):
        nome = self.linha.get()
        dados = self.gestor.linhas.get(nome)
        if dados:
            self.status_linha.set(dados["status"])
            self.intervalo.set(str(dados["intervalo"]))
