import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import math

# Konfigurasi style untuk chart yang lebih elegan
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (14, 7)
plt.rcParams['font.family'] = 'sans-serif'

csv_path = "komparasi_rag_vs_norag.csv"
df = pd.read_csv(csv_path)

# Label untuk sumbu X
x = np.arange(len(df))
width = 0.35
labels = [f"Q{i+1}" for i in range(len(df))]

# 1. Chart ROUGE-L per Pertanyaan (Line Chart)
# Line chart direkomendasikan karena memberikan sensasi visual 'gap' performa yang berkesinambungan
fig, ax = plt.subplots(figsize=(14, 6))

ax.plot(x, df["RAG - ROUGE-L F1"], marker='o', markersize=8, linewidth=3, label='Sistem DENGAN RAG', color='#2980b9')
ax.plot(x, df["No-RAG - ROUGE-L F1"], marker='s', markersize=8, linewidth=3, label='Sistem TANPA RAG', color='#e74c3c')

# Memberikan bayangan (fill) di antara dua garis untuk menonjolkan Ablation Gap (Perbedaan Kinerja)
ax.fill_between(x, df["RAG - ROUGE-L F1"], df["No-RAG - ROUGE-L F1"], color='gray', alpha=0.1)

ax.set_ylabel('ROUGE-L F1 Score', fontsize=12)
ax.set_title('Komparasi Akurasi Fakta (ROUGE-L) per Pertanyaan: Efek Ablasi RAG', fontsize=14, fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=11)
ax.legend(fontsize=12, loc='upper right')
ax.set_ylim(-0.05, 1.1)

# Anotasi nilai pada titik
for i, txt in enumerate(df["RAG - ROUGE-L F1"]):
    trunc_val = math.floor(txt * 100) / 100.0
    ax.annotate(f'{trunc_val:.2f}', (x[i], df["RAG - ROUGE-L F1"][i]), textcoords="offset points", xytext=(0,10), ha='center', fontsize=9, color='#2980b9', fontweight='bold')
for i, txt in enumerate(df["No-RAG - ROUGE-L F1"]):
    trunc_val = math.floor(txt * 100) / 100.0
    ax.annotate(f'{trunc_val:.2f}', (x[i], df["No-RAG - ROUGE-L F1"][i]), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=9, color='#e74c3c', fontweight='bold')

plt.tight_layout()
plt.savefig("chart_rouge_line_per_question.png", dpi=300, bbox_inches='tight')
plt.close()


# 2. Chart Rata-rata ROUGE-L (Bar Chart Tebal)
fig, ax = plt.subplots(figsize=(8, 6))

avg_rouge_rag = df["RAG - ROUGE-L F1"].mean()
avg_rouge_norag = df["No-RAG - ROUGE-L F1"].mean()

bars = ax.bar(['Model DENGAN RAG', 'Model TANPA RAG'], [avg_rouge_rag, avg_rouge_norag], color=['#2980b9', '#e74c3c'], width=0.5)
ax.set_title('Rata-rata Akurasi Faktual Mutlak (ROUGE-L)', fontsize=14, fontweight='bold', pad=20)
ax.set_ylim(0, 1.1)
ax.set_ylabel('Mean F1 Score', fontsize=12)

for p in bars:
    height = p.get_height()
    ax.text(p.get_x() + p.get_width() / 2., height + 0.02, f'{height:.4f}', ha='center', fontweight='bold', fontsize=13)

plt.tight_layout()
plt.savefig("chart_rouge_average.png", dpi=300, bbox_inches='tight')
plt.close()

print("✅ Proses pembuatan chart ROUGE-L selesai! 2 gambar telah disimpan.")
