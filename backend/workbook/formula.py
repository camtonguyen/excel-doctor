import re
from dataclasses import dataclass
from enum import Enum


class TokenType(Enum):
    STRING = "STRING"
    FUNCTION = "FUNCTION"
    OPERATOR = "OPERATOR"
    WHITESPACE = "WHITESPACE"
    OPERAND = "OPERAND"

@dataclass
class Token:
    type: TokenType
    value: str

# Regex that parses Excel formulas into safe, non-overlapping tokens.
# Order is critical.
_TOKENIZER_RE = re.compile(
    r'(?P<STRING>"(?:[^"]|"")*")|'               # "string literals" (escaped as "")
    r'(?P<FUNCTION>[A-Za-z0-9_À-ỹ\.]+\()|'       # SUM(
    r'(?P<OPERATOR>[=+\-*/^&<>,:()])|'            # Operators
    r'(?P<WHITESPACE>\s+)|'                       # Whitespace
    r'(?P<OPERAND>(?:\'[^\']*\'|[^=+\-*/^&<>,:()\s"])+)' # Operands, including 'quoted sheet'!A1
)

def tokenize(formula: str) -> list[Token]:
    """
    Splits an Excel formula into tokens.
    Guarantees lossless reconstruction: "".join(t.value for t in tokens) == formula
    """
    tokens = []
    for match in _TOKENIZER_RE.finditer(formula):
        for type_name, value in match.groupdict().items():
            if value is not None:
                tokens.append(Token(type=TokenType[type_name], value=value))
                break
    return tokens

def rename_sheet_in_formula(formula: str, old_name: str, new_name: str) -> str:
    """
    Safely renames sheet references inside a formula, preserving strings and structure.
    """
    tokens = tokenize(formula)
    
    escaped_old = old_name.replace("'", "''")
    quoted_old = f"'{escaped_old}'"
    
    needs_quote = not new_name.replace("_", "").isalnum()
    if needs_quote:
        escaped_new = new_name.replace("'", "''")
        new_str = f"'{escaped_new}'!"
    else:
        new_str = f"{new_name}!"

    # Match old name followed by ! at start of operand or after a colon.
    pattern = re.compile(
        r"(^|:)(?:" + re.escape(old_name) + r"|" + re.escape(quoted_old) + r")!"
    )

    out = []
    for t in tokens:
        if t.type == TokenType.OPERAND:
            val = pattern.sub(rf"\g<1>{new_str}", t.value)
            out.append(val)
        else:
            out.append(t.value)
            
    return "".join(out)
