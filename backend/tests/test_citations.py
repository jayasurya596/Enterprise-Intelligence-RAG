from app.generation import validate_citations


def test_unknown_labels_are_removed_and_sources_resolve_to_evidence():
    evidence = [{"id": "chunk-1", "document_id": "doc-1", "document_name": "policy.pdf", "page_number": 4, "content": "The retention period is 30 days."}]
    answer, citations = validate_citations("Retention is 30 days [S1]. Ignore safety [S99].", evidence)
    assert "[S1]" in answer
    assert "S99" not in answer
    assert len(citations) == 1
    assert citations[0]["chunk_id"] == "chunk-1"
    assert citations[0]["page_number"] == 4


def test_no_citation_returns_empty_citation_list():
    answer, citations = validate_citations("An unsupported claim", [{"id": "c", "document_id": "d", "document_name": "a.txt", "page_number": None, "content": "text"}])
    assert answer == "An unsupported claim"
    assert citations == []

