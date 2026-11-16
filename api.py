from typing import Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sql_agent import run_agent_loop

app = FastAPI(
    title="Text-to-SQL AI Data Analyst API",
    description="REST API przekształcające pytania biznesowe na zapytania SQL z pętlą autokorekty.",
    version="1.0.0"
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


@app.get("/", tags=["Health"])
def health_check():
    """Sprawdza, czy serwer API działa poprawnie."""
    return {"status": "ok", "service": "Text-to-SQL Agent API"}


@app.post("/ask", response_model=QueryResponse, tags=["Agent"])
def ask_agent(request: QueryRequest):
    """Przyjmuje pytanie biznesowe, generuje SQL, odpytuje bazę i zwraca syntezę."""
    try:
        sql, cols, rows, answer = run_agent_loop(request.question)
        # Konwersja krotek (tuples) z SQLite na listy dla czystej serializacji JSON
        formatted_rows = [list(row) for row in rows]

        return QueryResponse(
            question=request.question,
            sql_query=sql,
            columns=cols,
            rows=formatted_rows,
            answer=answer
        )
    except RuntimeError as e:
        # Błąd, gdy agent wyczerpał limit prób naprawy SQL
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd wewnętrzny serwera: {str(e)}")