import os
from typing import Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sql_agent import run_agent_loop

app = FastAPI(
    title="Text-to-SQL AI Data Analyst API",
    description="REST API przekształcające pytania biznesowe na zapytania SQL, syntezę Pandas i wykresy.",
    version="1.1.0"
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


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "Text-to-SQL Agent API"}


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