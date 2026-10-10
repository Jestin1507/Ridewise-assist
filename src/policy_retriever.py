
from policy_search import build_policy_chunks, search_policies


class PolicyRetriever:
    def __init__(self):
        # Read policy PDFs and prepare searchable chunks once.
        self.chunks = build_policy_chunks()

    def retrieve(self, question, top_k=3):
        """Return relevant policy passages with source and page details."""
        results = search_policies(
            question=question,
            chunks=self.chunks,
            top_k=top_k
        )

        passages = []

        for score, chunk in results:
            passages.append({
                "score": score,
                "source": chunk["source"],
                "page": chunk["page"],
                "text": chunk["text"]
            })

        return passages


if __name__ == "__main__":
    retriever = PolicyRetriever()

    question = input("Ask a policy question: ").strip()
    results = retriever.retrieve(question)

    if not results:
        print("No relevant policy evidence found.")
    else:
        for item in results:
            print(f"\nSource: {item['source']}")
            print(f"Page: {item['page']}")
            print(f"Text: {item['text']}")
