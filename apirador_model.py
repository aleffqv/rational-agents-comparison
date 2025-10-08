# aspirador_model.py
from mesa import Model, Agent
from mesa.space import MultiGrid
import random

# tipos de sujeira e seus valores
DIRTY_TYPES = {
    "poeira": 1,
    "liquido": 2,
    "detritos": 3
}


class Sujeira(Agent):
    def __init__(self, model, tipo):
        # note: em Mesa 3.x o construtor do Agent recebe o model apenas
        super().__init__(model)
        self.tipo = tipo
        self.pontos = DIRTY_TYPES[tipo]

    def step(self):
        pass  # sujeira não age sozinha


class Movel(Agent):
    def __init__(self, model):
        super().__init__(model)

    def step(self):
        pass  # móveis não se movem


class Aspirador(Agent):
    def __init__(self, model):
        super().__init__(model)
        self.energia = 30
        self.pontos = 0
        self.parado = False

    def step(self):
        if self.parado:
            return

        if self.energia <= 0:
            print("Sem energia para mover ou limpar.")
            self.parado = True
            return

        # Verifica sujeiras na célula
        cell_contents = self.model.grid.get_cell_list_contents([self.pos])
        sujeiras = [obj for obj in cell_contents if isinstance(obj, Sujeira)]

        if sujeiras and self.energia >= 2:
            alvo = sujeiras[0]
            # remove do grid
            try:
                self.model.grid.remove_agent(alvo)
            except Exception:
                pass
            # remove da lista custom
            try:
                self.model.custom_agents.remove(alvo)
            except ValueError:
                pass
            self.pontos += alvo.pontos
            self.energia -= 2
            print(f"Limpo {alvo.tipo} | Pontos: {self.pontos} | Energia: {self.energia}")
        else:
            # movimentos von Neumann (N,S,L,O)
            possible_positions = self.model.grid.get_neighborhood(
                self.pos, moore=False, include_center=False
            )
            # filtrar posições ocupadas por móveis
            valid_moves = []
            for pos in possible_positions:
                contents = self.model.grid.get_cell_list_contents([pos])
                if any(isinstance(o, Movel) for o in contents):
                    continue
                valid_moves.append(pos)

            if valid_moves and self.energia >= 1:
                new_position = random.choice(valid_moves)
                self.model.grid.move_agent(self, new_position)
                self.energia -= 1
                print(f"Moveu para {new_position} | Energia: {self.energia}")
            else:
                print(f"Sem movimentos válidos ou energia insuficiente em {self.pos}.")


class Ambiente(Model):
    def __init__(self, width=5, height=5, n_sujeiras=5, n_moveis=3):
        super().__init__()
        self.grid = MultiGrid(width, height, torus=False)
        # não usar model.agents (reservado), usar nome customizado
        self.custom_agents = []

        # criar sujeiras
        for i in range(n_sujeiras):
            x, y = random.randint(0, width - 1), random.randint(0, height - 1)
            tipo = random.choice(list(DIRTY_TYPES.keys()))
            sujeira = Sujeira(self, tipo)   # instanciar passando o model primeiro
            self.grid.place_agent(sujeira, (x, y))
            self.custom_agents.append(sujeira)

        # criar móveis
        for i in range(n_moveis):
            x, y = random.randint(0, width - 1), random.randint(0, height - 1)
            movel = Movel(self)
            self.grid.place_agent(movel, (x, y))
            self.custom_agents.append(movel)

        # criar aspirador
        aspirador = Aspirador(self)
        self.grid.place_agent(aspirador, (0, 0))
        self.custom_agents.append(aspirador)

    def step(self):
        # ativa cada agente (ordem fixa); se quiser aleatório, use random.shuffle antes
        for agent in list(self.custom_agents):
            agent.step()
