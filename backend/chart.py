import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

CHART_DIR = os.getcwd()


def save_and_close(fig, filename):
    filepath = os.path.join(CHART_DIR, filename)
    fig.tight_layout()
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return filename


def truncate_label(val, max_len=28):
    """Truncate long text so it doesn't collide on axes."""
    s = str(val).strip()
    return (s[:max_len] + "…") if len(s) > max_len else s


def is_free_form_text(series):
    """Detect if a column contains long sentences rather than categories."""
    str_series = series.dropna().astype(str)
    if str_series.empty:
        return True
    avg_len = str_series.str.len().mean()
    unique_ratio = str_series.nunique() / max(len(str_series), 1)
    # If average length > 30 chars or almost every row is unique sentences
    return avg_len > 30 or (len(str_series) > 10 and unique_ratio > 0.85)


def render_metric_card(title, value, subtitle=""):
    """Clean visual KPI card when data is purely narrative/textual."""
    fig, ax = plt.subplots(figsize=(7, 2.6))
    ax.text(0.5, 0.65, str(value), ha='center', va='center',
            fontsize=26, fontweight='bold', color='#161b22')
    ax.text(0.5, 0.32, title, ha='center', va='center',
            fontsize=13, fontweight='600', color='#9c6b15')
    if subtitle:
        ax.text(0.5, 0.12, subtitle, ha='center', va='center',
                fontsize=10.5, color='#5b6472')
    ax.set_facecolor('#f4f6f8')
    fig.patch.set_facecolor('#ffffff')
    ax.axis('off')
    return [save_and_close(fig, "metric_chart.png")]


def _generate_fallback_chart(message="Visualisation not applicable"):
    fig, ax = plt.subplots(figsize=(7, 2))
    ax.text(0.5, 0.5, message, ha='center', va='center',
            fontsize=11, color='#5b6472', style='italic')
    ax.axis('off')
    return [save_and_close(fig, "info_chart.png")]


def generate_chart_from_result(result):
    try:
        # Convert numpy scalars to native python
        if isinstance(result, (np.integer, np.floating)):
            result = result.item()

        # ---------------- 1. SINGLE NUMERIC VALUE ----------------
        if isinstance(result, (int, float)):
            return render_metric_card("Calculated Value", f"{result:,.2f}" if isinstance(result, float) else f"{result:,}")

        # ---------------- 2. ARRAYS, LISTS, INDEXES ----------------
        if isinstance(result, (list, tuple, pd.Index, np.ndarray)):
            if len(result) == 0:
                return _generate_fallback_chart("Empty result set")

            s = pd.Series(list(result)).dropna()
            if s.empty:
                return _generate_fallback_chart("No non-null records found")

            # Numeric list
            s_num = pd.to_numeric(s, errors='coerce')
            if s_num.notnull().sum() == len(s):
                fig, ax = plt.subplots(figsize=(8, 4))
                ax.bar(range(len(s_num.head(20))), s_num.head(20), color="#faad14")
                ax.set_title("Numeric List Items", fontsize=12, fontweight='bold')
                ax.grid(axis='y', linestyle='--', alpha=0.4)
                return [save_and_close(fig, "list_chart.png")]

            # Free-form sentence list -> show count metric card
            if is_free_form_text(s):
                return render_metric_card("Total Items Found", f"{len(s):,}", f"{s.nunique()} unique values")

            # Categorical string list -> Horizontal Bar
            counts = s.astype(str).value_counts().head(8)
            counts.index = [truncate_label(k) for k in counts.index]
            counts = counts.iloc[::-1]  # reverse so top is on top

            fig, ax = plt.subplots(figsize=(8, 4.5))
            ax.barh(counts.index, counts.values, color="#1890ff")
            ax.set_title("Top Items Frequency", fontsize=12, fontweight='bold')
            ax.set_xlabel("Count")
            ax.grid(axis='x', linestyle='--', alpha=0.4)
            return [save_and_close(fig, "list_chart.png")]

        # ---------------- 3. DICTIONARY OR PANDAS SERIES ----------------
        if isinstance(result, (dict, pd.Series)):
            s = pd.Series(result).dropna()
            if s.empty:
                return _generate_fallback_chart("Empty series returned")

            # Numeric conversion check
            s_num = pd.to_numeric(s, errors='coerce')
            if s_num.notnull().sum() > 0:
                s = s_num.dropna()
            else:
                s = s.astype(str).value_counts()

            s = s.head(10)
            clean_labels = [truncate_label(k) for k in s.index]

            charts = []
            # Clean Horizontal Bar Chart
            fig, ax = plt.subplots(figsize=(8, 4.5))
            ax.barh(clean_labels[::-1], s.values[::-1], color="#2f54eb")
            ax.set_title("Breakdown", fontsize=12, fontweight='bold')
            ax.set_xlabel("Value")
            ax.grid(axis='x', linestyle='--', alpha=0.4)
            charts.append(save_and_close(fig, "bar_chart.png"))

            # Pie Chart (only for suitable distributions)
            if pd.api.types.is_numeric_dtype(s) and (s > 0).all() and 2 <= len(s) <= 6:
                fig, ax = plt.subplots(figsize=(6, 5))
                ax.pie(s.values, labels=clean_labels, autopct="%1.1f%%", startangle=90)
                ax.set_title("Proportion", fontsize=12, fontweight='bold')
                charts.append(save_and_close(fig, "pie_chart.png"))

            return charts

        # ---------------- 4. DATAFRAME ----------------
        if isinstance(result, pd.DataFrame):
            if result.empty:
                return _generate_fallback_chart("No records matched query")

            num_cols = result.select_dtypes(include=['number']).columns.tolist()
            cat_cols = [c for c in result.columns if c not in num_cols]

            # Case A: Free-form text dump (e.g. MCQ questions/options like your screenshot)
            # If all columns are long text sentences, do not draw chaotic bars.
            if len(num_cols) == 0 and all(is_free_form_text(result[c]) for c in cat_cols[:2]):
                return render_metric_card(
                    "Matched Records",
                    f"{len(result):,}",
                    f"Showing text records across {len(result.columns)} columns"
                )

            # Case B: 1 Categorical + 1 Numeric (e.g. Sales by Category)
            if len(cat_cols) >= 1 and len(num_cols) >= 1:
                cat_col, num_col = cat_cols[0], num_cols[0]
                plot_data = result.head(10).copy()
                labels = [truncate_label(x) for x in plot_data[cat_col]]

                fig, ax = plt.subplots(figsize=(8, 4.5))
                ax.barh(labels[::-1], plot_data[num_col].iloc[::-1], color="#13c2c2")
                ax.set_title(f"{num_col} by {cat_col}", fontsize=12, fontweight='bold')
                ax.set_xlabel(num_col)
                ax.grid(axis='x', linestyle='--', alpha=0.4)
                return [save_and_close(fig, "bar_chart.png")]

            # Case C: Pure Numeric DataFrame
            if len(num_cols) >= 1:
                target_col = num_cols[0]
                fig, ax = plt.subplots(figsize=(8, 4.2))
                if len(result) <= 15:
                    ax.bar(range(len(result)), result[target_col], color="#722ed1")
                    ax.set_title(f"{target_col} Values", fontsize=12, fontweight='bold')
                else:
                    ax.hist(result[target_col].dropna(), bins=15, color="#fa8c16", edgecolor="white")
                    ax.set_title(f"{target_col} Distribution", fontsize=12, fontweight='bold')
                    ax.set_xlabel(target_col)
                    ax.set_ylabel("Count")

                ax.grid(axis='y', linestyle='--', alpha=0.4)
                return [save_and_close(fig, "num_chart.png")]

            # Case D: Categorical columns with short labels (e.g., status, skills, gender)
            if len(cat_cols) >= 1:
                col = cat_cols[0]
                counts = result[col].dropna().astype(str).value_counts().head(8)
                labels = [truncate_label(k) for k in counts.index]

                fig, ax = plt.subplots(figsize=(8, 4.5))
                ax.barh(labels[::-1], counts.values[::-1], color="#52c41a")
                ax.set_title(f"Frequency in {col}", fontsize=12, fontweight='bold')
                ax.set_xlabel("Count")
                ax.grid(axis='x', linestyle='--', alpha=0.4)
                return [save_and_close(fig, "cat_chart.png")]

        return _generate_fallback_chart(f"Result type: {type(result).__name__}")

    except Exception as e:
        print("CHART ERROR:", e)
        return _generate_fallback_chart("Could not render chart")