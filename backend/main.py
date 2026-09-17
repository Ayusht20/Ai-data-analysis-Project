import os
import re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd
import numpy as np

from chart import generate_chart_from_result
from ai import get_ai_code

app = FastAPI()

# ---------------- CORS ----------------
origins = [
    "https://ai-data-analysis-project.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

df = None


# ---------------- CODE EXECUTION ----------------
def execute_code(data_df, code):
    try:
        # Strip markdown syntax and extra whitespace
        code = re.sub(r"^```(?:python)?\s*", "", code.strip(), flags=re.IGNORECASE)
        code = re.sub(r"\s*```$", "", code.strip())

        # Strip accidental import statements
        cleaned_lines = [
            line for line in code.split("\n")
            if not line.strip().startswith("import ") and not line.strip().startswith("from ")
        ]
        code = "\n".join(cleaned_lines).strip()

        # Block strictly malicious function calls and attributes
        dangerous_patterns = [
            r"\b__import__\b", r"\bopen\s*\(", r"\bos\.", r"\bsys\.",
            r"\bsubprocess\b", r"\beval\s*\(", r"\bexec\s*\(",
            r"__class__", r"__subclasses__", r"__globals__", r"__builtins__"
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                return "Unsafe code execution blocked"

        # Auto-patch scalar strings passed to .isin() (e.g., .isin('HTML') -> .isin(['HTML']))
        code = re.sub(r"\.isin\(\s*(['\"][^'\"\[\]]+['\"])\s*\)", r".isin([\1])", code)

        # Auto-patch invalid keep arguments in nlargest / nsmallest / drop_duplicates
        code = re.sub(r"keep\s*=\s*(?:False|None)", "keep='first'", code)

        # Regex fix for case-insensitive startswith
        pattern = r"df\['(.*?)'\]\.str\.startswith\('(.*?)'\)"
        match = re.search(pattern, code)
        if match:
            col, value = match.group(1), match.group(2).lower()
            code = f"df[df['{col}'].str.lower().str.strip().str.startswith('{value}')]"

        # Deprecated append fix
        if ".append(" in code:
            code = code.replace(".append(", ", ")
            code = f"pd.concat([{code}])"

        safe_builtins = {
            "int": int, "float": float, "str": str, "bool": bool,
            "list": list, "dict": dict, "set": set, "tuple": tuple,
            "len": len, "min": min, "max": max, "sum": sum,
            "range": range, "round": round, "sorted": sorted, "abs": abs,
            "enumerate": enumerate, "zip": zip, "print": print
        }

        scope = {
            "__builtins__": safe_builtins,
            "df": data_df,
            "pd": pd,
            "np": np,
            "plt": plt
        }

        # Single expression evaluation
        if "\n" not in code and "=" not in code:
            return eval(code, scope)

        # Multi-statement execution
        if "result" not in code:
            lines = [l for l in code.strip().split("\n") if l.strip()]
            if lines:
                lines[-1] = f"result = {lines[-1]}"
                code = "\n".join(lines)

        exec(code, scope)
        return scope.get("result", "Execution succeeded.")

    except Exception as e:
        return f"Error: {str(e)}"
# ---------------- DATA SANITIZATION ----------------
def convert_result(result):
    if result is None:
        return None

    # Handle Pandas Index / NumPy 1D arrays
    if isinstance(result, (np.ndarray, pd.Index)):
        return [convert_result(x) for x in result.tolist()]

    # Handle Series
    if isinstance(result, pd.Series):
        if result.empty:
            return "No matching records found."
        clean_s = result.replace({np.nan: None})
        if isinstance(result.index, pd.RangeIndex):
            return clean_s.tolist()
        return {str(k): convert_result(v) for k, v in clean_s.to_dict().items()}

    # Handle DataFrame
    if isinstance(result, pd.DataFrame):
        if result.empty:
            return "No matching records found."

        # Flatten MultiIndex columns (from crosstab or pivot_table)
        if isinstance(result.columns, pd.MultiIndex):
            result.columns = ['_'.join([str(c) for c in col if str(c)]).strip() for col in result.columns.values]

        # Flatten MultiIndex rows into columns
        if isinstance(result.index, pd.MultiIndex) or result.index.name is not None:
            result = result.reset_index()

        # Round floats to 3 decimal places for readability
        float_cols = result.select_dtypes(include=['float']).columns
        result[float_cols] = result[float_cols].round(3)

        # Cap output records to avoid client-side freezing
        if len(result) > 500:
            result = result.head(500)

        clean_df = result.replace({np.nan: None})
        return clean_df.to_dict(orient="records")

    # Handle NumPy numbers
    if isinstance(result, (np.integer, np.floating)):
        val = result.item()
        return None if (isinstance(val, float) and np.isnan(val)) else val

    # Handle Dict
    if isinstance(result, dict):
        return {str(k): convert_result(v) for k, v in result.items()}

    # Handle List or Tuple
    if isinstance(result, (list, tuple)):
        return [convert_result(r) for r in result]

    return result


# ---------------- API ENDPOINTS ----------------
@app.get("/")
def health():
    return {"status": "healthy", "service": "AI Data Analyst API"}


@app.post("/upload")
def upload(file: UploadFile = File(...)):
    global df
    try:
        df = pd.read_csv(file.file)
        # Strip trailing/leading spaces from column names
        df.columns = [str(c).strip() for c in df.columns]
        return {
            "message": "File uploaded successfully",
            "columns": list(df.columns),
            "rows": len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read CSV: {str(e)}")


@app.get("/ai-query")
def ai_query(q: str):
    global df

    if df is None:
        return {"error": "Upload a CSV file first"}

    try:
        chart_path = os.path.join(os.getcwd(), "chart.png")
        if os.path.exists(chart_path):
            os.remove(chart_path)

        code = get_ai_code(q, list(df.columns))
        raw_result = execute_code(df, code)

        final_result = convert_result(raw_result)

        charts = []
        # Check if an intentional chart was generated by the executed code
        if os.path.exists(chart_path) and os.path.getsize(chart_path) > 0:
            charts = ["chart.png"]
        else:
            try:
                charts = generate_chart_from_result(raw_result, df_columns=list(df.columns)) or []
            except Exception as chart_err:
                print("Fallback chart error:", chart_err)
                charts = []

        return {
            "result": final_result,
            "charts": charts
        }
    except Exception as e:
        return {"error": f"Query processing failed: {str(e)}"}


@app.get("/chart-image/{name}")
def chart_image(name: str):
    safe_name = os.path.basename(name)
    path = os.path.join(os.getcwd(), safe_name)

    if not os.path.exists(path):
        return {"error": "Chart not found"}

    return FileResponse(path, media_type="image/png")


@app.get("/chart")
def chart_status():
    return {"status": "chart ready"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)