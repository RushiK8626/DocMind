"""Module llm.py."""
from langchain_groq import ChatGroq


def build_llm(config, temperature=0.2):
    """build_llm function."""
    return ChatGroq(
        model=config["LLM_MODEL"],
        api_key=config["LLM_API_KEY"],
        temperature=temperature,
        max_tokens=config["LLM_MAX_TOKENS"],
    )
