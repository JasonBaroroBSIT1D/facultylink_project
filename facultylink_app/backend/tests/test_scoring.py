from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from ocr import configure_tesseract, extract_text
from kra_config import (
    final_score,
    resolve_rank_band,
    weighted_final_score,
    weights_for_rank,
)
from scoring import classify_kra, contribution_score, file_hash, process_upload, score_indicator


def test_classify_research_from_journal_keywords():
    kra, ambiguous = classify_kra("Peer-reviewed journal article ISSN 2244-1180")
    assert kra == "research"
    assert ambiguous is False


def test_classify_falls_back_when_unclear():
    kra, flagged = classify_kra("Untitled scan", fallback="instruction")
    assert kra == "instruction"
    assert flagged is False


def test_contribution_score_divides_by_author_count():
    assert contribution_score(10, 2) == 5
    assert contribution_score(8, 1) == 8


def test_final_score_matches_web_formula():
    # Final Score = Base Points × Contribution Percentage
    assert final_score(10, 60) == 6
    assert final_score(80, 70) == 56
    assert final_score(10, 50) == 5


def test_table_22_assoc_professor_weights():
    assert resolve_rank_band("Associate Professor III") == "Assoc. Professor"
    band, weights = weights_for_rank({}, "Associate Professor III")
    assert band == "Assoc. Professor"
    assert weights == {
        "instruction": 40,
        "research": 30,
        "extension": 20,
        "professionalDevelopment": 10,
    }
    # Example: 85, 70, 60, 50 → 34 + 21 + 12 + 5 = 72
    score = weighted_final_score(
        {
            "instruction": 85,
            "research": 70,
            "extension": 60,
            "professionalDevelopment": 50,
        },
        weights,
    )
    assert score == 72.0


def test_table_22_instructor_weights():
    band, weights = weights_for_rank({}, "Instructor I")
    assert band == "Instructor"
    assert weights["instruction"] == 60
    assert weights["research"] == 10



def test_duplicate_file_hash_matches_same_bytes(tmp_path: Path):
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("faculty evidence", encoding="utf-8")
    second.write_text("faculty evidence", encoding="utf-8")
    assert file_hash(str(first)) == file_hash(str(second))


def test_indicator_score_uses_declared_share_and_cap():
    shared = score_indicator(
        "kra2-a-journal-co",
        contribution_percent=40,
        rating=None,
        authors=2,
    )
    assert shared["base_points"] == 50
    assert shared["points"] == 20

    poetry = score_indicator(
        "kra2-c-poetry",
        contribution_percent=100,
        rating=None,
        authors=1,
    )
    assert poetry["points"] == 2
    assert poetry["max_points"] == 2


def test_indicator_rating_formula():
    scored = score_indicator(
        "kra1-a-student",
        contribution_percent=None,
        rating=80,
        authors=1,
    )
    assert scored["points"] == 28.8


def test_process_upload_uses_indicator_points():
    result = process_upload(
        title="Algebra textbook",
        author="Maria Santos",
        file_path=None,
        declared_kra="instruction",
        indicator_id="kra1-b-textbook-sole",
        contribution_percent=100,
    )
    assert result["status"] == "pendingReview"
    assert result["base_points"] == 30
    assert result["points"] == 0
    assert float(result["extracted_info"]["Provisional score"]) == 30


def test_process_upload_flags_missing_title():
    result = process_upload(title="", author="", file_path=None, declared_kra="instruction")
    assert result["flagged_for_review"] is True
    assert result["status"] == "pendingReview"
    assert result["kra"] == "instruction"
    assert result["points"] == 0


@pytest.mark.skipif(not configure_tesseract(), reason="Tesseract is not installed")
def test_ocr_reads_journal_keywords_from_image(tmp_path: Path):
    image_path = tmp_path / "journal.png"
    canvas = Image.new("RGB", (900, 240), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    draw.text((30, 90), "Journal article ISSN 2244-1180", fill="black", font=font)
    canvas.save(image_path)

    text = extract_text(str(image_path))
    assert "journal" in text.lower() or "issn" in text.lower()
    result = process_upload(
        title="Scanned publication",
        author="Maria Santos",
        file_path=str(image_path),
        declared_kra="instruction",
    )
    assert result["kra"] == "research"
    assert "OCR excerpt" in result["extracted_info"]
