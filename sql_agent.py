import os
import sqlite3
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

DB_NAME = "company.db"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("Brak klucza GROQ_API_KEY w pliku .env!")

client = Groq(api_key=GROQ_API_KEY)
MODEL_NAME = "qwen/qwen3.8-27b"


def get_database_schema(db_path: str) -> str:
    """Pobiera dynamicznie schemat wszystkich tabel w bazie SQLite."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = cursor.fetchall()
    conn.close()

    schema = "\n\n".join([table[0] for table in tables if table[0]])
    return schema


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


def synthesize_answer(user_question: str, sql_query: str, columns: list, rows: list) -> str:
    """Tworzy zwięzłe podsumowanie biznesowe w języku naturalnym."""
    system_prompt = """Jesteś profesjonalnym Analitykiem Danych.
Na podstawie pytania biznesowego, wykonanego zapytania SQL oraz surowych wyników z bazy, przygotuj czytelną, zwięzłą odpowiedź po polsku.
Formułuj konkretne wnioski, podając najważniejsze liczby i nazwy."""

    user_content = f"""Pytanie: {user_question}
Wykonany SQL: {sql_query}
Kolumny: {columns}
Wyniki z bazy: {rows}"""

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
    """Pętla agentowa z mechanizmem autokorekty (Self-Correction Loop)."""
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

        # Przeznaczamy try...except WYŁĄCZNIE do wychwytywania błędów wykonywania SQL w bazie
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

        # Po udanym wykonaniu SQL przechodzimy do syntezy
        final_answer = synthesize_answer(user_question, generated_sql, columns, rows)
        return generated_sql, columns, rows, final_answer

    raise RuntimeError(f"Agent nie zdołał wygenerować poprawnego zapytania SQL po {max_retries} próbach.")


if __name__ == "__main__":
    question = (
        "Podaj łączną kwotę wydaną na zrealizowane zamówienia (status COMPLETED) "
        "przez poszczególnych klientów. Pokaż nazwę klienta i sumaryczną kwotę."
    )

    sql, cols, rows, answer = run_agent_loop(question)

    print("\n[ODPOWIEDŹ ANALITYKA DANYCH]:")
    print(answer)