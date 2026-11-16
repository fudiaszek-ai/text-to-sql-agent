import json
import os
import re
from typing import Any, List, Optional
import matplotlib

# Wymuszenie trybu bezokienkowego (kluczowe dla wątków FastAPI)
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from groq import Groq

CHARTS_DIR = "charts"


def build_dataframe_summary(columns: List[str], rows: List[Any]) -> str:
    """Liczy deterministyczne sumy dla kolumn numerycznych w Pandas."""
    if not rows:
        return "Brak danych."

    df = pd.DataFrame(rows, columns=columns)
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    if not numeric_cols:
        return f"Liczba wierszy: {len(df)}."

    summaries = [f"Liczba wierszy: {len(df)}"]
    for col in numeric_cols:
        total = df[col].sum()
        summaries.append(f"Dokładna suma kolumny '{col}': {total:,.2f}")

    return " | ".join(summaries)


def generate_chart(
    client: Groq,
    model_name: str,
    user_question: str,
    columns: List[str],
    rows: List[Any]
) -> Optional[str]:
    """Dobiera typ wykresu przez LLM i renderuje plik PNG za pomocą Pandas + Matplotlib."""
    # Wykres ma sens tylko dla co najmniej 2 wierszy i 2 kolumn
    if len(rows) < 2 or len(columns) < 2:
        return None

    df = pd.DataFrame(rows, columns=columns)

    prompt = f"""Przeanalizuj pytanie i kolumny tabeli, aby dobrać najlepszy wykres.
Pytanie: {user_question}
Kolumny: {columns}
Przykładowe wiersze: {rows[:3]}

Zwróć WYŁĄCZNIE poprawny obiekt JSON w formacie:
{{
    "chart_type": "bar" | "line" | "pie" | "none",
    "x_col": "nazwa_kolumny_osi_x",
    "y_col": "nazwa_kolumny_wartosci_y",
    "title": "Krótki tytuł wykresu po polsku"
}}

Zasady:
- Użyj "bar" do porównania kategorii/klientów/produktów.
- Użyj "line" dla trendów w czasie (daty, miesiące).
- Użyj "pie" tylko gdy jest maks. 5 kategorii i pytamy o udział procentowy.
- Użyj "none" jeśli dane nie nadają się na wykres."""

    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"}
    )

    raw_content = response.choices[0].message.content.strip()
    clean_json = re.sub(r"```json|```", "", raw_content).strip()

    try:
        config = json.loads(clean_json)
    except json.JSONDecodeError:
        return None

    chart_type = config.get("chart_type", "none")
    x_col = config.get("x_col")
    y_col = config.get("y_col")
    title = config.get("title", "Analiza danych")

    if chart_type == "none" or x_col not in df.columns or y_col not in df.columns:
        return None

    # Konwersja osi Y na typ numeryczny
    df[y_col] = pd.to_numeric(df[y_col], errors="coerce")
    df = df.dropna(subset=[y_col])
    if df.empty:
        return None

    os.makedirs(CHARTS_DIR, exist_ok=True)
    output_path = os.path.join(CHARTS_DIR, "latest_chart.png")

    fig, ax = plt.subplots(figsize=(9, 5))

    if chart_type == "bar":
        bars = ax.bar(df[x_col].astype(str), df[y_col], color="#2563EB", width=0.55)
        ax.bar_label(bars, fmt="%.0f", padding=3, fontsize=9)
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        plt.xticks(rotation=15, ha="right")
    elif chart_type == "line":
        ax.plot(df[x_col].astype(str), df[y_col], marker="o", linewidth=2.5, color="#2563EB")
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.grid(True, linestyle="--", alpha=0.5)
        plt.xticks(rotation=15, ha="right")
    elif chart_type == "pie":
        ax.pie(df[y_col], labels=df[x_col].astype(str), autopct="%1.1f%%", startangle=140)
        ax.axis("equal")

    ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close(fig)

    return output_path