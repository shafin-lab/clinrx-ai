from app.services.retrieval_service import search_knowledge


def test_search_by_query():
    results = search_knowledge(query="Metabolic")

    assert len(results) == 1
    assert results[0].knowledge_id == "NUT-STATE-002"


def test_filter_by_status():
    results = search_knowledge(status="Approved")

    assert len(results) == 1
    assert results[0].knowledge_id == "NUT-STATE-002"


def test_filter_by_domain():
    results = search_knowledge(domain="Nutrition & Metabolism")

    assert len(results) == 2


def test_filter_by_object_class():
    results = search_knowledge(object_class="Clinical State")

    assert len(results) == 2


def test_combined_filters():
    results = search_knowledge(
        domain="Nutrition & Metabolism",
        status="Approved",
    )

    assert len(results) == 1
    assert results[0].knowledge_id == "NUT-STATE-002"


def test_search_with_no_results():
    results = search_knowledge(query="Cardiology")

    assert results == []


def test_ranking_by_title_match():
    results = search_knowledge(query="Nutrition")

    assert len(results) == 2
    assert results[0].knowledge_id == "NUT-STATE-001"


def test_ranking_by_exact_title():
    results = search_knowledge(query="Metabolic State")

    assert len(results) == 1
    assert results[0].knowledge_id == "NUT-STATE-002"
    