"""Interactive CLI for the Podcast Q&A Bot."""
from src.services.qa_pipeline import QAPipeline

pipeline = QAPipeline()
print("Podcast Q&A Bot (type 'exit' to quit)\n")

while True:
    q = input("Q: ").strip()
    if q.lower() in ("exit", "quit", "q"):
        break

    result = pipeline.ask(q)
    print(f"A: {result['answer']}")

    for s in result["sources"]:
        m = s["metadata"]
        print(f"   [{m['start']:.0f}s – {m['end']:.0f}s] {s['text'][:80]}...")
    print()
