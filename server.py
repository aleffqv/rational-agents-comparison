# server.py
from mesa.visualization import SolaraViz, make_space_component
from apirador_model import Ambiente, Sujeira, Movel, Aspirador

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

page = SolaraViz(
    model=Ambiente(),
    components=[space_component],
    model_params={},
    name="Aspirador Inteligente"
)

if __name__ == "__main__":
    print("Use: solara run server.py  (veja instruções no README abaixo)")