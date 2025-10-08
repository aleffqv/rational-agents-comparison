# aspirador_modelo_model.py
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


class AspiradorModelo(Agent):
    """Agente baseado em modelo (com memória)"""
    def __init__(self, model):
        super().__init__(model)
        self.energia = 30
        self.pontos = 0
        self.memoria = {}  # {(x, y): {"visto": [(pos, tipo_objeto), ...], "limpo": bool}}
        self.parado = False

    def lembrar_vizinhanca(self, pos):
        """Lembra o que está ao redor de uma posição"""
        vizinhos = self.model.grid.get_neighborhood(pos, moore=False, include_center=False)
        vistos = []
        for v in vizinhos:
            objs = self.model.grid.get_cell_list_contents([v])
            for o in objs:
                tipo = o.__class__.__name__
                if isinstance(o, Sujeira):
                    tipo = f"sujeira_{o.tipo}"
                elif isinstance(o, Movel):
                    tipo = "movel"
            vistos.append((v, tipo if objs else "vazio"))
        return vistos

    def registrar_memoria(self, pos, limpo=False):
        """Registra a célula atual e o que viu ao redor"""
        self.memoria[pos] = {
            "visto": self.lembrar_vizinhanca(pos),
            "limpo": limpo
        }

    def ja_visitou(self, pos):
        return pos in self.memoria

    def step(self):
        if self.energia <= 0:
            self.parado = True
            return

        grid = self.model.grid
        pos_atual = self.pos

        # Limpar sujeira na célula atual
        cell_contents = grid.get_cell_list_contents([pos_atual])
        sujeiras = [a for a in cell_contents if isinstance(a, Sujeira)]
        if sujeiras:
            alvo = sujeiras[0]
            if self.energia >= alvo.pontos:
                grid.remove_agent(alvo)
                try: self.model.custom_agents.remove(alvo)
                except ValueError: pass
                self.pontos += alvo.pontos
                self.energia -= alvo.pontos
                self.registrar_memoria(pos_atual, limpo=True)
                return

        # Limpar sujeira na vizinhança
        vizinhos = grid.get_neighborhood(pos_atual, moore=False, include_center=False)
        for v in vizinhos:
            # Ignora células com móveis
            if any(isinstance(o, Movel) for o in grid.get_cell_list_contents([v])):
                continue

            viz_contents = grid.get_cell_list_contents([v])
            viz_sujeira = [a for a in viz_contents if isinstance(a, Sujeira)]
            if viz_sujeira and self.energia >= viz_sujeira[0].pontos:
                alvo = viz_sujeira[0]
                grid.remove_agent(alvo)
                try: self.model.custom_agents.remove(alvo)
                except ValueError: pass
                self.pontos += alvo.pontos
                self.energia -= alvo.pontos
                # mover para a célula da sujeira limpa
                grid.move_agent(self, v)
                self.registrar_memoria(v, limpo=True)
                return

        # Atualiza memória da célula atual
        self.registrar_memoria(pos_atual, limpo=True)

        # Procurar sujeira conhecida na memória
        sujeira_memoria = []
        for pos, info in self.memoria.items():
            if info.get("limpo", False):
                continue
            for vpos, tipo in info["visto"]:
                if "sujeira" in tipo:
                    # adiciona somente se não tem móvel
                    contents = grid.get_cell_list_contents([vpos])
                    if not any(isinstance(o, Movel) for o in contents):
                        sujeira_memoria.append(vpos)
        if sujeira_memoria and self.energia >= 1:
            alvo_pos = random.choice(sujeira_memoria)
            grid.move_agent(self, alvo_pos)
            self.energia -= 1
            return

        # Explorar células não visitadas, evitando móveis
        valid_moves = [
            pos for pos in vizinhos
            if not self.ja_visitou(pos)
            and not any(isinstance(o, Movel) for o in grid.get_cell_list_contents([pos]))
        ]
        if valid_moves and self.energia >= 1:
            new_pos = random.choice(valid_moves)
            grid.move_agent(self, new_pos)
            self.energia -= 1
            return

        # Exploração forçada se houver sujeira restante, evitando móveis
        todas_sujeiras = [a for a in self.model.custom_agents if isinstance(a, Sujeira)]
        if todas_sujeiras:
            possiveis = [
                pos for pos in vizinhos
                if not any(isinstance(o, Movel) for o in grid.get_cell_list_contents([pos]))
            ]
            if possiveis and self.energia >= 1:
                grid.move_agent(self, random.choice(possiveis))
                self.energia -= 1
                return

        #  Se não há sujeira nem energia, para
        self.parado = True





class AmbienteModelo(Model):
    def __init__(self, width=5, height=5, n_sujeiras=5, n_moveis=3):
        super().__init__()
        self.grid = MultiGrid(width, height, torus=False)
        self.custom_agents = []

        for i in range(n_sujeiras):
            x, y = random.randint(1, width - 1), random.randint(1, height - 1)
            tipo = random.choice(list(DIRTY_TYPES.keys()))
            sujeira = Sujeira(self, tipo)
            self.grid.place_agent(sujeira, (x, y))
            self.custom_agents.append(sujeira)

        for i in range(n_moveis):
            x, y = random.randint(1, width - 1), random.randint(1, height - 1)
            movel = Movel(self)
            self.grid.place_agent(movel, (x, y))
            self.custom_agents.append(movel)

        aspirador = AspiradorModelo(self)
        self.grid.place_agent(aspirador, (0, 0))
        self.custom_agents.append(aspirador)

    def step(self):
        for agent in list(self.custom_agents):
            agent.step()
