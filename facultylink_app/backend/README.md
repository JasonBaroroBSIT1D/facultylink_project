# FacultyLink backend

Flask + SQLAlchemy API for the FacultyLink faculty mobile app. PostgreSQL is the thesis database; SQLite is the default so a Windows demo can start without extra installs.

FacultyLink is **preparatory**. Reviewers confirm documents. The system does not certify authenticity or replace official DBM–CHED evaluation.

## Demo accounts

| Role | Email | Password |
| --- | --- | --- |
| Faculty | `maria.santos@university.edu.ph` | `password123` |
| Reviewer | `elena.cruz@university.edu.ph` | `reviewer123` |
| Admin | `admin@university.edu.ph` | `admin123` |

## Run the API

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

The API listens on `http://127.0.0.1:5000`. Android emulators should use `http://10.0.2.2:5000`.

If `pip` cannot build Pillow or `psycopg2-binary` on a newer Python, install the core packages first (`flask`, `flask-sqlalchemy`, `flask-jwt-extended`, `flask-cors`, `python-dotenv`, `pytest`). SQLite and keyword scoring still work. Install `Pillow`/`pytesseract` when you want image OCR, and `psycopg2-binary` when you use PostgreSQL.

### PostgreSQL (this machine already has PostgreSQL 18)

The Flutter app never talks to Postgres. It calls Flask at `http://127.0.0.1:5000`. Flask reads `DATABASE_URL` from `backend/.env` and creates the tables on first boot.

1. In pgAdmin or `psql`, create an empty database named `facultylink` (use the `postgres` password you set during install):

```
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres
CREATE DATABASE facultylink;
```

2. Edit `backend/.env` and replace `YOUR_PASSWORD`:

```
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@127.0.0.1:5432/facultylink
```

3. Restart Flask (`python app.py`). It creates the ERD tables and seeds Maria Santos if that account is missing.

### Tesseract OCR

Tesseract 5 is installed at `C:\Program Files\Tesseract-OCR\tesseract.exe`. Uploaded images and PDFs are read on the server. Keyword rules still classify the KRA, and a reviewer still confirms the result.

If you reinstall Windows, run:

```
winget install --id tesseract-ocr.tesseract --source winget
```

Then keep this line in `.env`:

```
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

## Faculty API

- `POST /api/auth/login`
- `POST /api/auth/register` (request only)
- `GET /api/me`
- `PATCH /api/me/profile`
- `GET /api/documents`, `POST /api/documents`, `GET /api/documents/:id`
- `POST /api/documents/:id/process`
- `GET /api/assessment/kra-scores`
- `GET /api/assessment/requirements`
- `GET /api/simulation`
- `GET /api/notifications`, `POST /api/notifications/:id/read`
- `GET /api/preparation-period`

## Reviewer / admin

JSON:

- `POST /api/auth/staff-login`
- `GET /api/review/queue`
- `POST /api/documents/:id/review` with `{ "action": "validate"|"revise"|"reject" }`
- `GET /api/admin/users`
- `GET /api/admin/scoring-rules`
- `PATCH /api/admin/preparation-period`

## Tests

```bash
cd backend
pytest
```

## Run with Flutter

1. Start this API.
2. From the project root: `flutter pub get`
3. `flutter run` (Chrome uses `127.0.0.1:5000`; Android emulator uses `10.0.2.2:5000`).
4. Sign in as Maria Santos.

Widget tests still open `MainShell` against mock data so they do not require a live server.
