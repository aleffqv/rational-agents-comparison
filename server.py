# server.py
from mesa.visualization import SolaraViz, make_space_component
from aspirador_bmodel import AmbienteModelo
from aspirador_objetivo import AmbienteObjetivo
from aspirador_utilidade import AmbienteUtilidade 
from aspirador_BDI import AmbienteBDI
from apirador_model import Ambiente
import solara
import pandas as pd
import matplotlib.pyplot as plt


histories = {}  # histórico de energia e pontos para cada modelo

def agent_portrayal(agent):
    if agent is None:
        return

    portrayal = {"shape": "circle", "filled": "true", "layer": 0, "r": 0.5}

    tipo = getattr(agent, "tipo", None)
    if tipo is not None:
        portrayal["layer"] = 1
        portrayal["r"] = 0.3
        colors = {"poeira": "saddlebrown", "liquido": "blue", "detritos": "red"}
        portrayal["color"] = colors.get(tipo, "brown")
        portrayal["text"] = str(tipo)[0].upper()
        return portrayal

    if agent.__class__.__name__ == "Movel":
        portrayal["color"] = "gray"
        portrayal["layer"] = 2
        portrayal["r"] = 0.5
        return portrayal

    energia = getattr(agent, "energia", None)
    if energia is not None:
        portrayal["color"] = "yellow"
        portrayal["layer"] = 3
        portrayal["r"] = 0.6
        points = getattr(agent, "pontos", 0)
        portrayal["text"] = f"E:{energia}\nP:{points}"
        return portrayal

    portrayal["color"] = "blue"
    return portrayal

space_component = make_space_component(agent_portrayal, draw_grid=True)

# ---------------------- PAINEL DE INFOs ----------------------
def info_panel(model):
    agentes = []
    if hasattr(model, "schedule"):
        agentes = getattr(model.schedule, "agents", [])
    elif hasattr(model, "agents"):
        agentes = model.agents
    elif hasattr(model, "grid"):
        agentes = [a for cell in model.grid.coord_iter() for a in cell[0]]

    liquidos = sum(getattr(a, "tipo", "") == "liquido" for a in agentes)
    poeiras = sum(getattr(a, "tipo", "") == "poeira" for a in agentes)
    detritos = sum(getattr(a, "tipo", "") == "detritos" for a in agentes)
    moveis = sum(a.__class__.__name__ == "Movel" for a in agentes)

    aspirador = next((a for a in agentes if getattr(a, "energia", None) is not None), None)
    energia = aspirador.energia if aspirador else 0
    pontos = aspirador.pontos if aspirador else 0
    eficiencia = round(pontos / max(1, 30 - energia), 2)

    return solara.Column(
        [
            solara.Text(f"💧 Líquidos restantes: {liquidos}"),
            solara.Text(f"🌫️ Poeiras restantes: {poeiras}"),
            solara.Text(f"🪨 Detritos restantes: {detritos}"),
            solara.Text(f"🪑 Móveis: {moveis}"),
            solara.Text(f"⚡ Energia atual: {energia}"),
            solara.Text(f"⭐ Pontos acumulados: {pontos}"),
            solara.Text(f"📊 Eficiência: {eficiencia}"),
        ],
        style={"padding": "10px"}
    )

# ---------------------- DASHBOARD DINÂMICO ----------------------
def dashboard_component(model, model_name):
    global histories
    if model_name not in histories:
        histories[model_name] = {"energia": [], "pontos": [], "steps": []}

    agentes = []
    if hasattr(model, "schedule"):
        agentes = getattr(model.schedule, "agents", [])
    elif hasattr(model, "agents"):
        agentes = model.agents
    elif hasattr(model, "grid"):
        agentes = [a for cell in model.grid.coord_iter() for a in cell[0]]

    aspirador = next((a for a in agentes if getattr(a, "energia", None) is not None), None)
    if aspirador:
        histories[model_name]["energia"].append(aspirador.energia)
        histories[model_name]["pontos"].append(aspirador.pontos)
        histories[model_name]["steps"].append(len(histories[model_name]["steps"]) + 1)

    df = pd.DataFrame(histories[model_name])
    if df.empty:
        return solara.Text("Sem dados ainda")

    fig, ax = plt.subplots(figsize=(6, 4))
    energia_gasta = [30 - e for e in df["energia"]]  
    eficiencia = [p / max(1, eg) for p, eg in zip(df["pontos"], energia_gasta)]
    ax.plot(df["steps"], df["pontos"], label="Pontos", color="green", linewidth=2)
    ax.plot(df["steps"], eficiencia, label="Eficiência", color="orange", linestyle="--", linewidth=2)
    ax.set_xlabel("Passos")
    ax.set_ylabel("Valor")
    ax.set_title(f"Histórico: {model_name}")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    plt.tight_layout()

    return solara.FigureMatplotlib(fig)


# ---------------------- DASHBOARD COMPARATIVO ----------------------
def comparative_dashboard(model=None):
    if not histories:
        return solara.Text("Sem dados comparativos ainda")

    fig, ax = plt.subplots(figsize=(8, 5))
    for model_name, data in histories.items():
        if data["steps"]:
            df = pd.DataFrame(data)
            energia_gasta = [30 - e for e in df["energia"]]
            eficiencia = [p / max(1, eg) for p, eg in zip(df["pontos"], energia_gasta)]
            ax.plot(df["steps"], eficiencia, linestyle="--", label=f"Eficiência {model_name}", linewidth=2)

    ax.set_xlabel("Passos")
    ax.set_ylabel("Eficiência")
    ax.set_title("Comparativo de Eficiência dos Agentes")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    plt.tight_layout()

    return solara.FigureMatplotlib(fig)


@solara.component
def Page():
    current, set_current = solara.use_state("re") 

    nav = solara.Row(
        [
            solara.Button("Aspirador Reativo", on_click=lambda: set_current("re")),
            solara.Button("Aspirador (Baseado em Modelo)", on_click=lambda: set_current("bm")),
            solara.Button("Aspirador (Baseado em Objetivo)", on_click=lambda: set_current("bo")),
            solara.Button("Aspirador (Baseado em Utilidade)", on_click=lambda: set_current("bu")),
            solara.Button("Aspirador (Modelo BDI)", on_click=lambda: set_current("bdi")),
        ],
        style={"gap": "8px", "margin-bottom": "10px"}
    )

    model_map = {
        "re": (Ambiente, "Aspirador Reativo"),
        "bm": (AmbienteModelo, "Aspirador (Baseado em Modelo)"),
        "bo": (AmbienteObjetivo, "Aspirador (Baseado em Objetivo)"),
        "bu": (AmbienteUtilidade, "Aspirador (Baseado em Utilidade)"),
        "bdi": (AmbienteBDI, "Aspirador (Modelo BDI)")
    }
    model_class, name = model_map.get(current, (Ambiente, "Aspirador Reativo"))

    histories[name] = {"energia": [], "pontos": [], "steps": []}

    model_instance = model_class()

    viz = SolaraViz(
        model=model_instance,
        components=[
            space_component,
            lambda m=model_instance: info_panel(m),
            lambda m=model_instance, n=name: dashboard_component(m, n),
            comparative_dashboard
        ],
        name=name
    )

    return solara.Column([nav, viz])


if __name__ == "__main__":
    print("Use: solara run server.py  (veja instruções no README)")
