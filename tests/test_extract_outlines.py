from bnm_compliance_assistant.ingestion.extract_outlines import classify_outline_title


def test_classify_clause_outline_title() -> None:
    result = classify_outline_title("14A.9.14 Reporting institutions are required to take measures")

    assert result["entry_type"] == "clause"
    assert result["clause"] == "14A.9.14"
    assert result["section"] == "14A"


def test_classify_appendix_outline_title() -> None:
    result = classify_outline_title("APPENDIX 4a For Banking and Deposit-Taking Institutions")

    assert result["entry_type"] == "appendix"
    assert result["appendix"] == "APPENDIX 4A"
