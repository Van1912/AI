# Evaluation/plots.py
import os
import matplotlib.pyplot as plt

def plot_convergence(history_sa, history_gwo, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.figure()
    plt.plot(history_sa, label="SA")
    plt.plot(history_gwo, label="GWO")
    plt.xlabel("Step")
    plt.ylabel("Best Cost")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
