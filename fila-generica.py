from enum import Enum
import yaml
from sys import argv

class Estatisticas:
    def __init__(self, simulacao):
        self.simulacao = simulacao

    def calcular_distribuicao_probabilidade(self, fila):
        distribuicao = [0] * (fila.capacidade + 1)
        estados = fila.estados
        tempo_global = self.simulacao.tempo_global

        for indice, estado in enumerate(estados):
            distribuicao[indice] = (indice, estado, estado/tempo_global)

        return distribuicao

    def mostrar_distribuicao_probabilidade(self, fila):
        distribuicao = self.calcular_distribuicao_probabilidade(fila)

        print("Estado\t\tTempo\t\tProbabilidade")
        for linha in distribuicao:
            if linha[1] != 0:
                print(f"{linha[0]}\t\t{round(linha[1], 4)}\t\t{linha[2] * 100:,.2f}%")

    def mostrar_tempo_global(self):
        print("Tempo médio da simulação:", self.simulacao.tempo_global)

    def mostrar_perdas(self, fila):
        print("Número de perdas:", fila.perdas)

    def relatorio(self):
        for indice, fila in enumerate(self.simulacao.filas):
            k = fila.capacidade
            print("***********************************************************")
            if not k == 100:
                print(f"Fila:    F{indice+1} (G/G/{fila.servidores}/{fila.capacidade})")
            else:
                print(f"Fila:    F{indice+1} (G/G/{fila.servidores})")
            if fila.intervalo_chegada != None:
                print(f"Chegada: {fila.intervalo_chegada.inicio} ... {fila.intervalo_chegada.fim}")
            print(f"Atendimento: {fila.intervalo_atendimento.inicio} ... {fila.intervalo_atendimento.fim}")
            print("***********************************************************")
            self.mostrar_distribuicao_probabilidade(fila)
            self.mostrar_perdas(fila)

        self.mostrar_tempo_global()

class TipoEvento(Enum):
    CHEGADA = 'chegada'
    SAIDA = 'saida'
    MOVER = 'mover'

class Evento:
    def __init__(self, tipo, tempo, origem, alvo) -> None:
        self.tipo = tipo
        self.tempo = tempo
        self.origem = origem
        self.alvo = alvo

    def __str__(self):
        if self.origem == None:
            return f'Tipo:{self.tipo} | Tempo: {self.tempo} | Origem: {self.origem} | Alvo: {self.alvo.id}'
        if self.alvo == None:
            return f'Tipo:{self.tipo} | Tempo: {self.tempo} | Origem: {self.origem.id} | Alvo: {self.alvo}'
        return f'Tipo:{self.tipo} | Tempo: {self.tempo} | Origem: {self.origem.id} | Alvo: {self.alvo.id}'

class Intervalo:
    def __init__(self, inicio, fim) -> None:
        self.inicio = inicio
        self.fim = fim

    def __str__(self) -> str:
        return f'Início {self.inicio} | Fim {self.fim}'

class NumerosPseudoAleatorios:
    def __init__(self, semente, total_numeros, numeros_aleatorios = None, gerar=False) -> None:
        self.m = 2**28
        self.a = 1317293
        self.c = 12309820398
        self.semente = semente

        self.x = semente
        self.total_numeros = total_numeros

        self.numeros = numeros_aleatorios
        self.gerar = gerar

        if gerar == False:
            self.total_numeros = len(numeros_aleatorios)

        self.atual = -1

    def gerar_aleatorio(self, n):
        x = self.semente
        arr = []
        for _ in range(n):
            if _ % 10000000 == 0: print(_)
            op = (self.a * x + self.c) % self.m
            x = op
            arr.append(op/self.m)
        return arr
    
    def obter_proximo_numero(self):
        self.atual += 1
        if self.numeros and not self.gerar:
            return self.numeros[self.atual % self.total_numeros]
        op = (self.a * self.x + self.c) % self.m
        self.x = op
        return op/self.m
    
    def resetar(self):
        self.x = self.semente
        self.atual = -1



class Escalonador:
    def __init__(self, numeros_aleatorios: NumerosPseudoAleatorios):
        self.numeros_aleatorios = numeros_aleatorios
        self.agenda = []

    def adicionar(self, evento, intervalo):
        if self.numeros_aleatorios.atual == self.numeros_aleatorios.total_numeros:
            return
        evento.tempo = evento.tempo + self.obter_aleatorio(intervalo)
        self.agenda.append(evento)
        self.agenda.sort(key=lambda evento: evento.tempo)

    def adicionar_aleatorio(self, evento, num_aleatorio):
        print(f"event {evento}")
        print(f"rand_num {num_aleatorio}")
        evento.tempo = evento.tempo + num_aleatorio
        self.agenda.append(evento)
        self.agenda.sort(key=lambda evento: evento.tempo)

    def agendar(self) -> Evento:
        return self.agenda.pop(0)
    
    def obter_aleatorio(self, intervalo) -> float:
        num_aleatorio = self.numeros_aleatorios.obter_proximo_numero()
        return intervalo.inicio + (intervalo.fim - intervalo.inicio) * num_aleatorio


class Fila:
    def __init__(self, id, capacidade, servidores, intervalo_chegada, intervalo_atendimento) -> None:
        self.id = id
        self.capacidade = capacidade 
        self.servidores = servidores
        self.intervalo_chegada = intervalo_chegada
        self.intervalo_atendimento = intervalo_atendimento
        self.status = 0
        self.perdas = 0
        self.estados = [0] * (capacidade + 1)
        self.candidatas_filas = []

    def adicionar(self):
        self.status = self.status + 1

    def sair(self):
        self.status = self.status - 1

    def perda(self):
        self.perdas = self.perdas + 1

    def atualizar_estados(self, tempo):
        self.estados[self.status] = self.estados[self.status] + tempo 
        
    def adicionar_fila(self, fila, prob):
        self.candidatas_filas.append((fila, prob))
        
    def alvo(self, prob, tempo):
        limiar = 1e-6
        prob_cumulativa = 0
        for alvo, prob_fila in self.candidatas_filas:
            prob_cumulativa += prob_fila
            if prob < prob_cumulativa + limiar:
                return Evento(TipoEvento.MOVER, tempo, self, alvo)
        return Evento(TipoEvento.SAIDA, tempo, self, None)
    
    def __str__(self) -> str:
        string = f'Capacidade: {self.capacidade}' + '\n'
        string = string + f'Servidores: {self.servidores}' + '\n'
        string = string + f'Intervalo Chegada: {self.intervalo_chegada}' + '\n'
        string = string + f'Intervalo Atendimento: {self.intervalo_atendimento}' + '\n'
        string = string + f'Status: {self.status}' + '\n'
        string = string + f'Perdas: {self.perdas}' + '\n'
        string = string + f'Estados: {self.estados}'

        return string

class Simulacao: 
    def __init__(self, tempo_chegada, filas, escalonador):
        self.tempo_chegada = tempo_chegada
        self.filas = filas
        self.escalonador = escalonador
        self.tempo_global = 0

    def executar(self):
        primeira_fila = self.filas[0]
        self.escalonador.adicionar_aleatorio(Evento(TipoEvento.CHEGADA, self.tempo_chegada, None, primeira_fila), 0)
        while (self.escalonador.numeros_aleatorios.atual + 2) <= self.escalonador.numeros_aleatorios.total_numeros: 
            prox_evento = self.escalonador.agendar()
            
            self.__atualizar_tempo_global(prox_evento)

            if (prox_evento.tipo == TipoEvento.CHEGADA):
                self.chegada(None, prox_evento.alvo)
            elif (prox_evento.tipo == TipoEvento.SAIDA):
                self.saida(prox_evento.origem, None)
            elif (prox_evento.tipo == TipoEvento.MOVER):
                self.mover(prox_evento.origem, prox_evento.alvo)
        
    def chegada(self, _, alvo: Fila):
        if alvo.status < alvo.capacidade:
            alvo.adicionar()
            if alvo.status <= alvo.servidores:
                evento = alvo.alvo(self.escalonador.obter_aleatorio(Intervalo(0, 1)), self.tempo_global)
                self.escalonador.adicionar(evento, alvo.intervalo_atendimento)
        else:
            alvo.perda()
        print(alvo)
        self.escalonador.adicionar_aleatorio(Evento(TipoEvento.CHEGADA, self.tempo_global, None, alvo), alvo.intervalo_chegada)

    def saida(self, origem, _):
        origem.sair()
        if origem.status >= origem.servidores:
            self.escalonador.adicionar(origem.alvo(self.escalonador.obter_aleatorio(Intervalo(0, 1)), self.tempo_global), origem.intervalo_atendimento)
            
    def mover(self, origem, alvo):
        origem.sair()
        if origem.status >= origem.servidores:
            self.escalonador.adicionar(origem.alvo(self.escalonador.obter_aleatorio(Intervalo(0, 1)), self.tempo_global), origem.intervalo_atendimento)
        if alvo.status < alvo.capacidade:
            alvo.adicionar()
            if alvo.status <= alvo.servidores:
                self.escalonador.adicionar(alvo.alvo(self.escalonador.obter_aleatorio(Intervalo(0, 1)), self.tempo_global), alvo.intervalo_atendimento)
        else:
            alvo.perda()

    def __atualizar_tempo_global(self, evento):
        for fila in self.filas:
            fila.atualizar_estados(evento.tempo - self.tempo_global)
        self.tempo_global = evento.tempo


def carregar_config(nome_arquivo):
    with open(nome_arquivo) as stream:
        try:
            config = yaml.safe_load(stream)
        except:
            print('=== ERRO AO CARREGAR ARQUIVO YAML ===')
            exit(0)

    return config

def obter_filas(config) -> list:
    config_filas = config['filas']

    filas = []

    for _, id_fila in enumerate(config_filas):
        config_fila = config_filas[id_fila]

        servidores = config_fila['servidores']
        intervalo_atendimento = Intervalo(config_fila['minAtendimento'], config_fila['maxAtendimento'])

        if "capacidade" in config_fila:
            capacidade = config_fila['capacidade']
        else:
            capacidade = 100

        if "minChegada" in config_fila:
            intervalo_chegada = Intervalo(config_fila['minChegada'], config_fila['maxChegada'])
        else:
            intervalo_chegada = None
            
        filas.append(Fila(capacidade=capacidade, id=id_fila, servidores=servidores, intervalo_chegada=intervalo_chegada, intervalo_atendimento=intervalo_atendimento))
    
    return filas

def adicionar_rede(origem_id, alvo_id, prob, filas: list):
    origem: Fila = filas[int(origem_id[1:]) - 1]
    alvo: Fila = filas[int(alvo_id[1:]) - 1]
    origem.adicionar_fila(alvo, prob)

def main():
    CONFIG = carregar_config(argv[1])

    tempo_chegada = CONFIG['chegadas']['Q1']

    sementes = CONFIG['semente']
    
    filas = obter_filas(CONFIG)
    
    rede = CONFIG["rede"]
    
    for evento in rede:
        adicionar_rede(evento["origem"], evento["alvo"], evento["probabilidade"], filas)
        
    total_numeros_rnd = CONFIG['numerosRndPorSemente']

    numeros_aleatorios = CONFIG.get('numerosRnd')
      
    numeros_aleatorios = NumerosPseudoAleatorios(sementes[0], total_numeros_rnd, numeros_aleatorios=numeros_aleatorios, gerar=not bool(numeros_aleatorios))
    
    escalonador = Escalonador(numeros_aleatorios)

    sim = Simulacao(tempo_chegada=tempo_chegada, filas=filas, escalonador=escalonador)

    sim.executar()

    Estatisticas(sim).relatorio()

if __name__ == "__main__":
    main()
