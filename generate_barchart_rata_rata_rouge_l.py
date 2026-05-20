import matplotlib.pyplot as plt
import numpy as np


plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.25
plt.rcParams["grid.linestyle"] = "-"

methods = ["RAG", "Tanpa RAG"]
metrics = ["Precision", "Recall", "F1-Score"]

scores = {
    "RAG": [0.6115, 0.8455, 0.6664],
    "Tanpa RAG": [0.2596, 0.3260, 0.2784],
}

x = np.arange(len(metrics))
width = 0.36

fig, ax = plt.subplots(figsize=(10, 6))

rag_bars = ax.bar(
    x - width / 2,
    scores["RAG"],
    width,
    label="RAG",
    color="#2ecc71",
)
no_rag_bars = ax.bar(
    x + width / 2,
    scores["Tanpa RAG"],
    width,
    label="Tanpa RAG",
    color="#c62828",
)

ax.set_title(
    "Perbandingan Rata-rata Metrik ROUGE-L",
    fontsize=15,
    fontweight="bold",
    pad=18,
)
ax.set_ylabel("Skor Rata-rata", fontsize=12)
ax.set_xticks(x)
ax.set_xticklabels(metrics, fontsize=11)
ax.set_ylim(0, 1.0)
ax.legend(fontsize=11)

for bars in (rag_bars, no_rag_bars):
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + 0.015,
            f"{height:.4f}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

plt.tight_layout()
plt.savefig("barchart_rata_rata_rouge_l.png", dpi=300, bbox_inches="tight")
plt.close()

print("Bar chart berhasil disimpan ke barchart_rata_rata_rouge_l.png")
