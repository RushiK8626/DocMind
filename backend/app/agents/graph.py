"""Module graph.py."""
from langgraph.graph import StateGraph, END
from app.agents.graph_state import PipelineState
from app.agents.nodes.reasoning_node import make_reasoning_node
from app.agents.nodes.answer_node import make_answer_node
from langgraph.prebuilt import tools_condition

GREETINGS = {"hi", "hello", "hey", "hii", "yo", "sup"}


def route_entry(state: PipelineState):
    """route_entry function."""
    if state["query"].lower().strip(" !.,") in GREETINGS:
        return "greeting"
    return "reason"


def greeting_node(state):
    """greeting_node function."""
    return {"final_answer": "Hey! What would you like to know?"}


def build_graph(config, user_id, project_id):
    """build_graph function."""
    reasoning_node, reasoning_tools = make_reasoning_node(config, user_id, project_id)

    answer_node = make_answer_node(config)

    graph = StateGraph(PipelineState)

    graph.add_node("greeting", greeting_node)
    graph.add_node("reason", reasoning_node)
    graph.add_node("reason_tools", reasoning_tools)
    graph.add_node("answer", answer_node)

    graph.set_conditional_entry_point(
        route_entry,
        {
            "greeting": "greeting",
            "reason": "reason",
        },
    )

    graph.add_conditional_edges(
        "reason",
        tools_condition,
        {
            "tools": "reason_tools",
            END: "answer",
        },
    )

    graph.add_edge("reason_tools", "reason")

    graph.add_edge("answer", END)
    graph.add_edge("greeting", END)

    return graph.compile()
