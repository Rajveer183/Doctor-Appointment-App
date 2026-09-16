from app.services import symptom_match


async def test_emergency_standalone_keyword_short_circuits():
    result = await symptom_match.match_symptom("my friend is unconscious and not responding")
    assert result.emergency is True
    assert result.source == "emergency"
    assert result.specialty is None


async def test_compound_emergency_rule_requires_all_groups():
    # "chest pain" alone must NOT trigger the emergency path — it's too common on its
    # own (could be a muscle strain) and should just route to Cardiology instead. Only
    # chest pain + breathing difficulty together is the emergency signal.
    alone = await symptom_match.match_symptom("chest pain")
    assert alone.emergency is False
    assert alone.specialty == "Cardiology"
    assert alone.source == "exact"

    combined = await symptom_match.match_symptom("I have chest pain and I can't breathe")
    assert combined.emergency is True


async def test_exact_fuzzy_layer_matches_taxonomy_phrase():
    result = await symptom_match.match_symptom("skin rash")
    assert result.emergency is False
    assert result.source == "exact"
    assert result.specialty == "Dermatology"


async def test_fuzzy_layer_rejects_unrelated_free_text():
    # Regression test: WRatio previously scored this 85.5 against "pain after a fall"
    # purely from partial-substring overlap. token_set_ratio must reject it.
    result = await symptom_match.match_symptom("my toenail feels weird lately after gardening")
    assert result.source != "exact"


async def test_embedding_fallback_used_when_fuzzy_finds_nothing(monkeypatch):
    async def fake_embed(texts, input_type):
        assert input_type == "query"
        return [[0.1, 0.2, 0.3]]

    class FakeCollection:
        def count(self):
            return 10

        def query(self, query_embeddings, n_results):
            return {
                "ids": [["orthopedics-3"]],
                "distances": [[0.3]],  # similarity = 1 - 0.3 = 0.7, clears the 0.45 threshold
                "metadatas": [[{"phrase": "back pain", "specialty": "Orthopedics"}]],
            }

    monkeypatch.setattr(symptom_match, "embed", fake_embed)
    monkeypatch.setattr(symptom_match, "get_taxonomy_collection", lambda: FakeCollection())

    result = await symptom_match.match_symptom("a completely unrecognizable paraphrase nobody typed before")
    assert result.source == "embedding"
    assert result.specialty == "Orthopedics"


async def test_embedding_below_threshold_falls_through_to_no_match(monkeypatch):
    async def fake_embed(texts, input_type):
        return [[0.1, 0.2, 0.3]]

    class FakeCollection:
        def count(self):
            return 10

        def query(self, query_embeddings, n_results):
            return {
                "ids": [["orthopedics-3"]],
                "distances": [[0.9]],  # similarity = 0.1, well under threshold
                "metadatas": [[{"phrase": "back pain", "specialty": "Orthopedics"}]],
            }

    monkeypatch.setattr(symptom_match, "embed", fake_embed)
    monkeypatch.setattr(symptom_match, "get_taxonomy_collection", lambda: FakeCollection())

    result = await symptom_match.match_symptom("a completely unrecognizable paraphrase nobody typed before")
    assert result.source == "none"
    assert result.specialty is None


async def test_no_match_when_embedding_api_unavailable(monkeypatch):
    async def failing_embed(texts, input_type):
        raise symptom_match.NvidiaAPIError("no API key configured")

    monkeypatch.setattr(symptom_match, "embed", failing_embed)

    result = await symptom_match.match_symptom("what is the capital of France")
    assert result.emergency is False
    assert result.source == "none"
    assert result.specialty is None
    assert result.message
