
from policy_retriever import PolicyRetriever
from llm_client import ask_llm


class RideWiseRAG:
    def __init__(self):
        # Initialize the policy retriever once.
        self.retriever = PolicyRetriever()

    def answer_question(self, question):
        """Retrieve policy evidence and generate a grounded answer."""

        question = question.strip()

        if not question:
            return {
                "answer": "Please enter a question.",
                "sources": [],
            }

        # Step 1: Retrieve relevant policy passages.
        passages = self.retriever.retrieve(question, top_k=3)

        if not passages:
            return {
                "answer": (
                    "I couldn't find sufficient evidence in the "
                    "available policy documents to answer that question."
                ),
                "sources": [],
            }

        # Step 2: Build the evidence context for the LLM.
        context_parts = []

        for passage in passages:
            context_parts.append(
                f"Source: {passage['source']}\n"
                f"Page: {passage['page']}\n"
                f"Evidence:\n{passage['text']}"
            )

        context = "\n\n".join(context_parts)

        # Step 3: Ask the permitted NeoStats LLM to answer from evidence.
        try:
            answer = ask_llm(question, context)

            if not answer or not answer.strip():
                answer = (
                    "I couldn't generate a reliable answer from the "
                    "available policy evidence. Please try again."
                )

        except Exception:
            # Avoid exposing API keys or internal error details.
            return {
                "answer": (
                    "I'm unable to generate an answer right now. "
                    "Please try again shortly."
                ),
                "sources": [],
            }

        # Step 4: Return unique document/page references.
        # These are retrieved sources, not proof that the LLM
        # relied on every source in its final answer.
        sources = []
        seen_sources = set()

        for passage in passages:
            key = (passage["source"], passage["page"])

            if key not in seen_sources:
                seen_sources.add(key)

                sources.append({
                    "source": passage["source"],
                    "page": passage["page"],
                })

        # Step 5: Return a consistent result for the caller.
        return {
            "answer": answer,
            "sources": sources,
        }



if __name__ == "__main__":
    try:
        rag = RideWiseRAG()

        print("RideWise Assist — Policy Q&A")
        print("Type 'exit' to stop.\n")

        while True:
            try:
                question = input("Ask RideWise Assist: ").strip()
            except EOFError:
                print("\nGoodbye!")
                break

            if question.lower() in {"exit", "quit"}:
                print("Goodbye!")
                break

            if not question:
                print("Please enter a question.\n")
                continue

            result = rag.answer_question(question)

            print("\nAnswer:")
            print(result["answer"])

            if result["sources"]:
                print("\nRetrieved sources:")
                for source in result["sources"]:
                    print(
                        f"- {source['source']}, "
                        f"page {source['page']}"
                    )

            print()

    except KeyboardInterrupt:
        print("\nRideWise Assist stopped. Goodbye!")

    except Exception as error:
        print(f"\nUnable to start RideWise Assist: {error}")
