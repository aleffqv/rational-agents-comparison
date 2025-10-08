# run_simulation.py
from apirador_model import Ambiente

model = Ambiente()

for i in range(20):
    print(f"\n--- Step {i+1} ---")
    model.step()
