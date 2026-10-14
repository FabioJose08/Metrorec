"""Regras e persistência local do painel de administração demonstrativo."""
import json
import math
import os
import shutil
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


STATUS_LINHA = ("Operação normal", "Operação com restrições", "Indisponível")
STATUS_MAQUINISTA = ("Disponível", "Em serviço", "Afastado")
STATUS_TREM = ("Disponível", "Aguardando despacho", "Em operação", "Parado", "Interrompido", "Manutenção")
TIPOS_OCORRENCIA = ("Falha técnica", "Sinalização", "Energia", "Estação", "Segurança", "Outro")


def _arquivo_operacional():
    if not getattr(sys, "frozen", False):
        return Path(__file__).with_name("operacao.json")

    pasta = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "MetroREC"
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / "operacao.json"
    inicial = Path(sys._MEIPASS) / "operacao.json"
    if not arquivo.exists() and inicial.exists():
        shutil.copy2(inicial, arquivo)
    return arquivo


class GestorOperacional:
    def __init__(self, linhas, arquivo=None):
        self.linhas = linhas
        self.ao_atualizar_linha = None
        self.ao_atualizar_frota = None
        self.validar_despacho = None
        self.arquivo = Path(arquivo) if arquivo else _arquivo_operacional()
        tarifas = [float(linha["tarifa"]) for linha in linhas.values()]
        self.tarifa = tarifas[0] if tarifas else 0.0
        self.trens = [
            {"id": i, "linha": nome, "status": "Disponível", "maquinista_id": None}
            for i, nome in enumerate(linhas, 1)
        ]
        self.maquinistas = []
        self.ocorrencias = []
        self._carregar()
        self._aplicar_linhas()

    def _carregar(self):
        try:
            dados = json.loads(self.arquivo.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return
        if not isinstance(dados, dict):
            return
        tarifa = dados.get("tarifa")
        if isinstance(tarifa, (int, float)) and not isinstance(tarifa, bool) and math.isfinite(tarifa) and tarifa > 0:
            self.tarifa = round(float(tarifa), 2)
        configuracoes = dados.get("linhas", {})
        for nome, config in configuracoes.items() if isinstance(configuracoes, dict) else ():
            if nome not in self.linhas or not isinstance(config, dict):
                continue
            status, intervalo = config.get("status"), config.get("intervalo")
            status_legacy = {"Atenção": "Operação com restrições",
                             "Operação reduzida": "Operação com restrições",
                             "Interrompida": "Indisponível"}
            status = status_legacy.get(status, status)
            if status in STATUS_LINHA:
                self.linhas[nome]["status"] = status
            if isinstance(intervalo, int) and not isinstance(intervalo, bool) and 1 <= intervalo <= 120:
                self.linhas[nome]["intervalo"] = intervalo
        trens_salvos = dados.get("trens")
        if isinstance(trens_salvos, list):
            bases = {t["id"]: t for t in self.trens}
            carregados = []
            for item in trens_salvos:
                if not isinstance(item, dict) or type(item.get("id")) is not int:
                    continue
                linha = item.get("linha")
                if linha not in self.linhas:
                    continue
                estacao = item.get("estacao", bases.get(item["id"], {}).get(
                    "estacao", self.linhas[linha]["estacoes"][0]))
                if estacao not in self.linhas[linha]["estacoes"]:
                    estacao = self.linhas[linha]["estacoes"][0]
                status = item.get("status", "Disponível")
                if status not in STATUS_TREM:
                    status = "Disponível"
                carregados.append({"id": item["id"], "linha": linha, "estacao": estacao,
                                   "status": status, "maquinista_id": item.get("maquinista_id")})
            if carregados:
                self.trens = carregados
        equipe = dados.get("maquinistas", [])
        if isinstance(equipe, list):
            vistos = set()
            for m in equipe:
                if (not isinstance(m, dict) or type(m.get("id")) is not int
                        or m["id"] in vistos or not isinstance(m.get("nome"), str)
                        or not m["nome"].strip()):
                    continue
                vistos.add(m["id"])
                self.maquinistas.append(m)
        registros = dados.get("ocorrencias", [])
        if isinstance(registros, list):
            self.ocorrencias = [o for o in registros if isinstance(o, dict)
                                and type(o.get("id")) is int
                                and o.get("linha") in self.linhas
                                and o.get("status") in ("Aberta", "Resolvida")]
        self._sanear_vinculos()

    def _sanear_vinculos(self):
        ids_trem = {t["id"] for t in self.trens}
        usados = set()
        for m in self.maquinistas:
            if not isinstance(m.get("matricula", ""), str):
                m["matricula"] = ""
            tid = m.get("trem_id")
            if m.get("status") not in STATUS_MAQUINISTA:
                m["status"] = "Disponível"
            if tid not in ids_trem or tid in usados or m.get("status") not in STATUS_MAQUINISTA:
                m["trem_id"] = None
                if m.get("status") == "Em serviço":
                    m["status"] = "Disponível"
            elif m["status"] == "Afastado":
                m["trem_id"] = None
            elif tid is not None:
                usados.add(tid)
        maquinistas = {m["id"]: m for m in self.maquinistas}
        for trem in self.trens:
            if trem.get("status") not in STATUS_TREM:
                trem["status"] = "Disponível"
            m = maquinistas.get(trem.get("maquinista_id"))
            if not m or m.get("trem_id") != trem["id"]:
                trem["maquinista_id"] = None
                if trem["status"] in ("Em operação", "Manutenção"):
                    trem["status"] = "Disponível"
            elif trem["status"] == "Manutenção":
                m.update(status="Disponível", trem_id=None)
                trem["maquinista_id"] = None
            elif trem["status"] == "Em operação" and m.get("status") != "Em serviço":
                trem["status"] = "Disponível"

    def _aplicar_linhas(self):
        for linha in self.linhas.values():
            linha["tarifa"] = self.tarifa

    def salvar(self):
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        dados = {
            "tarifa": self.tarifa,
            "linhas": {n: {"status": l["status"], "intervalo": l["intervalo"]}
                       for n, l in self.linhas.items()},
            "trens": self.trens,
            "maquinistas": self.maquinistas,
            "ocorrencias": self.ocorrencias,
        }
        temporario = self.arquivo.with_suffix(self.arquivo.suffix + ".tmp")
        temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        temporario.replace(self.arquivo)

    def atualizar_tarifa(self, valor):
        try:
            valor = Decimal(str(valor).replace(",", "."))
        except (InvalidOperation, TypeError, ValueError) as erro:
            raise ValueError("Informe um valor numérico para a tarifa.") from erro
        if not valor.is_finite() or not 0 < valor <= 100:
            raise ValueError("A tarifa deve ser maior que zero e no máximo R$ 100,00.")
        valor = valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if valor == 0:
            raise ValueError("A tarifa deve ser de pelo menos R$ 0,01.")
        self.tarifa = float(valor)
        self._aplicar_linhas()
        self.salvar()

    def validar_maquinista_para_trem(self, trem_id):
        trem = next((t for t in self.trens if t["id"] == trem_id), None)
        maquinista = next((m for m in self.maquinistas
                           if trem and m.get("id") == trem.get("maquinista_id")), None)
        if not maquinista or maquinista.get("status") != "Em serviço" \
                or maquinista.get("trem_id") != trem_id:
            raise ValueError("Designe um maquinista em serviço ao trem antes do despacho.")

    def registrar_status_simulado(self, trem_id, status):
        trem = next((t for t in self.trens if t["id"] == trem_id), None)
        status = {"Em circulação": "Em operação"}.get(status, status)
        if trem and status in STATUS_TREM:
            trem["status"] = status
            if status == "Interrompido":
                maquinista = next((m for m in self.maquinistas
                                  if m.get("id") == trem.get("maquinista_id")), None)
                if maquinista and maquinista.get("status") == "Em serviço":
                    maquinista["status"] = "Disponível"
            self.salvar()

    def atualizar_linha(self, nome, status, intervalo):
        if nome not in self.linhas:
            raise ValueError("Linha não encontrada.")
        if status not in STATUS_LINHA:
            raise ValueError("Selecione um status operacional válido.")
        try:
            numero = float(str(intervalo).replace(",", "."))
            if not math.isfinite(numero) or not numero.is_integer():
                raise ValueError
            intervalo = int(numero)
        except (TypeError, ValueError) as erro:
            raise ValueError("O intervalo deve ser um número inteiro de minutos.") from erro
        if not 1 <= intervalo <= 120:
            raise ValueError("O intervalo deve estar entre 1 e 120 minutos.")
        self.linhas[nome].update(status=status, intervalo=intervalo)
        if status == "Indisponível":
            for trem in self.trens:
                if trem["linha"] == nome and trem["status"] == "Em operação":
                    trem["status"] = "Interrompido"
                    maquinista = next((m for m in self.maquinistas
                                      if m["id"] == trem.get("maquinista_id")), None)
                    if maquinista and maquinista["status"] == "Em serviço":
                        maquinista["status"] = "Disponível"
        self.salvar()
        if self.ao_atualizar_linha:
            self.ao_atualizar_linha()

    def adicionar_trem(self, linha, estacao=None):
        if linha not in self.linhas:
            raise ValueError("Selecione uma linha válida.")
        if self.linhas[linha].get("status") == "Indisponível":
            raise ValueError("Não é possível cadastrar ou despachar trem em linha indisponível.")
        estacao = estacao or self.linhas[linha]["estacoes"][0]
        if estacao not in self.linhas[linha]["estacoes"]:
            raise ValueError("A estação não pertence à linha selecionada.")
        novo = {"id": max((t["id"] for t in self.trens), default=0) + 1,
                "linha": linha, "estacao": estacao,
                "status": "Disponível", "maquinista_id": None}
        self.trens.append(novo)
        self.salvar()
        if self.ao_atualizar_frota:
            self.ao_atualizar_frota(self.trens, {novo["id"]})
        return novo["id"]

    def editar_trem(self, id, linha, estacao):
        trem = next((t for t in self.trens if t["id"] == id), None)
        if not trem:
            raise ValueError("Trem não encontrado.")
        if trem["status"] == "Em operação":
            raise ValueError("Encerre o serviço antes de alterar o trem.")
        if linha not in self.linhas or self.linhas[linha].get("status") == "Indisponível":
            raise ValueError("Selecione uma linha disponível.")
        if estacao not in self.linhas[linha]["estacoes"]:
            raise ValueError("A estação não pertence à linha selecionada.")
        trem.update(linha=linha, estacao=estacao)
        self.salvar()
        if self.ao_atualizar_frota:
            self.ao_atualizar_frota(self.trens, {id})
        return trem

    def remover_trem(self, id):
        trem = next((t for t in self.trens if t["id"] == id), None)
        if not trem:
            raise ValueError("Trem não encontrado.")
        maquinista = next((m for m in self.maquinistas if m.get("id") == trem.get("maquinista_id")), None)
        if maquinista:
            maquinista.update(status="Disponível", trem_id=None)
        self.trens.remove(trem)
        self.salvar()
        if self.ao_atualizar_frota:
            self.ao_atualizar_frota(self.trens, {id})

    def salvar_maquinista(self, nome, matricula="", status="Disponível", trem_id=None, id=None):
        nome = nome.strip() if isinstance(nome, str) else ""
        matricula = matricula.strip() if isinstance(matricula, str) else ""
        if not nome:
            raise ValueError("Informe o nome do maquinista.")
        if status not in STATUS_MAQUINISTA:
            raise ValueError("Selecione um status válido para o maquinista.")
        if trem_id in ("", None):
            trem_id = None
        else:
            if isinstance(trem_id, bool):
                raise ValueError("Selecione um trem válido.")
            try:
                trem_id = int(trem_id)
            except (TypeError, ValueError) as erro:
                raise ValueError("Selecione um trem válido.") from erro
            if trem_id not in {t["id"] for t in self.trens}:
                raise ValueError("Trem não encontrado.")
        if status == "Em serviço" and trem_id is None:
            raise ValueError("Maquinista em serviço precisa estar designado a um trem.")
        if status == "Afastado" and trem_id is not None:
            raise ValueError("Maquinista afastado não pode estar designado a um trem.")
        trem_destino = next((t for t in self.trens if t["id"] == trem_id), None)
        if trem_destino and trem_destino["status"] == "Em operação" and status != "Em serviço":
            raise ValueError("Um trem em operação precisa de maquinista em serviço.")
        for atual in self.maquinistas:
            if atual["id"] == id:
                continue
            if matricula and atual.get("matricula", "").casefold() == matricula.casefold():
                raise ValueError("Já existe um maquinista com essa matrícula.")
            if trem_id is not None and atual.get("trem_id") == trem_id:
                raise ValueError("Esse trem já tem um maquinista designado.")
        if id is None:
            id = max((m.get("id", 0) for m in self.maquinistas), default=0) + 1
            registro = {"id": id}
            self.maquinistas.append(registro)
        else:
            registro = next((m for m in self.maquinistas if m["id"] == id), None)
            if registro is None:
                raise ValueError("Maquinista não encontrado.")
        trens_alterados = {t["id"] for t in self.trens if t.get("maquinista_id") == id}
        if trem_id is not None:
            trens_alterados.add(trem_id)
        registro.update(nome=nome, matricula=matricula, status=status, trem_id=trem_id)
        for trem in self.trens:
            if trem.get("maquinista_id") == id:
                trem["maquinista_id"] = None
                if trem["status"] == "Em operação":
                    trem["status"] = "Disponível"
        if trem_id is not None:
            trem = next(t for t in self.trens if t["id"] == trem_id)
            trem["maquinista_id"] = id
        self.salvar()
        if self.ao_atualizar_frota:
            self.ao_atualizar_frota(self.trens, trens_alterados)
        return id

    def remover_maquinista(self, id):
        maquinista = next((m for m in self.maquinistas if m["id"] == id), None)
        if not maquinista:
            raise ValueError("Maquinista não encontrado.")
        if maquinista.get("status") == "Em serviço":
            raise ValueError("Encerre o serviço e libere a associação antes de remover o maquinista.")
        trens_alterados = {t["id"] for t in self.trens if t.get("maquinista_id") == id}
        for trem in self.trens:
            if trem.get("maquinista_id") == id:
                trem["maquinista_id"] = None
                if trem["status"] == "Em operação":
                    trem["status"] = "Disponível"
        self.maquinistas.remove(maquinista)
        self.salvar()
        if self.ao_atualizar_frota:
            self.ao_atualizar_frota(self.trens, trens_alterados)

    def atualizar_trem(self, id, status):
        if status not in STATUS_TREM:
            raise ValueError("Selecione um status válido para o trem.")
        trem = next((t for t in self.trens if t["id"] == id), None)
        if not trem:
            raise ValueError("Trem não encontrado.")
        maquinista = next((m for m in self.maquinistas if m.get("id") == trem.get("maquinista_id")), None)
        if status == "Em operação" and (not maquinista or maquinista.get("status") != "Em serviço"):
            raise ValueError("Designe um maquinista em serviço antes de liberar o trem.")
        if status == "Em operação" and trem["status"] != "Em operação" and self.validar_despacho:
            self.validar_despacho(id)
        if status != "Em operação" and maquinista:
            maquinista.update(status="Disponível", trem_id=None)
            trem["maquinista_id"] = None
        trem["status"] = status
        self.salvar()
        if self.ao_atualizar_frota:
            self.ao_atualizar_frota(self.trens, {id})

    def registrar_ocorrencia(self, linha, tipo, descricao):
        descricao = descricao.strip()
        if linha not in self.linhas:
            raise ValueError("Selecione uma linha válida.")
        if tipo not in TIPOS_OCORRENCIA:
            raise ValueError("Selecione um tipo de ocorrência válido.")
        if not descricao:
            raise ValueError("Descreva a ocorrência.")
        id = max((o.get("id", 0) for o in self.ocorrencias), default=0) + 1
        self.ocorrencias.insert(0, {
            "id": id, "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "linha": linha, "tipo": tipo, "descricao": descricao, "status": "Aberta",
        })
        self.salvar()
        return id

    def resolver_ocorrencia(self, id):
        ocorrencia = next((o for o in self.ocorrencias if o.get("id") == id), None)
        if not ocorrencia:
            raise ValueError("Ocorrência não encontrada.")
        ocorrencia["status"] = "Resolvida"
        self.salvar()
