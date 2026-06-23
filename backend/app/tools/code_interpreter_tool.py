"""Module code_interpreter_tool.py."""
import logging
import subprocess
import sys
import textwrap

from langchain_core.tools import tool
from pydantic import BaseModel, Field


logger = logging.getLogger('app')


_BLOCKED_PATTERNS = [
    "import os",
    "import sys",
    "import subprocess",
    "import shutil",
    "__import__",
    "open(",
    "exec(",
    "eval(",
    "compile(",
    "importlib",
    "socket",
    "requests",
    "urllib",
]


class CodeInterpreterInput(BaseModel):
    """CodeInterpreterInput class."""

    code: str = Field(
        ...,
        description=(
            "Valid Python 3 code to execute. "
            "Only print() output is captured. "
            "No file I/O or network access allowed."
        ),
    )


def create_code_interpreter_tool():
    """create_code_interpreter_tool function."""

    @tool("code_interpreter", args_schema=CodeInterpreterInput)
    def code_interpreter(code: str) -> str:
        """
        Executes Python 3 code in a sandboxed environment.
        """

        for pattern in _BLOCKED_PATTERNS:
            if pattern in code:
                return f"❌ Blocked: '{pattern}' is not allowed in sandboxed execution."

        code = textwrap.dedent(code).strip()

        from flask import current_app

        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=current_app.config["CODE_EXEC_TIMEOUT"],
            )
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()

            if proc.returncode != 0:
                return f"❌ Execution error:\n{stderr or 'Unknown error'}"

            if not stdout and not stderr:
                return "✅ Code executed successfully but produced no output (use print() to see results)."

            result = stdout
            if stderr:
                result += f"\n⚠️ Stderr:\n{stderr}"

            logger.debug(f"Code executed OK — {len(stdout)} chars output")
            return result

        except subprocess.TimeoutExpired:
            return f"❌ Execution timed out after {current_app.config['CODE_EXEC_TIMEOUT']}s."
        except Exception as e:
            logger.error(f"Code interpreter error: {e}")
            return f"❌ Unexpected error: {str(e)}"

    return code_interpreter
