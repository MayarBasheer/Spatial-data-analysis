from fastapi import FastAPI
import subprocess
import re

app = FastAPI()

OLLAMA_PATH = r"C:\Users\user\AppData\Local\Programs\Ollama\ollama.exe"

# Regex for removing ANSI escape codes
ANSI_CLEANER = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

def clean_output(text: str) -> str:
    """
    Cleans model output by removing ANSI codes,
    spinner characters, and markdown wrappers.
    """
    text = ANSI_CLEANER.sub("", text)
    text = re.sub(r"[⠋⠙⠸⠼⠧⠦⠇]", "", text)
    text = text.replace("```sql", "").replace("```", "")
    return text.strip()

def run_llm(prompt: str) -> str:
    """
    Sends a prompt to the local LLM via Ollama
    and returns the cleaned SQL output.
    """
    result = subprocess.run(
        [OLLAMA_PATH, "run", "llama3"],
        input=prompt,
        text=True,
        capture_output=True,
        timeout=300
    )
    return clean_output(result.stdout)

@app.post("/nl2sql")
def convert(payload: dict):
    """
    Converts a natural language spatial query
    into a PostGIS SQL statement.
    """
    question = payload.get("question", "")
    schema = payload.get("schema", "public")
    table = payload.get("table", "")
    geom_column = payload.get("geom", "geom")

    full_table = f"{schema}.{table}" if table else "public.UNKNOWN_TABLE"

    prompt = f"""
You are an expert PostGIS SQL generator.

ABSOLUTE RULES (MUST FOLLOW STRICTLY):

1. Output ONLY valid SQL.
2. Output EXACTLY ONE statement.
3. The output MUST start with:
   CREATE TABLE public.analysis_result AS SELECT ...
4. Use ONLY this table:
   {full_table}
5. Geometry column name is: {geom_column}
6. NEVER use SELECT *.
7. Select ONLY ONE geometry column and alias it as:
   geom
8. If a column named "gid" already exists:
   - DO NOT create another "gid".
   - Use "result_id" instead.
9. If an identifier is required, use:
   row_number() OVER ()::integer AS result_id
10. Geometry columns are NOT composite types:
    - NEVER use (geom).geom
    - ALWAYS use geom
11. ST_DWithin, ST_Intersects, ST_Intersection are predicates:
    - NEVER select them as columns.
12. Ensure geometries use the same SRID
    (apply ST_Transform only if required).
13. Do NOT add extra columns unless explicitly requested.
14. Do NOT include explanations, comments, or markdown.
15. NEVER use subqueries returning multiple rows
    as spatial function arguments.
16. Distance-based queries MUST use JOIN or EXISTS,
    NOT scalar subqueries.
17. The base table in FROM MUST match the main entity
    mentioned in the user request.
18. NEVER change the base table to an unrelated table.
19. NEVER use JOIN LATERAL.
20. ST_DWithin MUST have exactly three arguments:
    geometry, geometry, distance (numeric).
21. Do NOT combine ST_Buffer with ST_DWithin.
22. ST_Within MUST have exactly two geometry arguments
    and MUST NOT be used for distance queries.

User request:
{question}

Return ONLY the SQL.
""".strip()

    sql = run_llm(prompt)

    # Minor normalization safeguard
    sql = sql.replace("row_number() OVER 0", "row_number() OVER ()")

    return {"sql": sql}
