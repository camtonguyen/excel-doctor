from typing import Literal

from backend.model import CellEdit, Finding


class Rule:
    """Base class for all audit rules."""
    id: str
    title: str
    why: str
    severity: Literal["error", "warning", "style"]
    risk: Literal["safe", "display", "value"]
    auto_fixable: bool

    def detect(self, wb) -> list[Finding]:
        """Scans the workbook and returns a list of Findings."""
        raise NotImplementedError

    def fix(self, wb, finding: Finding) -> list[CellEdit]:
        """Returns the edits required to fix the finding."""
        raise NotImplementedError

class RuleRegistry:
    def __init__(self):
        self.rules: dict[str, Rule] = {}

    def register(self, rule: Rule):
        self.rules[rule.id] = rule

    def get_all(self) -> list[Rule]:
        return list(self.rules.values())

registry = RuleRegistry()
