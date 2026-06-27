"""Utility module for parsing inline citations from assistant responses."""
import re
from dataclasses import dataclass

@dataclass
class Citation:
    """Represents a single parsed document citation."""
    source_num:        int
    page_number:       int | None
    layout_element_id: str | None
    element_type:      str | None


def extract_citations(response_text: str) -> list[Citation]:
    """
    Parse the **References** block from agent response into structured citations.
    Matches lines like:
      [SOURCE 1] Page 4 | Element ID: uuid-abc | Type: text
    """
    pattern = re.compile(
        r'\[SOURCE (\d+)\]\s+Page (\d+)\s*\|\s*Element ID:\s*(\S+)\s*\|\s*Type:\s*(\S+)',
        re.IGNORECASE
    )
    citations = []
    for match in pattern.finditer(response_text):
        citations.append(Citation(
            source_num=        int(match.group(1)),
            page_number=       int(match.group(2)),
            layout_element_id= match.group(3),
            element_type=      match.group(4),
        ))
    return citations