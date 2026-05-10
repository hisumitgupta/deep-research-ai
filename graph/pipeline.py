from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.sqlite import SqliteSaver
from core.state import ResearchState
from agents.planner import planner_node
from agents.quality_checker import quality_checker_node, should_research_more
from agents.synthesizer import synthesizer_node
from agents.critic import critique_node, should_retry
from agents.publisher import publisher_node
from graph.research_subgraph import build_research_subgraph
import sqlite3


def build_graph(checkpointer):
    research_subgraph = build_research_subgraph(checkpointer=checkpointer)

    graph = StateGraph(ResearchState)

    graph.add_node("planner_node",        planner_node)
    graph.add_node("research_subgraph",   research_subgraph)
    graph.add_node("quality_checker",     quality_checker_node)
    graph.add_node("synthesizer_node",    synthesizer_node)
    graph.add_node("critique_node",       critique_node)
    graph.add_node("publisher_node",      publisher_node)

    graph.add_edge(START,                 "planner_node")
    graph.add_edge("planner_node",        "research_subgraph")
    graph.add_edge("research_subgraph",   "quality_checker")

    # Quality gate — loop back if not enough sources
    graph.add_conditional_edges(
        "quality_checker",
        should_research_more,
        {
            "research_subgraph": "research_subgraph",
            "synthesizer_node":  "synthesizer_node"
        }
    )

    graph.add_edge("synthesizer_node",    "critique_node")

    graph.add_conditional_edges(
        "critique_node",
        should_retry,
        {
            "synthesizer_node": "synthesizer_node",
            "__end__":          "publisher_node"
        }
    )

    graph.add_edge("publisher_node", END)

    return graph.compile(checkpointer=checkpointer)