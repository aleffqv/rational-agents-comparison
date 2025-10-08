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
    """Agente baseado em objetivo com exploração inteligente."""
    def __init__(self, model):
        super().__init__(model)
        self.energia = 30
        self.pontos = 0
        self.memoria = {}
        self.parado = False
        self.objetivo_atual = None
        self.varOcg = 0  # __define-ocg__

    # ---------------------- MEMÓRIA ----------------------
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
        self.memoria[pos] = {
            "visto": self.lembrar_vizinhanca(pos),
            "limpo": limpo
        }

    def ja_visitou(self, pos):
        return pos in self.memoria

    def posicoes_desconhecidas(self):
        """Retorna posições adjacentes ainda não visitadas"""
        vizinhos = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False)
        desconhecidos = [v for v in vizinhos if v not in self.memoria]
        return desconhecidos

    # ---------------------- PLANEJAMENTO ----------------------
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

    def mover_para(self, destino):
        """Move-se um passo em direção ao destino, evitando móveis e priorizando locais novos"""
        x, y = self.pos
        dx, dy = destino[0] - x, destino[1] - y

        candidatos = []
        if abs(dx) > abs(dy):
            candidatos = [(x + (1 if dx > 0 else -1), y)]
        elif dy != 0:
            candidatos = [(x, y + (1 if dy > 0 else -1))]

        grid = self.model.grid
        for passo in candidatos:
            if (0 <= passo[0] < grid.width and 0 <= passo[1] < grid.height):
                if not any(isinstance(o, Movel) for o in grid.get_cell_list_contents([passo])):
                    grid.move_agent(self, passo)
                    self.energia -= 1
                    return True
        return False

    def explorar_inteligente(self):
        """Explora áreas novas priorizando posições desconhecidas"""
        pos = self.pos
        vizinhos = self.model.grid.get_neighborhood(pos, moore=False, include_center=False)

        # 1️⃣ Prioriza posições desconhecidas
        desconhecidos = [v for v in vizinhos if v not in self.memoria]
        livres = [v for v in desconhecidos if not any(isinstance(o, Movel) for o in self.model.grid.get_cell_list_contents([v]))]

        # 2️⃣ Se todas já foram visitadas, anda para a que foi visitada há mais tempo
        if not livres:
            todas_livres = [
                v for v in vizinhos
                if not any(isinstance(o, Movel) for o in self.model.grid.get_cell_list_contents([v]))
            ]
            livres = todas_livres

        if livres:
            destino = random.choice(livres)
            self.model.grid.move_agent(self, destino)
            self.energia -= 1

    # ---------------------- DECISÃO ----------------------
    def step(self):
        if self.energia <= 0:
            self.parado = True
            return

        if not any(isinstance(a, Sujeira) for a in self.model.custom_agents):
            self.parado = True
            return

        grid = self.model.grid
        pos = self.pos

        # Limpa se houver sujeira na posição
        cell_contents = grid.get_cell_list_contents([pos])
        sujeiras = [a for a in cell_contents if isinstance(a, Sujeira)]
        if sujeiras:
            alvo = sujeiras[0]
            grid.remove_agent(alvo)
            try:
                self.model.custom_agents.remove(alvo)
            except ValueError:
                pass
            self.pontos += alvo.pontos
            self.energia -= alvo.pontos
            self.registrar_memoria(pos, limpo=True)
            self.objetivo_atual = None
        else:
            self.registrar_memoria(pos, limpo=True)

        # Atualiza sujeiras conhecidas
        sujeiras_conhecidas = [
            s for s in self.encontrar_sujeiras_conhecidas()
            if any(isinstance(o, Sujeira) for o in grid.get_cell_list_contents([s]))
        ]

        # Se não há objetivo, procura um novo
        if not self.objetivo_atual:
            if sujeiras_conhecidas:
                self.objetivo_atual = self.escolher_sujeira_mais_proxima(sujeiras_conhecidas)
            else:
                self.explorar_inteligente()
                return

        # Move-se para o objetivo
        if self.objetivo_atual:
            if self.objetivo_atual == pos:
                self.objetivo_atual = None
            else:
                moved = self.mover_para(self.objetivo_atual)
                if not moved:
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
