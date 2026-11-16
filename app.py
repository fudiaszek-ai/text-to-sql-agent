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
st.caption("Zadawaj pytania biznesowe w języku naturalnym. Agent wygeneruje SQL, zweryfikuje wyniki w Pandas i dobierze wizualizację.")

# Inicjalizacja historii czatu
if "messages" not in st.session_state:
    st.session_state.messages = []

# Panel boczny: status API oraz gotowe pytania testowe
with st.sidebar:
    st.header("⚙️ Status Systemu")
    try:
        health = requests.get(f"{API_URL}/", timeout=2)
        if health.status_code == 200:
            st.success("Backend FastAPI: Online")
        else:
            st.warning(f"Backend odpowiedział kodem: {health.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("Backend FastAPI: Offline (uruchom uvicorn)")

    st.divider()
    st.subheader("💡 Przykładowe pytania")
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
    # Wyświetlenie i zapisanie wiadomości użytkownika
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # Zapytanie do backendu FastAPI
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

                    # Pobranie bajtów wykresu, jeśli został wygenerowany
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