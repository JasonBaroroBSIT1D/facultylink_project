from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(180), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="faculty")
    created_at = db.Column(db.DateTime, default=utcnow)

    profile = db.relationship(
        "FacultyProfile", backref="user", uselist=False, cascade="all, delete-orphan"
    )
    documents = db.relationship("Document", backref="owner", cascade="all, delete-orphan")
    notifications = db.relationship(
        "Notification", backref="user", cascade="all, delete-orphan"
    )
    kra_scores = db.relationship("KraScore", backref="user", cascade="all, delete-orphan")
    simulation = db.relationship(
        "RankSimulation", backref="user", uselist=False, cascade="all, delete-orphan"
    )
    requirements = db.relationship(
        "Requirement", backref="user", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class FacultyProfile(db.Model):
    __tablename__ = "faculty_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    full_name = db.Column(db.String(160), nullable=False)
    faculty_id = db.Column(db.String(40), unique=True, nullable=False)
    department = db.Column(db.String(160), nullable=False)
    college = db.Column(db.String(160), nullable=False)
    current_rank = db.Column(db.String(80), nullable=False)
    highest_degree = db.Column(db.String(160), nullable=False)
    specialization = db.Column(db.String(160), nullable=False)
    years_in_service = db.Column(db.Integer, nullable=False, default=0)
    employment_status = db.Column(db.String(40), nullable=False)
    campus = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(40), nullable=False)

    def to_dict(self):
        return {
            "fullName": self.full_name,
            "facultyId": self.faculty_id,
            "email": self.user.email,
            "department": self.department,
            "college": self.college,
            "currentRank": self.current_rank,
            "highestDegree": self.highest_degree,
            "specialization": self.specialization,
            "yearsInService": self.years_in_service,
            "employmentStatus": self.employment_status,
            "campus": self.campus,
            "phone": self.phone,
        }


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(40), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    kra = db.Column(db.String(40), nullable=False)
    submitted_at = db.Column(db.DateTime, default=utcnow)
    status = db.Column(db.String(40), nullable=False, default="pendingReview")
    points = db.Column(db.Integer, nullable=False, default=0)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(400))
    file_hash = db.Column(db.String(64))
    author = db.Column(db.String(200))
    extracted_info = db.Column(db.JSON, default=dict)
    extracted_text = db.Column(db.Text)
    reviewer_feedback = db.Column(db.Text)
    validation_result = db.Column(db.String(255))
    author_count = db.Column(db.Integer, default=1)
    base_points = db.Column(db.Integer, default=0)
    flagged_for_review = db.Column(db.Boolean, default=False)
    # Shared with web reviewer pipeline (same Postgres columns).
    indicator_id = db.Column(db.String(80))
    reviewer_score = db.Column(db.Float)
    reviewer_remarks = db.Column(db.Text)
    review_snapshot = db.Column(db.Text)
    decided_at = db.Column(db.String(40))

    def to_dict(self):
        return {
            "id": self.public_id,
            "title": self.title,
            "category": self.category,
            "kra": self.kra,
            "submittedAt": self.submitted_at.isoformat() if self.submitted_at else None,
            "status": self.status,
            "points": self.points,
            "fileName": self.file_name,
            "author": self.author,
            "extractedInfo": self.extracted_info or {},
            "reviewerFeedback": self.reviewer_feedback,
            "validationResult": self.validation_result,
            "indicatorId": self.indicator_id,
            "reviewerScore": self.reviewer_score,
        }


class KraScore(db.Model):
    __tablename__ = "kra_scores"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    kra = db.Column(db.String(40), nullable=False)
    current_points = db.Column(db.Integer, nullable=False, default=0)
    target_points = db.Column(db.Integer, nullable=False, default=20)
    document_count = db.Column(db.Integer, nullable=False, default=0)
    status_label = db.Column(db.String(40), nullable=False, default="In progress")
    breakdown = db.Column(db.JSON, default=list)

    def to_dict(self):
        return {
            "type": self.kra,
            "currentPoints": self.current_points,
            "targetPoints": self.target_points,
            "documentCount": self.document_count,
            "statusLabel": self.status_label,
            "breakdown": self.breakdown or [],
        }


class RankSimulation(db.Model):
    __tablename__ = "rank_simulations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    current_rank = db.Column(db.String(80), nullable=False)
    target_rank = db.Column(db.String(80), nullable=False)
    current_points = db.Column(db.Integer, nullable=False, default=0)
    required_points = db.Column(db.Integer, nullable=False, default=100)
    eligibility_label = db.Column(db.String(80), nullable=False, default="Pending")
    areas_to_improve = db.Column(db.JSON, default=list)
    kra_config_version = db.Column(db.Integer, nullable=False, default=0)
    scoring_formula = db.Column(
        db.String(160),
        nullable=False,
        default="Final Score = Base Points × Contribution Percentage",
    )
    config_snapshot = db.Column(db.JSON, default=dict)
    history = db.Column(db.JSON, default=list)

    def to_dict(self):
        remaining = max(self.required_points - self.current_points, 0)
        progress = (
            0
            if self.required_points == 0
            else min(self.current_points / self.required_points, 1)
        )
        snapshot = self.config_snapshot or {}
        return {
            "currentRank": self.current_rank,
            "targetRank": self.target_rank,
            "currentPoints": self.current_points,
            "requiredPoints": self.required_points,
            "eligibilityLabel": self.eligibility_label,
            "remainingPoints": remaining,
            "progress": progress,
            "areasToImprove": self.areas_to_improve or [],
            "kraConfigVersion": self.kra_config_version or 0,
            "scoringFormula": self.scoring_formula
            or "Weighted Final Score = Σ (KRA points × Table 2.2 rank weight %)",
            "weightBand": snapshot.get("weightBand") or "",
            "appliedWeights": snapshot.get("appliedWeights") or {},
            "kraPoints": snapshot.get("kraPoints") or {},
            "weightedScore": snapshot.get("weightedScore", self.current_points),
        }


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(40), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    kind = db.Column(db.String(60), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    visual_state = db.Column(db.String(30), nullable=False, default="unread")
    related_document_id = db.Column(db.String(40))
    related_kra = db.Column(db.String(40))

    def to_dict(self):
        return {
            "id": self.public_id,
            "kind": self.kind,
            "message": self.message,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "visualState": self.visual_state,
            "relatedDocumentId": self.related_document_id,
            "relatedKra": self.related_kra,
        }


class Requirement(db.Model):
    __tablename__ = "requirements"

    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(40), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    kra = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(40), nullable=False)
    hint = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.public_id,
            "title": self.title,
            "description": self.description,
            "kra": self.kra,
            "status": self.status,
            "hint": self.hint,
        }


class PreparationPeriod(db.Model):
    __tablename__ = "preparation_periods"

    id = db.Column(db.Integer, primary_key=True)
    cycle_name = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reviewer_available_until = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="closingSoon")
    is_current = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            "cycleName": self.cycle_name,
            "startDate": self.start_date.isoformat(),
            "endDate": self.end_date.isoformat(),
            "reviewerAvailableUntil": self.reviewer_available_until.isoformat(),
            "status": self.status,
        }


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_email = db.Column(db.String(180), nullable=False)
    action = db.Column(db.String(80), nullable=False)
    detail = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)

    def to_dict(self):
        return {
            "actorEmail": self.actor_email,
            "action": self.action,
            "detail": self.detail,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


class ScoringRule(db.Model):
    __tablename__ = "scoring_rules"

    id = db.Column(db.Integer, primary_key=True)
    kra = db.Column(db.String(40), unique=True, nullable=False)
    base_points = db.Column(db.Integer, nullable=False, default=5)
    keywords = db.Column(db.JSON, default=list)

    def to_dict(self):
        return {
            "kra": self.kra,
            "basePoints": self.base_points,
            "keywords": self.keywords or [],
        }


class RegistrationRequest(db.Model):
    __tablename__ = "registration_requests"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(180), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    status = db.Column(db.String(20), default="pending")
