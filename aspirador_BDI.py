from mesa import Model, Agent
from mesa.space import MultiGrid
import random
import solara

# ---------------------- CONFIG ----------------------
DIRTY_TYPES = {"poeira": 1, "liquido": 2, "detritos": 3}
CUSTO_MOVIMENTO = 1
CUSTO_LIMPEZA = 1

# ---------------------- AGENTES ----------------------
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


# ---------------------- ASPIRADOR BDI ----------------------
class AspiradorBDI(Agent):
    """Agente BDI (Belief–Desire–Intention) otimizado, evolução do modelo baseado em utilidade."""
    def __init__(self, model):
        super().__init__(model)
        self.energia = 30
        self.pontos = 0
        self.crencas = {}  # crenças sobre o ambiente
        self.desejo_limpar_tudo = True
        self.intencao = None
        self.parado = False
        self.varOcg = 0  # __define-ocg__

    # ---------------------- CRENÇAS ----------------------
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

    def atualizar_crencas(self, pos, limpo=False):
        """Atualiza o que o agente acredita sobre o ambiente."""
        vistos = self.lembrar_vizinhanca(pos)
        if pos not in self.crencas:
            self.crencas[pos] = {
                "visto": vistos,
                "limpo": limpo,
                "visitado": True,
                "visitas": 1,
            }
        else:
            self.crencas[pos]["visto"] = vistos
            self.crencas[pos]["limpo"] = limpo
            self.crencas[pos]["visitado"] = True
            self.crencas[pos]["visitas"] += 1

    # ---------------------- DESEJOS ----------------------
    def sujeiras_conhecidas(self):
        sujeiras = []
        for pos, info in self.crencas.items():
            for vpos, tipo in info["visto"]:
                if "sujeira" in tipo:
                    cell_contents = self.model.grid.get_cell_list_contents([vpos])
                    if any(isinstance(a, Sujeira) for a in cell_contents):
                        t = tipo.split("_")[1]
                        sujeiras.append((vpos, t))
        return sujeiras

    def calcular_utilidade(self, destino, tipo_sujeira):
        x0, y0 = self.pos
        distancia = abs(destino[0] - x0) + abs(destino[1] - y0)
        ganho = DIRTY_TYPES[tipo_sujeira]
        custo = (distancia * CUSTO_MOVIMENTO) + (DIRTY_TYPES[tipo_sujeira] * CUSTO_LIMPEZA)
        return ganho / custo if custo > 0 else 0

    def definir_intencao(self):
        """Define intenção (alvo) com base nas crenças e desejos."""
        sujeiras = self.sujeiras_conhecidas()
        if not sujeiras:
            return None
        utilidades = [(pos, self.calcular_utilidade(pos, tipo)) for pos, tipo in sujeiras]
        utilidades.sort(key=lambda x: x[1], reverse=True)
        return utilidades[0][0] if utilidades else None

    # ---------------------- INTENÇÃO (AÇÕES) ----------------------
    def mover_para(self, destino):
        if not destino:
            return False
        x, y = self.pos
        dx, dy = destino[0] - x, destino[1] - y

        if dx != 0:
            passo = (x + (1 if dx > 0 else -1), y)
        elif dy != 0:
            passo = (x, y + (1 if dy > 0 else -1))
        else:
            return False

        if 0 <= passo[0] < self.model.grid.width and 0 <= passo[1] < self.model.grid.height:
            if not any(isinstance(o, Movel) for o in self.model.grid.get_cell_list_contents([passo])):
                self.model.grid.move_agent(self, passo)
                self.energia -= CUSTO_MOVIMENTO
                return True
        return False

    def explorar(self):
        """Explora locais pouco visitados e desconhecidos, evitando desperdício de energia."""
        vizinhos = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False)
        candidatos = []

        for v in vizinhos:
            objs = self.model.grid.get_cell_list_contents([v])
            if any(isinstance(o, Movel) for o in objs):
                continue
            visitas = self.crencas[v]["visitas"] if v in self.crencas else 0
            candidatos.append((v, visitas))

        if candidatos:
            candidatos.sort(key=lambda x: x[1])
            destino = candidatos[0][0]
            self.model.grid.move_agent(self, destino)
            self.energia -= CUSTO_MOVIMENTO

    # ---------------------- DECISÃO ----------------------
    def step(self):
        if self.parado or self.energia <= 0:
            self.parado = True
            return

        pos = self.pos
        grid = self.model.grid
        self.atualizar_crencas(pos, limpo=True)

        # limpar sujeira
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
            self.energia -= alvo.pontos * CUSTO_LIMPEZA
            self.atualizar_crencas(pos, limpo=True)
            self.intencao = None
            return

        # verifica se há sujeira restante
        if not any(isinstance(a, Sujeira) for a in self.model.custom_agents):
            self.parado = True
            return

        # define ou executa intenção
        if not self.intencao:
            self.intencao = self.definir_intencao()

        if self.intencao:
            moved = self.mover_para(self.intencao)
            if not moved:
                self.intencao = None
                self.explorar()
        else:
            self.explorar()



class AmbienteBDI(Model):
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

        aspirador = AspiradorBDI(self)
        self.grid.place_agent(aspirador, (0, 0))
        self.custom_agents.append(aspirador)

    def step(self):
        for agent in list(self.custom_agents):
            agent.step()