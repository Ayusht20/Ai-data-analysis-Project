import os
import re
import matplotlib
matplotlib.use('Agg')

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
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory dataset
df = None


# ---------------- CODE EXECUTION ----------------
def execute_code(data_df, code):
    try:
        # Strip markdown syntax and extra spaces
        code = code.replace("```python", "").replace("```", "").strip()

        # Startswith case-insensitive regex fix
        pattern = r"df\['(.*?)'\]\.str\.startswith\('(.*?)'\)"
        match = re.search(pattern, code)
        if match:
            col = match.group(1)
            value = match.group(2).lower()
            code = f"df[df['{col}'].str.lower().str.strip().str.startswith('{value}')]"

        # Deprecated append fix
        if ".append(" in code:
            code = code.replace(".append(", ", ")
            code = f"pd.concat([{code}])"

        # Security check for banned statements
        banned_words = ["import", "__", "os", "sys", "eval", "exec", "open", "subprocess"]
        for word in banned_words:
            if word in code:
                return "Unsafe code execution blocked"

        # Whitelist safe built-in functions
        safe_builtins = {
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "len": len,
            "min": min,
            "max": max,
            "sum": sum,
            "range": range,
            "round": round,
            "sorted": sorted,
            "abs": abs,
            "enumerate": enumerate,
            "zip": zip,
            "print": print,
        }

        # Execution scope
        scope = {
            "__builtins__": safe_builtins,
            "df": data_df,
            "pd": pd,
            "np": np
        }

        # If single-expression without assignment, evaluate directly
        if "\n" not in code and "=" not in code:
            return eval(code, scope)

        # Multi-line logic execution
        if "result" not in code:
            lines = [line for line in code.strip().split("\n") if line.strip()]
            if lines:
                lines[-1] = f"result = {lines[-1]}"
                code = "\n".join(lines)

        exec(code, scope)
        return scope.get("result", "Query executed successfully with no output.")

    except Exception as e:
        return f"Error: {str(e)}"

    # ---------------- RESULT SANITIZATION ----------------
def convert_result(result):
    if result is None:
        return None

    # NumPy arrays & Pandas Indexes
    if isinstance(result, (np.ndarray, pd.Index)):
        return [convert_result(x) for x in result.tolist()]

    # Pandas Series
    if isinstance(result, pd.Series):
        clean_s = result.replace({np.nan: None})
        if isinstance(result.index, pd.RangeIndex):
            return clean_s.tolist()
        return {str(k): convert_result(v) for k, v in clean_s.to_dict().items()}

    # Pandas DataFrame (capped at 500 records to prevent memory crashes)
    if isinstance(result, pd.DataFrame):
        if result.empty:
            return []
        if len(result) > 500:
            result = result.head(500)
        clean_df = result.replace({np.nan: None})
        return clean_df.to_dict(orient="records")

    # NumPy numeric values
    if isinstance(result, (np.integer, np.floating)):
        val = result.item()
        return None if (isinstance(val, float) and np.isnan(val)) else val

    # Dict
    if isinstance(result, dict):
        return {str(k): convert_result(v) for k, v in result.items()}

    # List or tuple
    if isinstance(result, (list, tuple)):
        return [convert_result(r) for r in result]

    return result


# ---------------- API ROUTES ----------------
@app.get("/")
def health_check():
    return {"status": "healthy", "service": "AI Data Analyst API"}


@app.post("/upload")
def upload(file: UploadFile = File(...)):
    global df
    try:
        df = pd.read_csv(file.file)
        return {
            "message": "File uploaded successfully",
            "columns": list(df.columns),
            "rows": len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")


@app.get("/ai-query")
def ai_query(q: str):
    global df

    if df is None:
        return {"error": "Upload a CSV file first"}

    try:
        code = get_ai_code(q, list(df.columns))
        code = code.replace("```python", "").replace("```", "").strip()

        raw_result = execute_code(df, code)

        # Generate charts safely
        chart_files = []
        try:
            chart_files = generate_chart_from_result(raw_result)
        except Exception as chart_err:
            print("Chart generation exception:", chart_err)

        final_result = convert_result(raw_result)

        return {
            "result": final_result,
            "charts": chart_files or []
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
def trigger_manual_chart():
    return {"message": "Chart endpoint ready"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)