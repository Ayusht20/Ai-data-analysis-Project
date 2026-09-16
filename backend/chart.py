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


def _generate_fallback_chart(message="Visualisation not applicable"):
    fig, ax = plt.subplots(figsize=(7, 2.5))
    ax.text(
        0.5, 0.5, message,
        horizontalalignment='center',
        verticalalignment='center',
        fontsize=11,
        color='#5b6472',
        style='italic',
        wrap=True
    )
    ax.axis('off')
    return [save_and_close(fig, "info_chart.png")]


def generate_chart_from_result(result):
    try:
        # Convert NumPy scalars to native Python primitives
        if isinstance(result, (np.integer, np.floating)):
            result = result.item()

        # ---------------- 1. SINGLE VALUE (int, float) ----------------
        if isinstance(result, (int, float)):
            fig, ax = plt.subplots(figsize=(6, 4))
            bars = ax.bar(["Metric"], [result], color="#9c6b15", width=0.4)
            ax.set_title("Result Value", fontsize=12, fontweight='bold')
            ax.bar_label(bars, fmt="%.2f" if isinstance(result, float) else "%d", padding=3)
            ax.grid(axis='y', linestyle='--', alpha=0.5)
            return [save_and_close(fig, "chart.png")]

        # ---------------- 2. ARRAYS, LISTS, INDEXES ----------------
        if isinstance(result, (list, tuple, pd.Index, np.ndarray)):
            if len(result) == 0:
                return _generate_fallback_chart("Empty list returned")

            # Convert to Pandas Series of object dtype to safely bypass StringDtype checks
            s = pd.Series(list(result)).dropna()

            if s.empty:
                return _generate_fallback_chart("No non-null items found")

            # Check if values are numeric
            s_numeric = pd.to_numeric(s, errors='coerce')
            if s_numeric.notnull().sum() > 0:
                s = s_numeric.dropna().head(20)
                fig, ax = plt.subplots(figsize=(8, 4.5))
                ax.bar(range(len(s)), s.values, color="#faad14")
                ax.set_title("Numeric Items", fontsize=12, fontweight='bold')
                ax.grid(axis='y', linestyle='--', alpha=0.4)
                return [save_and_close(fig, "list_chart.png")]
            else:
                # String / Categorical list: compute frequencies
                counts = s.astype(str).value_counts().head(10)
                fig, ax = plt.subplots(figsize=(8, 4.5))
                ax.bar(counts.index.astype(str), counts.values, color="#1890ff")
                ax.set_title("Item Frequency", fontsize=12, fontweight='bold')
                ax.set_ylabel("Count")
                ax.grid(axis='y', linestyle='--', alpha=0.4)
                plt.xticks(rotation=30, ha='right')
                return [save_and_close(fig, "list_chart.png")]

        # ---------------- 3. DICTIONARY OR PANDAS SERIES ----------------
        if isinstance(result, (dict, pd.Series)):
            s = pd.Series(result).dropna()

            if s.empty:
                return _generate_fallback_chart("Empty series returned")

            # Numeric conversion check
            s_numeric = pd.to_numeric(s, errors='coerce')
            if s_numeric.notnull().sum() > 0:
                s = s_numeric.dropna()
            else:
                s = s.astype(str).value_counts()

            s = s.head(15)
            charts = []

            # Bar Chart
            fig, ax = plt.subplots(figsize=(8, 4.5))
            ax.bar(s.index.astype(str), s.values, color="#2f54eb")
            ax.set_title("Distribution / Breakdown", fontsize=12, fontweight='bold')
            ax.set_ylabel("Value")
            ax.grid(axis='y', linestyle='--', alpha=0.4)
            plt.xticks(rotation=30, ha='right')
            charts.append(save_and_close(fig, "bar_chart.png"))

            # Pie Chart (only if valid numeric values and manageable slice count)
            if pd.api.types.is_numeric_dtype(s) and (s > 0).all() and len(s) <= 8:
                fig, ax = plt.subplots(figsize=(6, 6))
                ax.pie(s.values, labels=s.index.astype(str), autopct="%1.1f%%", startangle=90)
                ax.set_title("Proportion", fontsize=12, fontweight='bold')
                charts.append(save_and_close(fig, "pie_chart.png"))

            return charts

        # ---------------- 4. DATAFRAME ----------------
        if isinstance(result, pd.DataFrame):
            if result.empty:
                return _generate_fallback_chart("No records matched the query")

            charts = []
            num_cols = result.select_dtypes(include=['number']).columns.tolist()
            cat_cols = [col for col in result.columns if col not in num_cols]

            # Case A: 1 Category + 1 Numeric (e.g. GroupBy results)
            if len(cat_cols) >= 1 and len(num_cols) >= 1:
                cat_col, num_col = cat_cols[0], num_cols[0]
                plot_data = result.head(12)
                fig, ax = plt.subplots(figsize=(8, 4.5))
                ax.bar(plot_data[cat_col].astype(str), plot_data[num_col], color="#13c2c2")
                ax.set_title(f"{num_col} by {cat_col}", fontsize=12, fontweight='bold')
                ax.set_ylabel(num_col)
                ax.grid(axis='y', linestyle='--', alpha=0.4)
                plt.xticks(rotation=30, ha='right')
                charts.append(save_and_close(fig, "bar_chart.png"))
                return charts

            # Case B: Pure numeric DataFrame
            if len(num_cols) >= 1:
                target_col = num_cols[0]
                fig, ax = plt.subplots(figsize=(8, 4.5))
                if len(result) <= 15:
                    ax.bar(range(len(result)), result[target_col], color="#722ed1")
                    ax.set_title(f"{target_col} Values", fontsize=12, fontweight='bold')
                else:
                    ax.hist(result[target_col].dropna(), bins=15, color="#fa8c16", edgecolor="white")
                    ax.set_title(f"{target_col} Distribution", fontsize=12, fontweight='bold')
                    ax.set_xlabel(target_col)
                    ax.set_ylabel("Frequency")

                ax.grid(axis='y', linestyle='--', alpha=0.4)
                charts.append(save_and_close(fig, "num_chart.png"))
                return charts

            # Case C: Pure categorical/text DataFrame
            if len(cat_cols) >= 1:
                col = cat_cols[0]
                counts = result[col].astype(str).value_counts().head(10)
                fig, ax = plt.subplots(figsize=(8, 4.5))
                ax.bar(counts.index.astype(str), counts.values, color="#52c41a")
                ax.set_title(f"Top Values in {col}", fontsize=12, fontweight='bold')
                ax.set_ylabel("Count")
                ax.grid(axis='y', linestyle='--', alpha=0.4)
                plt.xticks(rotation=30, ha='right')
                charts.append(save_and_close(fig, "cat_chart.png"))
                return charts

        return _generate_fallback_chart(f"Result type: {type(result).__name__}")

    except Exception as e:
        print("CHART ERROR:", e)
        return _generate_fallback_chart("Visualisation could not be rendered")