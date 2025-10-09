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

# ---------------------- AGENTE REATIVO ----------------------
class Aspirador(Agent):
    """Aspirador reativo simples, funcional mesmo cercado por móveis ou paredes"""
    def __init__(self, model):
        super().__init__(model)
        self.energia = 30
        self.pontos = 0
        self.parado = False

    def step(self):
        if self.parado or self.energia <= 0:
            self.parado = True
            return

        grid = self.model.grid
        x, y = self.pos

        # limpar sujeira na célula atual
        cell_contents = grid.get_cell_list_contents([self.pos])
        sujeiras = [obj for obj in cell_contents if isinstance(obj, Sujeira)]
        if sujeiras:
            alvo = sujeiras[0]
            if self.energia >= alvo.pontos:
                grid.remove_agent(alvo)
                try:
                    self.model.custom_agents.remove(alvo)
                except ValueError:
                    pass
                self.pontos += alvo.pontos
                self.energia -= alvo.pontos
            return  # limpou, termina o passo

        # procurar sujeira em células vizinhas
        vizinhos = grid.get_neighborhood(self.pos, moore=False, include_center=False)
        for pos in vizinhos:
            contents = grid.get_cell_list_contents([pos])
            if any(isinstance(obj, Sujeira) for obj in contents):
                # mover se célula não estiver bloqueada
                if not any(isinstance(obj, Movel) for obj in contents):
                    grid.move_agent(self, pos)
                    self.energia -= 1
                    return

        # movimentação aleatória segura
        valid_moves = []
        for pos in vizinhos:
            contents = grid.get_cell_list_contents([pos])
            if not any(isinstance(obj, Movel) for obj in contents):
                valid_moves.append(pos)

        if valid_moves:
            new_pos = random.choice(valid_moves)
            grid.move_agent(self, new_pos)
            self.energia -= 1
        else:
            # não há movimentos válidos, permanece no lugar
            pass

# ---------------------- AMBIENTE ----------------------
class Ambiente(Model):
    def __init__(self, width=5, height=5, n_sujeiras=5, n_moveis=3):
        super().__init__()
        self.grid = MultiGrid(width, height, torus=False)
        self.custom_agents = []

        # criar sujeiras
        for _ in range(n_sujeiras):
            while True:
                x, y = random.randint(0, width - 1), random.randint(0, height - 1)
                if not self.grid.get_cell_list_contents([(x, y)]):
                    break
            tipo = random.choice(list(DIRTY_TYPES.keys()))
            sujeira = Sujeira(self, tipo)
            self.grid.place_agent(sujeira, (x, y))
            self.custom_agents.append(sujeira)

        # criar móveis
        for _ in range(n_moveis):
            while True:
                x, y = random.randint(0, width - 1), random.randint(0, height - 1)
                if not self.grid.get_cell_list_contents([(x, y)]):
                    break
            movel = Movel(self)
            self.grid.place_agent(movel, (x, y))
            self.custom_agents.append(movel)

        # criar aspirador
        aspirador = Aspirador(self)
        self.grid.place_agent(aspirador, (0, 0))
        self.custom_agents.append(aspirador)

    def step(self):
        for agent in list(self.custom_agents):
            agent.step()
