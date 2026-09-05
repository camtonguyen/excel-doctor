import tempfile
from pathlib import Path

import pytest

from backend.audit.base import registry
from backend.model import Edit
from backend.workbook.reader import read_workbook
from backend.workbook.xml_patcher import apply_edits

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"

IDEMPOTENCY_FIXTURES = [
    "whitespace.xlsx",
    "r11_date_serial.xlsx",
    "r08_outlier.xlsx",
    "r09_number_as_text.xlsx",
    "r10_date_as_text.xlsx",
    "r12_bool_percent_text.xlsx",
    "r13_percent_wrong_scale.xlsx",
    "r16_inconsistent_numfmt.xlsx",
]


@pytest.mark.parametrize("fixture_name", IDEMPOTENCY_FIXTURES)
def test_fixture_idempotency(fixture_name: str):
    """
    Spec §7: Idempotency.
    Repair twice in a row; the second run finds nothing to fix and produces a
    byte-comparable file.
    """
    src = FIXTURES_DIR / fixture_name
    assert src.exists(), f"Fixture {fixture_name} not found"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pass1_out = tmp_path / "pass1.xlsx"
        pass2_out = tmp_path / "pass2.xlsx"

        # Pass 1: Scan and fix
        wb1 = read_workbook(src)
        all_rules = registry.get_all()
        findings1 = []
        for r in all_rules:
            findings1.extend(r.detect(wb1))

        # Initial file must have at least one finding
        assert len(findings1) > 0, f"Expected findings in {fixture_name}"

        # Generate edits for auto-fixable rules
        rules_map = {r.id: r for r in all_rules}
        edits1: list[Edit] = []
        for f in findings1:
            rule = rules_map.get(f.rule_id)
            if rule and rule.auto_fixable:
                edits1.extend(rule.fix(wb1, f))

        assert len(edits1) > 0, f"Expected fixable edits for {fixture_name}"
        apply_edits(src, pass1_out, edits1)

        # Pass 2: Scan repaired file
        wb2 = read_workbook(pass1_out)
        findings2 = []
        for r in all_rules:
            findings2.extend(r.detect(wb2))

        # The second run finds nothing to fix (zero auto-fixable findings remain)
        fixable_findings2 = [
            f
            for f in findings2
            if rules_map.get(f.rule_id) and rules_map[f.rule_id].auto_fixable
        ]
        assert len(fixable_findings2) == 0, (
            f"Pass 2 found lingering fixable issues in {fixture_name}: {fixable_findings2}"
        )

        # Generating edits on pass 2 yields 0 edits
        edits2: list[Edit] = []
        for f in findings2:
            rule = rules_map.get(f.rule_id)
            if rule and rule.auto_fixable:
                edits2.extend(rule.fix(wb2, f))

        assert len(edits2) == 0, f"Pass 2 generated edits unexpectedly: {edits2}"

        # Applying pass 2 with 0 edits produces a byte-comparable / identical output
        apply_edits(pass1_out, pass2_out, edits2)
        assert pass1_out.stat().st_size > 0
        assert pass2_out.stat().st_size > 0
        # Files should be byte-identical when 0 edits are applied
        assert pass1_out.read_bytes() == pass2_out.read_bytes()
