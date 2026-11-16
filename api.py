import os
import re
import shutil
import sqlite3
from typing import Any, List, Optional
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sql_agent import (
    DEFAULT_DB,
    get_active_database,
    get_tables_info,
    run_agent_loop,
    set_active_database,
)

UPLOAD_DIR = "uploads"

app = FastAPI(
    title="Text-to-SQL AI Data Analyst API",
    description="REST API przekształcające pytania biznesowe na zapytania SQL, syntezę Pandas i wykresy.",
    version="1.2.0"
)


class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        json_schema_extra={"example": "Podaj łączną kwotę wydaną na zrealizowane zamówienia przez poszczególnych klientów."}
    )


class QueryResponse(BaseModel):
    question: str
    sql_query: str
    columns: List[str]
    rows: List[List[Any]]
    answer: str
    chart_path: Optional[str] = None


def _sanitize_identifier(name: str, fallback: str = "data") -> str:
    """Zamienia spacje i znaki specjalne na podkreślenia dla bezpiecznych nazw SQL."""
    cleaned = re.sub(r"\W+", "_", name.strip()).strip("_")
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"{fallback}_{cleaned}" if cleaned else fallback
    return cleaned.lower()


@app.get("/", tags=["Health"])
def health_check():
    """Zwraca status serwera, nazwę aktywnej bazy oraz listę jej tabel."""
    return {
        "status": "ok",
        "service": "Text-to-SQL Agent API",
        "active_db": os.path.basename(get_active_database()),
        "is_default": get_active_database() == DEFAULT_DB,
        "tables": get_tables_info()
    }


@app.post("/upload", tags=["Database"])
def upload_database(file: UploadFile = File(...)):
    """Przyjmuje plik CSV lub bazę SQLite (.db/.sqlite) i ustawia ją jako aktywne źródło danych."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nie przesłano nazwy pliku.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in {".csv", ".db", ".sqlite"}:
        raise HTTPException(
            status_code=400,
            detail="Nieobsługiwany format pliku. Wgraj plik .csv, .db lub .sqlite."
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_base = _sanitize_identifier(os.path.splitext(file.filename)[0], fallback="uploaded")

    if ext == ".csv":
        temp_csv_path = os.path.join(UPLOAD_DIR, f"{safe_base}.csv")
        with open(temp_csv_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            # sep=None z engine='python' automatycznie wykrywa separator ',' oraz ';'
            df = pd.read_csv(temp_csv_path, sep=None, engine="python")
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Błąd odczytu pliku CSV: {str(e)}")

        if df.empty:
            raise HTTPException(status_code=422, detail="Przesłany plik CSV jest pusty.")

        # Normalizacja nazw kolumn pod SQLite
        df.columns = [_sanitize_identifier(str(col), fallback=f"col_{i}") for i, col in enumerate(df.columns)]

        target_db_path = os.path.join(UPLOAD_DIR, f"{safe_base}.db")
        conn = sqlite3.connect(target_db_path)
        df.to_sql(safe_base, conn, if_exists="replace", index=False)
        conn.close()

        set_active_database(target_db_path)
    else:
        target_db_path = os.path.join(UPLOAD_DIR, f"{safe_base}{ext}")
        with open(target_db_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            tables = get_tables_info(target_db_path)
            if not tables:
                raise HTTPException(status_code=422, detail="Baza SQLite nie zawiera żadnych tabel.")
        except sqlite3.DatabaseError:
            os.remove(target_db_path)
            raise HTTPException(status_code=422, detail="Przesłany plik nie jest prawidłową bazą SQLite.")

        set_active_database(target_db_path)

    return {
        "message": f"Pomyślnie załadowano źródło danych: {file.filename}",
        "active_db": os.path.basename(get_active_database()),
        "tables": get_tables_info()
    }


@app.post("/reset-db", tags=["Database"])
def reset_database():
    """Przywraca domyślną bazę danych company.db."""
    set_active_database(DEFAULT_DB)
    return {
        "message": "Przywrócono domyślną bazę danych.",
        "active_db": os.path.basename(DEFAULT_DB),
        "tables": get_tables_info()
    }


@app.post("/ask", response_model=QueryResponse, tags=["Agent"])
def ask_agent(request: QueryRequest):
    try:
        sql, cols, rows, answer, chart_path = run_agent_loop(request.question)
        formatted_rows = [list(row) for row in rows]

        return QueryResponse(
            question=request.question,
            sql_query=sql,
            columns=cols,
            rows=formatted_rows,
            answer=answer,
            chart_path=chart_path
        )
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd wewnętrzny serwera: {str(e)}")


@app.get("/chart/latest", tags=["Visualization"])
def get_latest_chart():
    """Zwraca ostatnio wygenerowany wykres jako obraz PNG."""
    chart_file = os.path.join("charts", "latest_chart.png")
    if not os.path.exists(chart_file):
        raise HTTPException(status_code=404, detail="Nie wygenerowano jeszcze żadnego wykresu.")
    return FileResponse(chart_file, media_type="image/png")