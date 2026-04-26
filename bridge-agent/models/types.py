"""
models/types.py
---------------
Primitive types and shared utilities reused across the models package.
"""

from typing import Literal

# The three possible outcomes the agent can assign to a Teams message.
ActionType = Literal["CREATE", "UPDATE", "SKIP"]


def format_arr(arr: int | None) -> str:
    """
    Format an ARR integer as a human-readable display string.

    Examples
    --------
    >>> format_arr(520000)
    '$520k ARR'
    >>> format_arr(1250000)
    '$1.2m ARR'
    >>> format_arr(None)
    'Unknown ARR'
    """
    if arr is None:
        return "Unknown ARR"
    if arr >= 1_000_000:
        return f"${arr / 1_000_000:.1f}m ARR"
    if arr >= 1_000:
        return f"${arr // 1_000}k ARR"
    return f"${arr} ARR"
