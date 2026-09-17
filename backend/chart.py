import os
import traceback
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

CHART_DIR = os.getcwd()


def save_and_close(fig, filename="chart.png"):
    filepath = os.path.join(CHART_DIR, filename)
    fig.tight_layout()
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return filename


def truncate_label(val, max_len=24):
    s = str(val).strip()
    return (s[:max_len] + "…") if len(s) > max_len else s


def render_metric_card(title, value, subtitle=""):
    fig, ax = plt.subplots(figsize=(7, 2.5))
    ax.text(0.5, 0.65, str(value), ha='center', va='center',
            fontsize=26, fontweight='bold', color='#161b22')
    ax.text(0.5, 0.32, str(title), ha='center', va='center',
            fontsize=13, fontweight='600', color='#9c6b15')
    if subtitle:
        ax.text(0.5, 0.12, str(subtitle), ha='center', va='center',
                fontsize=10.5, color='#5b6472')
    ax.set_facecolor('#f4f6f8')
    fig.patch.set_facecolor('#ffffff')
    ax.axis('off')
    return [save_and_close(fig, "metric_chart.png")]


def _generate_fallback_card(message="Visualization not applicable"):
    fig, ax = plt.subplots(figsize=(7, 2))
    ax.text(0.5, 0.5, message, ha='center', va='center',
            fontsize=11, color='#5b6472', style='italic')
    ax.axis('off')
    return [save_and_close(fig, "info_chart.png")]

def generate_chart_from_result(result, df_columns=None):
    try:
        plt.close('all')

        if isinstance(result, (np.integer, np.floating)):
            result = result.item()

        # 0. Single string result (e.g. "option_c")
        if isinstance(result, str):
            if result.strip().lower() in ["none", "no records found", "completed"]:
                return _generate_fallback_card(result)
            return render_metric_card("Answer", result)

        # 1. Single numeric scalar
        if isinstance(result, (int, float)):
            return render_metric_card("Calculated Value", f"{result:,.2f}" if isinstance(result, float) else f"{result:,}")

        # 2. Compound Dictionary
        if isinstance(result, dict):
            for key in ["records", "data", "rows"]:
                if key in result:
                    val = result[key]
                    if isinstance(val, pd.DataFrame) and not val.empty:
                        return generate_chart_from_result(val, df_columns)
                    elif isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                        return generate_chart_from_result(pd.DataFrame(val), df_columns)

            numeric_items = {k: v for k, v in result.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
            
            # If all numeric values are 0 (like 0 hard and 0 easy), show clear info tile
            if numeric_items and all(v == 0 for v in numeric_items.values()):
                return render_metric_card("Count", "0 Matching Records", ", ".join(numeric_items.keys()))

            if len(numeric_items) == 1:
                k, v = list(numeric_items.items())[0]
                label = result.get("least_skill") or result.get("skill") or k
                return render_metric_card(str(label).replace("_", " ").title(), f"{v:,}")
            elif len(numeric_items) > 1:
                return generate_chart_from_result(pd.Series(numeric_items), df_columns)

            return render_metric_card("Summary", f"{len(result)} fields returned")

        # 3. Lists / Arrays / Indexes
        if isinstance(result, (list, tuple, pd.Index, np.ndarray)):
            if len(result) == 0:
                return _generate_fallback_card("No records found")

            s = pd.Series(list(result)).dropna()
            if s.empty:
                return _generate_fallback_card("Empty result set")

            # Check if this list is just column names (Screenshot 2 bug)
            if df_columns and set(s.astype(str)).issubset(set(df_columns)):
                return _generate_fallback_card("Result contains column headers only")

            s_num = pd.to_numeric(s, errors='coerce')
            if s_num.notnull().sum() == len(s):
                fig, ax = plt.subplots(figsize=(8, 4))
                ax.bar(range(len(s_num.head(20))), s_num.head(20), color="#faad14", width=0.5)
                ax.set_title("Values", fontsize=12, fontweight='bold')
                ax.grid(axis='y', linestyle='--', alpha=0.4)
                return [save_and_close(fig, "list_chart.png")]

            counts = s.astype(str).value_counts().head(8)
            # If every item appears only once and there are <= 4 items, don't draw equal width blocks
            if (counts == 1).all() and len(counts) <= 4:
                return render_metric_card("Items", f"{len(s)} items", ", ".join(counts.index))

            labels = [truncate_label(k) for k in counts.index]
            fig, ax = plt.subplots(figsize=(8, 4.5))
            ax.barh(labels[::-1], counts.values[::-1], color="#1890ff", height=0.55)
            ax.set_title("Frequency", fontsize=12, fontweight='bold')
            ax.set_xlabel("Count")
            ax.grid(axis='x', linestyle='--', alpha=0.4)
            return [save_and_close(fig, "list_chart.png")]

        # 4. Pandas Series
        if isinstance(result, pd.Series):
            s = result.dropna()
            if s.empty:
                return _generate_fallback_card("Empty series")

            s_num = pd.to_numeric(s, errors='coerce')
            if s_num.notnull().sum() > 0:
                s = s_num.dropna()
            else:
                s = s.astype(str).value_counts()

            if (s == 0).all():
                return render_metric_card("Count", "0", "All values are zero")

            if len(s) == 1:
                return render_metric_card(str(s.index[0]), f"{s.values[0]:,}")

            s = s.head(10)
            labels = [truncate_label(k) for k in s.index]
            fig, ax = plt.subplots(figsize=(8, 4.5))
            ax.barh(labels[::-1], s.values[::-1], color="#2f54eb", height=0.55)
            ax.set_title("Breakdown", fontsize=12, fontweight='bold')
            ax.set_xlabel("Value")
            ax.grid(axis='x', linestyle='--', alpha=0.4)
            return [save_and_close(fig, "bar_chart.png")]

        # 5. DataFrame
        if isinstance(result, pd.DataFrame):
            if result.empty:
                return _generate_fallback_card("No records matched query")

            num_cols = result.select_dtypes(include=['number']).columns.tolist()
            cat_cols = [c for c in result.columns if c not in num_cols]

            # 1 Category + 1 Numeric (e.g., grouped by skill and count of topics)
            if len(cat_cols) >= 1 and len(num_cols) >= 1:
                cat_col, num_col = cat_cols[0], num_cols[0]
                plot_data = result.head(10)
                labels = [truncate_label(x) for x in plot_data[cat_col]]
                fig, ax = plt.subplots(figsize=(8, 4.5))
                ax.barh(labels[::-1], plot_data[num_col].iloc[::-1], color="#13c2c2", height=0.55)
                ax.set_title(f"{num_col.replace('_', ' ').title()} by {cat_col.title()}", fontsize=12, fontweight='bold')
                ax.set_xlabel(num_col.replace('_', ' ').title())
                ax.grid(axis='x', linestyle='--', alpha=0.4)
                return [save_and_close(fig, "bar_chart.png")]

            # Varied categorical distribution
            varying_cols = [c for c in result.columns if result[c].nunique() > 1]
            for col_name in ["difficulty", "topic", "type", "skill"]:
                matched = [c for c in varying_cols if col_name in c.lower()]
                if matched:
                    target_col = matched[0]
                    counts = result[target_col].dropna().astype(str).value_counts().head(8)
                    labels = [truncate_label(k) for k in counts.index]
                    fig, ax = plt.subplots(figsize=(8, 4.2))
                    ax.barh(labels[::-1], counts.values[::-1], color="#52c41a", height=0.55)
                    ax.set_title(f"Breakdown by {target_col.title()}", fontsize=12, fontweight='bold')
                    ax.set_xlabel("Count")
                    ax.grid(axis='x', linestyle='--', alpha=0.4)
                    return [save_and_close(fig, "bar_chart.png")]

            return render_metric_card("Records Found", f"{len(result):,} rows")

        return _generate_fallback_card("Completed")

    except Exception as e:
        return _generate_fallback_card("Could not render chart")