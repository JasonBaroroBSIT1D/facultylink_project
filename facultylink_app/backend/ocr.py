import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


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


def _ocr_image(image) -> str:
    import pytesseract

    return pytesseract.image_to_string(image) or ""


def _ocr_pdf(path: Path) -> str:
    try:
        import fitz
    except ImportError:
        return ""

    pages = []
    with fitz.open(path) as pdf:
        for page in pdf:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            png_bytes = pixmap.tobytes("png")
            from PIL import Image
            import io

            with Image.open(io.BytesIO(png_bytes)) as image:
                text = _ocr_image(image).strip()
            if text:
                pages.append(text)
    return "\n\n".join(pages)


def extract_text(file_path: str | None) -> str:
    """Extract text with Tesseract when available. Never fail the request."""
    if not file_path:
        return ""
    path = Path(file_path)
    if not path.exists():
        return ""

    suffix = path.suffix.lower()
    if suffix in {".txt"}:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""

    if not configure_tesseract():
        return ""

    try:
        from PIL import Image
    except ImportError:
        return ""

    try:
        if suffix == ".pdf":
            return _ocr_pdf(path)
        if suffix in IMAGE_SUFFIXES:
            with Image.open(path) as image:
                return _ocr_image(image)
    except Exception:
        return ""
    return ""
