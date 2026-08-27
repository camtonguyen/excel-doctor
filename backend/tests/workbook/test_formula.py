from backend.workbook.formula import TokenType, rename_sheet_in_formula, tokenize


def test_tokenize_simple_reference():
    tokens = tokenize("=A1+B1")
    assert len(tokens) == 4
    assert tokens[0].type == TokenType.OPERATOR
    assert tokens[0].value == "="
    assert tokens[1].type == TokenType.OPERAND
    assert tokens[1].value == "A1"
    assert tokens[2].type == TokenType.OPERATOR
    assert tokens[2].value == "+"
    assert tokens[3].type == TokenType.OPERAND
    assert tokens[3].value == "B1"

def test_tokenize_missing_equals_prefix():
    # As per Trap 3, JS libraries might strip leading =
    # We should normalize and handle it. We can assume if it's passed here it's formula content.
    tokens = tokenize("SUM(A1:A10)")
    assert "".join(t.value for t in tokens) == "SUM(A1:A10)"
    assert tokens[0].type == TokenType.FUNCTION
    assert tokens[0].value == "SUM("

def test_tokenize_vietnamese_sheet_name_unquoted():
    # Actually, if a sheet name has spaces or non-alphanumeric, Excel quotes it.
    # Unquoted sheet names are usually simple alphanumeric, but we should test standard ones.
    tokens = tokenize("Sheet1!A1")
    assert len(tokens) == 1
    assert tokens[0].type == TokenType.OPERAND
    assert tokens[0].value == "Sheet1!A1"

def test_tokenize_vietnamese_sheet_name_quoted():
    # Trap 8: Quoted sheet names
    tokens = tokenize("='Báo cáo tháng 10'!A1")
    # Lossless reconstruction
    assert "".join(t.value for t in tokens) == "='Báo cáo tháng 10'!A1"
    
    assert tokens[1].type == TokenType.OPERAND
    assert tokens[1].value == "'Báo cáo tháng 10'!A1"

def test_tokenize_string_literal_with_comma():
    # Trap 8: String literal containing comma and sheet-like names
    tokens = tokenize('=SUMIF(A:A, "nl_MUỐI,", B:B)')
    
    # Check that "nl_MUỐI," is a single string literal token
    string_tokens = [t for t in tokens if t.type == TokenType.STRING]
    assert len(string_tokens) == 1
    assert string_tokens[0].value == '"nl_MUỐI,"'

def test_tokenize_escaped_quotes_in_string():
    # Excel escapes double quotes inside strings by doubling them
    tokens = tokenize('="He said ""hello"""')
    assert tokens[1].type == TokenType.STRING
    assert tokens[1].value == '"He said ""hello"""'

def test_lossless_reconstruction():
    formulas = [
        "=A1+B1",
        "SUM(A1:A10)",
        "='Báo cáo tháng 10'!A1",
        '=SUMIF(A:A, "nl_MUỐI,", B:B)',
        '="He said ""hello"""',
        "=IF(A1>0, A1*2, \"Zero\")"
    ]
    for f in formulas:
        tokens = tokenize(f)
        assert "".join(t.value for t in tokens) == f, f"Lossless check failed for: {f}"

def test_rename_sheet_in_formula_unquoted():
    f = "=Sheet1!A1 + Sheet1!B2"
    assert rename_sheet_in_formula(f, "Sheet1", "NewSheet") == "=NewSheet!A1 + NewSheet!B2"

def test_rename_sheet_in_formula_quoted_old():
    f = "='Báo cáo tháng 10'!A1"
    assert rename_sheet_in_formula(f, "Báo cáo tháng 10", "Report") == "=Report!A1"

def test_rename_sheet_in_formula_needs_quotes_new():
    f = "=Sheet1!A1"
    assert rename_sheet_in_formula(f, "Sheet1", "My Sheet") == "='My Sheet'!A1"

def test_rename_sheet_in_formula_quotes_numeric_new_name():
    # A purely numeric sheet name must be quoted, or Excel can't parse the reference.
    f = "=Sheet1!A1"
    assert rename_sheet_in_formula(f, "Sheet1", "123") == "='123'!A1"

def test_rename_sheet_in_formula_with_apostrophe():
    f = "='A''B'!A1"
    assert rename_sheet_in_formula(f, "A'B", "AB") == "=AB!A1"

def test_rename_sheet_in_formula_leaves_strings_alone():
    f = '=SUMIF(A:A, "Sheet1!A1", Sheet1!B:B)'
    assert rename_sheet_in_formula(f, "Sheet1", "Sheet2") == '=SUMIF(A:A, "Sheet1!A1", Sheet2!B:B)'

def test_rename_sheet_in_formula_range():
    f = "=Sheet1!A1:Sheet1!B2"
    assert rename_sheet_in_formula(f, "Sheet1", "S2") == "=S2!A1:S2!B2"

def test_rename_sheet_in_formula_ignores_other_sheets():
    f = "=OtherSheet!A1 + Sheet1!B1"
    assert rename_sheet_in_formula(f, "Sheet1", "S2") == "=OtherSheet!A1 + S2!B1"
