# TASK4-CRUD-OPERATIONS-

Simple Flask CRUD application for managing people.

The app uses SQLAlchemy ORM with the local SQLite database file `people.db`.

How to run

1. Create and activate a virtual environment (recommended):

```bash
python -m venv .venv
.\\.venv\\Scripts\\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python app.py
```

4. Open http://127.0.0.1:5000 in your browser.

Notes
- `people.db` is the ORM-backed SQLite storage file.
- The schema is created automatically on startup if it does not exist.
