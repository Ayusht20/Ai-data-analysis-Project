from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import pandas as pd
import matplotlib
matplotlib.use('Agg')

import os
import numpy as np
import re

from chart import generate_chart_from_result

from ai import get_ai_code

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ai-data-analysis-project.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- FRONTEND ----------------
# app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# @app.get("/")
# def serve_frontend():
#     return FileResponse("../frontend/index.html")


# Global dataframe
df = None


# ---------------- EXECUTE AI CODE ----------------
def execute_code(df, code):
    try:
        # remove ```python ```
        code = code.replace("```python", "").replace("```", "").strip()

        # Fix: startswith case-insensitive
        pattern = r"df\['(.*?)'\]\.str\.startswith\('(.*?)'\)"
        match = re.search(pattern, code)

        if match:
            col = match.group(1)
            value = match.group(2).lower()

            code = f"df[df['{col}'].str.lower().str.strip().str.startswith('{value}')]"

        # Fix: append deprecated
        if ".append(" in code:
            code = code.replace(".append(", ", ")
            code = f"pd.concat([{code}])"

        # Block unsafe code
        banned_words = ["import", "__", "os", "sys", "eval", "exec"]
        for word in banned_words:
            if word in code:
                return "Unsafe code blocked"

        # Execute code
        result = eval(code, {"__builtins__": {}}, {"df": df, "pd": pd})

        return result

    except Exception as e:
        return f"Error: {str(e)}"


# ---------------- CONVERT RESULT ----------------
def convert_result(result):

    # numpy number
    if isinstance(result, (np.integer, np.floating)):
        return result.item()

    # pandas Index
    if isinstance(result, pd.Index):
        return result.tolist()

    # pandas Series
    if isinstance(result, pd.Series):
        return result.to_dict()

    # pandas DataFrame
    if isinstance(result, pd.DataFrame):
        if result.empty:
            return []
        return result.to_dict(orient="records")

    # list or tuple
    if isinstance(result, (list, tuple)):
        return [convert_result(r) for r in result]

    # dict
    if isinstance(result, dict):
        return {k: convert_result(v) for k, v in result.items()}

    return result


# ---------------- API ----------------

@app.post("/upload")
def upload(file: UploadFile = File(...)):
    global df

    df = pd.read_csv(file.file)

    return {
        "message": "File uploaded",
        "columns": list(df.columns)
    }


@app.get("/ai-query")
def ai_query(q: str):
    global df

    if df is None:
        return {"error": "Upload file first"}

    try:
        code = get_ai_code(q, list(df.columns))
        code = code.replace("```python", "").replace("```", "").strip()

        result = execute_code(df, code)

        # 1. Skip chart generation if it's a massive raw dataframe dump
        chart_files = []
        if isinstance(result, pd.DataFrame) and len(result) > 50:
            chart_files = []  # Do not choke Matplotlib with full table dumps
        else:
            try:
                chart_files = generate_chart_from_result(result)
            except Exception:
                chart_files = []

        # 2. Prevent OOM by capping maximum returned rows
        if isinstance(result, pd.DataFrame):
            if len(result) > 500:
                result = result.head(500)  # Cap preview to 500 rows
            # 3. Clean NaNs so JSON serialization never throws 500
            result = result.replace({np.nan: None})

        result = convert_result(result)

        return {
            "result": result,
            "charts": chart_files or []
        }
    except Exception as e:
        # Return a 200 with error JSON so CORS headers remain intact
        return {"error": f"Execution failed: {str(e)}"}
    
@app.get("/chart-image/{name}")
def chart_image(name: str):
    path = os.path.join(os.getcwd(), name)

    if not os.path.exists(path):
        return {"error": "Chart not found"}

    return FileResponse(path, media_type="image/png")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)