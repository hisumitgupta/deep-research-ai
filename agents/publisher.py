from core.state import ResearchState
from datetime import datetime
import os


def publisher_node(state: ResearchState) -> dict:
    """
    Saves report as markdown file.
    Later you can add: post to Twitter, LinkedIn, Medium, WhatsApp.
    That's the 'post research' feature you wanted.
    """
    if not _should_save_report(state):
        print("\n[Publisher] Skipping file save for non-research response.")
        return {"published": False, "output_path": ""}

    print("\n[Publisher] Saving report...")

    os.makedirs("output/reports", exist_ok=True)

    # Clean filename from query
    safe_name = (
        state["query"][:40]
        .strip()
        .replace(" ", "_")
        .replace("/", "-")
        .replace("\\", "-")
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"output/reports/{safe_name}_{timestamp}.md"

    # Source breakdown summary
    source_types = {}
    for s in state.get("all_sources", []):
        t = s.get("source_type", "unknown")
        source_types[t] = source_types.get(t, 0) + 1

    source_summary = " | ".join(
        [f"{k}: {v}" for k, v in source_types.items()]
    )

    # Write markdown
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# Deep Research Report\n\n")
        f.write(f"**Query:** {state['query']}\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**Total Sources:** {state['source_count']} ({source_summary})\n\n")
        f.write(f"**Quality Score:** {state.get('score', 0)}/10\n\n")
        f.write("---\n\n")
        f.write(state["report"])
        f.write("\n\n---\n\n")
        f.write("## Critic Feedback\n\n")
        f.write(state.get("feedback", ""))
        f.write("\n\n---\n\n")
        f.write("## All Sources\n\n")
        for s in state.get("all_sources", []):
            f.write(f"- [{s['title']}]({s['url']}) `{s['source_type']}`\n")

    print(f"[Publisher] Report saved: {filename}")
    return {"published": True, "output_path": filename}


def _should_save_report(state: ResearchState) -> bool:
    report = state.get("report", "").strip()
    source_count = state.get("source_count", 0)

    if not report:
        return False

    if source_count <= 0:
        return False

    return True
