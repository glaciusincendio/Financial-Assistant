"""Simple monthly RBI chatbot powered by local retrieval and lightweight semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re


SEMANTIC_ALIASES = {
    "repo rate": {"repo rate", "policy rate", "rate setting"},
    "liquidity": {"liquidity", "money supply", "surplus liquidity", "funding conditions"},
    "inflation": {"inflation", "price rise", "consumer prices", "price pressure"},
    "banking": {"banking", "bank credit", "banks", "credit conditions"},
    "growth": {"growth", "economic activity", "output", "expansion"},
}


@dataclass(frozen=True)
class KnowledgeDocument:
    """One source document in the monthly RBI knowledge repository."""

    title: str
    month: str
    path: Path
    text: str


@dataclass
class ChatAnswer:
    """Structured answer returned by the local chatbot."""

    answer: str
    sources: list[str] = field(default_factory=list)
    clarification_question: str | None = None
    reasoning: str = ""
    relevant_documents: list[KnowledgeDocument] = field(default_factory=list)


def _normalize(value: str) -> set[str]:
    """Return normalized keyword tokens for retrieval scoring."""
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def _expanded_query_terms(query: str) -> set[str]:
    """Expand common RBI wording to a small semantic alias set."""
    tokens = _normalize(query)
    expanded = set(tokens)
    for canonical, aliases in SEMANTIC_ALIASES.items():
        if canonical in query.lower():
            expanded.update(aliases)
        else:
            for alias in aliases:
                if alias in query.lower():
                    expanded.add(canonical)
                    expanded.add(alias)
    return expanded


def _score_document(query: str, document: KnowledgeDocument) -> float:
    """Simple local retrieval score based on overlap and semantic alias matching."""
    query_terms = _expanded_query_terms(query)
    if not query_terms:
        return 0.0
    document_terms = _normalize(document.text)
    overlap = len(query_terms & document_terms)
    if overlap == 0:
        return 0.0
    score = overlap / max(len(query_terms), 1)
    if any(term in document.text.lower() for term in {"repo rate", "liquidity", "inflation"}):
        score += 0.05
    return min(score, 1.0)


def _create_default_documents(base_dir: Path) -> list[KnowledgeDocument]:
    """Create a tiny monthly repository so the app works without manual setup."""
    base_dir.mkdir(parents=True, exist_ok=True)
    samples = {
        "2024-01-rbi-policy-update.md": """# RBI Policy Update - January 2024

The Reserve Bank of India kept the repo rate unchanged during its January review. The policy emphasised liquidity management and inflation control. The central bank noted that banking conditions remained stable while credit conditions were closely monitored.
""",
        "2024-02-liquidity-review.md": """# Liquidity Review - February 2024

The RBI continued to monitor surplus liquidity and funding conditions. It highlighted the need to maintain smooth money market operations and support orderly credit flow. Inflation was seen as a key risk factor during the month.
""",
        "2024-03-growth-and-inflation.md": """# Growth and Inflation - March 2024

The RBI review discussed economic growth, inflation pressure, and the need for prudent monetary policy. The committee noted that repo rate decisions should remain data-dependent while banking sector resilience continued to improve.
""",
    }
    docs: list[KnowledgeDocument] = []
    for file_name, text in samples.items():
        path = base_dir / file_name
        path.write_text(text, encoding="utf-8")
        month = file_name.split("-")[0] + "-" + file_name.split("-")[1]
        docs.append(KnowledgeDocument(title=path.stem.replace("-", " ").title(), month=month, path=path, text=text))
    return docs


def load_monthly_documents(base_dir: str | Path) -> list[KnowledgeDocument]:
    """Load the monthly RBI repository from disk, creating a default sample set if empty."""
    repo_dir = Path(base_dir)
    repo_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(repo_dir.glob("*.md")) + sorted(repo_dir.glob("*.txt"))
    if not files:
        return _create_default_documents(repo_dir)

    documents: list[KnowledgeDocument] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        month = path.stem.split("-")[:2]
        display_month = "-".join(month) if month else "unknown"
        documents.append(
            KnowledgeDocument(
                title=path.stem.replace("-", " ").title(),
                month=display_month,
                path=path,
                text=text,
            )
        )
    return documents


def answer_question(query: str, documents: list[KnowledgeDocument]) -> ChatAnswer:
    """Return a simple grounded answer using local retrieval with basic semantic expansion."""
    normalized = query.strip()
    if not normalized:
        return ChatAnswer(
            answer="Please ask a question about RBI policy, liquidity, inflation, or banking conditions.",
            sources=[],
            reasoning="No question was provided.",
        )

    ranked = sorted(
        ((document, _score_document(normalized, document)) for document in documents),
        key=lambda item: item[1],
        reverse=True,
    )

    top_document, top_score = ranked[0] if ranked else (None, 0.0)
    second_document, second_score = ranked[1] if len(ranked) > 1 else (None, 0.0)

    if top_document is None or top_score <= 0.05:
        return ChatAnswer(
            answer="I could not find enough evidence in the current monthly repository to answer this confidently.",
            sources=[],
            reasoning="The query did not match any indexed monthly document closely enough for a grounded response.",
            relevant_documents=[],
        )

    if second_document and abs(top_score - second_score) <= 0.08 and second_score > 0.05:
        return ChatAnswer(
            answer="I found more than one likely monthly source for this question. Please tell me which month or topic you mean.",
            sources=[top_document.title, second_document.title],
            clarification_question="Do you want the answer from the January 2024 policy update or the February 2024 liquidity review?",
            reasoning="The query matches multiple documents with similar relevance, so a clarification is safer than guessing.",
            relevant_documents=[top_document, second_document],
        )

    summary = top_document.text.strip().replace("\n", " ")
    if len(summary) > 500:
        summary = summary[:500].rsplit(" ", 1)[0] + "..."

    answer_text = (
        f"Based on {top_document.title} ({top_document.month}), the relevant RBI material says: "
        f"{summary}. In simple terms, the document suggests the RBI is focusing on the current policy, liquidity conditions, and inflation risks described in the source."
    )
    return ChatAnswer(
        answer=answer_text,
        sources=[top_document.title],
        reasoning="The system matched the user’s question to the most relevant monthly document using keyword overlap and a small semantic alias map for common RBI terminology.",
        relevant_documents=[top_document],
    )
