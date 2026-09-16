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

def generate_chart_from_result(result):
    try:
        # Convert numpy scalars to native python
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

        # ---------------- 2. DICTIONARY OR PANDAS SERIES ----------------
        if isinstance(result, (dict, pd.Series)):
            s = pd.Series(result).dropna()

            if s.empty:
                return _generate_fallback_chart("Empty series returned")

            # Try numeric conversion if values are strings of numbers
            s_numeric = pd.to_numeric(s, errors='coerce')
            if s_numeric.notnull().sum() > 0:
                s = s_numeric.dropna()

            # If still non-numeric, show frequency distribution of the values
            if not np.issubdtype(s.dtype, np.number):
                s = s.value_counts().head(10)

            # Limit to top 15 entries for readability
            s = s.head(15)

            charts = []

            # A. Horizontal / Vertical Bar Chart
            fig, ax = plt.subplots(figsize=(8, 4.5))
            s.plot(kind="bar", ax=ax, color="#2f54eb")
            ax.set_title("Distribution / Breakdown", fontsize=12, fontweight='bold')
            ax.set_ylabel("Value")
            ax.grid(axis='y', linestyle='--', alpha=0.4)
            plt.xticks(rotation=30, ha='right')
            charts.append(save_and_close(fig, "bar_chart.png"))

            # B. Pie Chart (Only if values are positive and non-zero)
            if (s > 0).all() and len(s) <= 8:
                fig, ax = plt.subplots(figsize=(6, 6))
                s.plot(kind="pie", ax=ax, autopct="%1.1f%%", startangle=90)
                ax.set_title("Proportion", fontsize=12, fontweight='bold')
                ax.set_ylabel("")
                charts.append(save_and_close(fig, "pie_chart.png"))

            return charts

        # ---------------- 3. DATAFRAME ----------------
        if isinstance(result, pd.DataFrame):
            if result.empty:
                return _generate_fallback_chart("No records matched the query")

            charts = []
            num_cols = result.select_dtypes(include=[np.number]).columns.tolist()
            cat_cols = result.select_dtypes(exclude=[np.number]).columns.tolist()

            # Case 3A: One category + One or more numeric columns (e.g., GroupBy result)
            if len(cat_cols) >= 1 and len(num_cols) >= 1:
                cat_col = cat_cols[0]
                num_col = num_cols[0]
                plot_data = result.head(12)

                fig, ax = plt.subplots(figsize=(8, 4.5))
                ax.bar(plot_data[cat_col].astype(str), plot_data[num_col], color="#13c2c2")
                ax.set_title(f"{num_col} by {cat_col}", fontsize=12, fontweight='bold')
                ax.set_ylabel(num_col)
                ax.set_xlabel(cat_col)
                ax.grid(axis='y', linestyle='--', alpha=0.4)
                plt.xticks(rotation=30, ha='right')
                charts.append(save_and_close(fig, "bar_chart.png"))
                return charts

            # Case 3B: Numeric data only
            if len(num_cols) >= 1:
                target_col = num_cols[0]

                fig, ax = plt.subplots(figsize=(8, 4.5))
                if len(result) <= 15:
                    result[target_col].plot(kind="bar", ax=ax, color="#722ed1")
                    ax.set_title(f"{target_col} Values", fontsize=12, fontweight='bold')
                    plt.xticks(rotation=0)
                else:
                    result[target_col].plot(kind="hist", bins=15, ax=ax, color="#fa8c16", edgecolor="white")
                    ax.set_title(f"{target_col} Distribution", fontsize=12, fontweight='bold')
                    ax.set_xlabel(target_col)
                    ax.set_ylabel("Frequency")

                ax.grid(axis='y', linestyle='--', alpha=0.4)
                charts.append(save_and_close(fig, "num_chart.png"))
                return charts

            # Case 3C: Categorical data only (Text columns)
            if len(cat_cols) >= 1:
                col = cat_cols[0]
                counts = result[col].value_counts().head(10)

                fig, ax = plt.subplots(figsize=(8, 4.5))
                counts.plot(kind="bar", ax=ax, color="#52c41a")
                ax.set_title(f"Top Values in {col}", fontsize=12, fontweight='bold')
                ax.set_ylabel("Count")
                ax.grid(axis='y', linestyle='--', alpha=0.4)
                plt.xticks(rotation=30, ha='right')
                charts.append(save_and_close(fig, "cat_chart.png"))
                return charts

        # ---------------- 4. LIST / ARRAYS ----------------
        if isinstance(result, (list, tuple)):
            if len(result) == 0:
                return _generate_fallback_chart("Empty list returned")

            # Numeric list
            try:
                numeric_arr = pd.to_numeric(pd.Series(result), errors='raise')
                fig, ax = plt.subplots(figsize=(8, 4))
                numeric_arr.head(20).plot(kind="bar", ax=ax, color="#faad14")
                ax.set_title("List Item Values", fontsize=12, fontweight='bold')
                ax.grid(axis='y', linestyle='--', alpha=0.4)
                return [save_and_close(fig, "list_chart.png")]
            except Exception:
                # String list (e.g., column names, unique strings)
                counts = pd.Series(result).value_counts().head(10)
                fig, ax = plt.subplots(figsize=(8, 4))
                counts.plot(kind="bar", ax=ax, color="#1890ff")
                ax.set_title("Frequency of Items", fontsize=12, fontweight='bold')
                plt.xticks(rotation=30, ha='right')
                return [save_and_close(fig, "list_chart.png")]

        # Default fallback
        return _generate_fallback_chart(f"Result type: {type(result).__name__}")

    except Exception as e:
        print("CHART GENERATION FAILED:", e)
        return _generate_fallback_chart(f"Could not render chart: {str(e)[:40]}")


def _generate_fallback_chart(message="Visualisation not applicable"):
    """Generates an informational visual tile so every query has a chart."""
    fig, ax = plt.subplots(figsize=(7, 2))
    ax.text(0.5, 0.5, message, horizontalalignment='center', verticalalignment='center',
            fontsize=11, color='#5b6472', style='italic')
    ax.axis('off')
    return [save_and_close(fig, "info_chart.png")]