import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

def generate_chart_from_result(result):
    try:
        base_path = os.getcwd()

        # convert numpy → python
        if isinstance(result, (np.integer, np.floating)):
            result = result.item()

        # -------- SINGLE VALUE --------
        if isinstance(result, (int, float)):
            plt.clf()
            plt.bar(["Result"], [result])
            plt.title("Result")
            plt.tight_layout()

            plt.savefig(os.path.join(base_path, "chart.png"))
            return ["chart.png"]

        # -------- DICT / SERIES --------
        if isinstance(result, (dict, pd.Series)):
            s = pd.Series(result)

            # Bar chart
            plt.clf()
            s.plot(kind="bar")
            plt.title("Bar Chart")
            plt.tight_layout()
            plt.savefig(os.path.join(base_path, "bar_chart.png"))

            # Pie chart
            plt.clf()
            s.plot(kind="pie", autopct="%1.1f%%")
            plt.title("Pie Chart")
            plt.ylabel("")
            plt.tight_layout()
            plt.savefig(os.path.join(base_path, "pie_chart.png"))

            return ["bar_chart.png", "pie_chart.png"]

        # -------- DATAFRAME --------
        if isinstance(result, pd.DataFrame) and not result.empty:

            num_cols = result.select_dtypes(include=['number']).columns

            if len(num_cols) == 0:
                return None

            col = num_cols[0]

            # small data → bar
            if len(result) <= 10:
                plt.clf()
                result[col].plot(kind="bar")
                plt.title(f"{col} values")
                plt.tight_layout()
                plt.savefig(os.path.join(base_path, "bar_chart.png"))

                return ["bar_chart.png"]

            # large data → histogram
            else:
                plt.clf()
                result[col].plot(kind="hist", bins=5)
                plt.title(f"{col} distribution")
                plt.xlabel(col)
                plt.ylabel("Count")
                plt.tight_layout()
                plt.savefig(os.path.join(base_path, "hist_chart.png"))

                return ["hist_chart.png"]

        return None

    except Exception as e:
        print("CHART ERROR:", e)
        return None