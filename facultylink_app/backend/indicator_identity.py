"""Indicator-specific identity labels and validation policies for all four KRAs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

IdentityMode = Literal[
    "faculty_evaluated",  # SET/SEF — faculty must match uploader
    "publication_author",  # books, journals, chapters
    "material_author",  # textbook, module, manual, multimedia
    "program_lead",
    "program_contributor",
    "adviser",
    "panel_member",
    "mentor",
    "inventor",
    "developer",
    "creative_author",
    "performer",
    "director_role",
    "citation",
    "linkage",
    "income_lead",
    "income_contributor",
    "extension_head",
    "extension_participant",
    "admin_designation",
    "client_satisfaction",
    "resource_person",
    "consultant",
    "participant",
    "awardee",
    "member",
    "graduate",
    "service_record",
    "generic",
]


@dataclass(frozen=True)
class IdentityProfile:
    mode: IdentityMode
    display_label: str
    preferred_ocr_labels: tuple[str, ...]
    require_named_party: bool
    uploader_must_match: bool
    uploader_should_match: bool
    allow_multiple_names: bool


def resolve_identity_profile(indicator_id: str | None) -> IdentityProfile:
    iid = (indicator_id or "").lower()
    if not iid:
        return IdentityProfile(
            mode="generic",
            display_label="Named party",
            preferred_ocr_labels=("Named party",),
            require_named_party=False,
            uploader_must_match=False,
            uploader_should_match=False,
            allow_multiple_names=True,
        )

    if iid in {"kra1-a-student", "kra1-a-supervisor"}:
        return IdentityProfile(
            mode="faculty_evaluated",
            display_label="Faculty Name",
            preferred_ocr_labels=("Faculty Name", "Evaluated Faculty", "Employee Name"),
            require_named_party=False,
            uploader_must_match=True,
            uploader_should_match=False,
            allow_multiple_names=False,
        )

    if iid.startswith("kra1-b-program-lead"):
        return IdentityProfile(
            mode="program_lead",
            display_label="Project Leader",
            preferred_ocr_labels=("Project Leader", "Lead", "Coordinator", "Developer"),
            require_named_party=True,
            uploader_must_match=True,
            uploader_should_match=False,
            allow_multiple_names=False,
        )
    if iid.startswith("kra1-b-program-contributor"):
        return IdentityProfile(
            mode="program_contributor",
            display_label="Contributor",
            preferred_ocr_labels=("Contributor", "Co-developer", "Team Member"),
            require_named_party=True,
            uploader_must_match=False,
            uploader_should_match=True,
            allow_multiple_names=True,
        )
    if "multimedia" in iid:
        return IdentityProfile(
            mode="material_author",
            display_label="Developer(s)" if "-co" in iid else "Developer",
            preferred_ocr_labels=("Developer", "Author(s)", "Contributor(s)"),
            require_named_party=True,
            uploader_must_match="-sole" in iid,
            uploader_should_match="-co" in iid,
            allow_multiple_names="-co" in iid,
        )
    if any(token in iid for token in ("textbook", "module", "manual")):
        return IdentityProfile(
            mode="material_author",
            display_label="Author(s)" if "-co" in iid else "Author",
            preferred_ocr_labels=("Author(s)", "Co-author(s)", "Developer(s)"),
            require_named_party=True,
            uploader_must_match="-sole" in iid,
            uploader_should_match="-co" in iid,
            allow_multiple_names=True,
        )

    if iid.startswith("kra1-c-adviser"):
        return IdentityProfile(
            mode="adviser",
            display_label="Research Adviser",
            preferred_ocr_labels=("Adviser", "Thesis Adviser", "Faculty Name", "Research Adviser"),
            require_named_party=True,
            uploader_must_match=True,
            uploader_should_match=False,
            allow_multiple_names=False,
        )
    if iid.startswith("kra1-c-panel"):
        return IdentityProfile(
            mode="panel_member",
            display_label="Panel Member",
            preferred_ocr_labels=("Panel Member", "Panelist", "Examiner", "Faculty Name"),
            require_named_party=False,
            uploader_must_match=False,
            uploader_should_match=True,
            allow_multiple_names=True,
        )
    if iid.startswith("kra1-c-mentor"):
        return IdentityProfile(
            mode="mentor",
            display_label="Mentor / Coach",
            preferred_ocr_labels=("Mentor", "Coach", "Faculty Name"),
            require_named_party=True,
            uploader_must_match=True,
            uploader_should_match=False,
            allow_multiple_names=False,
        )

    # KRA II — Research
    if iid == "kra2-a-cite":
        return IdentityProfile(
            mode="citation",
            display_label="Cited Researcher",
            preferred_ocr_labels=("Researcher", "Author(s)", "Faculty Name"),
            require_named_party=False,
            uploader_must_match=False,
            uploader_should_match=True,
            allow_multiple_names=True,
        )
    if "translation" in iid:
        label = "Lead Researcher" if "sole" in iid or "lead" in iid else "Co-contributor"
        return IdentityProfile(
            mode="program_contributor" if "-co" in iid else "program_lead",
            display_label=label,
            preferred_ocr_labels=("Lead Researcher", "Project Leader", "Contributor(s)", "Researcher"),
            require_named_party=True,
            uploader_must_match="-sole" in iid or "lead" in iid,
            uploader_should_match="-co" in iid,
            allow_multiple_names=True,
        )
    if any(
        token in iid
        for token in ("journal", "book", "chapter", "monograph", "proceeding", "novel", "story", "poetry", "essay")
    ):
        return IdentityProfile(
            mode="publication_author",
            display_label="Author(s)",
            preferred_ocr_labels=("Author(s)", "Co-author(s)", "Researcher"),
            require_named_party=True,
            uploader_must_match="-sole" in iid,
            uploader_should_match="-co" in iid or "co" in iid,
            allow_multiple_names=True,
        )
    if any(token in iid for token in ("patent", "um-", "id-", "variety")) or iid.startswith("kra2-b-patent"):
        return IdentityProfile(
            mode="inventor",
            display_label="Inventor(s)",
            preferred_ocr_labels=("Inventor(s)", "Co-inventor(s)", "Applicant"),
            require_named_party=True,
            uploader_must_match="-sole" in iid,
            uploader_should_match="-co" in iid,
            allow_multiple_names=True,
        )
    if "sw-" in iid or "developer" in iid:
        return IdentityProfile(
            mode="developer",
            display_label="Developer(s)",
            preferred_ocr_labels=("Developer(s)", "Co-developer(s)", "Programmer"),
            require_named_party=True,
            uploader_must_match="-sole" in iid,
            uploader_should_match="-co" in iid,
            allow_multiple_names=True,
        )
    if "comm-" in iid:
        return IdentityProfile(
            mode="inventor",
            display_label="Patent Holder / Inventor",
            preferred_ocr_labels=("Inventor(s)", "Owner", "Faculty Name"),
            require_named_party=True,
            uploader_should_match=True,
            uploader_must_match=False,
            allow_multiple_names=True,
        )
    if any(
        token in iid
        for token in (
            "music",
            "choreo",
            "playwright",
            "visual",
            "arch-design",
            "film",
            "acting",
            "prod-design",
            "conducting",
            "dance-perf",
        )
    ):
        perf = any(token in iid for token in ("perf", "conducting", "acting", "dance-perf"))
        return IdentityProfile(
            mode="performer" if perf else "creative_author",
            display_label="Performer" if perf else "Creator / Author",
            preferred_ocr_labels=(
                ("Performer", "Conductor", "Artist", "Author(s)", "Creator")
                if perf
                else ("Artist", "Author(s)", "Composer", "Choreographer", "Creator")
            ),
            require_named_party=True,
            uploader_must_match="-sole" in iid and not perf,
            uploader_should_match="-co" in iid or perf,
            allow_multiple_names=True,
        )
    if "directing" in iid:
        return IdentityProfile(
            mode="director_role",
            display_label="Director",
            preferred_ocr_labels=("Director", "Faculty Name"),
            require_named_party=True,
            uploader_must_match=True,
            uploader_should_match=False,
            allow_multiple_names=False,
        )

    # KRA III — Extension
    if iid == "kra3-a-linkage":
        return IdentityProfile(
            mode="linkage",
            display_label="Signatory / Partner contact",
            preferred_ocr_labels=("Signatory", "Coordinator", "Faculty Name", "Representative"),
            require_named_party=False,
            uploader_must_match=False,
            uploader_should_match=False,
            allow_multiple_names=True,
        )
    if "income-lead" in iid:
        return IdentityProfile(
            mode="income_lead",
            display_label="Project Leader",
            preferred_ocr_labels=("Project Leader", "Lead", "Coordinator"),
            require_named_party=True,
            uploader_must_match=True,
            uploader_should_match=False,
            allow_multiple_names=False,
        )
    if "income-co" in iid:
        return IdentityProfile(
            mode="income_contributor",
            display_label="Contributor",
            preferred_ocr_labels=("Contributor", "Team Member", "Faculty Name"),
            require_named_party=True,
            uploader_should_match=True,
            uploader_must_match=False,
            allow_multiple_names=True,
        )
    if iid == "kra3-c-satisfaction":
        return IdentityProfile(
            mode="client_satisfaction",
            display_label="Extension Project Lead",
            preferred_ocr_labels=("Project Leader", "Faculty Name", "Coordinator"),
            require_named_party=False,
            uploader_should_match=True,
            uploader_must_match=False,
            allow_multiple_names=False,
        )
    if iid.startswith("kra3-d-"):
        return IdentityProfile(
            mode="admin_designation",
            display_label="Designated Officer",
            preferred_ocr_labels=("Employee Name", "Faculty Name", "Name of Official", "Designation"),
            require_named_party=True,
            uploader_must_match=True,
            uploader_should_match=False,
            allow_multiple_names=False,
        )
    if iid == "kra3-b-ext-head":
        return IdentityProfile(
            mode="extension_head",
            display_label="Project Head",
            preferred_ocr_labels=("Project Head", "Project Leader", "Extension Coordinator"),
            require_named_party=True,
            uploader_must_match=True,
            uploader_should_match=False,
            allow_multiple_names=False,
        )
    if iid == "kra3-b-ext-participant":
        return IdentityProfile(
            mode="extension_participant",
            display_label="Project Participant",
            preferred_ocr_labels=("Participant", "Team Member", "Contributor"),
            require_named_party=True,
            uploader_should_match=True,
            uploader_must_match=False,
            allow_multiple_names=True,
        )
    if any(token in iid for token in ("train-", "consult-", "guest", "host", "column", "judge")):
        return IdentityProfile(
            mode="resource_person",
            display_label="Resource Person / Expert",
            preferred_ocr_labels=(
                "Resource Person",
                "Speaker",
                "Facilitator",
                "Consultant",
                "Judge",
                "Host",
                "Columnist",
                "Faculty Name",
            ),
            require_named_party=True,
            uploader_should_match=True,
            uploader_must_match=False,
            allow_multiple_names=False,
        )
    if "qa-" in iid:
        return IdentityProfile(
            mode="consultant",
            display_label="Assessor / Evaluator",
            preferred_ocr_labels=("Assessor", "Evaluator", "Faculty Name"),
            require_named_party=True,
            uploader_should_match=True,
            uploader_must_match=False,
            allow_multiple_names=False,
        )

    # KRA IV — Professional Development
    if iid.startswith("kra4-a-"):
        return IdentityProfile(
            mode="member",
            display_label="Member Name",
            preferred_ocr_labels=("Member Name", "Faculty Name", "Employee Name"),
            require_named_party=True,
            uploader_must_match=True,
            uploader_should_match=False,
            allow_multiple_names=False,
        )
    if iid.startswith("kra4-c-"):
        return IdentityProfile(
            mode="awardee",
            display_label="Awardee / Recipient",
            preferred_ocr_labels=("Awardee", "Recipient", "Faculty Name"),
            require_named_party=True,
            uploader_must_match=True,
            uploader_should_match=False,
            allow_multiple_names=False,
        )
    if iid.startswith("kra4-d-"):
        return IdentityProfile(
            mode="service_record",
            display_label="Employee Name",
            preferred_ocr_labels=("Employee Name", "Faculty Name", "Name"),
            require_named_party=True,
            uploader_must_match=True,
            uploader_should_match=False,
            allow_multiple_names=False,
        )
    if any(token in iid for token in ("postmaster", "postdoc", "masters", "doctorate")):
        return IdentityProfile(
            mode="graduate",
            display_label="Graduate / Candidate Name",
            preferred_ocr_labels=("Graduate", "Candidate", "Faculty Name", "Employee Name"),
            require_named_party=True,
            uploader_must_match=True,
            uploader_should_match=False,
            allow_multiple_names=False,
        )
    if iid.startswith("kra4-b-part") or "part-local" in iid or "part-intl" in iid:
        return IdentityProfile(
            mode="participant",
            display_label="Participant Name",
            preferred_ocr_labels=("Participant Name", "Participant", "Faculty Name"),
            require_named_party=True,
            uploader_should_match=True,
            uploader_must_match=False,
            allow_multiple_names=False,
        )
    if "paper-" in iid:
        return IdentityProfile(
            mode="publication_author",
            display_label="Presenter / Author",
            preferred_ocr_labels=("Presenter", "Author(s)", "Speaker", "Faculty Name"),
            require_named_party=True,
            uploader_should_match=True,
            uploader_must_match=False,
            allow_multiple_names=True,
        )

    return IdentityProfile(
        mode="generic",
        display_label="Named party",
        preferred_ocr_labels=("Faculty Name", "Employee Name", "Author(s)", "Participant Name"),
        require_named_party=False,
        uploader_must_match=False,
        uploader_should_match=False,
        allow_multiple_names=True,
    )
