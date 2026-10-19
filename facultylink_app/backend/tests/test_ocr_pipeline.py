"""Extraction behaviour for digital PDFs, scans, photos, and field reading."""

import io
import zipfile
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from document_validation import extract_named_parties, extract_rating
from ocr import configure_tesseract, extract_document
from scoring import process_upload

pytestmark_ocr = pytest.mark.skipif(not configure_tesseract(), reason="Tesseract is not installed")

SET_LINES = [
    "SAMPLE STATE UNIVERSITY",
    "Student Evaluation of Teachers (SET) Rating Summary",
    "Faculty Name: Maria Santos",
    "Academic Year: 2024-2025",
    "Overall SET rating: 90",
    "Prepared by: Alex Reyes",
]


def _font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _set_image() -> Image.Image:
    image = Image.new("RGB", (1400, 1800), "white")
    draw = ImageDraw.Draw(image)
    y = 120
    for line in SET_LINES:
        draw.text((80, y), line, fill="black", font=_font(42))
        y += 90
    return image


def _save_image(path: Path, image: Image.Image) -> None:
    image.convert("RGB").save(path)


def _docx(path: Path, lines: list[str]) -> None:
    body = "".join(
        "<w:p><w:r><w:t xml:space=\"preserve\">"
        + line.replace("&", "&amp;").replace("<", "&lt;")
        + "</w:t></w:r></w:p>"
        for line in lines
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("[Content_Types].xml", types)
        package.writestr("_rels/.rels", rels)
        package.writestr("word/document.xml", document)


def _digital_pdf(path: Path) -> None:
    import pymupdf

    pdf = pymupdf.open()
    page = pdf.new_page()
    y = 72
    for line in SET_LINES:
        page.insert_text((72, y), line, fontsize=14)
        y += 28
    pdf.save(path)
    pdf.close()


def _scanned_pdf(path: Path, image: Image.Image) -> None:
    import pymupdf

    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, "JPEG", quality=90)
    pdf = pymupdf.open()
    page = pdf.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=buffer.getvalue())
    pdf.save(path)
    pdf.close()


def _upload(path: Path, *, author="Maria Santos", uploader="Maria Santos"):
    return process_upload(
        title="SET Rating Summary",
        author=author,
        file_path=str(path),
        declared_kra="instruction",
        criterion_id="kra1-a",
        uploader_name=uploader,
    )


def test_rating_ignores_unrelated_numbers():
    assert extract_rating("Attendance rate 85%\nPage 3 of 12\nscore 7") is None
    assert extract_rating("Overall SET rating: 92 percent for AY 2024-2025") == 92
    assert extract_rating("Overall SET rating: 9O") == 90
    assert extract_rating("Overall SET rating\n90.00 / 100") == 90


def test_stacked_faculty_label_beats_the_upload_form_name():
    label, names, from_document = extract_named_parties(
        ocr_text="Student Evaluation of Teachers\nFaculty\nPedro Cruz\nOverall SET rating: 90",
        upload_author="Maria Santos",
        indicator_id="kra1-a-student",
    )
    assert from_document is True
    assert label == "Faculty Name"
    assert names[0] == "Pedro Cruz"


def test_author_without_colon_is_read():
    _label, names, from_document = extract_named_parties(
        ocr_text="Peer-reviewed journal article. Author Maria Santos. Published March 15, 2024.",
        upload_author=None,
        indicator_id="kra2-a-journal-sole",
    )
    assert from_document is True
    assert "Maria Santos" in names[0]


def test_docx_text_is_read_without_ocr(tmp_path: Path):
    path = tmp_path / "certificate.docx"
    _docx(
        path,
        [
            "Certificate of Participation",
            "Participant Name: Jose Reyes",
            "Date: March 10, 2024",
        ],
    )
    extracted = extract_document(str(path))
    assert extracted.source == "docx"
    assert extracted.confidence is None
    assert extracted.reliable is True
    assert "Jose Reyes" in extracted.text
    result = process_upload(
        title="Training certificate",
        author="Jose Reyes",
        file_path=str(path),
        declared_kra="professionalDevelopment",
        criterion_id="kra4-b",
        uploader_name="Jose Reyes",
    )
    assert "Jose Reyes" in result["extracted_info"]["Extracted names"]


def test_legacy_doc_is_not_pretended_readable(tmp_path: Path):
    path = tmp_path / "legacy.doc"
    path.write_bytes(b"\xd0\xcf\x11\xe0 not a real document")
    extracted = extract_document(str(path))
    assert extracted.reliable is False
    assert extracted.text == ""
    assert "DOCX" in extracted.note or "doc" in extracted.note.lower()


def test_digital_pdf_uses_embedded_text(tmp_path: Path):
    path = tmp_path / "digital.pdf"
    _digital_pdf(path)
    extracted = extract_document(str(path))
    assert extracted.source == "embedded"
    assert extracted.confidence is None
    assert "Not applicable" in extracted.confidence_label
    assert "Maria Santos" in extracted.text
    result = _upload(path)
    assert result["status"] == "system_approved"
    assert result["indicator_id"] == "kra1-a-student"
    assert result["extracted_info"]["OCR source"] == "embedded"
    assert result["extracted_info"]["OCR quality"] == "Reliable"


@pytestmark_ocr
def test_scanned_pdf_is_ocr(tmp_path: Path):
    path = tmp_path / "scanned.pdf"
    _scanned_pdf(path, _set_image())
    extracted = extract_document(str(path))
    assert extracted.source == "ocr"
    assert extracted.confidence is not None and extracted.confidence >= 60
    assert "maria santos" in extracted.text.lower()
    result = _upload(path)
    assert result["status"] == "system_approved"
    assert result["extracted_info"]["Name source"] == "Document"


@pytestmark_ocr
def test_sideways_photo_is_turned_upright(tmp_path: Path):
    path = tmp_path / "sideways.png"
    _save_image(path, _set_image().rotate(90, expand=True, fillcolor="white"))
    extracted = extract_document(str(path))
    assert "maria santos" in extracted.text.lower()
    assert extracted.reliable is True
    assert "rotated" in extracted.note


@pytestmark_ocr
def test_exif_portrait_photo_is_read(tmp_path: Path):
    path = tmp_path / "portrait.jpg"
    raw = _set_image().rotate(90, expand=True, fillcolor="white")
    exif = Image.Exif()
    exif[274] = 6
    raw.convert("RGB").save(path, quality=90, exif=exif)
    extracted = extract_document(str(path))
    assert "maria santos" in extracted.text.lower()
    assert extracted.reliable is True


@pytestmark_ocr
def test_upside_down_photo_is_turned_upright(tmp_path: Path):
    path = tmp_path / "upside.png"
    _save_image(path, _set_image().rotate(180, expand=True, fillcolor="white"))
    extracted = extract_document(str(path))
    assert "maria santos" in extracted.text.lower()
    assert extracted.reliable is True


@pytestmark_ocr
def test_cropped_page_missing_the_rating_is_not_approved(tmp_path: Path):
    image = _set_image().crop((0, 0, 1400, 280))
    path = tmp_path / "cropped.png"
    _save_image(path, image)
    result = _upload(path)
    assert result["status"] == "pendingReview"


@pytestmark_ocr
def test_mild_skew_still_reads_the_rating(tmp_path: Path):
    path = tmp_path / "skew.png"
    _save_image(path, _set_image().rotate(-8, expand=True, fillcolor="white"))
    result = _upload(path)
    assert result["status"] == "system_approved"
    assert result["extracted_info"]["Extracted rating"] == "90.0"


@pytestmark_ocr
def test_heavy_blur_is_not_auto_approved(tmp_path: Path):
    path = tmp_path / "blur.png"
    _save_image(path, _set_image().filter(ImageFilter.GaussianBlur(6)))
    result = _upload(path)
    assert result["status"] == "pendingReview"
    assert result["extracted_info"]["OCR quality"] == "Unreliable" or "review" in result["validation_result"].lower() or result["flagged_for_review"]


def test_conflicting_document_name_is_not_auto_approved(tmp_path: Path):
    path = tmp_path / "set.txt"
    path.write_text(
        "Student Evaluation of Teachers (SET)\nFaculty\nPedro Cruz\n"
        "Overall SET rating: 90\nAcademic Year 2024-2025\n",
        encoding="utf-8",
    )
    result = _upload(path, author="Maria Santos", uploader="Maria Santos")
    assert result["status"] == "pendingReview"
    assert "Pedro Cruz" in result["extracted_info"]["Extracted names"]
