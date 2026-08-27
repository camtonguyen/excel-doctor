from pathlib import Path

from backend.audit.base import registry
from backend.audit.rules_formula import RuleR01, RuleR02, RuleR03, RuleR04, RuleR05
from backend.workbook.reader import read_workbook


def test_sokho_google_rules():
    fixture_path = Path(__file__).parent.parent.parent.parent / "fixtures" / "sokho_google.xlsx"
    wb = read_workbook(fixture_path)
    
    # R01: A2 formula contains #REF!
    r01 = RuleR01()
    findings_r01 = r01.detect(wb)
    assert len(findings_r01) == 1
    assert findings_r01[0].ref == "A2"
    assert findings_r01[0].rule_id == "R01"

    # R02: A2 (t="e") evaluates to error, B1 (v="#VALUE!") evaluates to error, A3 (v="#REF!")
    r02 = RuleR02()
    findings_r02 = r02.detect(wb)
    assert len(findings_r02) == 3
    refs = {f.ref for f in findings_r02}
    assert refs == {"A2", "B1", "A3"}
    
    # R03: B2 has t="s" and points to shared string #REF! (idx 0)
    r03 = RuleR03()
    findings_r03 = r03.detect(wb)
    assert len(findings_r03) == 1
    assert findings_r03[0].ref == "B2"
    
    # R04: B1 has formula A1*2, and A1 has t="str" v=""
    r04 = RuleR04()
    findings_r04 = r04.detect(wb)
    assert len(findings_r04) == 2
    refs_r04 = {f.ref for f in findings_r04}
    assert refs_r04 == {"B1", "A2"}
    
    # R05: A3 references 'Missing Sheet'
    r05 = RuleR05()
    findings_r05 = r05.detect(wb)
    assert len(findings_r05) == 1
    assert findings_r05[0].ref == "A3"
    
    # Registry test
    all_rules = registry.get_all()
    assert len(all_rules) >= 5
