"""Module answer_node.py."""
from app.agents.llm import build_llm


def make_answer_node(config):
    """make_answer_node function."""
    llm = build_llm(config, temperature=0.3)

    def answer_node(state):
        """answer_node function."""
        background_parts = []
        for msg in state.get("messages", []):
            if msg.type == "tool":
                background_parts.append(f"[Tool Output]:\n{msg.content}")
            elif msg.type == "ai" and msg.content:
                background_parts.append(f"[Analyst Reasoning]:\n{msg.content}")

        for trace in state.get("reasoning_trace", []):
            if trace:
                background_parts.append(f"[Internal Trace]:\n{trace}")

        background = "\n\n".join(background_parts)

        prompt = (
            f"User query: '{state['query']}'\n\n"
            f"Background (do not mention these labels):\n"
            f"{background}\n\n"
            "Write a direct, natural answer based on the background information."
        )
        result = llm.invoke(prompt)
        return {"final_answer": result.content}

    return answer_node
