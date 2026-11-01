"""Simple Streamlit chat UI for the local RBI monthly chatbot."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from financial_assistant.chatbot import answer_question, load_monthly_documents


def run_chat_ui(data_dir: str | Path = "data/monthly") -> None:
    """Render a lightweight chat interface with grounded local retrieval."""
    st.set_page_config(page_title="RBI Monthly Chatbot", layout="wide")
    st.title("RBI Monthly Chatbot")
    st.caption("Simple local RAG-style chatbot for monthly RBI documents.")

    repo_dir = Path(data_dir)
    documents = load_monthly_documents(repo_dir)

    if not documents:
        st.warning("No monthly RBI documents were found. The app created a small sample repository to demonstrate the flow.")

    st.subheader("Available monthly sources")
    for doc in documents:
        st.write(f"- {doc.title} ({doc.month})")

    st.subheader("Ask a question")
    query = st.text_input("Question", placeholder="Example: What did RBI say about inflation and liquidity?")
    if st.button("Ask") and query:
        result = answer_question(query, documents)
        st.markdown("### Answer")
        st.write(result.answer)

        if result.sources:
            st.markdown("### Sources")
            for source in result.sources:
                st.write(f"- {source}")

        if result.clarification_question:
            st.warning(result.clarification_question)

        st.markdown("### Reasoning")
        st.write(result.reasoning)


if __name__ == "__main__":
    run_chat_ui()
