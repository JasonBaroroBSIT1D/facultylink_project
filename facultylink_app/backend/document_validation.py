"""Field extraction and indicator-specific validation for automatic system approval."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from indicator_identity import resolve_identity_profile
from indicator_rules import rule_for
from kra_catalog import MOBILE_TO_WEB, find_criterion, load_catalog

# Keep in sync with kra1a_evaluation.RATING_AGGREGATION_INDICATORS (avoid import cycle with web reviewer API).
_RATING_AGGREGATION_INDICATORS = frozenset({"kra1-a-student", "kra1-a-supervisor"})

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

# A rating counts only when a scoring label introduces it. A bare percentage,
# a page number, or the word "score" on its own is not a rating.
RATING_PATTERNS = [
    re.compile(
        r"(?:osetr|osefr|overall(?:\s+(?:set|sef))?\s+rating|overall rating|set rating|sef rating|"
        r"rating summary|client satisfaction(?:\s+rating)?)\s*[:\-]?\s*(\d+(?:\.\d+)?)"
        r"(?:\s*(?:%|percent))?(?:\s*/\s*100)?",
        re.I,
    ),
]
RATING_HEADER = re.compile(
    r"(?i)^(?:osetr|osefr|overall(?:\s+(?:set|sef))?\s+rating|set rating|sef rating|"
    r"rating summary|client satisfaction(?:\s+rating)?|overall rating)\s*:?\s*$"
)
RATING_VALUE = re.compile(r"^(\d{1,3}(?:\.\d+)?)(?:\s*(?:%|percent))?(?:\s*/\s*100)?\b")

ISSN_PATTERN = re.compile(r"\b\d{4}[- ]?\d{3}[\dxX]\b|\bissn\b", re.I)
ISBN_PATTERN = re.compile(r"\b(?:ISBN(?:-1[03])?:?\s*)?(?:97[89][- ]?)?\d{1,5}[- ]?\d{1,7}[- ]?\d{1,7}[- ]?\d[\dXx]\b")

_FACULTY_LABEL = r"faculty(?!\s+(?:subject|subjects|id|no|number))"

NAME_LINE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"(?im)^{_FACULTY_LABEL}\s*[:\-]\s*(.+)$"), "Faculty Name"),
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
    (re.compile(r"(?im)^(?:performer|dancer|actor|actress)\s*[:\-]\s*(.+)$"), "Performer"),
    (re.compile(r"(?im)^(?:conductor)\s*[:\-]\s*(.+)$"), "Conductor"),
]

# Label on its own line, value on the next line. Includes the short "Faculty"
# heading used on evaluation summaries, mapped to the Faculty Name identity label.
STACKED_LABELS: list[tuple[str, str]] = [
    ("faculty name", "Faculty Name"),
    ("evaluated faculty", "Evaluated Faculty"),
    ("name of faculty", "Faculty Name"),
    ("employee name", "Employee Name"),
    ("name of employee", "Employee Name"),
    ("participant name", "Participant Name"),
    ("name of participant", "Participant Name"),
    ("participant", "Participant Name"),
    ("awardee", "Awardee"),
    ("recipient", "Awardee"),
    ("honoree", "Awardee"),
    ("author", "Author(s)"),
    ("authors", "Author(s)"),
    ("co-author", "Co-author(s)"),
    ("co-authors", "Co-author(s)"),
    ("researcher", "Researcher"),
    ("researchers", "Researcher"),
    ("inventor", "Inventor(s)"),
    ("inventors", "Inventor(s)"),
    ("developer", "Developer(s)"),
    ("developers", "Developer(s)"),
    ("contributor", "Contributor(s)"),
    ("contributors", "Contributor(s)"),
    ("project leader", "Project Leader"),
    ("project head", "Project Head"),
    ("adviser", "Adviser"),
    ("advisor", "Adviser"),
    ("thesis adviser", "Adviser"),
    ("panel member", "Panel Member"),
    ("panelist", "Panel Member"),
    ("examiner", "Panel Member"),
    ("mentor", "Mentor"),
    ("coach", "Coach"),
    ("resource person", "Resource Person"),
    ("speaker", "Resource Person"),
    ("presenter", "Resource Person"),
    ("member name", "Member Name"),
    ("signatory", "Signatory"),
    ("prepared by", "Prepared by"),
    ("faculty", "Faculty Name"),
    ("performer", "Performer"),
    ("dancer", "Performer"),
    ("conductor", "Conductor"),
]
_STACKED_LOOKUP = {phrase: label for phrase, label in STACKED_LABELS}

# "Author Maria Santos" without a colon, limited to a short capitalized name.
def _capitalized_name(value: str) -> bool:
    parts = [part for part in value.split() if part]
    return bool(parts) and all(part[0].isupper() for part in parts)


LOOSE_NAME_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            rf"\b{_FACULTY_LABEL}[ \t]*[:\-][ \t]+([A-Za-z][A-Za-z.'-]+(?:[ \t]+[A-Za-z][A-Za-z.'-]+){{0,3}})",
            re.I,
        ),
        "Faculty Name",
    ),
    (re.compile(r"\b(?:faculty name|evaluated faculty)[ \t]*[:\-]?[ \t]+([A-Za-z][A-Za-z.'-]+(?:[ \t]+[A-Za-z][A-Za-z.'-]+){0,3})", re.I), "Faculty Name"),
    (re.compile(r"\b(?:employee name)[ \t]*[:\-]?[ \t]+([A-Za-z][A-Za-z.'-]+(?:[ \t]+[A-Za-z][A-Za-z.'-]+){0,3})", re.I), "Employee Name"),
    (re.compile(r"\b(?:participant name|participant)[ \t]*[:\-]?[ \t]+([A-Za-z][A-Za-z.'-]+(?:[ \t]+[A-Za-z][A-Za-z.'-]+){0,3})", re.I), "Participant Name"),
    (re.compile(r"\b(?:awardee|recipient)[ \t]*[:\-]?[ \t]+([A-Za-z][A-Za-z.'-]+(?:[ \t]+[A-Za-z][A-Za-z.'-]+){0,3})", re.I), "Awardee"),
    (re.compile(r"\b(?:authors?|co-?authors?)[ \t]*[:\-]?[ \t]+([A-Za-z][A-Za-z.'-]+(?:[ \t]+[A-Za-z][A-Za-z.'-]+){0,3})", re.I), "Author(s)"),
    (re.compile(r"\b(?:inventors?|co-?inventors?)[ \t]*[:\-]?[ \t]+([A-Za-z][A-Za-z.'-]+(?:[ \t]+[A-Za-z][A-Za-z.'-]+){0,3})", re.I), "Inventor(s)"),
    (re.compile(r"\b(?:developers?)[ \t]*[:\-]?[ \t]+([A-Za-z][A-Za-z.'-]+(?:[ \t]+[A-Za-z][A-Za-z.'-]+){0,3})", re.I), "Developer(s)"),
    (re.compile(r"\b(?:project leader|project head)[ \t]*[:\-]?[ \t]+([A-Za-z][A-Za-z.'-]+(?:[ \t]+[A-Za-z][A-Za-z.'-]+){0,3})", re.I), "Project Leader"),
    (re.compile(r"\b(?:performer|dancer)[ \t]*[:\-]?[ \t]+([A-Za-z][A-Za-z.'-]+(?:[ \t]+[A-Za-z][A-Za-z.'-]+){0,3})", re.I), "Performer"),
    (re.compile(r"\b(?:conductor)[ \t]*[:\-]?[ \t]+([A-Za-z][A-Za-z.'-]+(?:[ \t]+[A-Za-z][A-Za-z.'-]+){0,3})", re.I), "Conductor"),
]

INLINE_NAME_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"(?i){_FACULTY_LABEL}\s*[:\-]\s*([^\n\r;]+)"), "Faculty Name"),
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
    (re.compile(r"(?i)(?:performer|dancer)\s*[:\-]\s*([^\n\r;]+)"), "Performer"),
    (re.compile(r"(?i)(?:conductor)\s*[:\-]\s*([^\n\r;]+)"), "Conductor"),
]


# These roles appear on a document without being the faculty member it is about.
# They count only when an indicator's own identity labels ask for them, such as a linkage signatory.
_NON_SUBJECT_LABELS = {"Prepared by", "Submitted by", "Signatory", "Representative"}


def _trim_name_phrase(raw: str) -> str:
    """Keep a name and drop a following sentence. Initials such as C. stay."""
    return re.split(r"(?<!\b[A-Za-z])\.\s+", raw or "", maxsplit=1)[0].strip()


def _split_names(raw: str) -> list[str]:
    # A value stays on its own line. The following line is a different field.
    first_line = (raw or "").split("\n", 1)[0].split("\r", 1)[0]
    first_line = _trim_name_phrase(first_line)
    return [part.strip(" .") for part in re.split(r"[;/]| and ", first_line) if part.strip(" .")]


def _counts_as_subject(label: str, profile) -> bool:
    if label in profile.preferred_ocr_labels or label == profile.display_label:
        return True
    return label not in _NON_SUBJECT_LABELS


def _normalize_person_name(name: str) -> str:
    cleaned = re.sub(r"^(mr|mrs|ms|dr|prof|professor)\.?\s+", "", (name or "").strip().lower())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _name_tokens(name: str) -> list[str]:
    tokens = []
    for part in re.split(r"[\s,]+", _normalize_person_name(name)):
        part = part.strip(".")
        if not part or re.fullmatch(r"[a-z]", part):
            continue
        tokens.append(part)
    return tokens


def _names_similar(left: str, right: str) -> bool:
    """Match the same person. A shorter fragment is not a match."""
    a = _normalize_person_name(left)
    b = _normalize_person_name(right)
    if not a or not b:
        return False
    if a == b:
        return True
    left_tokens = _name_tokens(left)
    right_tokens = _name_tokens(right)
    if len(left_tokens) >= 2 and left_tokens == right_tokens:
        return True
    if len(left_tokens) >= 2 and len(left_tokens) == len(right_tokens):
        return SequenceMatcher(None, a, b).ratio() >= 0.84
    return False


def preferred_identity_label(indicator_id: str | None) -> str:
    return resolve_identity_profile(indicator_id).display_label


def _label_priority(label: str, profile) -> int:
    preferred = profile.preferred_ocr_labels
    if label in preferred:
        return preferred.index(label)
    if label == profile.display_label:
        return 0
    return len(preferred) + 2


def _label_key(line: str) -> str:
    return re.sub(r"[:\-\s]+$", "", (line or "").strip().lower())


def _looks_like_person(line: str) -> bool:
    cleaned = (line or "").strip(" .")
    if not cleaned or len(cleaned) > 80 or any(char.isdigit() for char in cleaned):
        return False
    if _label_key(cleaned) in _STACKED_LOOKUP:
        return False
    parts = cleaned.split()
    if not 1 <= len(parts) <= 5:
        return False
    return all(re.match(r"[A-Za-z][A-Za-z.'-]*$", part) for part in parts)


def _stacked_names(ocr_text: str) -> list[tuple[str, list[str]]]:
    """Read a label line whose value is the next non-empty line."""
    lines = [line.strip() for line in (ocr_text or "").splitlines()]
    found = []
    for index, line in enumerate(lines):
        label = _STACKED_LOOKUP.get(_label_key(line))
        if not label or ":" in line or "-" in line.strip()[-1:]:
            # Same-line "Label: value" is handled by the line patterns.
            if ":" in line:
                continue
        if not label:
            continue
        for follower in lines[index + 1 : index + 3]:
            if not follower:
                continue
            if _looks_like_person(follower):
                found.append((label, _split_names(follower)))
            break
    return found


def extract_named_parties(
    *,
    ocr_text: str,
    upload_author: str | None,
    indicator_id: str | None,
) -> tuple[str, list[str], bool]:
    """Return the identity label, names, and whether a name was read from the document.

    upload_author is ignored. The logged-in account is compared later, and a name
    typed into the upload form cannot stand in for either side.
    """
    del upload_author
    profile = resolve_identity_profile(indicator_id)
    display = profile.display_label
    found: list[tuple[int, str, list[str]]] = []

    def register(label: str, names: list[str]) -> None:
        cleaned = [name.strip(" .") for name in names if name and name.strip(" .")]
        if cleaned:
            found.append((_label_priority(label, profile), label, cleaned))

    for pattern, label in NAME_LINE_PATTERNS:
        for line in (ocr_text or "").splitlines():
            match = pattern.search(line.strip())
            if match:
                register(label, _split_names(match.group(1)))

    for pattern, label in INLINE_NAME_PATTERNS:
        match = pattern.search(ocr_text or "")
        if match:
            register(label, _split_names(match.group(1)))

    for pattern, label in LOOSE_NAME_PATTERNS:
        match = pattern.search(ocr_text or "")
        if match and _capitalized_name(match.group(1)):
            register(label, _split_names(match.group(1)))

    for label, names in _stacked_names(ocr_text or ""):
        register(label, names)

    # The name typed on the upload form is not the logged-in faculty member and is not
    # the person the document is about. Only a subject label printed on the document counts.
    subject_hits = [item for item in found if _counts_as_subject(item[1], profile)]
    if not subject_hits:
        return display, [], False

    subject_hits.sort(key=lambda item: item[0])
    from_document = True
    pool = subject_hits
    primary_label = pool[0][1]
    names: list[str] = []
    for _, item_label, item_names in pool:
        if item_label == primary_label or item_label in profile.preferred_ocr_labels:
            for name in item_names:
                if name not in names:
                    names.append(name)
    if not names:
        names = pool[0][2]
    shown = primary_label if primary_label != "Upload form name" else display
    return shown, names, from_document


ACADEMIC_YEAR_PATTERN = re.compile(
    r"(?i)(?:academic year|school year|sy|ay)\s*[:\-]?\s*(\d{4}\s*[-–/]\s*\d{4})"
)
ACADEMIC_TERM_PATTERN = re.compile(
    r"(?i)(?:academic term|semester|term)\s*[:\-]?\s*([^\n\r;]+)"
)
EVALUATION_TYPE_PATTERN = re.compile(
    r"(?i)evaluation type\s*[:\-]?\s*([^\n\r;]+)"
)


def extract_document_period(*, ocr_text: str, title: str = "") -> str | None:
    """Prefer a full academic year over a lone calendar year."""
    haystack = "\n".join(part for part in (ocr_text, title) if part)
    match = ACADEMIC_YEAR_PATTERN.search(haystack)
    if match:
        return re.sub(r"\s+", "", match.group(1).replace("/", "-"))
    range_match = re.search(r"\b(\d{4}\s*[-–/]\s*\d{4})\b", haystack)
    if range_match:
        return re.sub(r"\s+", "", range_match.group(1).replace("/", "-"))
    for source in (ocr_text, title):
        match = DATE_PATTERN.search(source or "")
        if match:
            return match.group(1).strip()
    return None


def extract_evaluation_metadata(ocr_text: str) -> dict[str, str]:
    text = ocr_text or ""
    metadata: dict[str, str] = {}
    term = ACADEMIC_TERM_PATTERN.search(text)
    if term:
        metadata["academic_term"] = term.group(1).strip()
    eval_type = EVALUATION_TYPE_PATTERN.search(text)
    if eval_type:
        metadata["evaluation_type"] = eval_type.group(1).strip()
    return metadata


def extract_fields(
    *,
    title: str,
    author: str | None,
    ocr_text: str,
    indicator_id: str | None = None,
) -> dict:
    cleaned_title = (title or "").strip()
    profile = resolve_identity_profile(indicator_id)
    identity_label, named_parties, name_from_document = extract_named_parties(
        ocr_text=ocr_text,
        upload_author=author,
        indicator_id=indicator_id,
    )
    date_value = extract_document_period(ocr_text=ocr_text, title=cleaned_title)
    eval_meta = extract_evaluation_metadata(ocr_text)
    if not eval_meta.get("academic_term") and cleaned_title:
        lower = cleaned_title.lower()
        if re.search(r"(?:^|[\s_./-])sem(?:ester)?\s*2\b|2nd\s*sem", lower):
            eval_meta["academic_term"] = "2nd Semester"
        elif re.search(r"(?:^|[\s_./-])sem(?:ester)?\s*1\b|1st\s*sem", lower):
            eval_meta["academic_term"] = "1st Semester"
    haystack = " ".join(part for part in (title, author, ocr_text) if part)
    return {
        "title": cleaned_title,
        "authors": named_parties,
        "identity_label": identity_label or profile.display_label,
        "identity_mode": profile.mode,
        "named_parties": named_parties,
        "name_from_document": name_from_document,
        "date": date_value,
        "academic_term": eval_meta.get("academic_term"),
        "evaluation_type": eval_meta.get("evaluation_type"),
        "issn": bool(ISSN_PATTERN.search(haystack or "")),
        "isbn": bool(ISBN_PATTERN.search(haystack or "")),
        "rating": extract_rating(haystack),
    }


def _normalize_rating_digits(text: str) -> str:
    """Turn a misread zero (letter O beside a digit) back into 0. Leaves words alone."""
    return re.sub(r"(?<=\d)[Oo]|[Oo](?=\d)", "0", text)


def _rating_value(raw: str) -> float | None:
    try:
        value = float(raw)
    except ValueError:
        return None
    if 0 <= value <= 100:
        return value
    return None


def extract_rating(text: str | None) -> float | None:
    if not text:
        return None
    normalized = _normalize_rating_digits(text)
    for pattern in RATING_PATTERNS:
        match = pattern.search(normalized)
        if match:
            value = _rating_value(match.group(1))
            if value is not None:
                return value
    lines = [line.strip() for line in normalized.splitlines()]
    for index, line in enumerate(lines):
        if not RATING_HEADER.match(line):
            continue
        for follower in lines[index + 1 : index + 3]:
            if not follower:
                continue
            match = RATING_VALUE.match(follower)
            if match:
                value = _rating_value(match.group(1))
                if value is not None:
                    return value
            break
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
            return True, label, "Identity matched."
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
        if indicator_id in _RATING_AGGREGATION_INDICATORS:
            # SET/SEF semesters share one indicator; slot duplicates are handled in period aggregation.
            continue
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
