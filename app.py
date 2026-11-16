import pandas as pd
import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="AI Data Analyst | Text-to-SQL",
    page_icon="📊",
    layout="wide"
)

st.title("📊 AI Data Analyst — Text-to-SQL Agent")
st.caption("Zadawaj pytania biznesowe w języku naturalnym lub wgraj własny plik CSV / SQLite w panelu bocznym.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Panel boczny: status, wgrywanie plików, struktura bazy
with st.sidebar:
    st.header("⚙️ Status i Źródło Danych")

    api_online = False
    is_default_db = True
    tables_info = {}

    try:
        health = requests.get(f"{API_URL}/", timeout=2)
        if health.status_code == 200:
            api_online = True
            info_data = health.json()
            active_db_name = info_data.get("active_db", "company.db")
            is_default_db = info_data.get("is_default", True)
            tables_info = info_data.get("tables", {})

            st.success(f"Backend FastAPI: Online\n\nAktywna baza: **`{active_db_name}`**")
        else:
            st.warning(f"Backend odpowiedział kodem: {health.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("Backend FastAPI: Offline (uruchom uvicorn)")

    # Sekcja wgrywania własnych plików
    if api_online:
        st.divider()
        st.subheader("📂 Wgraj własne dane")
        uploaded_file = st.file_uploader(
            "Wybierz plik CSV lub SQLite",
            type=["csv", "db", "sqlite"],
            help="Plik CSV zostanie automatycznie przekonwertowany na tabelę SQLite."
        )

        if uploaded_file is not None:
            if st.button("📥 Załaduj plik do analizy", type="primary", use_container_width=True):
                with st.spinner("Przetwarzam plik..."):
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                    resp = requests.post(f"{API_URL}/upload", files=files, timeout=30)
                    if resp.status_code == 200:
                        st.session_state.messages = []
                        st.toast(f"Załadowano: {uploaded_file.name}", icon="✅")
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "Błąd podczas wgrywania pliku."))

        if not is_default_db:
            if st.button("🔄 Przywróć bazę company.db", use_container_width=True):
                requests.post(f"{API_URL}/reset-db", timeout=10)
                st.session_state.messages = []
                st.rerun()

        # Podgląd struktury tabel aktywnej bazy
        if tables_info:
            with st.expander("📋 Tabele i kolumny w bazie", expanded=not is_default_db):
                for tbl, cols in tables_info.items():
                    st.markdown(f"**`{tbl}`**")
                    st.caption(", ".join(cols))

    # Gotowe pytania pokazujemy tylko dla domyślnej bazy company.db
    if is_default_db:
        st.divider()
        st.subheader("💡 Przykładowe pytania dla bazy company.db")
        example_questions = [
            "Podaj łączną kwotę wydaną na zrealizowane zamówienia przez poszczególnych klientów.",
            "Które produkty sprzedają się najlepiej pod względem liczby zamówionych sztuk?",
            "Pokaż wartość zamówień w podziale na ich status.",
            "Jakie zamówienia złożył klient TechCorp Sp. z o.o.?"
        ]

        for eq in example_questions:
            if st.button(eq, use_container_width=True):
                st.session_state.pending_prompt = eq

    st.divider()
    if st.button("🗑️ Wyczyść historię czatu", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Renderowanie dotychczasowej historii rozmowy
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg.get("chart_bytes"):
            st.image(msg["chart_bytes"], use_container_width=False, width=700)

        if msg.get("df") is not None and not msg["df"].empty:
            st.dataframe(msg["df"], use_container_width=True, hide_index=True)

        if msg.get("sql"):
            with st.expander("🔍 Zobacz wygenerowane zapytanie SQL"):
                st.code(msg["sql"], language="sql")

# Obsługa pola tekstowego lub kliknięcia przycisku z panelu bocznego
user_prompt = st.chat_input("Wpisz pytanie biznesowe o dane...")
if "pending_prompt" in st.session_state:
    user_prompt = st.session_state.pop("pending_prompt")

if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analizuję bazę, generuję SQL i tworzę wykres..."):
            try:
                response = requests.post(
                    f"{API_URL}/ask",
                    json={"question": user_prompt},
                    timeout=60
                )

                if response.status_code == 200:
                    data = response.json()
                    answer = data["answer"]
                    sql_query = data["sql_query"]
                    df = pd.DataFrame(data["rows"], columns=data["columns"]) if data["rows"] else pd.DataFrame()

                    chart_bytes = None
                    if data.get("chart_path"):
                        chart_resp = requests.get(f"{API_URL}/chart/latest", timeout=10)
                        if chart_resp.status_code == 200:
                            chart_bytes = chart_resp.content

                    st.markdown(answer)
                    if chart_bytes:
                        st.image(chart_bytes, use_container_width=False, width=700)
                    if not df.empty:
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    with st.expander("🔍 Zobacz wygenerowane zapytanie SQL"):
                        st.code(sql_query, language="sql")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sql": sql_query,
                        "df": df,
                        "chart_bytes": chart_bytes
                    })
                else:
                    error_detail = response.json().get("detail", "Nieznany błąd API")
                    error_msg = f"❌ Błąd przetwarzania zapytania: {error_detail}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

            except requests.exceptions.ConnectionError:
                conn_msg = "❌ Brak połączenia z API. Upewnij się, że serwer `uvicorn api:app --reload` jest uruchomiony."
                st.error(conn_msg)
                st.session_state.messages.append({"role": "assistant", "content": conn_msg})