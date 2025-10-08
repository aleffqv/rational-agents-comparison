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



#Agente reativo simples
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

        grid = self.model.grid

        # --- 1️⃣ Verifica sujeira na célula atual ---
        cell_contents = grid.get_cell_list_contents([self.pos])
        sujeiras = [obj for obj in cell_contents if isinstance(obj, Sujeira)]

        if sujeiras and self.energia >= sujeiras[0].pontos:
            alvo = sujeiras[0]
            grid.remove_agent(alvo)
            try:
                self.model.custom_agents.remove(alvo)
            except ValueError:
                pass
            self.pontos += alvo.pontos
            self.energia -= alvo.pontos  # custo proporcional à sujeira
            print(f"🧹 Limpou {alvo.tipo} | Pontos: {self.pontos} | Energia: {self.energia}")
            return

        # --- 2️⃣ Verifica sujeira nas células vizinhas ---
        vizinhos = grid.get_neighborhood(self.pos, moore=False, include_center=False)
        sujeiras_vizinhas = []
        for pos in vizinhos:
            for obj in grid.get_cell_list_contents([pos]):
                if isinstance(obj, Sujeira):
                    sujeiras_vizinhas.append((pos, obj))

        if sujeiras_vizinhas:
            alvo_pos, alvo_obj = sujeiras_vizinhas[0]

            # verifica se há móvel bloqueando
            bloqueado = any(isinstance(o, Movel) for o in grid.get_cell_list_contents([alvo_pos]))
            if not bloqueado and self.energia >= 1:
                grid.move_agent(self, alvo_pos)
                self.energia -= 1
                print(f"➡ Moveu para sujeira {alvo_obj.tipo} em {alvo_pos} | Energia: {self.energia}")
            return

        #  Caso não tenha sujeira por perto, move-se aleatoriamente
        possible_positions = grid.get_neighborhood(self.pos, moore=False, include_center=False)
        valid_moves = []
        for pos in possible_positions:
            contents = grid.get_cell_list_contents([pos])
            if any(isinstance(o, Movel) for o in contents):
                continue
            valid_moves.append(pos)

        if valid_moves and self.energia >= 1:
            new_position = random.choice(valid_moves)
            grid.move_agent(self, new_position)
            self.energia -= 1
            print(f"➡ Moveu aleatoriamente para {new_position} | Energia: {self.energia}")
        else:
            print(f"⚠ Sem movimentos válidos ou energia insuficiente em {self.pos}.")















class Ambiente(Model):
    def __init__(self, width=5, height=5, n_sujeiras=5, n_moveis=3):
        super().__init__()
        self.grid = MultiGrid(width, height, torus=False)
        # não usar model.agents (reservado), usar nome customizado
        self.custom_agents = []

        # criar sujeiras
        for i in range(n_sujeiras):
            x, y = random.randint(1, width - 1), random.randint(1, height - 1)
            tipo = random.choice(list(DIRTY_TYPES.keys()))
            sujeira = Sujeira(self, tipo)   # instanciar passando o model primeiro
            self.grid.place_agent(sujeira, (x, y))
            self.custom_agents.append(sujeira)

        # criar móveis
        for i in range(n_moveis):
            x, y = random.randint(1, width - 1), random.randint(1, height - 1)
            movel = Movel(self)
            self.grid.place_agent(movel, (x, y))
            self.custom_agents.append(movel)

        # criar aspirador
        aspirador = Aspirador(self)
        self.grid.place_agent(aspirador, (0, 0))
        self.custom_agents.append(aspirador)

    def step(self):
        # ativa cada agente (ordem fixa); aleatório: random.shuffle
        for agent in list(self.custom_agents):
            agent.step()
