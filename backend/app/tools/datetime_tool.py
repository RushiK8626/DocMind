"""Module datetime_tool.py."""
from datetime import datetime
from langchain_core.tools import tool
from pydantic import BaseModel


class DatetimeInput(BaseModel):
    """Empty input schema for datetime tool."""
    pass


def create_datetime_tool():
    """Returns a tool that provides the current local date and time."""

    @tool("get_current_datetime", args_schema=DatetimeInput)
    def get_current_datetime() -> str:
        """
        Returns the current local date and time. Use this to determine relative dates (e.g., 'this year', 'today').
        """
        now = datetime.now()
        return f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"

    return get_current_datetime
