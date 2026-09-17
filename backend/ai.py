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
    prompt = f"""You are a senior pandas and data visualization engineer.
You are given a pre-loaded pandas DataFrame `df` with columns: {list(columns)}

Generate Python code that computes the exact analytical answer AND saves an insightful visualization to `chart.png`.

STRICT PANDAS RULES:
1. SORTING & TOP-N QUERIES:
   - For top/bottom N items by computed values (such as text/character length):
     Calculate length into a helper column or sort directly:
     ```python
     temp_df = df.copy()
     temp_df['exp_len'] = temp_df['explanation'].astype(str).str.len()
     result = temp_df.sort_values(by='exp_len', ascending=False).head(5)[['question', 'exp_len', 'skill']]
     ```
   - If using `.nlargest()` or `.nsmallest()`, the `keep` argument must only ever be `'first'`, `'last'`, or `'all'`. NEVER use `keep=False`.

2. SAFE FILTERING & GROUPING:
   - ALWAYS assign the actual records or summary table to `result`. NEVER assign `.columns` to `result`.
   - Normalize strings for filtering: `df['col'].astype(str).str.strip().str.upper() == 'HARD'`
   - If using `.groupby()`, `.pivot_table()`, or `.unstack()`, ALWAYS call `.reset_index()` on the final DataFrame.
   - If a filter matches 0 rows, set: `result = "No matching records found."`

3. VISUALIZATION RULES:
   - Always plot comparisons or distributions:
     * For top-N questions: Plot horizontal bars (`ax.barh(..., height=0.55)`) comparing lengths or metric values.
     * For categories: Plot counts across all categories so differences are visible.
   - Setup: `fig, ax = plt.subplots(figsize=(8, 4.2))`
   - Clean save:
     ```python
     plt.tight_layout()
     plt.savefig('chart.png', dpi=150, bbox_inches='tight')
     plt.close(fig)
     ```
   - NEVER call `plt.show()`.

4. EXECUTION CONSTRAINTS:
   - Output ONLY runnable Python code.
   - NO markdown fences (no ```), backticks, comments, or conversational text.
   - Do NOT write import statements (`df`, `pd`, `np`, and `plt` are already loaded).

Question: {question}
"""

    response = client.chat.completions.create(
        model="openai/gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )

    code = response.choices[0].message.content.strip()

    # Clean markdown fences
    code = re.sub(r"^```(?:python)?\s*", "", code, flags=re.IGNORECASE)
    code = re.sub(r"\s*```$", "", code)

    # Strip any accidental import statements
    cleaned_lines = [
        line for line in code.splitlines()
        if not re.match(r"^\s*(?:import|from)\s+", line)
    ]

    return "\n".join(cleaned_lines).strip()