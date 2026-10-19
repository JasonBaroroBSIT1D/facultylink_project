"""Text extraction for uploads.

Digital PDF pages keep their embedded text. Image-only PDF pages and camera
photos go through Tesseract after orientation, EXIF, and deskew correction.
The returned confidence is the mean of Tesseract's own per-word scores.
Embedded text has no OCR confidence, and that absence is reported as such.
"""

from __future__ import annotations

import io
import os
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from dotenv import load_dotenv

load_dotenv()

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
# Enough letters that a page is real text rather than a watermark or page number.
_MIN_EMBEDDED_LETTERS = 40
# A page that also contains images and only a short text layer is still scanned.
_SHORT_EMBEDDED_LETTERS = 250
_OCR_PAGE_LIMIT = 12
_MIN_OCR_WORDS = 5
_MIN_OCR_LETTERS = 20
# Mean of Tesseract word confidences (0-100). Below this, automatic approval stops.
_MIN_MEAN_CONFIDENCE = 60
_WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass(frozen=True)
class Extraction:
    text: str
    source: str
    confidence: float | None
    reliable: bool
    note: str
    pages: int = 0

    @property
    def confidence_label(self) -> str:
        if self.confidence is None:
            return "Not applicable (no OCR)"
        return f"{self.confidence:.0f}"


def _tesseract_candidates():
    return (
        Path(os.environ.get("TESSERACT_CMD", "")),
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    )


def configure_tesseract() -> bool:
    """Point pytesseract at a Windows Tesseract install. Return True if usable."""
    try:
        import pytesseract
    except ImportError:
        return False

    for candidate in _tesseract_candidates():
        if candidate and candidate.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            break

    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _letters(text: str) -> int:
    return sum(1 for char in text if char.isalpha())


def _empty(note: str, source: str = "none") -> Extraction:
    return Extraction("", source, None, False, note, 0)


def _read_plain(path: Path) -> Extraction:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return _empty("The text file could not be read.", "plain")
    if not text:
        return _empty("The text file was empty.", "plain")
    return Extraction(text, "plain", None, True, "Plain text was read directly.", 1)


def _read_docx(path: Path) -> Extraction:
    """Read a DOCX (Office Open XML) document. Legacy binary .doc is not read."""
    if not zipfile.is_zipfile(path):
        return _empty(
            "Legacy Word .doc files have no reader. Save the document as PDF or DOCX.",
            "doc",
        )
    try:
        with zipfile.ZipFile(path) as package:
            xml = package.read("word/document.xml")
    except (KeyError, OSError, zipfile.BadZipFile):
        return _empty("The Word document did not contain readable text.", "docx")
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return _empty("The Word document XML could not be parsed.", "docx")
    paragraphs = []
    for paragraph in root.iter(_WORD_NS + "p"):
        parts = []
        for node in paragraph.iter(_WORD_NS + "t"):
            if node.text:
                parts.append(node.text)
        line = "".join(parts).strip()
        if line:
            paragraphs.append(line)
    text = "\n".join(paragraphs).strip()
    if _letters(text) < _MIN_OCR_LETTERS:
        return _empty("The Word document did not contain enough readable text.", "docx")
    return Extraction(text, "docx", None, True, "DOCX text was read from the document XML.", 1)


def _osd_rotation(image) -> int:
    """Degrees clockwise that Tesseract says the page must turn to stand upright."""
    import pytesseract

    try:
        report = pytesseract.image_to_osd(image)
    except Exception:
        return 0
    angle = re.search(r"Rotate:\s*(\d+)", report or "")
    confidence = re.search(r"Orientation confidence:\s*([0-9.]+)", report or "")
    if not angle or not confidence:
        return 0
    degrees = int(angle.group(1)) % 360
    # Low-confidence orientation guesses are ignored so an upright page is left alone.
    if degrees == 0 or float(confidence.group(1)) < 5:
        return 0
    return degrees


def _skew_correction(image) -> float:
    """Small rotation, in Pillow's counter-clockwise degrees, that levels the text lines."""
    gray = image.convert("L")
    width = 360
    height = max(1, int(gray.height * width / max(gray.width, 1)))
    sample = gray.resize((width, height)).point(lambda pixel: 0 if pixel < 170 else 255)
    best_angle = 0.0
    best_score = -1.0
    for angle in range(-15, 16):
        turned = sample.rotate(angle, resample=0, fillcolor=255)
        raw = turned.tobytes()
        row_width = turned.size[0]
        row_height = turned.size[1]
        counts = []
        for row in range(row_height):
            start = row * row_width
            counts.append(sum(1 for pixel in raw[start : start + row_width] if pixel == 0))
        mean = sum(counts) / row_height
        score = sum((count - mean) ** 2 for count in counts) / row_height
        if score > best_score:
            best_score = score
            best_angle = float(angle)
    return best_angle if abs(best_angle) >= 1 else 0.0


def _prepare_image(image):
    """Apply EXIF, quarter-turn, and deskew corrections. Return the image and a short note."""
    from PIL import Image, ImageOps

    notes = []
    image = ImageOps.exif_transpose(image) or image
    image = image.convert("RGB")
    clockwise = _osd_rotation(image)
    if clockwise:
        # Pillow rotates counter-clockwise, and Tesseract's angle is clockwise.
        image = image.rotate(-clockwise, expand=True, fillcolor="white")
        notes.append(f"rotated {clockwise}°")
    skew = _skew_correction(image)
    if skew:
        image = image.rotate(skew, expand=True, fillcolor="white", resample=Image.BICUBIC)
        notes.append(f"deskewed {skew:.0f}°")
    if image.width < 1000:
        scale = min(3.0, 1400 / max(image.width, 1))
        if scale > 1.05:
            image = image.resize(
                (int(image.width * scale), int(image.height * scale)),
                Image.Resampling.LANCZOS,
            )
            notes.append("upscaled")
    image = ImageOps.autocontrast(image.convert("L"), cutoff=0.5).convert("RGB")
    return image, ", ".join(notes)


def _ocr_image(image) -> tuple[str, float | None, int]:
    """One Tesseract pass. Confidence is the mean of per-word scores from 0 to 100."""
    from pytesseract import Output
    import pytesseract

    data = pytesseract.image_to_data(image, output_type=Output.DICT)
    rows: dict[tuple, list[str]] = {}
    confidences = []
    total = len(data.get("text") or [])
    for index in range(total):
        word = (data["text"][index] or "").strip()
        if not word:
            continue
        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            confidence = -1
        if confidence >= 0:
            confidences.append(confidence)
        key = (data["block_num"][index], data["par_num"][index], data["line_num"][index])
        rows.setdefault(key, []).append(word)
    text = "\n".join(" ".join(words) for words in rows.values()).strip()
    if not confidences:
        return text, None, 0
    return text, sum(confidences) / len(confidences), len(confidences)


def _ocr_quality(text: str, confidence: float | None, words: int) -> tuple[bool, str]:
    if words < _MIN_OCR_WORDS or _letters(text) < _MIN_OCR_LETTERS or confidence is None:
        return False, "OCR extracted too little readable text for automatic approval."
    if confidence < _MIN_MEAN_CONFIDENCE:
        return (
            False,
            f"OCR word confidence averaged {confidence:.0f}, which is below the reliability threshold of {_MIN_MEAN_CONFIDENCE}.",
        )
    return True, f"OCR word confidence averaged {confidence:.0f} across {words} words."


def _ocr_prepared(image) -> tuple[str, float | None, int, str]:
    prepared, note = _prepare_image(image)
    text, confidence, words = _ocr_image(prepared)
    detail = f" ({note})" if note else ""
    return text, confidence, words, detail


def _render_ocr(page) -> tuple[str, float | None, int, str]:
    import pymupdf
    from PIL import Image

    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
    with Image.open(io.BytesIO(pixmap.tobytes("png"))) as image:
        return _ocr_prepared(image)


def _usable_embedded(text: str, has_images: bool) -> bool:
    letters = _letters(text)
    if letters < _MIN_EMBEDDED_LETTERS:
        return False
    if has_images and letters < _SHORT_EMBEDDED_LETTERS:
        return False
    return True


def _ocr_pdf(path: Path) -> Extraction:
    try:
        import pymupdf
    except ImportError:
        return _empty("PyMuPDF is not installed, so the PDF could not be read.", "pdf")

    parts = []
    sources = []
    confidences = []
    word_counts = []
    truncated = False
    note_missing = False
    ocr_pages = 0
    try:
        pdf = pymupdf.open(path)
    except Exception:
        return _empty("The PDF could not be opened.", "pdf")
    try:
        for page in pdf:
            embedded = (page.get_text("text") or "").strip()
            has_images = bool(page.get_images())
            if _usable_embedded(embedded, has_images):
                parts.append(embedded)
                sources.append("embedded")
                continue
            if not configure_tesseract():
                parts.append(embedded)
                sources.append("ocr")
                truncated = True
                note_missing = True
                break
            if ocr_pages >= _OCR_PAGE_LIMIT:
                truncated = True
                break
            ocr_pages += 1
            text, confidence, words, _detail = _render_ocr(page)
            # A short text layer can still be better than a weak OCR of the same page.
            if embedded and _letters(embedded) > _letters(text):
                parts.append(embedded)
                sources.append("embedded")
                continue
            if text:
                parts.append(text)
            sources.append("ocr")
            if confidence is not None:
                confidences.append(confidence)
                word_counts.append(words)
    finally:
        pdf.close()

    text = "\n\n".join(part for part in parts if part).strip()
    if not sources:
        return _empty("The PDF had no pages.", "pdf")
    if set(sources) == {"embedded"}:
        source = "embedded"
    elif set(sources) == {"ocr"}:
        source = "ocr"
    else:
        source = "mixed"
    mean = sum(confidences) / len(confidences) if confidences else None
    words = sum(word_counts)
    if "ocr" in sources:
        reliable, note = _ocr_quality(text, mean, words)
    else:
        reliable = _letters(text) >= _MIN_OCR_LETTERS
        note = "Embedded PDF text was used, so there is no OCR confidence score."
        mean = None
    if note_missing:
        reliable = False
        note = "Tesseract is not available, so scanned pages could not be read. " + note
    elif truncated:
        reliable = False
        note = f"Stopped after {_OCR_PAGE_LIMIT} scanned pages. {note}"
    if not text:
        return Extraction("", source, mean, False, note or "No readable text was found in the PDF.", len(sources))
    return Extraction(text, source, mean, reliable, note, len(sources))


def _ocr_picture(path: Path) -> Extraction:
    from PIL import Image

    try:
        with Image.open(path) as image:
            frames = getattr(image, "n_frames", 1) or 1
            image.seek(0)
            text, confidence, words, detail = _ocr_prepared(image)
    except Exception:
        return _empty("The image could not be opened.", "ocr")
    reliable, note = _ocr_quality(text, confidence, words)
    if frames > 1:
        note = f"Only the first frame of {frames} was read. {note}"
        reliable = False
    return Extraction(text, "ocr", confidence, reliable, note + detail, 1)


def extract_document(file_path: str | None) -> Extraction:
    """Extract text and a real quality judgement. Never raise to the caller."""
    if not file_path:
        return _empty("No file was stored for this document.")
    path = Path(file_path)
    if not path.exists():
        return _empty("The stored file could not be found.")

    suffix = path.suffix.lower()
    try:
        if suffix == ".txt":
            return _read_plain(path)
        if suffix == ".docx":
            return _read_docx(path)
        if suffix == ".doc":
            return _read_docx(path)
    except Exception:
        return _empty("The document text could not be read.", suffix.lstrip(".") or "file")

    if suffix == ".pdf":
        try:
            return _ocr_pdf(path)
        except Exception:
            return _empty("Text extraction failed for this PDF.", "pdf")

    if suffix not in IMAGE_SUFFIXES:
        return _empty(f"Files of type {suffix or 'unknown'} are not read for text extraction.", "unsupported")

    if not configure_tesseract():
        return _empty("Tesseract is not available, so the scan could not be read.", "ocr")
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        return _empty("Pillow is not installed, so the scan could not be read.", "ocr")
    try:
        return _ocr_picture(path)
    except Exception:
        return _empty("Text extraction failed for this file.", "ocr")


def extract_text(file_path: str | None) -> str:
    """Extract text with Tesseract when a scan has to be read. Never fail the request."""
    return extract_document(file_path).text
