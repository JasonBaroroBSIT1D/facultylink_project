from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from ocr import configure_tesseract, extract_text
from kra_config import final_score
from scoring import classify_kra, contribution_score, file_hash, process_upload


def test_classify_research_from_journal_keywords():
    kra, ambiguous = classify_kra("Peer-reviewed journal article ISSN 2244-1180")
    assert kra == "research"
    assert ambiguous is False


def test_classify_falls_back_when_unclear():
    kra, flagged = classify_kra("Untitled scan", fallback="instruction")
    assert kra == "instruction"
    assert flagged is True


def test_contribution_score_divides_by_author_count():
    assert contribution_score(10, 2) == 5
    assert contribution_score(8, 1) == 8


def test_final_score_matches_web_formula():
    # Final Score = Base Points × Contribution Percentage
    assert final_score(10, 60) == 6
    assert final_score(80, 70) == 56
    assert final_score(10, 50) == 5


def test_duplicate_file_hash_matches_same_bytes(tmp_path: Path):
    first = tmp_path / "a.txt"
    second = tmp_path / "b.txt"
    first.write_text("faculty evidence", encoding="utf-8")
    second.write_text("faculty evidence", encoding="utf-8")
    assert file_hash(str(first)) == file_hash(str(second))


def test_process_upload_flags_missing_author():
    result = process_upload(title="Course syllabus", author="", file_path=None, declared_kra="instruction")
    assert result["flagged_for_review"] is True
    assert result["status"] == "pendingReview"
    assert result["kra"] == "instruction"


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
