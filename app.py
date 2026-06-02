from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from pathlib import Path

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "people.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "crud-dashboard-secret")


def get_db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with closing(get_db_connection()) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL
            )
            """
        )
        connection.commit()


@app.before_request
def ensure_database() -> None:
    if not DATABASE_PATH.exists():
        init_db()


@app.route("/")
def index():
    edit_id = request.args.get("edit", type=int)
    with closing(get_db_connection()) as connection:
        people = connection.execute(
            "SELECT id, name, age FROM people ORDER BY id ASC"
        ).fetchall()
        edit_person = None
        if edit_id is not None:
            edit_person = connection.execute(
                "SELECT id, name, age FROM people WHERE id = ?",
                (edit_id,),
            ).fetchone()
    return render_template("index.html", people=people, edit_person=edit_person)


@app.route("/add", methods=["POST"])
def add_person():
    name = request.form.get("name", "").strip()
    age = request.form.get("age", "").strip()

    if not name or not age.isdigit():
        flash("Enter a valid name and age.", "error")
        return redirect(url_for("index"))

    with closing(get_db_connection()) as connection:
        connection.execute(
            "INSERT INTO people (name, age) VALUES (?, ?)",
            (name, int(age)),
        )
        connection.commit()

    flash("Record added successfully.", "success")
    return redirect(url_for("index"))


@app.route("/update/<int:person_id>", methods=["POST"])
def update_person(person_id: int):
    name = request.form.get("name", "").strip()
    age = request.form.get("age", "").strip()

    if not name or not age.isdigit():
        flash("Enter a valid name and age.", "error")
        return redirect(url_for("index", edit=person_id))

    with closing(get_db_connection()) as connection:
        cursor = connection.execute(
            "UPDATE people SET name = ?, age = ? WHERE id = ?",
            (name, int(age), person_id),
        )
        connection.commit()

    if cursor.rowcount == 0:
        abort(404)

    flash("Record updated successfully.", "success")
    return redirect(url_for("index"))


@app.route("/delete/<int:person_id>", methods=["POST"])
def delete_person(person_id: int):
    with closing(get_db_connection()) as connection:
        cursor = connection.execute("DELETE FROM people WHERE id = ?", (person_id,))
        connection.commit()

    if cursor.rowcount == 0:
        abort(404)

    flash("Record deleted successfully.", "success")
    return redirect(url_for("index"))


@app.route("/api/people", methods=["GET", "POST"])
def people_api():
    if request.method == "GET":
        with closing(get_db_connection()) as connection:
            rows = connection.execute(
                "SELECT id, name, age FROM people ORDER BY id ASC"
            ).fetchall()
        return jsonify([dict(row) for row in rows])

    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    age = payload.get("age")

    if not name or not isinstance(age, int):
        return jsonify({"error": "name and integer age are required"}), 400

    with closing(get_db_connection()) as connection:
        cursor = connection.execute(
            "INSERT INTO people (name, age) VALUES (?, ?)",
            (name, age),
        )
        connection.commit()

    return jsonify({"id": cursor.lastrowid, "name": name, "age": age}), 201


@app.route("/api/people/<int:person_id>", methods=["PUT", "DELETE"])
def person_api(person_id: int):
    if request.method == "DELETE":
        with closing(get_db_connection()) as connection:
            cursor = connection.execute("DELETE FROM people WHERE id = ?", (person_id,))
            connection.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "not found"}), 404
        return jsonify({"message": "deleted"})

    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    age = payload.get("age")

    if not name or not isinstance(age, int):
        return jsonify({"error": "name and integer age are required"}), 400

    with closing(get_db_connection()) as connection:
        cursor = connection.execute(
            "UPDATE people SET name = ?, age = ? WHERE id = ?",
            (name, age, person_id),
        )
        connection.commit()

    if cursor.rowcount == 0:
        return jsonify({"error": "not found"}), 404

    return jsonify({"id": person_id, "name": name, "age": age})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
