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
git clone https://github.com/fudiaszek-ai/text-to-sql-agent.git
cd text-to-sql-agent
python -m venv venv
```

### 2. Aktywacja środowiska wirtualnego
- **Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\activate
  ```

### 3. Instalacja zależności
```bash
pip install groq python-dotenv
```

### 4. Konfiguracja klucza API
Stwórz plik `.env` w głównym katalogu projektu:
```env
GROQ_API_KEY=twój_klucz_groq_api
```

### 5. Uruchomienie Agenta
```bash
python sql_agent.py
```

## 📋 Przykład Działania

**Zapytanie biznesowe:**
> *"Podaj łączną kwotę wydaną na zrealizowane zamówienia (status COMPLETED) przez poszczególnych klientów."*

**Wygenerowany SQL:**
```sql
SELECT c.name, SUM(o.quantity * p.price) AS total_amount
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN products p ON o.product_id = p.product_id
WHERE o.status = 'COMPLETED'
GROUP BY c.customer_id, c.name;
```

**Odpowiedź Agenta:**
> Największym klientem pod względem wartości zrealizowanych zamówień jest **TechCorp Sp. z o.o.**, którego łączne wydatki wynoszą **24 250,00 zł**...