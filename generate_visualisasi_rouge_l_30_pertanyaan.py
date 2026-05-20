import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.25
plt.rcParams["grid.linestyle"] = "-"


data = [
    [1, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
    [2, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    [3, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
    [4, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
    [5, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
    [6, 0.56, 0.3889, 1.0, 0.286, 0.286, 0.286],
    [7, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
    [8, 0.77, 0.625, 1.0, 0.333, 0.24, 0.533],
    [9, 0.286, 1.0, 0.1667, 0.0, 0.0, 0.0],
    [10, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
    [11, 0.3294, 0.2295, 0.5833, 0.3333, 0.5, 0.25],
    [12, 0.7368, 0.7, 0.7778, 0.4211, 0.4, 0.4444],
    [13, 0.3684, 0.2917, 0.5, 0.2553, 0.3158, 0.2143],
    [14, 0.566, 0.4054, 0.9375, 0.3256, 0.2593, 0.4375],
    [15, 0.6154, 0.4762, 0.8696, 0.4286, 0.3636, 0.5217],
    [16, 0.7619, 0.7273, 0.8, 0.5, 0.5, 0.5],
    [17, 0.4565, 0.3088, 0.875, 0.381, 0.3077, 0.5],
    [18, 0.7442, 0.6154, 0.9412, 0.449, 0.3438, 0.6471],
    [19, 0.3824, 0.2407, 0.9286, 0.2353, 0.1622, 0.4286],
    [20, 0.2957, 0.1771, 0.8947, 0.2642, 0.2059, 0.3684],
    [21, 0.2947, 0.1818, 0.7778, 0.2105, 0.2, 0.2222],
    [22, 0.6061, 0.5556, 0.6667, 0.359, 0.2917, 0.4667],
    [23, 0.5714, 0.5, 0.6667, 0.1538, 0.1818, 0.1333],
    [24, 0.6531, 0.5333, 0.8421, 0.3478, 0.2963, 0.4211],
    [25, 0.5882, 0.4167, 1.0, 0.2609, 0.2308, 0.3],
    [26, 0.9565, 0.9167, 1.0, 0.439, 0.4737, 0.4091],
    [27, 0.6667, 0.5484, 0.85, 0.4681, 0.4074, 0.55],
    [28, 0.593, 0.4554, 0.85, 0.2549, 0.3095, 0.2167],
    [29, 0.7, 0.5526, 0.9545, 0.5294, 0.3913, 0.8182],
    [30, 0.4906, 0.5, 0.4815, 0.1154, 0.12, 0.1111],
]

columns = [
    "No",
    "RAG F1-Score",
    "RAG Precision",
    "RAG Recall",
    "Tanpa RAG F1-Score",
    "Tanpa RAG Precision",
    "Tanpa RAG Recall",
]

df = pd.DataFrame(data, columns=columns)
df.to_csv("data_rouge_l_30_pertanyaan.csv", index=False, encoding="utf-8-sig")


def format_score(value: float) -> str:
    truncated_value = math.floor(value * 100) / 100.0
    return f"{truncated_value:.2f}"


def annotate_points(ax, x_values, y_values, color: str, y_offset: int):
    for x_value, y_value in zip(x_values, y_values):
        ax.annotate(
            format_score(y_value),
            (x_value, y_value),
            textcoords="offset points",
            xytext=(0, y_offset),
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
            color=color,
            bbox={
                "boxstyle": "round,pad=0.18",
                "facecolor": "white",
                "edgecolor": color,
                "linewidth": 0.6,
                "alpha": 0.85,
            },
        )


def generate_line_chart(
    metric: str,
    rag_column: str,
    no_rag_column: str,
    output_file: str,
    show_point_values: bool = False,
):
    fig_width = 15 if show_point_values else 13
    fig_height = 7 if show_point_values else 6
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    ax.plot(
        df["No"],
        df[rag_column],
        marker="o",
        markersize=5,
        linewidth=2.5,
        label="RAG",
        color="#2ecc71",
    )
    ax.plot(
        df["No"],
        df[no_rag_column],
        marker="s",
        markersize=5,
        linewidth=2.5,
        label="Tanpa RAG",
        color="#c62828",
    )

    ax.fill_between(df["No"], df[rag_column], df[no_rag_column], color="#9e9e9e", alpha=0.12)
    ax.set_title(f"Perbandingan ROUGE-L {metric} per Pertanyaan", fontsize=15, fontweight="bold", pad=18)
    ax.set_xlabel("Nomor Pertanyaan", fontsize=12)
    ax.set_ylabel(f"Skor {metric}", fontsize=12)
    ax.set_xticks(df["No"])
    ax.set_ylim(-0.12 if show_point_values else -0.03, 1.15 if show_point_values else 1.08)
    ax.legend(fontsize=11, loc="lower right")

    if show_point_values:
        annotate_points(ax, df["No"], df[rag_column], "#2ecc71", 14)
        annotate_points(ax, df["No"], df[no_rag_column], "#c62828", -16)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()


generate_line_chart(
    "F1-Score",
    "RAG F1-Score",
    "Tanpa RAG F1-Score",
    "visualisasi_rouge_l_f1_score_30_pertanyaan.png",
)
generate_line_chart(
    "F1-Score",
    "RAG F1-Score",
    "Tanpa RAG F1-Score",
    "visualisasi_rouge_l_f1_score_30_pertanyaan_dengan_angka.png",
    show_point_values=True,
)
generate_line_chart(
    "Precision",
    "RAG Precision",
    "Tanpa RAG Precision",
    "visualisasi_rouge_l_precision_30_pertanyaan.png",
)
generate_line_chart(
    "Precision",
    "RAG Precision",
    "Tanpa RAG Precision",
    "visualisasi_rouge_l_precision_30_pertanyaan_dengan_angka.png",
    show_point_values=True,
)
generate_line_chart(
    "Recall",
    "RAG Recall",
    "Tanpa RAG Recall",
    "visualisasi_rouge_l_recall_30_pertanyaan.png",
)
generate_line_chart(
    "Recall",
    "RAG Recall",
    "Tanpa RAG Recall",
    "visualisasi_rouge_l_recall_30_pertanyaan_dengan_angka.png",
    show_point_values=True,
)

print("Visualisasi ROUGE-L 30 pertanyaan berhasil dibuat.")
