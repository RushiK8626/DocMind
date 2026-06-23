"""Module reasoning_node.py."""
from app.agents.graph_state import _extract_reasoning
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.llm import build_llm
from app.tools.retrieval_tool import create_retrieval_tool
from app.tools.web_search_tool import create_web_search_tool
from app.tools.code_interpreter_tool import create_code_interpreter_tool


SYSTEM = (
    "You are a senior research analyst. Reason through the user's query using "
    "the tools available to you:\n"
    "- retrieve_documents: search the user's knowledge base. Call this first for any "
    "factual query — context is NOT pre-fetched, you must retrieve it yourself.\n"
    "- web_search: use only if the knowledge base is genuinely insufficient.\n"
    "- code_interpreter: use only for numerical/logical verification.\n\n"
    "If the query is casual conversation with nothing to look up, skip all tools "
    "and respond exactly: 'No reasoning required — conversational query.'"
)


def make_reasoning_node(config, user_id, project_id):
    """make_reasoning_node function."""
    retrieval_tool = create_retrieval_tool(user_id=user_id, project_id=project_id)
    web_search_tool = create_web_search_tool()
    code_interpreter_tool = create_code_interpreter_tool()

    tools = [retrieval_tool, web_search_tool, code_interpreter_tool]
    llm = build_llm(config).bind_tools(tools)

    def reasoning_node(state):
        """reasoning_node function."""
        messages = state["messages"] or [
            SystemMessage(content=SYSTEM),
            HumanMessage(content=f"User query: '{state['query']}'"),
        ]
        response = llm.invoke(messages)

        update = {"messages": [response]}
        trace = _extract_reasoning(response)
        if trace:
            update["reasoning_trace"] = [trace]
        return update

    return reasoning_node, ToolNode(tools)
