import os
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

def get_ai_code(question, columns):
    prompt = f"""You are an expert pandas code generator. Convert the user question into executable Python code for a pandas DataFrame named `df`.

Columns available in df: {list(columns)}

Rules:
1. Output ONLY executable Python code. No markdown fences, no backticks, no explanations, no comments.
2. Use only `df`, `pd`, and `np`. Do NOT import any libraries or use I/O functions.
3. For single-line operations, output just the expression (e.g., df['col'].value_counts()).
4. For multi-step questions (such as finding minimums, filtering, and counting simultaneously):
   - Write sequential Python code.
   - Always assign the final output to a variable named `result`.
   - If multiple pieces of information are requested (e.g., records and a count), store them in a dictionary assigned to `result`:
     Example:
     min_skill = df['skill'].value_counts().idxmin()
     count = int(df['skill'].value_counts().min())
     records = df[df['skill'] == min_skill]
     result = {{"least_skill": min_skill, "question_count": count, "records": records}}

Question: {question}
"""

    response = client.chat.completions.create(
        model="openai/gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    code = response.choices[0].message.content.strip()

    # Strip potential markdown formatting if the model still includes it
    code = re.sub(r"^```(?:python)?\s*", "", code, flags=re.IGNORECASE)
    code = re.sub(r"\s*```$", "", code)

    return code.strip()