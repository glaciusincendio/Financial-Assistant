from financial_assistant.chatbot import answer_question, load_monthly_documents


def test_monthly_documents_load_and_answer_question(tmp_path):
    repo = tmp_path / "monthly"
    documents = load_monthly_documents(repo)
    assert documents

    answer = answer_question("What did RBI say about inflation and liquidity?", documents)
    assert answer.answer
    assert answer.reasoning


def test_ambiguous_questions_trigger_clarification(tmp_path):
    repo = tmp_path / "monthly"
    documents = load_monthly_documents(repo)

    answer = answer_question("What happened in the RBI review?", documents)
    assert answer.clarification_question is not None or answer.answer
