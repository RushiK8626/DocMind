"""Node responsible for analyzing the query and deciding which tools to call."""
from app.agents.graph_state import _extract_reasoning
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.llm import build_llm
from app.tools.retrieval_tool import create_retrieval_tool
from app.tools.web_search_tool import create_web_search_tool
from app.tools.code_interpreter_tool import create_code_interpreter_tool
from app.tools.datetime_tool import create_datetime_tool

SYSTEM = (
    "You are a senior research analyst. Reason through the user's query using "
    "the tools available to you:\n"
    "- retrieve_documents: search the user's knowledge base. Call this first for any "
    "factual query — context is NOT pre-fetched, you must retrieve it yourself.\n"
    "- web_search: use this to look up current events, general knowledge, or external facts if the knowledge base is insufficient. NEVER rely on your internal knowledge for factual or current questions.\n"
    "- code_interpreter: use only for numerical/logical verification.\n"
    "- get_current_datetime: get the current local date and time. Use this when the query asks about relative dates like 'today', 'this year', 'current', etc.\n\n"
    "CRITICAL: When invoking a tool, do NOT output any conversational text, thinking, or reasoning. Output ONLY the tool call. "
    "If you output text alongside a tool call, the API will crash.\n\n"
    "When using retrieved document chunks, you MUST cite your sources inline using "
    "[SOURCE N] where N is the chunk_index from the retrieval result. "
    "At the end of your response include a **References** section in this exact format:\n"
    "[SOURCE N] Page <page_number> | Element ID: <layout_element_id> | Type: <element_type>\n\n"
    "Example:\n"
    "The profit margin was 18% [SOURCE 1], with Q3 being the strongest quarter [SOURCE 2].\n\n"
    "**References**\n"
    "[SOURCE 1] Page 4 | Element ID: uuid-abc | Type: text\n"
    "[SOURCE 2] Page 7 | Element ID: uuid-def | Type: table_cell\n\n"
    "If the query is casual conversation with nothing to look up, skip all tools "
    "and respond exactly: 'No reasoning required — conversational query.'"
)


def make_reasoning_node(config, user_id, project_id):
    """Builds and returns the reasoning node and its associated tools."""
    retrieval_tool = create_retrieval_tool(user_id=user_id, project_id=project_id)
    web_search_tool = create_web_search_tool()
    code_interpreter_tool = create_code_interpreter_tool()
    datetime_tool = create_datetime_tool()

    tools = [retrieval_tool, web_search_tool, code_interpreter_tool, datetime_tool]
    llm = build_llm(config).bind_tools(tools)

    def reasoning_node(state):
        """Executes the LLM to determine the next step or tool call."""
        if state["messages"]:
            messages = state["messages"]
        else:
            messages = [
                SystemMessage(content=SYSTEM),
                HumanMessage(content=f"User query: '{state['query']}'"),
            ]
            
        try:
            response = llm.invoke(messages)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"LLM invoke failed in reasoning node: {e}")
            from langchain_core.messages import AIMessage
            # Provide a fallback message so the graph can route to the answer node
            response = AIMessage(content="I encountered an internal error while trying to reason about or search for the answer. I will try to answer based on my internal knowledge.")

        update = {"messages": [response]}
        trace = _extract_reasoning(response)
        if trace:
            update["reasoning_trace"] = [trace]
        return update

    return reasoning_node, ToolNode(tools)
