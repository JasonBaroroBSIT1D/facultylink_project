# FacultyLink backend

Flask + SQLAlchemy API for the FacultyLink faculty mobile app. PostgreSQL is required (SQLite is disabled).

FacultyLink is **preparatory**. Reviewers confirm documents. The system does not certify authenticity or replace official DBM–CHED evaluation.

## Accounts

Create faculty and reviewers from the web admin. There is no startup demo seed.

Default local admin (if already present in your database):

| Role | Email | Password |
| --- | --- | --- |
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

If `pip` cannot build Pillow on a newer Python, install the core packages first (`flask`, `flask-sqlalchemy`, `flask-jwt-extended`, `flask-cors`, `python-dotenv`, `psycopg[binary]`, `pytest`). Install `Pillow`/`pytesseract` when you want image OCR.

### PostgreSQL (required)

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

3. Restart Flask (`python app.py`). It creates the ERD tables. No demo users or documents are seeded.

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

### Password recovery email (SMTP)

"Forgot your password?" emails a 6-digit code. No SMS service is used. Until SMTP is configured, the API answers `503` and names the missing settings instead of pretending to send. Add these to `backend/.env` and restart Flask:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURITY=starttls
SMTP_USERNAME=your.address@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=FacultyLink <your.address@gmail.com>
```

For Gmail, enable 2-step verification and create an App Password. Use `SMTP_SECURITY=ssl` with port 465 if your provider requires it.

Recovery state (hashed code, expiry, attempt count, hashed reset token) lives in new nullable columns on the existing `users` table. Flask adds them automatically on startup.

## Faculty API

- `POST /api/auth/login`
- `POST /api/auth/register` (request only)
- `POST /api/auth/forgot-password/request`: `{ "email" }` emails a code. The reply is the same whether or not the account exists. The code lasts 5 minutes, and a new one can be requested after 60 seconds.
- `POST /api/auth/forgot-password/verify`: `{ "email", "otp" }` returns a 10-minute `resetToken`. The code is single-use and locks after 5 wrong attempts.
- `POST /api/auth/forgot-password/reset`: `{ "email", "resetToken", "newPassword" }` updates the password.
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
