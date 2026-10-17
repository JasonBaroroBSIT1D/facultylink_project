from datetime import datetime, timezone
from functools import wraps
from uuid import uuid4

import mimetypes
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
)

from config import Config
from kra_catalog import catalog_for_api, criterion_for_indicator, validate_selection
from models import (
    AuditLog,
    Document,
    KraScore,
    Notification,
    PreparationPeriod,
    RankSimulation,
    RegistrationRequest,
    ScoringRule,
    User,
    db,
)
from kra_config import load_active_kra_config
from schedule import preparation_period_payload
from scoring import process_upload, refresh_user_scores
from sqlalchemy import text

app = Flask(__name__)
app.config.from_object(Config)
app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)
CORS(app, resources={r"/api/*": {"origins": "*"}})
db.init_app(app)
JWTManager(app)


def ensure_shared_schema():
    """Add columns the shared DB may already have from the web backend."""
    statements = [
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS indicator_id VARCHAR(80)",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS criterion_id VARCHAR(80)",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS mime_type VARCHAR(120)",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_size INTEGER",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS reviewer_score DOUBLE PRECISION",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS reviewer_remarks TEXT",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS review_snapshot TEXT",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS decided_at VARCHAR(40)",
        "ALTER TABLE rank_simulations ADD COLUMN IF NOT EXISTS kra_config_version INTEGER DEFAULT 0",
        "ALTER TABLE rank_simulations ADD COLUMN IF NOT EXISTS scoring_formula VARCHAR(160)",
        "ALTER TABLE rank_simulations ADD COLUMN IF NOT EXISTS config_snapshot JSON",
        "ALTER TABLE rank_simulations ADD COLUMN IF NOT EXISTS history JSON",
    ]
    for sql in statements:
        try:
            db.session.execute(text(sql))
            db.session.commit()
        except Exception:
            db.session.rollback()


def sync_user_scores(user: User):
    """Recompute KRA totals and Rank Simulation from the active published config."""
    refresh_user_scores(user, Document, KraScore, RankSimulation, db)
    db.session.commit()
    return user.simulation


def current_user():
    identity = get_jwt_identity()
    if not identity:
        return None
    return db.session.get(User, int(identity))


def faculty_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or user.role != "faculty":
            return jsonify({"error": "Faculty access required."}), 403
        return fn(user, *args, **kwargs)

    return wrapper


def staff_jwt_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or user.role not in {"reviewer", "admin"}:
            return jsonify({"error": "Staff access required."}), 403
        return fn(user, *args, **kwargs)

    return wrapper


def admin_jwt_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or user.role != "admin":
            return jsonify({"error": "Admin access required."}), 403
        return fn(user, *args, **kwargs)

    return wrapper


def _award_points(doc: Document, points, contribution_percent, rating) -> float:
    from scoring import score_indicator

    if points is not None and points != "":
        awarded = float(points)
    else:
        info = doc.extracted_info or {}
        raw_share = contribution_percent
        if raw_share is None and info.get("Contribution percent"):
            try:
                raw_share = float(info.get("Contribution percent"))
            except (TypeError, ValueError):
                raw_share = None
        scored = score_indicator(
            doc.indicator_id,
            contribution_percent=raw_share,
            rating=rating,
            authors=doc.author_count or 1,
            config=load_active_kra_config(db),
        )
        awarded = float(scored["points"] or doc.points or 0)
    cap_source = score_indicator(
        doc.indicator_id,
        contribution_percent=100,
        rating=100,
        authors=1,
        config=load_active_kra_config(db),
    )
    if cap_source.get("max_points") is not None:
        awarded = min(awarded, float(cap_source["max_points"]))
    return max(awarded, 0.0)


def apply_review(
    doc: Document,
    action: str,
    feedback: str | None,
    points,
    *,
    indicator_id: str | None = None,
    contribution_percent=None,
    rating=None,
):
    if indicator_id:
        doc.indicator_id = indicator_id
    if action in {"validate", "correct"}:
        awarded = _award_points(doc, points, contribution_percent, rating)
        doc.status = "validated"
        doc.points = int(round(awarded))
        doc.reviewer_score = awarded
        doc.reviewer_feedback = feedback or None
        doc.validation_result = (
            "Corrected and validated by reviewer."
            if action == "correct"
            else "Validated by reviewer."
        )
        info = dict(doc.extracted_info or {})
        info["Verified score"] = str(awarded)
        if contribution_percent not in (None, ""):
            info["Contribution percent"] = str(contribution_percent)
        doc.extracted_info = info
        add_notification(
            doc.user_id,
            "documentValidated",
            f"{doc.title} has been {'corrected' if action == 'correct' else 'validated'} (+{doc.points} points).",
            document_id=doc.public_id,
            kra=doc.kra,
        )
    elif action == "revise":
        doc.status = "needsRevision"
        doc.points = 0
        doc.reviewer_score = None
        doc.reviewer_feedback = feedback or "Please revise and resubmit."
        doc.validation_result = "Returned for revision."
        add_notification(
            doc.user_id,
            "documentNeedsRevision",
            f"{doc.title} needs revision.",
            document_id=doc.public_id,
            kra=doc.kra,
            state="actionRequired",
        )
    elif action == "reject":
        doc.status = "invalid"
        doc.points = 0
        doc.reviewer_score = None
        doc.reviewer_feedback = feedback or "This file could not be validated."
        doc.validation_result = "Rejected by reviewer."
        add_notification(
            doc.user_id,
            "reviewerFeedback",
            f"A reviewer left comments on {doc.title}.",
            document_id=doc.public_id,
            state="actionRequired",
        )
    elif action == "reopen":
        doc.status = "pendingReview"
        doc.reviewer_score = None
        doc.decided_at = None
        info = dict(doc.extracted_info or {})
        info.pop("Verified score", None)
        try:
            provisional = float(info.get("Provisional score") or doc.base_points or 0)
        except (TypeError, ValueError):
            provisional = float(doc.base_points or 0)
        doc.points = int(round(provisional))
        doc.reviewer_feedback = feedback or "Reopened. The provisional score is visible again until the next decision."
        doc.validation_result = "Reopened for review."
        doc.extracted_info = info
        add_notification(
            doc.user_id,
            "documentSubmitted",
            f"{doc.title} was reopened and is pending review again.",
            document_id=doc.public_id,
            kra=doc.kra,
        )
    else:
        return False
    refresh_user_scores(doc.owner, Document, KraScore, RankSimulation, db)
    return True


def write_audit(email: str, action: str, detail: str | None = None):
    db.session.add(AuditLog(actor_email=email, action=action, detail=detail))


def add_notification(user_id, kind, message, document_id=None, kra=None, state="unread"):
    db.session.add(
        Notification(
            public_id=f"n-{uuid4().hex[:10]}",
            user_id=user_id,
            kind=kind,
            message=message,
            visual_state=state,
            related_document_id=document_id,
            related_kra=kra,
        )
    )


def dashboard_payload(user: User):
    sync_user_scores(user)
    docs = user.documents
    validated = [d for d in docs if d.status == "validated"]
    pending = [d for d in docs if d.status == "pendingReview"]
    action = [d for d in docs if d.status in {"needsRevision", "invalid"}]
    scores = [row.to_dict() for row in user.kra_scores]
    total = sum(row.current_points for row in user.kra_scores)
    target = sum(row.target_points for row in user.kra_scores) or 100
    recent = sorted(docs, key=lambda d: d.submitted_at or datetime.min, reverse=True)[:3]
    feedback = [
        {
            "documentTitle": doc.title,
            "message": doc.reviewer_feedback,
            "timeLabel": "Recently",
        }
        for doc in docs
        if doc.reviewer_feedback
    ][:2]
    period = PreparationPeriod.query.filter_by(is_current=True).first()
    return {
        "totalPoints": total,
        "targetPoints": target,
        "documentCompletionPercent": round((len(validated) / len(docs)) * 100) if docs else 0,
        "validatedCount": len(validated),
        "pendingCount": len(pending),
        "actionRequiredCount": len(action),
        "kraScores": scores,
        "recentActivity": [
            {
                "title": doc.title,
                "subtitle": f"{doc.kra} · {doc.status}",
                "timeLabel": doc.submitted_at.date().isoformat() if doc.submitted_at else "",
                "status": doc.status,
            }
            for doc in recent
        ],
        "recentFeedback": feedback,
        "simulation": user.simulation.to_dict() if user.simulation else None,
        "preparationPeriod": preparation_period_payload(db, period),
        "kraConfig": {
            "version": (user.simulation.kra_config_version if user.simulation else 0) or 0,
            "formula": (user.simulation.scoring_formula if user.simulation else None)
            or "Final Score = Base Points × Contribution Percentage",
        },
    }


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password."}), 401
    if user.role != "faculty":
        return jsonify({"error": "Staff accounts sign in through the web app."}), 403
    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "email": user.email},
    )
    write_audit(user.email, "login", "Faculty signed in")
    db.session.commit()
    return jsonify({"accessToken": token, "profile": user.profile.to_dict()})


@app.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("fullName") or "").strip()
    email = (data.get("email") or "").strip().lower()
    if not name or not email:
        return jsonify({"error": "Name and email are required."}), 400
    db.session.add(RegistrationRequest(full_name=name, email=email))
    write_audit(email, "register_request", name)
    db.session.commit()
    return jsonify(
        {
            "message": "Faculty accounts are issued by your institution. This request was recorded."
        }
    ), 201


@app.get("/api/me")
@faculty_required
def me(user):
    return jsonify(user.profile.to_dict())


@app.patch("/api/me/profile")
@faculty_required
def update_profile(user):
    data = request.get_json(silent=True) or {}
    profile = user.profile
    profile.full_name = data.get("fullName", profile.full_name)
    profile.phone = data.get("phone", profile.phone)
    profile.department = data.get("department", profile.department)
    if data.get("email"):
        user.email = data["email"].strip().lower()
    write_audit(user.email, "update_profile")
    db.session.commit()
    return jsonify(profile.to_dict())


@app.get("/api/dashboard")
@faculty_required
def dashboard(user):
    return jsonify(dashboard_payload(user))


@app.get("/api/documents")
@faculty_required
def list_documents(user):
    docs = sorted(user.documents, key=lambda d: d.submitted_at or datetime.min, reverse=True)
    return jsonify([doc.to_dict() for doc in docs])


@app.get("/api/documents/<public_id>")
@faculty_required
def get_document(user, public_id):
    doc = Document.query.filter_by(user_id=user.id, public_id=public_id).first()
    if not doc:
        return jsonify({"error": "Document not found."}), 404
    return jsonify(doc.to_dict())


@app.get("/api/kra-catalog")
@jwt_required()
def kra_catalog():
    """Annex I hierarchy for upload forms (structure only; scoring stays in kra_settings)."""
    return jsonify(catalog_for_api())


@app.post("/api/documents")
@faculty_required
def create_document(user):
    category = request.form.get("category") or "supportingEvidence"
    kra = request.form.get("kra") or "instruction"
    author = (request.form.get("author") or "").strip()
    indicator_id = (request.form.get("indicatorId") or "").strip() or None
    criterion_id = (request.form.get("criterionId") or "").strip() or None
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "A document file is required."}), 400

    ok, message = validate_selection(
        kra=kra, criterion_id=criterion_id, indicator_id=indicator_id
    )
    if not ok:
        return jsonify({"error": message}), 400
    if indicator_id and not criterion_id:
        criterion_id = criterion_for_indicator(indicator_id)

    contribution_raw = (request.form.get("contributionPercent") or "").strip()
    rating_raw = (request.form.get("rating") or "").strip()
    contribution_percent = None
    rating = None
    if contribution_raw:
        try:
            contribution_percent = float(contribution_raw)
        except ValueError:
            return jsonify({"error": "Contribution percentage must be a number from 0 to 100."}), 400
        if contribution_percent < 0 or contribution_percent > 100:
            return jsonify({"error": "Contribution percentage must be from 0 to 100."}), 400
    if rating_raw:
        try:
            rating = float(rating_raw)
        except ValueError:
            return jsonify({"error": "Rating must be a number from 0 to 100."}), 400

    file_name = request.form.get("fileName") or uploaded.filename
    # Title defaults to the uploaded filename (without extension).
    title = (request.form.get("title") or "").strip() or Path(file_name).stem.replace("_", " ").replace("-", " ").strip()
    if not title:
        return jsonify({"error": "Title is required."}), 400
    safe = f"{uuid4().hex}_{Path(file_name).name}"
    upload_dir = Path(app.config["UPLOAD_FOLDER"]).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = (upload_dir / safe).resolve()
    uploaded.save(saved_path)
    mime_type = uploaded.mimetype or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    file_size = saved_path.stat().st_size if saved_path.exists() else None

    # Keep faculty-selected KRA; OCR still assists reviewer validation.
    processed = process_upload(
        title=title,
        author=author,
        file_path=str(saved_path),
        declared_kra=kra,
        indicator_id=indicator_id,
        contribution_percent=contribution_percent,
        rating=rating,
        config=load_active_kra_config(db),
    )
    if processed["file_hash"]:
        duplicate = Document.query.filter_by(
            user_id=user.id, file_hash=processed["file_hash"]
        ).first()
        if duplicate:
            try:
                saved_path.unlink(missing_ok=True)
            except OSError:
                pass
            return jsonify({"error": "Duplicate document ignored.", "existingId": duplicate.public_id}), 409

    doc = Document(
        public_id=f"doc-{uuid4().hex[:8]}",
        user_id=user.id,
        title=title,
        category=category,
        kra=kra,
        submitted_at=datetime.now(timezone.utc),
        status=processed["status"],
        points=processed["points"],
        file_name=file_name,
        file_path=str(saved_path),  # absolute path so web/mobile can both resolve it
        file_hash=processed["file_hash"],
        author=author or None,
        extracted_info=processed["extracted_info"],
        extracted_text=processed["extracted_text"],
        validation_result=processed["validation_result"],
        author_count=processed["author_count"],
        base_points=int(round(processed["base_points"] or 0)),
        flagged_for_review=processed["flagged_for_review"],
        indicator_id=indicator_id,
        criterion_id=criterion_id,
        mime_type=mime_type,
        file_size=file_size,
    )
    db.session.add(doc)
    add_notification(
        user.id,
        "documentSubmitted",
        f"{title} was submitted and is pending review.",
        document_id=doc.public_id,
        kra=doc.kra,
    )
    write_audit(user.email, "upload_document", title)
    db.session.flush()
    sync_user_scores(user)
    db.session.commit()
    return jsonify(doc.to_dict()), 201


def _authorized_document(user, public_id):
    doc = Document.query.filter_by(public_id=public_id).first()
    if not doc:
        return None, (jsonify({"error": "Document not found."}), 404)
    if user.role == "admin":
        return doc, None
    if user.role == "faculty":
        if doc.user_id != user.id:
            return None, (jsonify({"error": "Not authorized to access this document."}), 403)
        return doc, None
    if user.role == "reviewer":
        return doc, None
    return None, (jsonify({"error": "Not authorized to access this document."}), 403)


@app.get("/api/documents/<public_id>/file")
@jwt_required()
def download_document_file(public_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Authentication required."}), 401
    doc, err = _authorized_document(user, public_id)
    if err:
        return err
    file_path = _resolve_upload_path(doc.file_path)
    if not file_path:
        return jsonify({"error": "Original file is not available."}), 404
    mime = doc.mime_type or mimetypes.guess_type(doc.file_name or str(file_path))[0] or "application/octet-stream"
    return send_file(
        file_path,
        mimetype=mime,
        as_attachment=False,
        download_name=doc.file_name or file_path.name,
        max_age=0,
    )


def _resolve_upload_path(stored: str | None) -> Path | None:
    """Resolve absolute or relative upload paths from the shared uploads folder."""
    if not stored:
        return None
    candidate = Path(stored)
    if candidate.is_file():
        return candidate.resolve()
    upload_dir = Path(app.config["UPLOAD_FOLDER"]).resolve()
    relative = candidate.name if candidate.is_absolute() else candidate
    alt = (upload_dir / relative).resolve()
    if alt.is_file():
        return alt
    # Also try basename inside uploads (legacy relative paths like uploads\\file.pdf).
    alt2 = (upload_dir / Path(stored).name).resolve()
    if alt2.is_file():
        return alt2
    return None


@app.post("/api/documents/<public_id>/process")
@faculty_required
def reprocess_document(user, public_id):
    doc = Document.query.filter_by(user_id=user.id, public_id=public_id).first()
    if not doc:
        return jsonify({"error": "Document not found."}), 404
    processed = process_upload(
        title=doc.title,
        author=doc.author,
        file_path=doc.file_path,
        declared_kra=doc.kra,
        indicator_id=doc.indicator_id,
        config=load_active_kra_config(db),
    )
    doc.points = processed["points"]
    doc.extracted_info = processed["extracted_info"]
    doc.extracted_text = processed["extracted_text"]
    doc.file_hash = processed["file_hash"] or doc.file_hash
    doc.flagged_for_review = processed["flagged_for_review"]
    doc.validation_result = processed["validation_result"]
    doc.status = "pendingReview"
    write_audit(user.email, "reprocess_document", doc.public_id)
    sync_user_scores(user)
    db.session.commit()
    return jsonify(doc.to_dict())


@app.get("/api/assessment/kra-scores")
@faculty_required
def kra_scores(user):
    sync_user_scores(user)
    return jsonify([row.to_dict() for row in user.kra_scores])


@app.get("/api/assessment/requirements")
@faculty_required
def requirements(user):
    return jsonify([row.to_dict() for row in user.requirements])


@app.get("/api/kra-config")
@faculty_required
def kra_config(user):
    """Active published KRA configuration from the shared database."""
    config = load_active_kra_config(db)
    return jsonify(
        {
            "version": config["version"],
            "status": config["status"],
            "publishedAt": config["publishedAt"],
            "formula": config["formula"],
            "weightedFormula": config.get("weightedFormula"),
            "targets": config["targets"],
            "requiredPoints": config["requiredPoints"],
            "criteria": config["criteria"],
            "indicators": config["indicators"],
            "rankWeights": config["rankWeights"],
        }
    )


@app.get("/api/simulation")
@faculty_required
def simulation(user):
    sim = sync_user_scores(user)
    return jsonify(sim.to_dict() if sim else {})


@app.get("/api/notifications")
@faculty_required
def notifications(user):
    items = sorted(user.notifications, key=lambda n: n.created_at or datetime.min, reverse=True)
    return jsonify([item.to_dict() for item in items])


@app.post("/api/notifications/<public_id>/read")
@faculty_required
def read_notification(user, public_id):
    item = Notification.query.filter_by(user_id=user.id, public_id=public_id).first()
    if not item:
        return jsonify({"error": "Notification not found."}), 404
    item.visual_state = "read"
    db.session.commit()
    return jsonify(item.to_dict())


@app.post("/api/notifications/read-all")
@faculty_required
def read_all_notifications(user):
    for item in user.notifications:
        item.visual_state = "read"
    db.session.commit()
    return jsonify({"ok": True})


@app.delete("/api/notifications")
@faculty_required
def clear_notifications(user):
    Notification.query.filter_by(user_id=user.id).delete()
    db.session.commit()
    return jsonify({"ok": True})


@app.get("/api/preparation-period")
@jwt_required(optional=True)
def preparation_period():
    period = PreparationPeriod.query.filter_by(is_current=True).first()
    payload = preparation_period_payload(db, period)
    if not payload:
        return jsonify({"error": "No current preparation period."}), 404
    return jsonify(payload)


@app.post("/api/auth/staff-login")
def staff_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password) or user.role not in {"reviewer", "admin"}:
        return jsonify({"error": "Invalid staff credentials."}), 401
    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "email": user.email},
    )
    write_audit(user.email, "staff_login_api")
    db.session.commit()
    return jsonify({"accessToken": token, "role": user.role, "email": user.email})


@app.get("/api/review/queue")
@staff_jwt_required
def review_queue_api(user):
    queue = (
        Document.query.filter(Document.status.in_(["pendingReview", "processing", "needsRevision"]))
        .order_by(Document.submitted_at.desc())
        .all()
    )
    return jsonify(
        [
            {
                **doc.to_dict(),
                "facultyEmail": doc.owner.email,
                "facultyName": doc.owner.profile.full_name if doc.owner.profile else None,
                "flaggedForReview": doc.flagged_for_review,
            }
            for doc in queue
        ]
    )


@app.post("/api/documents/<public_id>/review")
@staff_jwt_required
def review_document_api(user, public_id):
    doc = Document.query.filter_by(public_id=public_id).first()
    if not doc:
        return jsonify({"error": "Document not found."}), 404
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    if not apply_review(
        doc,
        action,
        data.get("feedback"),
        data.get("points"),
        indicator_id=(data.get("indicatorId") or "").strip() or None,
        contribution_percent=data.get("contributionPercent"),
        rating=data.get("rating"),
    ):
        return jsonify({"error": "Action must be validate, correct, revise, reject, or reopen."}), 400
    write_audit(user.email, f"review_{action}", doc.public_id)
    db.session.commit()
    return jsonify(doc.to_dict())


@app.get("/api/admin/users")
@admin_jwt_required
def admin_users_api(user):
    return jsonify(
        [
            {
                "email": item.email,
                "role": item.role,
                "fullName": item.profile.full_name if item.profile else None,
            }
            for item in User.query.order_by(User.id).all()
        ]
    )


@app.get("/api/admin/scoring-rules")
@admin_jwt_required
def admin_rules_api(user):
    return jsonify([rule.to_dict() for rule in ScoringRule.query.order_by(ScoringRule.id)])


@app.patch("/api/admin/scoring-rules/<kra>")
@admin_jwt_required
def admin_rules_patch(user, kra):
    rule = ScoringRule.query.filter_by(kra=kra).first()
    if not rule:
        return jsonify({"error": "Rule not found."}), 404
    data = request.get_json(silent=True) or {}
    if "basePoints" in data:
        rule.base_points = int(data["basePoints"])
    if "keywords" in data:
        rule.keywords = data["keywords"]
    write_audit(user.email, "update_scoring_rule", kra)
    db.session.commit()
    return jsonify(rule.to_dict())


@app.patch("/api/admin/preparation-period")
@admin_jwt_required
def admin_period_api(user):
    period = PreparationPeriod.query.filter_by(is_current=True).first()
    if not period:
        return jsonify({"error": "No current preparation period."}), 404
    data = request.get_json(silent=True) or {}
    period.cycle_name = data.get("cycleName", period.cycle_name)
    period.status = data.get("status", period.status)
    if data.get("startDate"):
        period.start_date = datetime.fromisoformat(str(data["startDate"])[:10]).date()
    if data.get("endDate"):
        period.end_date = datetime.fromisoformat(str(data["endDate"])[:10]).date()
        period.reviewer_available_until = period.end_date
    write_audit(user.email, "update_period_api", period.cycle_name)
    db.session.commit()
    return jsonify(period.to_dict())


@app.get("/")
def root():
    return jsonify(
        {
            "name": "FacultyLink API",
            "status": "ok",
            "facultyLogin": "/api/auth/login",
            "staffLogin": "/api/auth/staff-login",
        }
    )


with app.app_context():
    db.create_all()
    ensure_shared_schema()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
