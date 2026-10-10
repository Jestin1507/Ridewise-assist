
from pathlib import Path
from pypdf import PdfReader

PROJECT_DIR = Path(__file__).resolve().parent.parent
POLICY_DIR = PROJECT_DIR / "policies"


def read_policies():
    documents = []

    for pdf_path in sorted(POLICY_DIR.glob("*.pdf")):
        reader = PdfReader(pdf_path)

        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""

            if text.strip():
                documents.append({
                    "source": pdf_path.name,
                    "page": page_number,
                    "text": text.strip(),
                })

    return documents


if __name__ == "__main__":
    documents = read_policies()

    print(f"Documents extracted: {len(documents)}")

    for document in documents:
        print(
            f"\nSource: {document['source']}"
            f" | Page: {document['page']}"
        )
        print(document["text"][:500])
        print("-" * 50)
