"""Module web_search_tool.py."""
import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger('app')


class WebSearchInput(BaseModel):
    """WebSearchInput class."""

    query: str = Field(..., description="The search query to look up on the web.")


def create_web_search_tool():
    """create_web_search_tool function."""

    @tool("web_search", args_schema=WebSearchInput)
    def web_search(query: str) -> str:
        """
        Searches the web for a query and returns results.
        """
        from flask import current_app

        api_key = current_app.config["SERPAPI_KEY"]
        max_results = current_app.config.get("WEB_SEARCH_MAX_RESULTS", 5)
        max_results = max(1, min(max_results, 10))

        try:
            from serpapi import GoogleSearch
        except ImportError:
            return "❌ google-search-results not installed. Run: pip install google-search-results"

        try:
            search = GoogleSearch(
                {
                    "q": query,
                    "num": max_results,
                    "api_key": api_key,
                }
            )
            data = search.get_dict()
            results = data.get("organic_results", [])
        except Exception as e:
            logger.error(f"SerpAPI search failed: {e}")
            return f"Web search failed: {str(e)}"

        if not results:
            return f"No web results found for: '{query}'"

        formatted = []
        for i, r in enumerate(results[:max_results], 1):
            formatted.append(
                f"[Result {i}]\n"
                f"Title:   {r.get('title',   'N/A')}\n"
                f"URL:     {r.get('link',    'N/A')}\n"
                f"Snippet: {r.get('snippet', 'N/A')}"
            )

        result = f"Google search results for '{query}':\n\n" + "\n\n---\n\n".join(
            formatted
        )
        logger.debug(f"WebSearchTool returned {len(results)} results for: '{query}'")
        return result

    return web_search
