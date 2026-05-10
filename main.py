import argparse
import sqlite3
from pprint import pprint

from langgraph.checkpoint.sqlite import SqliteSaver

from agents.intent import classify_intent
from core.env_check import check_env_keys, format_missing_env_message
from graph.pipeline import build_graph


def build_initial_state(query: str) -> dict:
    return {
        "query": query,
        "sub_questions": [],
        "web_sources": [],
        "news_sources": [],
        "paper_sources": [],
        "youtube_sources": [],
        "github_sources": [],
        "all_sources": [],
        "source_count": 0,
        "research_complete": False,
        "report": "",
        "feedback": "",
        "score": 0,
        "retry_count": 0,
        "published": False,
        "output_path": "",
    }


def print_env_status() -> bool:
    status = check_env_keys()

    print("\nEnvironment check")
    print("-" * 60)

    for item in status["required"]:
        mark = "OK" if item["ok"] else "MISSING"
        print(f"{mark:8} {item['key']} - {item['label']}")

    if not status["ok"]:
        print("\n" + format_missing_env_message(status))
        return False

    print("\nAll required environment variables are configured.")
    return True


def run_research(query: str, stream: bool = True) -> dict:
    state = build_initial_state(query)

    print("\nDeep Research terminal run")
    print("-" * 60)
    print(f"Query: {query}")

    intent = classify_intent(query)
    if intent["intent"] == "chat":
        print("\nChat response")
        print("-" * 60)
        print(intent["reply"])
        return {
            **state,
            "report": intent["reply"],
            "source_count": 0,
            "score": 0,
            "published": False,
            "output_path": "",
        }

    conn = sqlite3.connect("research.db", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    pipeline = build_graph(checkpointer)

    thread_id = query.strip().replace(" ", "_")[:40]
    config = {"configurable": {"thread_id": thread_id}}

    if stream:
        final_state = state
        for update in pipeline.stream(state, config=config, stream_mode="values"):
            if isinstance(update, dict):
                final_state.update(update)
                progress = []
                if final_state.get("sub_questions"):
                    progress.append("planner")
                if final_state.get("all_sources"):
                    progress.append("sources")
                if final_state.get("report"):
                    progress.append("report")
                if final_state.get("feedback"):
                    progress.append("critic")
                if progress:
                    print("Progress:", " -> ".join(progress))
        result = final_state
    else:
        result = pipeline.invoke(state, config=config)

    print("\nResearch complete")
    print("-" * 60)
    print(f"Sources: {result.get('source_count', 0)}")
    print(f"Score: {result.get('score', 0)}/10")

    if result.get("output_path"):
        print(f"Saved internally: {result['output_path']}")

    print("\nReport preview")
    print("-" * 60)
    report = result.get("report", "")
    print(report[:2500] + ("..." if len(report) > 2500 else ""))

    if result.get("feedback"):
        print("\nCritic feedback")
        print("-" * 60)
        print(result["feedback"][:1200])

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Deep Research from the terminal.")
    parser.add_argument("query", nargs="*", help="Research query to run")
    parser.add_argument("--no-stream", action="store_true", help="Run without progress streaming")
    parser.add_argument("--env-only", action="store_true", help="Only check environment variables")
    parser.add_argument("--debug-state", action="store_true", help="Print final result dictionary keys")
    args = parser.parse_args()

    env_ok = print_env_status()
    if args.env_only or not env_ok:
        return

    query = " ".join(args.query).strip()
    if not query:
        query = input("\nWhat do you want to research? ").strip()

    if not query:
        print("No query provided.")
        return

    result = run_research(query, stream=not args.no_stream)

    if args.debug_state:
        print("\nFinal state keys")
        print("-" * 60)
        pprint(sorted(result.keys()))


if __name__ == "__main__":
    main()
