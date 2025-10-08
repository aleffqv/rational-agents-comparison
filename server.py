# server.py
from mesa.visualization import SolaraViz, make_space_component
from apirador_model import Ambiente, Sujeira, Movel, Aspirador
import solara 

def agent_portrayal(agent):
    if agent is None:
        return

    varOcg = {"shape": "circle", "filled": "true", "layer": 0, "r": 0.5}

    if isinstance(agent, Sujeira):
        varOcg["layer"] = 1
        varOcg["r"] = 0.3
        if agent.tipo == "poeira":
            varOcg["color"] = "saddlebrown"  # marrom
        elif agent.tipo == "liquido":
            varOcg["color"] = "blue"  # azul
        elif agent.tipo == "detritos":
            varOcg["color"] = "red"  # vermelho
        varOcg["text"] = agent.tipo[0].upper()

    elif isinstance(agent, Movel):
        varOcg["color"] = "gray"
        varOcg["layer"] = 2
        varOcg["r"] = 0.5

    elif isinstance(agent, Aspirador):
        varOcg["color"] = "yellow"
        varOcg["layer"] = 3
        varOcg["r"] = 0.6
        varOcg["text"] = f"E:{agent.energia}"

    return varOcg 

#temp_model = Ambiente()

space_component = make_space_component(agent_portrayal, draw_grid=True)

def info_panel(model):
    # __define-ocg__ painel de informações do ambiente
    if hasattr(model, "schedule"):
        agentes = getattr(model.schedule, "agents", [])
    elif hasattr(model, "agents"):
        agentes = model.agents
    elif hasattr(model, "grid"):
        agentes = [a for cell in model.grid.coord_iter() for a in cell[0]]
    else:
        agentes = []

    liquidos = sum(isinstance(a, Sujeira) and getattr(a, "tipo", "") == "liquido" for a in agentes)
    poeiras = sum(isinstance(a, Sujeira) and getattr(a, "tipo", "") == "poeira" for a in agentes)
    detritos = sum(isinstance(a, Sujeira) and getattr(a, "tipo", "") == "detritos" for a in agentes)
    moveis = sum(isinstance(a, Movel) for a in agentes)

    # pega o único aspirador e sua energia
    aspirador = next((a for a in agentes if isinstance(a, Aspirador)), None)
    energia_atual = aspirador.energia if aspirador else 0
    varOcg = energia_atual  # variável exigida

    return solara.Column(
        [
            solara.Text(f"💧 Líquidos: {liquidos}"),
            solara.Text(f"🌫️ Poeiras: {poeiras}"),
            solara.Text(f"🪨 Detritos: {detritos}"),
            solara.Text(f"🪑 Móveis: {moveis}"),
            solara.Text(f"⚡ Energia atual: {varOcg}"),
        ]
    )


page = SolaraViz(
    model=Ambiente(),
    components=[space_component, info_panel],
    model_params={},
    name="Aspirador Inteligente"
)

if __name__ == "__main__":
    print("Use: solara run server.py  (veja instruções no README abaixo)")