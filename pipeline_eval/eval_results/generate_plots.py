import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# -------------------------------------------------------------
# 1. SETUP PATHS & CONFIGURATION
# -------------------------------------------------------------
eval_dir = r"d:\school\Các vấn đề\retrieval-multiturn-rag\pipeline_eval\eval_results"
figures_dir = r"d:\school\Các vấn đề\retrieval-multiturn-rag\pipeline_eval\figures"
os.makedirs(figures_dir, exist_ok=True)

# Set global matplotlib style parameters for a premium, clean aesthetic
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Liberation Sans']
plt.rcParams['axes.edgecolor'] = '#CBD5E1'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['grid.color'] = '#E2E8F0'
plt.rcParams['grid.linewidth'] = 0.5
plt.rcParams['xtick.color'] = '#475569'
plt.rcParams['ytick.color'] = '#475569'
plt.rcParams['text.color'] = '#1E293B'

# Curated premium color palette
COLORS_RECALL = ['#3B82F6', '#8B5CF6', '#EC4899']  # Blue, Violet, Pink for @1, @3, @5
COLOR_ACC_CATEGORIES = ['#3B82F6', '#6366F1', '#8B5CF6', '#D946EF', '#F43F5E']  # Tech palette for categories

# -------------------------------------------------------------
# 2. PLOTTING FUNCTION
# -------------------------------------------------------------
def plot_approach_metrics(excel_path, prefix, title_label, is_approach1=False):
    """
    Reads an overall_metrics_report Excel file and generates:
    1. prefix_recall_k.png
    2. prefix_accuracy_by_category.png
    """
    # Load sheets
    xls = pd.ExcelFile(excel_path)
    df_global = xls.parse('Global Averages')
    df_detail = xls.parse('Chi tiết từng Sample')
    
    # Sort by Conv Index
    df_detail = df_detail.sort_values(by='Conv Index')
    
    # Extract overall metrics
    row_global = df_global.iloc[0]
    total_qa_all = int(row_global.get('Tổng số câu QA', df_detail['Total QA'].sum()))
    total_passes_all = int(row_global.get('Tổng LLM Passes', df_detail['LLM Judge Passes'].sum()))
    
    avg_r1 = row_global.get('Micro-Average BM25 Hit Rate@1', df_detail['Hit Rate@1'].mean())
    avg_r3 = row_global.get('Micro-Average BM25 Hit Rate@3', df_detail['Hit Rate@3'].mean())
    avg_r5 = row_global.get('Micro-Average BM25 Hit Rate@5', df_detail['Hit Rate@5'].mean())
    global_avg_acc = row_global.get('Micro-Average LLM Accuracy', total_passes_all / total_qa_all if total_qa_all else 0.0)
    
    # -------------------------------------------------------------
    # PLOT A: RECALL@K COMPARISON
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(11, 6), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#F8FAFC')
    
    # X axis setup
    x_labels = [f"Conv {int(row['Conv Index'])}" for _, row in df_detail.iterrows()] + ['Overall\nAverage']
    x_indices = np.arange(len(x_labels))
    width = 0.24
    
    # Values to plot
    r1_vals = list(df_detail['Hit Rate@1']) + [avg_r1]
    r3_vals = list(df_detail['Hit Rate@3']) + [avg_r3]
    r5_vals = list(df_detail['Hit Rate@5']) + [avg_r5]
    
    # Plot bars
    rects1 = ax.bar(x_indices - width, r1_vals, width, label='Recall@1', color=COLORS_RECALL[0], edgecolor='#1D4ED8', linewidth=0.4, alpha=0.9)
    rects2 = ax.bar(x_indices, r3_vals, width, label='Recall@3', color=COLORS_RECALL[1], edgecolor='#6D28D9', linewidth=0.4, alpha=0.9)
    rects3 = ax.bar(x_indices + width, r5_vals, width, label='Recall@5', color=COLORS_RECALL[2], edgecolor='#BE185D', linewidth=0.4, alpha=0.9)
    
    # Grid and styling
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    ax.xaxis.grid(False)
    
    # Labels and title
    ax.set_ylabel('Recall Rate (%)', fontsize=11, fontweight='bold', labelpad=10)
    ax.set_title(f'Retrieval Phase Performance (Recall@K) - {title_label}', fontsize=12.5, fontweight='bold', pad=15)
    ax.set_xticks(x_indices)
    ax.set_xticklabels(x_labels, fontsize=9)
    ax.set_ylim(0, 1.1)
    
    # Format y ticks as percentages using FuncFormatter
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.0%}'.format(y)))
    
    # Add value labels on top of the bars for the "Overall Average"
    def autolabel_avg(rects):
        rect = rects[-1]
        height = rect.get_height()
        ax.annotate('{:.1%}'.format(height),
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=8.5, fontweight='bold', color='#1E293B')
    
    autolabel_avg(rects1)
    autolabel_avg(rects2)
    autolabel_avg(rects3)
    
    # Add a divider line before the average
    ax.axvline(x=len(df_detail) - 0.5, color='#94A3B8', linestyle=':', linewidth=1.2)
    
    # Legend
    ax.legend(loc='lower right', frameon=True, facecolor='#FFFFFF', edgecolor='#E2E8F0', framealpha=0.9, fontsize=9)
    
    plt.tight_layout()
    plot1_path = os.path.join(figures_dir, f"{prefix}_recall_k.png")
    plt.savefig(plot1_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[OK] Generated plot: {prefix}_recall_k.png")
    
    # -------------------------------------------------------------
    # PLOT B: LLM JUDGE ACCURACY BY QUESTION CATEGORY
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#F8FAFC')
    
    # Extract category rates
    cat_names = [
        "Category 1\n(Single-hop)",
        "Category 2\n(Temporal)",
        "Category 3\n(Multi-hop)",
        "Category 4\n(Open-domain)",
        "Category 5\n(Adversarial)"
    ]
    
    cat_accuracies = [
        row_global.get('Micro-Average Cat1 Accuracy'),
        row_global.get('Micro-Average Cat2 Accuracy'),
        row_global.get('Micro-Average Cat3 Accuracy'),
        row_global.get('Micro-Average Cat4 Accuracy'),
        row_global.get('Micro-Average Cat5 Accuracy')
    ]
    
    # Plot bars
    x_pos = np.arange(len(cat_names))
    bars = ax.bar(x_pos, cat_accuracies, color=COLOR_ACC_CATEGORIES, edgecolor='#1E293B', linewidth=0.4, width=0.52, alpha=0.85)
    
    # Styling and grid
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    ax.xaxis.grid(False)
    
    # Labels and title
    ax.set_ylabel('LLM Judge Accuracy (%)', fontsize=11, fontweight='bold', labelpad=10)
    ax.set_title(f'Query Rewriting Semantic Accuracy by Category - {title_label}', fontsize=12, fontweight='bold', pad=15)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(cat_names, fontsize=9.5, fontweight='bold')
    ax.set_ylim(0, 1.05)
    
    # Format y ticks as percentages using FuncFormatter
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.0%}'.format(y)))
    
    # Add value labels on top of the bars
    for idx, bar in enumerate(bars):
        height = bar.get_height()
        ax.annotate('{:.2%}'.format(height),
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 4),  # offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold', color='#1E293B')
    
    # Add a horizontal line showing the global average accuracy
    ax.axhline(y=global_avg_acc, color='#EF4444', linestyle='--', linewidth=1.2, label=f'Overall Micro-Avg ({global_avg_acc:.2%})')
    ax.legend(loc='upper right', frameon=True, facecolor='#FFFFFF', edgecolor='#E2E8F0', framealpha=0.9, fontsize=9)
    
    plt.tight_layout()
    plot2_path = os.path.join(figures_dir, f"{prefix}_accuracy_by_category.png")
    plt.savefig(plot2_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[OK] Generated plot: {prefix}_accuracy_by_category.png")

# -------------------------------------------------------------
# 3. RUN GENERATION
# -------------------------------------------------------------
if __name__ == "__main__":
    app1_path = os.path.join(eval_dir, "overall_metrics_report_approach1.xlsx")
    app2_path = os.path.join(eval_dir, "overall_metrics_report.xlsx")
    
    # 1. Generate Approach 1 plots
    plot_approach_metrics(app1_path, "approach1", "Approach 1 (Compression-Centric Baseline)", is_approach1=True)
    
    # 2. Generate Approach 2 plots
    plot_approach_metrics(app2_path, "approach2", "Approach 2 (State-Centric Proposed)")
    print("\n[OK] All 4 plots generated successfully!")
