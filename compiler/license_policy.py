"""Select an offered Cargo license alternative; this is not a license clearance.

Unknown terms stay unresolved. AND obligations are retained. This policy is used
for review reports, never to rewrite upstream licenses or notices.
"""

import re

PREFERENCE = {
    name: rank for rank, name in enumerate((
        "MIT", "ISC", "0BSD", "BSD-2-Clause", "BSD-3-Clause", "MIT-0", "Zlib",
        "Apache-2.0", "BSL-1.0", "Unicode-3.0", "Unicode-DFS-2016", "NCSA",
        "CC0-1.0", "Unlicense", "CDLA-Permissive-2.0", "WTFPL",
        "Apache-2.0 WITH LLVM-exception", "MPL-2.0",
    ))
}
LEGACY = {"MIT/Apache-2.0", "Apache-2.0/MIT", "Unlicense/MIT", "MIT / Apache-2.0", "Apache-2.0 / MIT"}


def select_license(expression):
    """Return selected offered terms, or None if the expression needs review."""
    if not isinstance(expression, str) or not expression.strip():
        return None
    if expression in LEGACY:
        expression = expression.replace("/", " OR ")
    tokens = re.findall(r"\(|\)|[A-Za-z0-9.+:-]+", expression)
    if "".join(tokens) != re.sub(r"\s+", "", expression):
        return None
    position = 0

    def consume(value):
        nonlocal position
        if position < len(tokens) and tokens[position] == value:
            position += 1
            return True
        return False

    def atom():
        nonlocal position
        if consume("("):
            result = either()
            if not consume(")"):
                raise ValueError("Unclosed license expression")
            return result
        if position >= len(tokens) or tokens[position] in {"AND", "OR", "WITH", ")"}:
            raise ValueError("Expected license identifier")
        value = tokens[position]
        position += 1
        if consume("WITH"):
            if position >= len(tokens) or tokens[position] in {"AND", "OR", "WITH", "(", ")"}:
                raise ValueError("Expected license exception")
            value += " WITH " + tokens[position]
            position += 1
        return (value,) if value in PREFERENCE else None

    def both():
        result = atom()
        while consume("AND"):
            other = atom()
            result = tuple(dict.fromkeys((*result, *other))) if result is not None and other is not None else None
        return result

    def either():
        result = both()
        while consume("OR"):
            other = both()
            choices = [choice for choice in (result, other) if choice is not None]
            result = min(choices, key=lambda choice: (max(PREFERENCE[term] for term in choice), len(choice))) if choices else None
        return result

    try:
        selected = either()
        if position != len(tokens) or selected is None:
            return None
        return " AND ".join(selected)
    except ValueError:
        return None
