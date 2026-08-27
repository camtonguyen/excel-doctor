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
