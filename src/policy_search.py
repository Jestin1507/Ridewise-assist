
import re

from policy_reader import read_policies


# Common words that do not help much with policy relevance.
STOP_WORDS = {
    "what", "when", "where", "who", "why", "how",
    "is", "are", "was", "were", "the", "a", "an",
    "if", "my", "me", "i", "during", "does", "do",
    "can", "could", "would", "should", "will", "to",
    "for", "of", "in", "on", "at", "and", "or",
    "it", "this", "that", "happens", "happen",
    "about", "please", "tell", "explain", "give",
    "your", "you", "we", "our", "be", "being",
    "have", "has", "had", "with", "from",
}


# Phrases that can improve ranking for common policy questions.
IMPORTANT_PHRASES = [
    "late return fee",
    "battery runs out",
    "cancellation and refund",
    "refund policy",
    "damage penalty",
]


def get_terms(text):
    """Extract meaningful keywords from text."""
    terms = set(re.findall(r"\b[a-z0-9]+\b", text.lower()))
    return terms - STOP_WORDS


def chunk_text(text, chunk_size=180, overlap=30):
    """Split text into overlapping word-based chunks."""
    words = text.split()

    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Invalid chunk_size or overlap")

    chunks = []

    for start in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[start:start + chunk_size])

        if chunk.strip():
            chunks.append(chunk)

        if start + chunk_size >= len(words):
            break

    return chunks


def build_policy_chunks():
    """Read policy pages and create searchable chunks."""
    documents = read_policies()
    all_chunks = []

    for document in documents:
        page_chunks = chunk_text(document["text"])

        for chunk_number, text in enumerate(page_chunks, start=1):
            all_chunks.append({
                "source": document["source"],
                "page": document["page"],
                "chunk_number": chunk_number,
                "text": text,
            })

    return all_chunks


def search_policies(question, chunks, top_k=3):
    """Rank policy passages using keyword overlap and phrase matching."""
    question_terms = get_terms(question)

    if not question_terms:
        return []

    question_lower = question.lower()
    results = []

    for chunk in chunks:
        text_lower = chunk["text"].lower()
        chunk_terms = get_terms(chunk["text"])

        matched_terms = question_terms & chunk_terms
        score = len(matched_terms)

        # Boost a result if it contains an important phrase
        # that also appears in the user's question.
        for phrase in IMPORTANT_PHRASES:
            if phrase in question_lower and phrase in text_lower:
                score += 5

        # Ignore passages with too little keyword overlap.
        if score >= 2:
            results.append((score, chunk))

    # Sort by score, then use source and page for consistent tie-breaking.
    results.sort(
        key=lambda item: (
            -item[0],
            item[1]["source"],
            item[1]["page"],
            item[1]["chunk_number"],
        )
    )

    return results[:top_k]


if __name__ == "__main__":
    try:
        chunks = build_policy_chunks()
        print(f"Total policy chunks: {len(chunks)}")

        question = input("\nAsk a policy question: ").strip()

        if not question:
            print("Please enter a question.")
        else:
            results = search_policies(question, chunks)

            if not results:
                print("No matching policy passages found.")
            else:
                for rank, (score, chunk) in enumerate(results, start=1):
                    print(f"\n--- Result {rank} | Score: {score} ---")
                    print(f"Source: {chunk['source']}")
                    print(f"Page: {chunk['page']}")
                    print(chunk["text"])

    except Exception as error:
        print(f"Policy search failed: {error}")
