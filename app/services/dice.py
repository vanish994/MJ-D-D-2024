"""Raw bounded dice utility from the MVP specification.

The turn pipeline does not call this function: the external Rule Engine remains
the authority for campaign mechanics and resolved outcomes.
"""

import re
import secrets
from typing import Callable


DICE_RE = re.compile(
    r"^\s*(?P<n>\d*)d(?P<sides>\d+)(?P<sign>[+-])?(?P<mod>\d+)?\s*$",
    re.IGNORECASE,
)
MAX_DICE = 100
MAX_SIDES = 1000
MAX_MODIFIER = 100_000


def roll(formula: str, *, randbelow: Callable[[int], int] | None = None) -> dict:
    if not isinstance(formula, str) or len(formula) > 50:
        raise ValueError("formula must be a string of at most 50 characters")
    match = DICE_RE.fullmatch(formula)
    if not match:
        raise ValueError("invalid dice formula; use NdS with an optional +N or -N")

    count = int(match.group("n") or "1")
    sides = int(match.group("sides"))
    modifier = int(match.group("mod") or "0")
    if match.group("sign") == "-":
        modifier = -modifier
    if not 1 <= count <= MAX_DICE or not 2 <= sides <= MAX_SIDES:
        raise ValueError("dice limits exceeded")
    if abs(modifier) > MAX_MODIFIER:
        raise ValueError("modifier limit exceeded")

    random_below = randbelow or secrets.randbelow
    results = []
    for _ in range(count):
        value = random_below(sides)
        if not isinstance(value, int) or not 0 <= value < sides:
            raise RuntimeError("random source returned a value outside its requested range")
        results.append(value + 1)

    normalized = f"{count}d{sides}"
    if modifier > 0:
        normalized += f"+{modifier}"
    elif modifier < 0:
        normalized += str(modifier)
    return {
        "formula": normalized,
        "dice": [{"sides": sides, "result": result} for result in results],
        "modifier": modifier,
        "total": sum(results) + modifier,
    }
