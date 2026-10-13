from datetime import date, datetime

from models import (
    Document,
    FacultyProfile,
    KraScore,
    Notification,
    PreparationPeriod,
    RankSimulation,
    Requirement,
    ScoringRule,
    User,
    db,
)


def seed_if_empty():
    if User.query.filter_by(email="maria.santos@university.edu.ph").first():
        return

    faculty = User(email="maria.santos@university.edu.ph", role="faculty")
    faculty.set_password("password123")
    reviewer = User(email="elena.cruz@university.edu.ph", role="reviewer")
    reviewer.set_password("reviewer123")
    admin = User(email="admin@university.edu.ph", role="admin")
    admin.set_password("admin123")
    db.session.add_all([faculty, reviewer, admin])
    db.session.flush()

    db.session.add(
        FacultyProfile(
            user_id=faculty.id,
            full_name="Maria Santos",
            faculty_id="FL-2024-0847",
            department="Department of Curriculum and Instruction",
            college="College of Education",
            current_rank="Instructor I",
            highest_degree="Master of Arts in Education",
            specialization="Curriculum and Instruction",
            years_in_service=4,
            employment_status="Permanent",
            campus="Main Campus",
            phone="+63 917 555 0847",
        )
    )

    documents = [
        dict(
            public_id="doc-001",
            title="Course Syllabus — ED 101, SY 2025–2026",
            category="teachingRecords",
            kra="instruction",
            submitted_at=datetime(2026, 8, 12),
            status="validated",
            points=8,
            file_name="ED101_Syllabus_SY2025-2026.pdf",
            author="Maria Santos",
            extracted_info={
                "Document type": "Course syllabus",
                "Course": "ED 101 — Foundations of Education",
                "Academic year": "SY 2025–2026",
            },
            validation_result="Document matches the submitted teaching record.",
        ),
        dict(
            public_id="doc-002",
            title="Student Evaluation Summary, 1st Sem AY 2025–2026",
            category="teachingRecords",
            kra="instruction",
            submitted_at=datetime(2026, 8, 10),
            status="validated",
            points=6,
            file_name="SET_Summary_1S_2025.pdf",
            author="Office of Academic Affairs",
            extracted_info={
                "Instrument": "Student Evaluation of Teaching",
                "Mean rating": "4.62 / 5.00",
            },
            validation_result="Official evaluation summary verified.",
        ),
        dict(
            public_id="doc-003",
            title="Classroom Observation Report",
            category="teachingRecords",
            kra="instruction",
            submitted_at=datetime(2026, 8, 27),
            status="pendingReview",
            points=5,
            file_name="Classroom_Observation_Aug2026.pdf",
            author="Dept. Chair, Curriculum and Instruction",
            extracted_info={"Observer": "Prof. Elena Cruz"},
            validation_result="Awaiting reviewer confirmation.",
            flagged_for_review=True,
        ),
        dict(
            public_id="doc-004",
            title="Journal Article: Inquiry-Based Learning in Basic Education",
            category="researchPublications",
            kra="research",
            submitted_at=datetime(2026, 8, 4),
            status="validated",
            points=10,
            file_name="Santos_Inquiry_Based_Learning_2025.pdf",
            author="Maria Santos",
            extracted_info={"ISSN": "2244-1180", "Year": "2025"},
            validation_result="Peer-reviewed publication accepted as research evidence.",
        ),
        dict(
            public_id="doc-005",
            title="Research Presentation Certificate — National Research Forum",
            category="researchPublications",
            kra="research",
            submitted_at=datetime(2026, 8, 20),
            status="needsRevision",
            points=0,
            file_name="NRF_Presentation_Certificate.pdf",
            author="Maria Santos",
            extracted_info={"Event": "National Research Forum 2026"},
            reviewer_feedback="Please attach the official conference program showing your paper title.",
            validation_result="Incomplete supporting evidence.",
            flagged_for_review=True,
        ),
        dict(
            public_id="doc-006",
            title="Community Literacy Program Completion Report",
            category="extensionDocuments",
            kra="extension",
            submitted_at=datetime(2026, 7, 28),
            status="validated",
            points=8,
            file_name="Literacy_Program_Report_2026.pdf",
            author="Maria Santos; Barangay San Isidro",
            extracted_info={"Beneficiaries": "42 parents"},
            validation_result="Extension output verified.",
        ),
        dict(
            public_id="doc-007",
            title="Barangay Training Facilitation Certificate",
            category="extensionDocuments",
            kra="extension",
            submitted_at=datetime(2026, 8, 22),
            status="pendingReview",
            points=6,
            file_name="Brgy_Training_Facilitation.pdf",
            author="LGU San Isidro",
            extracted_info={"Role": "Lead facilitator"},
            validation_result="Awaiting reviewer confirmation.",
            flagged_for_review=True,
        ),
        dict(
            public_id="doc-008",
            title="TESDA National Certificate — Bookkeeping",
            category="certifications",
            kra="professionalDevelopment",
            submitted_at=datetime(2026, 6, 15),
            status="validated",
            points=5,
            file_name="TESDA_NC_Bookkeeping.pdf",
            author="TESDA",
            extracted_info={"Credential": "National Certificate II"},
            validation_result="National certification accepted.",
        ),
        dict(
            public_id="doc-009",
            title="CHED Seminar on Outcomes-Based Education",
            category="trainingCertificates",
            kra="professionalDevelopment",
            submitted_at=datetime(2026, 8, 26),
            status="processing",
            points=0,
            file_name="CHED_OBE_Seminar_Certificate.jpg",
            author="Commission on Higher Education",
            extracted_info={"Status": "Queued for processing"},
            validation_result="Queued for processing.",
        ),
        dict(
            public_id="doc-010",
            title="Thesis Advisership Record — Graduate School",
            category="advisershipRecords",
            kra="instruction",
            submitted_at=datetime(2026, 8, 8),
            status="invalid",
            points=0,
            file_name="Advisership_Scan.jpg",
            author="Maria Santos",
            reviewer_feedback="The scan is unreadable. Upload the signed advisership certificate.",
            validation_result="Document could not be validated.",
            flagged_for_review=True,
        ),
        dict(
            public_id="doc-011",
            title="Instructional Materials Portfolio (Draft)",
            category="teachingRecords",
            kra="instruction",
            submitted_at=datetime(2026, 8, 18),
            status="needsRevision",
            points=0,
            file_name="IM_Portfolio_Draft.pdf",
            author="Maria Santos",
            reviewer_feedback="Include materials for at least two courses and a chair endorsement.",
            validation_result="Incomplete instructional materials set.",
            flagged_for_review=True,
        ),
    ]
    for item in documents:
        db.session.add(Document(user_id=faculty.id, **item))

    scores = [
        (
            "instruction",
            25,
            30,
            4,
            "On track",
            [
                {"title": "Teaching effectiveness", "points": 10, "note": "SET and observation reports"},
                {"title": "Instructional materials", "points": 8, "note": "Course syllabi"},
                {"title": "Student advising", "points": 7, "note": "Advisership records"},
            ],
        ),
        (
            "research",
            18,
            30,
            2,
            "Needs attention",
            [
                {"title": "Refereed publication", "points": 10, "note": "Journal article"},
                {"title": "Research presentation", "points": 8, "note": "Needs revised certificate"},
            ],
        ),
        (
            "extension",
            14,
            20,
            2,
            "In progress",
            [
                {"title": "Community literacy program", "points": 8, "note": "Completed report"},
                {"title": "Barangay training", "points": 6, "note": "Pending validation"},
            ],
        ),
        (
            "professionalDevelopment",
            15,
            20,
            2,
            "On track",
            [
                {"title": "National certification", "points": 5, "note": "TESDA NC"},
                {"title": "Seminars and training", "points": 10, "note": "CHED certificates"},
            ],
        ),
    ]
    for kra, current, target, count, label, breakdown in scores:
        db.session.add(
            KraScore(
                user_id=faculty.id,
                kra=kra,
                current_points=current,
                target_points=target,
                document_count=count,
                status_label=label,
                breakdown=breakdown,
            )
        )

    db.session.add(
        RankSimulation(
            user_id=faculty.id,
            current_rank="Instructor I",
            target_rank="Instructor II",
            current_points=72,
            required_points=100,
            eligibility_label="Potentially Eligible",
            areas_to_improve=[
                {
                    "kra": "instruction",
                    "recommendedPoints": 5,
                    "guidance": "Add a complete instructional materials portfolio.",
                },
                {
                    "kra": "research",
                    "recommendedPoints": 8,
                    "guidance": "Revise the conference certificate.",
                },
                {
                    "kra": "professionalDevelopment",
                    "recommendedPoints": 3,
                    "guidance": "Upload the latest in-service training certificate.",
                },
            ],
        )
    )

    notes = [
        ("n-001", "documentNeedsRevision", "Research Presentation Certificate needs a conference program.", "actionRequired", "doc-005", "research"),
        ("n-002", "missingRequirement", "Instruction is missing a complete instructional materials portfolio.", "unread", None, "instruction"),
        ("n-003", "documentSubmitted", "Classroom Observation Report was submitted and is pending review.", "unread", "doc-003", None),
        ("n-004", "reviewerFeedback", "A reviewer left comments on Thesis Advisership Record.", "actionRequired", "doc-010", None),
        ("n-005", "documentValidated", "Journal Article has been validated (+10 points).", "read", "doc-004", None),
        ("n-006", "kraScoreUpdated", "Your Instruction KRA preview is now 25 points.", "read", None, "instruction"),
        ("n-007", "rankSimulationUpdated", "Rank upgrade simulation refreshed. You are 28 points from Instructor II.", "read", None, None),
    ]
    for public_id, kind, message, state, doc_id, kra in notes:
        db.session.add(
            Notification(
                public_id=public_id,
                user_id=faculty.id,
                kind=kind,
                message=message,
                visual_state=state,
                related_document_id=doc_id,
                related_kra=kra,
                created_at=datetime(2026, 8, 27, 9, 15),
            )
        )

    requirements = [
        ("req-i-1", "Student evaluation of teaching", "Official SET summary for the latest rating period.", "instruction", "completed", None),
        ("req-i-2", "Course syllabus", "Updated syllabus for a handled course.", "instruction", "completed", None),
        ("req-i-3", "Classroom observation", "Signed observation report.", "instruction", "pending", "Pending review."),
        ("req-i-4", "Instructional materials portfolio", "Endorsed set covering at least two courses.", "instruction", "needsRevision", "Revise using reviewer comments."),
        ("req-r-1", "Refereed research publication", "Peer-reviewed journal article.", "research", "completed", None),
        ("req-r-2", "Research presentation", "Certificate plus official program.", "research", "needsRevision", "Attach the conference program."),
        ("req-r-3", "Additional research output", "A second refereed output.", "research", "missing", "Largest remaining gap."),
        ("req-e-1", "Completed extension program", "Narrative report and attendance.", "extension", "completed", None),
        ("req-e-2", "Community training or service", "Certificate of facilitated training.", "extension", "pending", None),
        ("req-e-3", "Impact or sustainability note", "Short outcomes statement.", "extension", "missing", None),
        ("req-p-1", "National or professional certification", "Valid national certificate.", "professionalDevelopment", "completed", None),
        ("req-p-2", "Relevant seminar or training", "Recent CHED or university training.", "professionalDevelopment", "pending", "OBE seminar is still processing."),
        ("req-p-3", "Membership or continuing education", "Proof of membership or CEUs.", "professionalDevelopment", "missing", None),
    ]
    for public_id, title, description, kra, status, hint in requirements:
        db.session.add(
            Requirement(
                public_id=public_id,
                user_id=faculty.id,
                title=title,
                description=description,
                kra=kra,
                status=status,
                hint=hint,
            )
        )

    for kra, points, keywords in (
        ("instruction", 8, ["teaching", "course", "instruction", "syllabus", "classroom"]),
        ("research", 10, ["journal", "issn", "publication", "article", "research"]),
        ("extension", 8, ["community", "outreach", "extension", "barangay", "literacy"]),
        ("professionalDevelopment", 5, ["training", "seminar", "certificate", "tesda", "ched"]),
    ):
        db.session.add(ScoringRule(kra=kra, base_points=points, keywords=keywords))

    db.session.add(
        PreparationPeriod(
            cycle_name="AY 2025–2026 Evaluation Preparation Cycle",
            start_date=date(2026, 6, 2),
            end_date=date(2026, 9, 15),
            reviewer_available_until=date(2026, 9, 12),
            status="closingSoon",
            is_current=True,
        )
    )
    db.session.commit()
