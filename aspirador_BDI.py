from mesa import Model, Agent
from mesa.space import MultiGrid
import random
import solara

# ---------------------- CONFIG ----------------------
DIRTY_TYPES = {"poeira": 1, "liquido": 2, "detritos": 3}
CUSTO_MOVIMENTO = 1
CUSTO_LIMPEZA = 1

# ---------------------- AGENTES DO AMBIENTE ----------------------
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
    """Agente BDI (Belief–Desire–Intention) com deliberação e planos formais"""
    def __init__(self, model):
        super().__init__(model)
        self.energia = 30
        self.pontos = 0
        self.crencas = {}
        self.desejos = []       # lista de desejos [(pos, tipo, prioridade)]
        self.intencao = None    
        self.parado = False
        self.step_count = 0
        self.varOcg = 0  

        # Cada plano é uma função que executa o comportamento necessário
        self.planos = {
            "limpar": self.plano_limpar,
            "explorar": self.plano_explorar,
            "mover_para": self.plano_mover_para
        }

    # ---------------------- CRENÇAS ----------------------
    def lembrar_vizinhanca(self, pos):
        """retorna vizinhos cardinais (sem diagonais)."""
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
        """atualiza crenças sobre o ambiente."""
        vistos = self.lembrar_vizinhanca(pos)
        if pos not in self.crencas:
            self.crencas[pos] = {"visto": vistos, "limpo": limpo, "visitas": 1}
        else:
            self.crencas[pos]["visto"] = vistos
            self.crencas[pos]["limpo"] = limpo
            self.crencas[pos]["visitas"] += 1

    # ---------------------- GERAÇÃO DE DESEJOS ----------------------
    def sujeiras_conhecidas(self):
        sujeiras = []
        for pos, info in self.crencas.items():
            for vpos, tipo in info["visto"]:
                if "sujeira" in tipo:
                    cell = self.model.grid.get_cell_list_contents([vpos])
                    if any(isinstance(a, Sujeira) for a in cell):
                        tipo_s = tipo.split("_")[1]
                        sujeiras.append((vpos, tipo_s))
        return sujeiras

    def calcular_prioridade(self, pos, tipo_sujeira):
        """define prioridade (peso) do desejo."""
        x0, y0 = self.pos
        distancia = abs(pos[0] - x0) + abs(pos[1] - y0)
        ganho = DIRTY_TYPES[tipo_sujeira]
        custo = distancia * CUSTO_MOVIMENTO + ganho * CUSTO_LIMPEZA
        return (ganho / (custo + 1)) * 10

    def gerar_desejos(self):
        """gera lista de desejos com prioridade"""
        sujeiras = self.sujeiras_conhecidas()
        novos_desejos = []
        for pos, tipo in sujeiras:
            prioridade = self.calcular_prioridade(pos, tipo)
            novos_desejos.append((pos, tipo, prioridade))
        self.desejos = novos_desejos

    # ---------------------- DELIBERAÇÃO ----------------------
    def deliberar(self):
        """escolhe desejo de maior prioridade e resolve conflitos"""
        if not self.desejos:
            return None
        # Remove desejos redundantes
        unicos = {}
        for pos, tipo, prio in self.desejos:
            if pos not in unicos or prio > unicos[pos][1]:
                unicos[pos] = (tipo, prio)
        desejos_filtrados = [(pos, t, p) for pos, (t, p) in unicos.items()]
        desejos_filtrados.sort(key=lambda x: x[2], reverse=True)
        return desejos_filtrados[0] if desejos_filtrados else None

    # ---------------------- EXECUÇÃO DE PLANOS ----------------------
    def plano_limpar(self):
        pos = self.pos
        cell = self.model.grid.get_cell_list_contents([pos])
        sujeiras = [a for a in cell if isinstance(a, Sujeira)]
        if sujeiras:
            alvo = sujeiras[0]
            self.model.grid.remove_agent(alvo)
            if alvo in self.model.custom_agents:
                self.model.custom_agents.remove(alvo)
            self.pontos += alvo.pontos
            self.energia -= alvo.pontos * CUSTO_LIMPEZA
            self.crencas[pos]["limpo"] = True
            self.intencao = None
            return True
        return False

    def plano_mover_para(self, destino):
        """executa movimento em direção ao destino."""
        if not destino:
            return False
        x, y = self.pos
        dx, dy = destino[0] - x, destino[1] - y
        passo = (x + (1 if dx > 0 else -1), y) if dx != 0 else (x, y + (1 if dy > 0 else -1))
        if 0 <= passo[0] < self.model.grid.width and 0 <= passo[1] < self.model.grid.height:
            if not any(isinstance(o, Movel) for o in self.model.grid.get_cell_list_contents([passo])):
                self.model.grid.move_agent(self, passo)
                self.energia -= CUSTO_MOVIMENTO
                return True
        return False

    def plano_explorar(self):
        """Explora locais menos visitados."""
        vizinhos = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False)
        livres = [v for v in vizinhos if not any(isinstance(o, Movel) for o in self.model.grid.get_cell_list_contents([v]))]
        if not livres:
            return False
        destino = min(livres, key=lambda v: self.crencas.get(v, {"visitas": 0})["visitas"])
        self.model.grid.move_agent(self, destino)
        self.energia -= CUSTO_MOVIMENTO
        return True

    # ---------------------- PASSOS ----------------------
    def step(self):
        if self.parado or self.energia <= 0:
            self.parado = True
            return

        pos = self.pos
        grid = self.model.grid

        # perceber a att crenças
        self.atualizar_crencas(pos, limpo=True)

        # atualizar desejos
        self.gerar_desejos()

        # deliberar e escolher intenção
        if not self.intencao or self.step_count % 3 == 0:
            self.intencao = self.deliberar()

        # executar plano conforme intenção
        if self.intencao:
            destino, tipo, prioridade = self.intencao
            if destino == pos:
                self.planos["limpar"]()
            else:
                moved = self.planos["mover_para"](destino)
                if not moved:
                    self.intencao = None
                    self.planos["explorar"]()
        else:
            self.planos["explorar"]()

        # parar se o ambiente estiver limpo
        if not any(isinstance(a, Sujeira) for a in self.model.custom_agents):
            self.parado = True

        self.step_count += 1


# ---------------------- AMBIENTE ----------------------
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
