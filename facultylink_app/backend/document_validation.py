"""Field extraction and indicator-specific validation for automatic system approval."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from indicator_identity import resolve_identity_profile
from indicator_rules import rule_for
from kra_catalog import MOBILE_TO_WEB, find_criterion, load_catalog

COUNTABLE_ACCOMPLISHMENT_STATUSES = {"validated", "approved", "system_approved"}

DATE_PATTERN = re.compile(
    r"\b("
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"[\s,./-]+\d{1,2}[\s,./-]+\d{4}"
    r"|\d{1,2}[\s,./-]+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"[\s,./-]+\d{4}"
    r"|\d{4}[\s,./-]\d{1,2}[\s,./-]\d{1,2}"
    r"|\b(20\d{2}|19\d{2})\b"
    r"|(?:AY|SY)\s*[\s./-]*\d{4}\s*[-–]\s*\d{4}"
    r")",
    re.IGNORECASE,
)

RATING_PATTERNS = [
    re.compile(r"(?:osetr|osefr|overall(?:\s+set|\s+sef)?\s+rating|rating summary)[:\s]+(\d+(?:\.\d+)?)", re.I),
    re.compile(r"(?:overall|rating|score)[:\s]+(\d+(?:\.\d+)?)\s*(?:%|percent)?", re.I),
    re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:rating|score|osetr|osefr)?", re.I),
]

ISSN_PATTERN = re.compile(r"\b\d{4}[- ]?\d{3}[\dxX]\b|\bissn\b", re.I)
ISBN_PATTERN = re.compile(r"\b(?:ISBN(?:-1[03])?:?\s*)?(?:97[89][- ]?)?\d{1,5}[- ]?\d{1,7}[- ]?\d{1,7}[- ]?\d[\dXx]\b")

NAME_LINE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?im)^(?:faculty name|evaluated faculty|name of faculty)\s*[:\-]\s*(.+)$"), "Faculty Name"),
    (re.compile(r"(?im)^(?:employee name|name of employee)\s*[:\-]\s*(.+)$"), "Employee Name"),
    (re.compile(r"(?im)^(?:participant name|name of participant)\s*[:\-]\s*(.+)$"), "Participant Name"),
    (re.compile(r"(?im)^(?:recipient|awardee|honoree)\s*[:\-]\s*(.+)$"), "Awardee"),
    (re.compile(r"(?im)^(?:author(?:s)?|co-?author(?:s)?)\s*[:\-]\s*(.+)$"), "Author(s)"),
    (re.compile(r"(?im)^(?:researcher(?:s)?|investigator(?:s)?)\s*[:\-]\s*(.+)$"), "Researcher"),
    (re.compile(r"(?im)^(?:inventor(?:s)?|co-?inventor(?:s)?)\s*[:\-]\s*(.+)$"), "Inventor(s)"),
    (re.compile(r"(?im)^(?:developer(?:s)?|co-?developer(?:s)?)\s*[:\-]\s*(.+)$"), "Developer(s)"),
    (re.compile(r"(?im)^(?:contributor(?:s)?|co-?contributor(?:s)?)\s*[:\-]\s*(.+)$"), "Contributor(s)"),
    (re.compile(r"(?im)^(?:project (?:head|leader)|team leader)\s*[:\-]\s*(.+)$"), "Project Leader"),
    (re.compile(r"(?im)^(?:adviser|advisor|thesis adviser)\s*[:\-]\s*(.+)$"), "Adviser"),
    (re.compile(r"(?im)^(?:panel(?:ist| member)?|examiner)\s*[:\-]\s*(.+)$"), "Panel Member"),
    (re.compile(r"(?im)^(?:mentor|coach)\s*[:\-]\s*(.+)$"), "Mentor"),
    (re.compile(r"(?im)^(?:resource person|speaker|presenter|facilitator|moderator)\s*[:\-]\s*(.+)$"), "Resource Person"),
    (re.compile(r"(?im)^(?:consultant|expert)\s*[:\-]\s*(.+)$"), "Consultant"),
    (re.compile(r"(?im)^(?:member name|name of member)\s*[:\-]\s*(.+)$"), "Member Name"),
    (re.compile(r"(?im)^(?:signatory|representative)\s*[:\-]\s*(.+)$"), "Signatory"),
    (re.compile(r"(?im)^(?:prepared by|submitted by)\s*[:\-]\s*(.+)$"), "Prepared by"),
]

INLINE_NAME_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)(?:faculty name|evaluated faculty)\s*[:\-]\s*([^\n\r;]+)"), "Faculty Name"),
    (re.compile(r"(?i)(?:employee name)\s*[:\-]\s*([^\n\r;]+)"), "Employee Name"),
    (re.compile(r"(?i)(?:participant name)\s*[:\-]\s*([^\n\r;]+)"), "Participant Name"),
    (re.compile(r"(?i)(?:recipient|awardee)\s*[:\-]\s*([^\n\r;]+)"), "Awardee"),
    (re.compile(r"(?i)(?:author(?:s)?|co-?author(?:s)?)\s*[:\-]\s*([^\n\r;]+)"), "Author(s)"),
    (re.compile(r"(?i)(?:researcher(?:s)?)\s*[:\-]\s*([^\n\r;]+)"), "Researcher"),
    (re.compile(r"(?i)(?:inventor(?:s)?|co-?inventor(?:s)?)\s*[:\-]\s*([^\n\r;]+)"), "Inventor(s)"),
    (re.compile(r"(?i)(?:developer(?:s)?|co-?developer(?:s)?)\s*[:\-]\s*([^\n\r;]+)"), "Developer(s)"),
    (re.compile(r"(?i)(?:contributor(?:s)?)\s*[:\-]\s*([^\n\r;]+)"), "Contributor(s)"),
    (re.compile(r"(?i)(?:project (?:head|leader))\s*[:\-]\s*([^\n\r;]+)"), "Project Leader"),
    (re.compile(r"(?i)(?:adviser|advisor)\s*[:\-]\s*([^\n\r;]+)"), "Adviser"),
    (re.compile(r"(?i)(?:panel(?:ist| member)?)\s*[:\-]\s*([^\n\r;]+)"), "Panel Member"),
    (re.compile(r"(?i)(?:mentor|coach)\s*[:\-]\s*([^\n\r;]+)"), "Mentor"),
    (re.compile(r"(?i)(?:resource person|speaker|presenter)\s*[:\-]\s*([^\n\r;]+)"), "Resource Person"),
    (re.compile(r"(?i)(?:consultant)\s*[:\-]\s*([^\n\r;]+)"), "Consultant"),
    (re.compile(r"(?i)(?:member name)\s*[:\-]\s*([^\n\r;]+)"), "Member Name"),
]


def _split_names(raw: str) -> list[str]:
    return [part.strip() for part in re.split(r"[;/]| and ", raw) if part.strip()]


def _normalize_person_name(name: str) -> str:
    cleaned = re.sub(r"^(mr|mrs|ms|dr|prof|professor)\.?\s+", "", (name or "").strip().lower())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _names_similar(left: str, right: str) -> bool:
    a = _normalize_person_name(left)
    b = _normalize_person_name(right)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.84


def preferred_identity_label(indicator_id: str | None) -> str:
    return resolve_identity_profile(indicator_id).display_label


def _label_priority(label: str, profile) -> int:
    preferred = profile.preferred_ocr_labels
    if label in preferred:
        return preferred.index(label)
    if label == profile.display_label:
        return 0
    return len(preferred) + 2


def extract_named_parties(
    *,
    ocr_text: str,
    upload_author: str | None,
    indicator_id: str | None,
) -> tuple[str, list[str]]:
    """Return the best identity label and extracted names for the classified indicator."""
    profile = resolve_identity_profile(indicator_id)
    display = profile.display_label
    found: list[tuple[int, str, list[str]]] = []

    def register(label: str, names: list[str]) -> None:
        cleaned = [name for name in names if name]
        if cleaned:
            found.append((_label_priority(label, profile), label, cleaned))

    if upload_author and upload_author.strip():
        register("Upload form name", _split_names(upload_author))

    for pattern, label in NAME_LINE_PATTERNS:
        for line in (ocr_text or "").splitlines():
            match = pattern.search(line.strip())
            if match:
                register(label, _split_names(match.group(1)))

    for pattern, label in INLINE_NAME_PATTERNS:
        match = pattern.search(ocr_text or "")
        if match:
            register(label, _split_names(match.group(1)))

    if not found:
        return display, []

    found.sort(key=lambda item: item[0])
    primary_label = found[0][1]
    names: list[str] = []
    for _, item_label, item_names in found:
        if item_label == primary_label or item_label in profile.preferred_ocr_labels:
            for name in item_names:
                if name not in names:
                    names.append(name)
    if not names:
        names = found[0][2]
    return primary_label if primary_label != "Upload form name" else display, names


def extract_fields(
    *,
    title: str,
    author: str | None,
    ocr_text: str,
    indicator_id: str | None = None,
) -> dict:
    cleaned_title = (title or "").strip()
    profile = resolve_identity_profile(indicator_id)
    identity_label, named_parties = extract_named_parties(
        ocr_text=ocr_text,
        upload_author=author,
        indicator_id=indicator_id,
    )
    date_value = None
    for source in (ocr_text, title or ""):
        match = DATE_PATTERN.search(source or "")
        if match:
            date_value = match.group(1).strip()
            break
    haystack = " ".join(part for part in (title, author, ocr_text) if part)
    return {
        "title": cleaned_title,
        "authors": named_parties,
        "identity_label": identity_label or profile.display_label,
        "identity_mode": profile.mode,
        "named_parties": named_parties,
        "date": date_value,
        "issn": bool(ISSN_PATTERN.search(haystack or "")),
        "isbn": bool(ISBN_PATTERN.search(haystack or "")),
        "rating": extract_rating(haystack),
    }


def extract_rating(text: str | None) -> float | None:
    if not text:
        return None
    for pattern in RATING_PATTERNS:
        match = pattern.search(text)
        if match:
            try:
                value = float(match.group(1))
            except ValueError:
                continue
            if 0 <= value <= 100:
                return value
    return None


def verify_identity(
    indicator_id: str | None,
    *,
    uploader_name: str | None,
    named_parties: list[str],
) -> tuple[bool, str, str]:
    """Check whether document names match the uploading faculty member when applicable."""
    profile = resolve_identity_profile(indicator_id)
    label = profile.display_label
    if not named_parties:
        if profile.uploader_must_match or profile.require_named_party:
            return (
                False,
                label,
                f"No {label.lower()} was extracted from the document for identity verification.",
            )
        return True, label, "No named party was extracted; reviewer may confirm identity."

    matched = bool(
        uploader_name and any(_names_similar(uploader_name, name) for name in named_parties)
    )

    if profile.uploader_must_match:
        if not uploader_name:
            return False, label, "Uploader profile name is unavailable for identity verification."
        if matched:
            return True, label, f"Extracted {label.lower()} matches the uploading faculty member."
        return (
            False,
            label,
            f"Extracted {label.lower()} does not match the uploading faculty member.",
        )

    if profile.uploader_should_match:
        if matched:
            return True, label, f"Uploader matches the extracted {label.lower()}."
        if profile.mode in {"panel_member", "linkage", "citation"}:
            return True, label, "Named parties were extracted; not every name is the document beneficiary."
        return (
            False,
            label,
            f"Uploader was not found among extracted names for {label.lower()}; reviewer verification required.",
        )

    if matched:
        return True, label, "Uploader matches an extracted named party."
    return True, label, "Named parties extracted; beneficiary role is not strictly enforced for this indicator."


def _similar_title(a: str, b: str) -> bool:
    left = (a or "").strip().lower()
    right = (b or "").strip().lower()
    if not left or not right:
        return False
    if left == right:
        return True
    return SequenceMatcher(None, left, right).ratio() >= 0.88


def find_duplicate_accomplishment(
    existing_docs,
    *,
    indicator_id: str | None,
    title: str,
    file_hash: str | None = None,
    exclude_public_id: str | None = None,
) -> str | None:
    if not indicator_id and not file_hash:
        return None
    countable = COUNTABLE_ACCOMPLISHMENT_STATUSES
    for doc in existing_docs or []:
        if exclude_public_id and getattr(doc, "public_id", None) == exclude_public_id:
            continue
        status = getattr(doc, "status", None)
        if status not in countable:
            continue
        if file_hash and getattr(doc, "file_hash", None) == file_hash:
            return getattr(doc, "public_id", None)
        if indicator_id and getattr(doc, "indicator_id", None) == indicator_id:
            if _similar_title(getattr(doc, "title", ""), title):
                return getattr(doc, "public_id", None)
    return None


def authorship_consistent(
    indicator_id: str | None, authors_count: int, contribution_percent
) -> tuple[bool, str | None]:
    rule = rule_for(indicator_id)
    if not rule or authors_count <= 0:
        return True, None
    contribution = rule.get("contribution") or "sole"
    lowered = (indicator_id or "").lower()
    if contribution == "declared" and contribution_percent is None:
        return False, "A declared contribution percentage is required for this indicator."
    if authors_count > 1 and (contribution == "sole" or "-sole" in lowered):
        return False, "Multiple authors were detected for a sole-authorship indicator."
    return True, None


def validate_scoring_inputs(
    indicator_id: str | None,
    *,
    rating: float | None,
    contribution_percent: float | None,
) -> tuple[bool, list[str]]:
    rule = rule_for(indicator_id)
    if not rule:
        return True, []
    reasons: list[str] = []
    if rule.get("multiplier") is not None and rating is None:
        reasons.append("Overall rating is required for this indicator.")
    if (rule.get("contribution") or "") == "declared" and contribution_percent is None:
        reasons.append("Contribution percentage is required for this indicator.")
    return not reasons, reasons


def validate_indicator_fields(
    indicator_id: str | None,
    fields: dict,
    *,
    ocr_text: str,
) -> tuple[bool, list[str]]:
    """Indicator-specific required fields (not universal author/title/date)."""
    reasons: list[str] = []
    iid = (indicator_id or "").lower()
    title = fields.get("title")
    named = fields.get("named_parties") or fields.get("authors") or []
    date = fields.get("date")
    rating = fields.get("rating")
    profile = resolve_identity_profile(indicator_id)

    if not indicator_id:
        reasons.append("No indicator was identified for field validation.")
        return False, reasons

    if profile.mode == "faculty_evaluated":
        if rating is None:
            label = "OSETR" if "student" in iid else "OSEFR"
            reasons.append(f"{label} or overall rating was not found in the document.")
        if not date:
            reasons.append("Academic period or evaluation date is required for this evaluation summary.")
        return not reasons, reasons

    if profile.mode == "client_satisfaction":
        if rating is None:
            reasons.append("Client satisfaction rating was not found in the document.")
        if not date:
            reasons.append("Extension activity date or period is required.")
        return not reasons, reasons

    if profile.require_named_party and not named:
        reasons.append(f"{profile.display_label} must be extracted from the document.")

    if profile.mode == "publication_author":
        if not title:
            reasons.append("Publication title is required.")
        if not date:
            reasons.append("Publication date or year is required.")
        if "journal" in iid and not fields.get("issn"):
            reasons.append("Journal evidence should include an ISSN or clear journal identifier.")

    elif profile.mode == "material_author":
        if not title:
            reasons.append("Material title is required.")
        if not date and not fields.get("isbn"):
            reasons.append("Publication year or ISBN is required for instructional materials.")

    elif profile.mode == "inventor":
        if not title:
            reasons.append("Patent or IP title is required.")
        text = (ocr_text or "").lower()
        if not any(token in text for token in ("patent", "utility model", "industrial design", "copyright")):
            reasons.append("IP documentation should reference the registered protection type.")

    elif profile.mode == "developer":
        if not title:
            reasons.append("Software or product title is required.")
        if "copyright" not in (ocr_text or "").lower() and "software" not in (ocr_text or "").lower():
            reasons.append("Software evidence should reference the program or copyright.")

    elif profile.mode == "linkage":
        if not date:
            reasons.append("Agreement or activity date is required.")
        if not any(
            token in (ocr_text or "").lower()
            for token in ("mou", "moa", "memorandum", "partnership", "linkage", "network")
        ):
            reasons.append("Linkage evidence should describe the partnership or networking activity.")

    elif profile.mode in {
        "participant",
        "awardee",
        "member",
        "graduate",
        "service_record",
        "resource_person",
        "consultant",
        "extension_head",
        "extension_participant",
        "income_lead",
        "income_contributor",
        "program_lead",
        "program_contributor",
        "adviser",
        "mentor",
        "admin_designation",
        "director_role",
        "performer",
        "creative_author",
    }:
        if not date:
            reasons.append("Document date or coverage period is required.")

    elif profile.mode == "citation":
        if not any(token in (ocr_text or "").lower() for token in ("cited", "citation", "scopus", "wos", "issn")):
            reasons.append("Citation evidence should reference the cited publication.")

    elif profile.mode == "panel_member":
        if not any(token in (ocr_text or "").lower() for token in ("panel", "examination", "defense", "thesis")):
            reasons.append("Panel evidence should reference the examination or defense activity.")

    else:
        if not title:
            reasons.append("Document title is required.")
        if not date:
            reasons.append("Document date or coverage period is required.")

    return not reasons, reasons


def detect_criterion_contradiction(
    *,
    declared_kra: str | None,
    criterion_id: str | None,
    resolved_indicator_id: str | None,
    haystack: str,
) -> str | None:
    """Flag when OCR/title content aligns much more strongly with another criterion under the same KRA."""
    if not declared_kra or not criterion_id or not haystack.strip():
        return None
    from document_classifier import score_indicator_text

    web_kra = MOBILE_TO_WEB.get(declared_kra or "")
    if not web_kra:
        return None
    selected = find_criterion(criterion_id)
    if not selected:
        return None

    best_selected = 0
    if resolved_indicator_id:
        for indicator in selected["criterion"].get("indicators") or []:
            if indicator.get("id") == resolved_indicator_id:
                best_selected, _ = score_indicator_text(indicator, haystack)
                break
    else:
        for indicator in selected["criterion"].get("indicators") or []:
            score, _ = score_indicator_text(indicator, haystack)
            best_selected = max(best_selected, score)

    best_other = 0
    other_label = None
    for kra in load_catalog().get("kras") or []:
        if kra.get("id") != web_kra:
            continue
        for criterion in kra.get("criteria") or []:
            if criterion.get("id") == criterion_id:
                continue
            for indicator in criterion.get("indicators") or []:
                score, _ = score_indicator_text(indicator, haystack)
                if score > best_other:
                    best_other = score
                    other_label = criterion.get("name") or criterion.get("id")
        break

    if best_other >= 5 and best_other >= best_selected + 3:
        return (
            f"The document content fits {other_label} more strongly than the selected criterion "
            f"({best_other} vs {best_selected} keyword score)."
        )
    return None
