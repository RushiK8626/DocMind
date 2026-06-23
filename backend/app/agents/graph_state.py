"""Module graph_state.py."""
import operator
from typing import Annotated, Sequence, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class PipelineState(TypedDict):
    """PipelineState class."""

    query: str
    user_id: str
    project_id: Optional[str]
    top_k: int

    raw_chunks: list[dict]
    context_text: str

    needs_more_research: bool

    reasoning_trace: Annotated[list[str], operator.add]
    messages: Annotated[Sequence[BaseMessage], add_messages]
    final_answer: str


def _extract_reasoning(message: BaseMessage) -> str:
    """_extract_reasoning function."""
    chunks = []
    for block in message.content_blocks:
        if block.get("type") == "reasoning":
            chunks.append(block.get("reasoning", ""))
    if not chunks:

        rc = message.additional_kwargs.get("reasoning_content")
        if rc:
            chunks.append(rc)
    return "\n".join(chunks)
