from mesa import Model, Agent
from mesa.space import MultiGrid
import random

DIRTY_TYPES = {
    "poeira": 1,
    "liquido": 2,
    "detritos": 3
}


class Sujeira(Agent):
    def __init__(self, model, tipo):
        super().__init__(model)
        self.tipo = tipo
        self.pontos = DIRTY_TYPES[tipo]

    def step(self):
        pass


class Movel(Agent):
    def __init__(self, model):
        super().__init__(model)

    def step(self):
        pass


class AspiradorObjetivo(Agent):
    """Agente baseado em objetivo — limpa todas as sujeiras"""
    def __init__(self, model):
        super().__init__(model)
        self.energia = 30
        self.pontos = 0
        self.memoria = {}
        self.objetivo_atual = None
        self.parado = False
        self.varOcg = 0  # __define-ocg__

    # ---------------------- MEMÓRIA E PERCEPÇÃO ----------------------
    def lembrar_vizinhanca(self, pos):
        vizinhos = self.model.grid.get_neighborhood(pos, moore=False, include_center=False)
        vistos = []
        for v in vizinhos:
            objs = self.model.grid.get_cell_list_contents([v])
            tipo = "vazio"
            for o in objs:
                if isinstance(o, Sujeira):
                    tipo = f"sujeira_{o.tipo}"
                elif isinstance(o, Movel):
                    tipo = "movel"
            vistos.append((v, tipo))
        return vistos

    def registrar_memoria(self, pos, limpo=False):
        if pos not in self.memoria:
            self.memoria[pos] = {
                "visto": self.lembrar_vizinhanca(pos),
                "limpo": limpo,
                "visitas": 1
            }
        else:
            self.memoria[pos]["visto"] = self.lembrar_vizinhanca(pos)
            self.memoria[pos]["limpo"] = limpo
            self.memoria[pos]["visitas"] += 1

    def posicoes_desconhecidas(self):
        vizinhos = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False)
        return [v for v in vizinhos if v not in self.memoria]

    # ---------------------- PLANEJAMENTO DE OBJETIVOS ----------------------
    def encontrar_sujeiras_conhecidas(self):
        sujeiras = set()
        for pos, info in self.memoria.items():
            for vpos, tipo in info["visto"]:
                if "sujeira" in tipo:
                    sujeiras.add(vpos)
        return list(sujeiras)

    def escolher_sujeira_mais_proxima(self, sujeiras):
        if not sujeiras:
            return None
        x0, y0 = self.pos
        return min(sujeiras, key=lambda pos: abs(pos[0] - x0) + abs(pos[1] - y0))

    # ---------------------- MOVIMENTO PLANEJADO ----------------------
    def mover_para(self, destino):
        """Move-se um passo em direção ao destino evitando móveis e voltas desnecessárias."""
        x, y = self.pos
        tx, ty = destino
        opcoes = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        opcoes.sort(key=lambda p: abs(p[0] - tx) + abs(p[1] - ty))

        for nx, ny in opcoes:
            if 0 <= nx < self.model.grid.width and 0 <= ny < self.model.grid.height:
                if not any(isinstance(o, Movel) for o in self.model.grid.get_cell_list_contents([(nx, ny)])):
                    # Prioriza locais não limpos ou pouco visitados
                    if (nx, ny) not in self.memoria or not self.memoria[(nx, ny)]["limpo"]:
                        self.model.grid.move_agent(self, (nx, ny))
                        self.energia -= 1
                        return True
        return False

    # ---------------------- EXPLORAÇÃO CONTROLADA ----------------------
    def explorar_inteligente(self):
        """Explora locais desconhecidos ou menos visitados."""
        pos = self.pos
        vizinhos = self.model.grid.get_neighborhood(pos, moore=False, include_center=False)
        livres = [v for v in vizinhos if not any(isinstance(o, Movel) for o in self.model.grid.get_cell_list_contents([v]))]

        desconhecidos = [v for v in livres if v not in self.memoria]
        if desconhecidos:
            destino = random.choice(desconhecidos)
        else:
            destino = min(livres, key=lambda v: self.memoria.get(v, {"visitas": 0})["visitas"])

        self.model.grid.move_agent(self, destino)
        self.energia -= 1

    # ---------------------- PASSOS ----------------------
    def step(self):
        if self.energia <= 0:
            self.parado = True
            return

        # verifica se ainda tem sujeiras existentes
        sujeiras_no_ambiente = [a for a in self.model.custom_agents if isinstance(a, Sujeira)]
        if not sujeiras_no_ambiente:
            self.parado = True
            return

        grid = self.model.grid
        pos = self.pos
        cell_contents = grid.get_cell_list_contents([pos])

        # limpeza imediata
        sujeiras = [a for a in cell_contents if isinstance(a, Sujeira)]
        if sujeiras:
            alvo = sujeiras[0]
            grid.remove_agent(alvo)
            self.model.custom_agents.remove(alvo)
            self.pontos += alvo.pontos
            self.energia -= alvo.pontos
            self.registrar_memoria(pos, limpo=True)
            self.objetivo_atual = None
            return

        # atualiza memória e busca objetivos
        self.registrar_memoria(pos, limpo=True)
        sujeiras_conhecidas = [
            s for s in self.encontrar_sujeiras_conhecidas()
            if any(isinstance(o, Sujeira) for o in grid.get_cell_list_contents([s]))
        ]

        # define objetivo, atualiza
        if not self.objetivo_atual:
            self.objetivo_atual = self.escolher_sujeira_mais_proxima(sujeiras_conhecidas)

        # caso tenha um objetivo definido
        if self.objetivo_atual:
            if self.objetivo_atual == pos:
                self.objetivo_atual = None
            else:
                moved = self.mover_para(self.objetivo_atual)
                if not moved:
                    # se travou, tenta um novo objetivo
                    self.objetivo_atual = self.escolher_sujeira_mais_proxima(sujeiras_conhecidas)
                    if not self.objetivo_atual:
                        self.explorar_inteligente()
        else:
            # se não há sujeiras conhecidas, explora
            self.explorar_inteligente()


class AmbienteObjetivo(Model):
    def __init__(self, width=5, height=5, n_sujeiras=5, n_moveis=3):
        super().__init__()
        self.grid = MultiGrid(width, height, torus=False)
        self.custom_agents = []

        for _ in range(n_sujeiras):
            x, y = random.randint(0, width - 1), random.randint(0, height - 1)
            tipo = random.choice(list(DIRTY_TYPES.keys()))
            sujeira = Sujeira(self, tipo)
            self.grid.place_agent(sujeira, (x, y))
            self.custom_agents.append(sujeira)

        for _ in range(n_moveis):
            x, y = random.randint(0, width - 1), random.randint(0, height - 1)
            movel = Movel(self)
            self.grid.place_agent(movel, (x, y))
            self.custom_agents.append(movel)

        aspirador = AspiradorObjetivo(self)
        self.grid.place_agent(aspirador, (0, 0))
        self.custom_agents.append(aspirador)

    def step(self):
        for agent in list(self.custom_agents):
            agent.step()
