"""Motor de circulação didático, controlado por tempo simulado."""
from dataclasses import dataclass
import math


CONFIG_SIMULACAO = {
    "inicio_minuto": 5 * 60, "fim_minuto": 23 * 60,
    "picos": ((6 * 60, 8 * 60 + 30), (16 * 60 + 30, 19 * 60 + 30)),
    "intervalos_pico_segundos": {"compartilhado": 1.5, "Jaboatão": 2.5, "Camaragibe": 2.5, "Sul": 2.0},
    "intervalos_fora_pico_segundos": {"compartilhado": 2.0, "Jaboatão": 3.5, "Camaragibe": 3.5, "Sul": 2.5},
    "escala_minutos_por_segundo": 3.0, "duracao_trecho_minutos": 3.0,
    "parada_terminal_segundos": 1.0,
    "velocidades": {"Jaboatão": 1.08, "Camaragibe": 1.0, "Sul": 1.0},
}


@dataclass
class Trem:
    id: int
    linha: str
    estacao_atual: str
    proxima_estacao: str
    sentido: str = "ida"
    status: str = "Aguardando despacho"
    progresso: float = 0.0
    velocidade: float = 1.0
    origem: str = ""
    destino: str = ""
    ultimo_movimento: float = 0.0


class SimulacaoTrens:
    TRECHOS_COMPARTILHADOS = {"Jaboatão", "Camaragibe"}
    STATUS_INDISPONIVEL = {"Indisponível", "Interrompida"}

    def __init__(self, linhas, fator_velocidade_restrita=0.75, config=None):
        self.linhas = linhas
        self.config = {**CONFIG_SIMULACAO, **(config or {})}
        self.config["velocidades"] = {**CONFIG_SIMULACAO["velocidades"],
                                       **self.config.get("velocidades", {})}
        self.velocidade = dict(self.config["velocidades"])
        self.fator_velocidade_restrita = fator_velocidade_restrita
        self.tempo = 0.0
        self.relogio = float(self.config["inicio_minuto"])
        self.ultimo_despacho = {}
        self.proximo_despacho = {}
        self.validar_maquinista = None
        self.ao_mudar_status = None
        self._parados_pela_simulacao = set()
        self.ativo = self.paused = self.parado = False
        self._montar_trens()

    def _montar_trens(self):
        terminais = {"Jaboatão": "Jaboatão", "Camaragibe": "Camaragibe", "Sul": "Cajueiro Seco"}
        self.trens = []
        for indice, (linha, terminal) in enumerate(terminais.items(), 1):
            if linha not in self.linhas:
                continue
            rota = self.linhas[linha]["estacoes"]
            estacao = terminal if terminal in rota else rota[0]
            destino = rota[1] if estacao == rota[0] else rota[-2]
            self.trens.append(Trem(indice, linha, estacao, destino,
                                   velocidade=self.velocidade.get(linha, 1), origem=estacao,
                                   destino=rota[-1] if estacao == rota[0] else rota[0]))

    def _obter_trem(self, trem_id):
        trem = next((t for t in self.trens if t.id == trem_id), None)
        if trem is None:
            raise ValueError("Trem não encontrado.")
        return trem

    def validar_despacho(self, trem_id):
        trem = self._obter_trem(trem_id)
        if self.linhas[trem.linha].get("status") in self.STATUS_INDISPONIVEL:
            raise ValueError(f"A linha {trem.linha} está indisponível.")
        if trem.status == "Em circulação":
            raise ValueError("O trem já está em circulação.")
        if self.validar_maquinista:
            self.validar_maquinista(trem_id)
        return trem

    def despachar(self, trem_id):
        trem = self.validar_despacho(trem_id)
        if not self._horario_operacional():
            raise ValueError("Fora do horário de operação configurado.")
        trem.status = "Em circulação"
        trem.ultimo_movimento = self.tempo
        self.ultimo_despacho[trem.linha] = self.tempo
        self.proximo_despacho[trem.linha] = self.tempo + self._intervalo(trem.linha)
        self._notificar_status(trem)

    def _horario_operacional(self):
        return self.config["inicio_minuto"] <= self.relogio < self.config["fim_minuto"]

    def _pico(self):
        return any(inicio <= self.relogio < fim for inicio, fim in self.config["picos"])

    def intervalo_despacho(self, linha):
        chave = "intervalos_pico_segundos" if self._pico() else "intervalos_fora_pico_segundos"
        tabela = self.config[chave]
        return float(tabela.get(linha, tabela["Sul"]))

    def _intervalo_compartilhado_simulado(self):
        return self.intervalo_despacho("compartilhado") * self.config["escala_minutos_por_segundo"]

    def _intervalo(self, linha):
        # As duas linhas Centro dividem o intervalo do tronco e respeitam também o intervalo do ramal.
        chave = "compartilhado" if linha in self.TRECHOS_COMPARTILHADOS else linha
        intervalo = self.intervalo_despacho(chave)
        if chave != "compartilhado":
            intervalo = max(intervalo, self.intervalo_despacho("compartilhado"))
        return intervalo * self.config["escala_minutos_por_segundo"]

    def atualizar_operacao(self):
        for trem in self.trens:
            indisponivel = self.linhas[trem.linha].get("status") in self.STATUS_INDISPONIVEL
            if indisponivel and trem.status == "Em circulação":
                trem.status = "Interrompido"
                trem.progresso = 0.0
                self._notificar_status(trem)
            elif not indisponivel and trem.status == "Interrompido":
                trem.status = "Aguardando despacho"
                self._notificar_status(trem)

    def sincronizar_frota(self, frota, ids_alterados=None):
        atuais = {t.id: t for t in self.trens}
        sincronizados = []
        for registro in frota:
            linha = registro.get("linha")
            if linha not in self.linhas:
                continue
            rota = self.linhas[linha]["estacoes"]
            estacao = registro.get("estacao", rota[0])
            if estacao not in rota:
                estacao = rota[0]
            trem = atuais.get(registro["id"])
            if trem is None:
                trem = Trem(registro["id"], linha, estacao, estacao, velocidade=self.velocidade.get(linha, 1),
                            origem=estacao, destino=rota[-1] if estacao == rota[0] else rota[0])
            elif trem.status != "Em circulação":
                trem.linha, trem.estacao_atual = linha, estacao
                trem.proxima_estacao = estacao
            altered = ids_alterados is None or registro["id"] in ids_alterados
            if altered:
                status = registro.get("status")
                self._parados_pela_simulacao.discard(registro["id"])
                if status == "Manutenção":
                    trem.status = "Indisponível"
                elif status == "Interrompido":
                    trem.status = "Interrompido"
                elif status == "Em operação" and self.linhas[linha].get("status") not in self.STATUS_INDISPONIVEL:
                    try:
                        if trem.status != "Em circulação":
                            self.despachar(trem.id)
                    except ValueError:
                        trem.status = "Aguardando despacho"
                elif status == "Parado":
                    trem.status = "Parado"
                elif trem.status not in ("Em circulação", "Indisponível", "Interrompido"):
                    trem.status = "Aguardando despacho"
            sincronizados.append(trem)
        self.trens = sincronizados

    def iniciar(self):
        self.ativo, self.paused, self.parado = True, False, False
        for trem in self.trens:
            if trem.status == "Parado" and self.linhas[trem.linha].get("status") not in self.STATUS_INDISPONIVEL:
                trem.status = "Aguardando despacho"
                self._notificar_status(trem)
        # O primeiro despacho Centro é Jaboatão; Camaragibe entra após o intervalo comum.
        if "Jaboatão" in self.linhas:
            self.proximo_despacho.setdefault("Jaboatão", self.tempo)
            if "Camaragibe" in self.linhas:
                ultimo_jaboatao = self.ultimo_despacho.get("Jaboatão", self.tempo)
                self.proximo_despacho.setdefault(
                    "Camaragibe", ultimo_jaboatao + self._intervalo_compartilhado_simulado())
        erros = []
        self._tentar_despachar(erros)
        return erros

    def _tentar_despachar(self, erros=None):
        if not self._horario_operacional():
            return
        for trem in self.trens:
            if trem.status != "Aguardando despacho" or self.linhas[trem.linha].get("status") in self.STATUS_INDISPONIVEL:
                continue
            devido = self.proximo_despacho.get(trem.linha, self.tempo)
            if self.tempo + 1e-9 < devido:
                continue
            # Cabeça de linha aguardando maquinista não bloqueia o outro ramal.
            try:
                self.despachar(trem.id)
            except ValueError as erro:
                if erros is not None:
                    erros.append(f"Trem {trem.id}: {erro}")
                self.proximo_despacho[trem.linha] = self.tempo + min(1.0, self._intervalo(trem.linha))

    def pausar(self):
        self.paused, self.ativo = True, False

    def parar(self):
        self.paused, self.ativo, self.parado = False, False, True
        for trem in self.trens:
            if trem.status == "Em circulação":
                trem.status = "Parado"
                self._parados_pela_simulacao.add(trem.id)
                self._notificar_status(trem)

    def reiniciar(self):
        self.tempo, self.relogio = 0.0, float(self.config["inicio_minuto"])
        self.ultimo_despacho.clear()
        self.proximo_despacho.clear()
        for trem in self.trens:
            if trem.id in self._parados_pela_simulacao:
                trem.status = "Aguardando despacho"
                self._parados_pela_simulacao.discard(trem.id)
            elif trem.status == "Em circulação":
                trem.status = "Aguardando despacho"
            trem.progresso = 0.0
            trem.ultimo_movimento = 0.0
            self._notificar_status(trem)
        self.ativo, self.paused, self.parado = True, False, False
        self.iniciar()

    def _proxima(self, trem):
        rota = self.linhas[trem.linha]["estacoes"]
        atual = rota.index(trem.estacao_atual)
        sentido = 1 if trem.sentido == "ida" else -1
        seguinte = atual + sentido
        if not 0 <= seguinte < len(rota):
            sentido *= -1
            seguinte = atual + sentido
        return rota[seguinte], sentido

    def _trecho(self, trem):
        return frozenset((trem.estacao_atual, self._proxima(trem)[0]))

    def _trechos_comuns(self):
        rotas = [self.linhas[n]["estacoes"] for n in self.TRECHOS_COMPARTILHADOS if n in self.linhas]
        if len(rotas) < 2:
            return set()
        pares = [set(frozenset((a, b)) for a, b in zip(r, r[1:])) for r in rotas]
        return pares[0] & pares[1]

    def _mover(self, trem):
        destino, sentido = self._proxima(trem)
        trem.sentido = "ida" if sentido == 1 else "volta"
        trem.estacao_atual = destino
        rota = self.linhas[trem.linha]["estacoes"]
        atual = rota.index(destino)
        seguinte = atual + sentido
        if not 0 <= seguinte < len(rota):
            trem.sentido = "volta" if sentido == 1 else "ida"
            trem.status = "Aguardando despacho"
            trem.origem, trem.destino = destino, trem.origem
            trem.proxima_estacao = destino
            parada = self.config["parada_terminal_segundos"] * self.config["escala_minutos_por_segundo"]
            self.proximo_despacho[trem.linha] = self.tempo + parada
            trem.progresso = 0
            self._notificar_status(trem)
        else:
            trem.proxima_estacao = rota[seguinte]

    def atualizar(self, passo=0.03):
        try:
            passo = float(passo)
        except (TypeError, ValueError) as erro:
            raise ValueError("O passo da simulação deve ser numérico.") from erro
        if not math.isfinite(passo) or not 0 <= passo <= 60:
            raise ValueError("O passo deve estar entre 0 e 60 minutos simulados.")
        if not self.ativo or self.paused or self.parado or passo == 0:
            return
        restante = passo
        # Subpassos mantêm o bloqueio de via coerente mesmo com callbacks atrasados.
        while restante > 1e-10:
            dt = min(restante, 0.05)
            restante -= dt
            self.tempo += dt
            self.relogio += dt
            self._tentar_despachar()
            comuns = self._trechos_comuns()
            ocupados = set()
            # Os intervalos Centro dão precedência a Jaboatão quando ambos requisitam a via.
            ordenados = sorted(self.trens, key=lambda t: (t.linha != "Jaboatão", t.id))
            for trem in ordenados:
                if trem.status != "Em circulação":
                    continue
                if self.linhas[trem.linha].get("status") in self.STATUS_INDISPONIVEL:
                    trem.status, trem.progresso = "Interrompido", 0.0
                    self._notificar_status(trem)
                    continue
                fator = self.fator_velocidade_restrita if self.linhas[trem.linha].get("status") == "Operação com restrições" else 1
                aresta = self._trecho(trem)
                if aresta in comuns and aresta in ocupados:
                    continue
                if aresta in comuns:
                    ocupados.add(aresta)
                trem.progresso += dt * trem.velocidade * fator / self.config["duracao_trecho_minutos"]
                trem.ultimo_movimento = self.tempo
                while trem.progresso >= 1 and trem.status == "Em circulação":
                    trem.progresso -= 1
                    self._mover(trem)
                    if trem.status == "Em circulação":
                        aresta = self._trecho(trem)
                        if aresta in comuns and aresta in ocupados:
                            trem.progresso = min(trem.progresso, .999)
                            break
                        if aresta in comuns:
                            ocupados.add(aresta)

    def alterar_velocidade(self, valor, linha=None):
        try:
            valor = float(valor)
        except (TypeError, ValueError) as erro:
            raise ValueError("A velocidade deve ser numérica.") from erro
        if not math.isfinite(valor) or not 0.1 <= valor <= 5:
            raise ValueError("A velocidade deve estar entre 0,1 e 5.")
        nomes = self.linhas if linha is None else [linha]
        if any(nome not in self.linhas for nome in nomes):
            raise ValueError("Linha não encontrada.")
        for nome in nomes:
            self.velocidade[nome] = valor
            self.config["velocidades"][nome] = valor
        for trem in self.trens:
            trem.velocidade = self.velocidade[trem.linha]

    def _notificar_status(self, trem):
        if self.ao_mudar_status:
            self.ao_mudar_status(trem.id, trem.status)
