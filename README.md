# Text-to-SQL AI Data Analyst Agent 📊🤖

Autonomiczny agent AI pełniący rolę Analityka Danych. Aplikacja przekształca pytania biznesowe zadawane w języku naturalnym na bezpieczne zapytania SQL, wykonuje je na relacyjnej bazie danych (SQLite) i generuje podsumowania biznesowe.

## 🌟 Kluczowe Funkcjonalności

- **Dynamic Schema Inspection:** Agent samodzielnie analizuje strukturę bazy danych (`sqlite_master`) przed wygenerowaniem zapytania.
- **Self-Correction Loop (Pętla Autokorekty):** W przypadku błędu składniowego lub braku kolumny w SQLite, agent przechwytuje komunikat błędu, analizuje go i automatycznie poprawia zapytanie (do 3 prób).
- **Read-Only Safety Guardrail:** Weryfikacja wykonywania wyłącznie zapytań odczytu (`SELECT`).
- **Natural Language Synthesis:** Przekształcanie surowych wyników tabelarycznych na czytelne raporty i wnioski biznesowe w języku polskim.

## 🛠️ Technologie

- **Language:** Python 3.11+
- **Database:** SQLite
- **LLM Engine:** Groq API (`qwen/qwen3.8-27b`)
- **Environment Management:** `python-dotenv`

## 🚀 Uruchomienie Projektu

### 1. Klonowanie repozytorium i konfiguracja środowiska
```bash
git clone [https://github.com/TwojUsername/text-to-sql-agent.git](https://github.com/TwojUsername/text-to-sql-agent.git)
cd text-to-sql-agent
python -m venv venv