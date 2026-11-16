import os
import sqlite3
from dotenv import load_dotenv
from groq import Groq
from visualizer import build_dataframe_summary, generate_chart

load_dotenv()

DB_NAME = "company.db"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("Brak klucza GROQ_API_KEY w pliku .env!")

client = Groq(api_key=GROQ_API_KEY)
MODEL_NAME = "qwen/qwen3.8-27b"


def get_database_schema(db_path: str) -> str:
    """Pobiera schemat tabel wraz z próbką danych dla lepszego kontekstu LLM."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = cursor.fetchall()

    schema_parts = []
    for table_name, create_sql in tables:
        if not create_sql:
            continue
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
        sample_rows = cursor.fetchall()
        col_names = [desc[0] for desc in cursor.description]

        part = f"{create_sql}\n/* Przykładowe wiersze {col_names}: {sample_rows} */"
        schema_parts.append(part)

    conn.close()
    return "\n\n".join(schema_parts)


def execute_sql_query(query: str, db_path: str):
    """Bezpiecznie wykonuje zapytanie SELECT na bazie danych."""
    clean_query = query.strip().rstrip(";")
    if not clean_query.upper().startswith("SELECT"):
        raise ValueError("Dozwolone są wyłącznie zapytania odczytu (SELECT)!")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(clean_query)
    results = cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    conn.close()

    return columns, results


def synthesize_answer(user_question: str, sql_query: str, columns: list, rows: list, stats_summary: str) -> str:
    """Tworzy zwięzłe podsumowanie biznesowe w oparciu o dokładne obliczenia Pandas."""
    system_prompt = """Jesteś profesjonalnym Analitykiem Danych.
Na podstawie pytania biznesowego, wyników z bazy oraz gotowych statystyk z Pandas, przygotuj czytelną, zwięzłą odpowiedź po polsku.
Używaj WYŁĄCZNIE dokładnych sum podanych w sekcji statystyk — nie licz sum samodzielnie."""

    user_content = f"""Pytanie: {user_question}
Wykonany SQL: {sql_query}
Kolumny: {columns}
Wyniki z bazy: {rows}
Statystyki Pandas: {stats_summary}"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        temperature=0.2
    )

    return response.choices[0].message.content.strip()


def run_agent_loop(user_question: str, max_retries: int = 3):
    """Pętla agentowa z autokorektą, syntezą Pandas oraz generowaniem wykresu."""
    schema = get_database_schema(DB_NAME)

    system_prompt = f"""Jesteś ekspertem SQL i Analitykiem Danych.
Twoim zadaniem jest przekształcanie pytań biznesowych użytkownika na poprawne zapytania SQL dla bazy SQLite.

Struktura bazy danych:
---
{schema}
---

ZASADY:
1. Generuj WYŁĄCZNIE czysty kod SQL (SELECT). Bez znaczników Markdown (```sql) ani komentarzy.
2. Jeśli w zapytaniu wystąpi błąd, przeanalizujesz go i zwrócisz poprawiony SQL.
3. Zwracaj uwagę na wielkość liter z przykładowych danych, a przy filtrowaniu tekstów stosuj porównania niewrażliwe na wielkość liter (np. UPPER(kolumna) = 'WARTOŚĆ').
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Pytanie: {user_question}"}
    ]

    print(f"\n[ZAPYTANIE BIZNESOWE]: {user_question}")
    print("-" * 60)

    for attempt in range(1, max_retries + 1):
        print(f"-> Próba {attempt} z {max_retries}...")

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.0
        )

        generated_sql = response.choices[0].message.content.strip()
        print(f"   Wygenerowany SQL: {generated_sql}")

        try:
            columns, rows = execute_sql_query(generated_sql, DB_NAME)
            print("   ✓ Sukces! Zapytanie wykonane poprawnie.")
            print("-" * 60)
        except Exception as e:
            error_message = str(e)
            print(f"   X Błąd wykonania SQL: {error_message}")

            messages.append({"role": "assistant", "content": generated_sql})
            messages.append({
                "role": "user",
                "content": f"Błąd bazy SQLite: '{error_message}'. Popraw kod SQL i zwróć tylko poprawną wersję."
            })
            continue

        stats_summary = build_dataframe_summary(columns, rows)
        final_answer = synthesize_answer(user_question, generated_sql, columns, rows, stats_summary)
        chart_path = generate_chart(client, MODEL_NAME, user_question, columns, rows)

        return generated_sql, columns, rows, final_answer, chart_path

    raise RuntimeError(f"Agent nie zdołał wygenerować poprawnego zapytania SQL po {max_retries} próbach.")


if __name__ == "__main__":
    question = (
        "Podaj łączną kwotę wydaną na zrealizowane zamówienia (status COMPLETED) "
        "przez poszczególnych klientów. Pokaż nazwę klienta i sumaryczną kwotę."
    )

    sql, cols, rows, answer, chart = run_agent_loop(question)

    print("\n[ODPOWIEDŹ ANALITYKA DANYCH]:")
    print(answer)
    if chart:
        print(f"\n[WYKRES ZAPISANY]: {chart}")