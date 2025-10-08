# server.py
from mesa.visualization import SolaraViz, make_space_component
from apirador_model import Ambiente, Sujeira, Movel, Aspirador
from aspirador_bmodel import AmbienteModelo
import solara 

def agent_portrayal(agent):
    if agent is None:
        return

    varOcg = {"shape": "circle", "filled": "true", "layer": 0, "r": 0.5}

    tipo = getattr(agent, "tipo", None)
    if tipo is not None:
        varOcg["layer"] = 1
        varOcg["r"] = 0.3
        if tipo == "poeira":
            varOcg["color"] = "saddlebrown"
        elif tipo == "liquido":
            varOcg["color"] = "blue"
        elif tipo == "detritos":
            varOcg["color"] = "red"
        else:
            varOcg["color"] = "brown"
        varOcg["text"] = str(tipo)[0].upper()
        return varOcg

    if agent.__class__.__name__ == "Movel":
        varOcg["color"] = "gray"
        varOcg["layer"] = 2
        varOcg["r"] = 0.5
        return varOcg

    energia = getattr(agent, "energia", None)
    if energia is not None:
        varOcg["color"] = "yellow"
        varOcg["layer"] = 3
        varOcg["r"] = 0.6
        varOcg["text"] = f"E:{energia}"
        return varOcg

    # fallback
    varOcg["color"] = "blue"
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

    liquidos = sum(getattr(a, "tipo", "") == "liquido" for a in agentes)
    poeiras = sum(getattr(a, "tipo", "") == "poeira" for a in agentes)
    detritos = sum(getattr(a, "tipo", "") == "detritos" for a in agentes)
    moveis = sum(a.__class__.__name__ == "Movel" for a in agentes)

    # pega o aspirador (qualquer classe que exponha `energia`)
    aspirador = next((a for a in agentes if getattr(a, "energia", None) is not None), None)
    energia_atual = aspirador.energia if aspirador else 0
    varOcg = energia_atual

    return solara.Column(
        [
            solara.Text(f"💧 Líquidos: {liquidos}"),
            solara.Text(f"🌫️ Poeiras: {poeiras}"),
            solara.Text(f"🪨 Detritos: {detritos}"),
            solara.Text(f"🪑 Móveis: {moveis}"),
            solara.Text(f"⚡ Energia atual: {varOcg}"),
        ]
    )


# Agente reativo simples
@solara.component
def Page0():
    viz = SolaraViz(
        model=Ambiente(),               # <-- instância do modelo reativo
        components=[space_component, info_panel],
        name="Aspirador Reativo"
    )
    return viz

# Agente baseado em modelo (com memória)
@solara.component
def Page1():
    viz = SolaraViz(
        model=AmbienteModelo(),         # <-- instância do modelo baseado em memória
        components=[space_component, info_panel],
        name="Aspirador (Baseado em Modelo)"
    )
    return viz

@solara.component
def Page():
    current, set_current = solara.use_state("re")  # "re" ou "bm"

    nav = solara.Row(
        [
            solara.Button("Aspirador Reativo", on_click=lambda: set_current("re")),
            solara.Button("Aspirador (Baseado em Modelo)", on_click=lambda: set_current("bm")),
        ],
        style={"gap": "8px"},
    )

    if current == "re":
        viz = SolaraViz(
            model=Ambiente(),
            components=[space_component, info_panel],
            name="Aspirador Reativo",
        )
    else:
        viz = SolaraViz(
            model=AmbienteModelo(),
            components=[space_component, info_panel],
            name="Aspirador (Baseado em Modelo)",
        )

    return solara.Column([nav, viz])




if __name__ == "__main__":
    print("Use: solara run server.py  (veja instruções no README abaixo)")