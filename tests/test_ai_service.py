"""
Unit tests for Strategic AI RFQ Parsing & Executive Synthesis
"""
import pytest
from src.ai_service import AIService
from src.matching_engine import MatchingEngine
from src.data_pipeline import get_pipeline
from src.models import BuyerRequirement

@pytest.fixture(scope="module")
def ai():
    return AIService()

def test_nlp_rfq_parsing_german_scenario(ai):
    text = (
        "A buyer in Germany is looking for aluminium parts, machined to order, "
        "in batches of a few thousand over time. Quality certification matters to them, "
        "and so does how soon the parts arrive (say within 6 weeks)."
    )

    req = ai.parse_natural_language_rfq(text)
    assert req.material == "aluminium"
    assert req.process in ["CNC milling", "CNC turning"]
    assert req.quantity in [2000, 3000]
    assert req.timeline_weeks == 6
    assert req.destination_country == "Germany"

def test_nlp_rfq_parsing_stainless_sheet_metal(ai):
    text = "We need 1,500 stainless sheet-metal components with ISO 9001 certification within 6 weeks for assembly."
    req = ai.parse_natural_language_rfq(text)
    assert req.material == "stainless steel"
    assert req.process == "sheet metal"
    assert req.quantity == 1500
    assert req.timeline_weeks == 6
    assert "ISO 9001" in req.required_certifications

def test_executive_pitch_synthesis(ai):
    pipe = get_pipeline()
    records = pipe.load_and_sanitize()
    engine = MatchingEngine(records)

    req = BuyerRequirement(
        material="aluminium",
        process="CNC milling",
        quantity=2000,
        timeline_weeks=6,
        required_certifications=["ISO 9001"],
        destination_country="Germany"
    )

    res = engine.match(req, top_k=1)
    assert len(res.matches) == 1
    top = res.matches[0]

    pitch = ai.generate_executive_pitch(top, req)
    assert "Executive Match Justification" in pitch
    assert top.manufacturer.name in pitch
    assert "Germany" in pitch
    assert str(top.score_breakdown.total_score) in pitch
