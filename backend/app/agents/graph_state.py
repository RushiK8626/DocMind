"""Defines the state schema for the LangGraph execution pipeline."""
import operator
from typing import Annotated, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class PipelineState(TypedDict):
    """Represents the mutable state passed between nodes in the graph."""

    query: str
    user_id: str
    project_id: Optional[str]
    top_k: int

    raw_chunks: list[dict]
    context_text: str

    needs_more_research: bool

    reasoning_trace: Annotated[list[str], operator.add]
    messages: Annotated[list[BaseMessage], add_messages]
    final_answer: str


def _extract_reasoning(message: BaseMessage) -> str:
    """Extracts reasoning traces from a message (handles DeepSeek, Anthropic, and standard LLM text)."""
    chunks = []
    
    # Anthropic-style reasoning blocks
    if hasattr(message, "content_blocks") and isinstance(message.content_blocks, list):
        for block in message.content_blocks:
            if isinstance(block, dict) and block.get("type") == "reasoning":
                chunks.append(block.get("reasoning", ""))
                
    # DeepSeek-style reasoning (via LiteLLM)
    rc = message.additional_kwargs.get("reasoning_content")
    if rc:
        chunks.append(rc)
        
    # Standard text content (since reasoning_node's textual output is inherently its thought process)
    if not chunks and message.content:
        if isinstance(message.content, str):
            chunks.append(message.content)
        elif isinstance(message.content, list):
            for block in message.content:
                if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                    chunks.append(block["text"])
                    
    return "\n\n".join(chunks).strip()
