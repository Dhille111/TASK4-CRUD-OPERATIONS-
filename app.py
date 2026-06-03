from __future__ import annotations

import csv
import os
from contextlib import contextmanager
from pathlib import Path

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "people.db"
CSV_PATH = BASE_DIR / "people.csv"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "crud-dashboard-secret")

engine = create_engine(
    f"sqlite:///{DATABASE_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)
    age: Mapped[int] = mapped_column(nullable=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def sync_people_csv() -> None:
    with get_db_session() as session:
        people = session.scalars(select(Person).order_by(Person.id)).all()

    with CSV_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["id", "name", "age"])
        writer.writeheader()
        for person in people:
            writer.writerow(person_to_dict(person))


@contextmanager
def get_db_session() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def person_to_dict(person: Person) -> dict[str, int | str]:
    return {"id": person.id, "name": person.name, "age": person.age}


@app.before_request
def ensure_database() -> None:
    if not DATABASE_PATH.exists():
        init_db()
        sync_people_csv()


@app.route("/")
def index():
    edit_id = request.args.get("edit", type=int)
    with get_db_session() as session:
        people = session.scalars(select(Person).order_by(Person.id)).all()
        edit_person = session.get(Person, edit_id) if edit_id is not None else None
    return render_template("index.html", people=people, edit_person=edit_person)


@app.route("/add", methods=["POST"])
def add_person():
    name = request.form.get("name", "").strip()
    age = request.form.get("age", "").strip()

    if not name or not age.isdigit():
        flash("Enter a valid name and age.", "error")
        return redirect(url_for("index"))

    with get_db_session() as session:
        session.add(Person(name=name, age=int(age)))

    sync_people_csv()

    flash("Record added successfully.", "success")
    return redirect(url_for("index"))


@app.route("/update/<int:person_id>", methods=["POST"])
def update_person(person_id: int):
    name = request.form.get("name", "").strip()
    age = request.form.get("age", "").strip()

    if not name or not age.isdigit():
        flash("Enter a valid name and age.", "error")
        return redirect(url_for("index", edit=person_id))

    with get_db_session() as session:
        person = session.get(Person, person_id)
        if person is None:
            abort(404)
        person.name = name
        person.age = int(age)

    sync_people_csv()

    flash("Record updated successfully.", "success")
    return redirect(url_for("index"))


@app.route("/delete/<int:person_id>", methods=["POST"])
def delete_person(person_id: int):
    with get_db_session() as session:
        person = session.get(Person, person_id)
        if person is None:
            abort(404)
        session.delete(person)

    sync_people_csv()

    flash("Record deleted successfully.", "success")
    return redirect(url_for("index"))


@app.route("/api/people", methods=["GET", "POST"])
def people_api():
    if request.method == "GET":
        with get_db_session() as session:
            people = session.scalars(select(Person).order_by(Person.id)).all()
        return jsonify([person_to_dict(person) for person in people])

    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    age = payload.get("age")

    if not name or not isinstance(age, int):
        return jsonify({"error": "name and integer age are required"}), 400

    with get_db_session() as session:
        person = Person(name=name, age=age)
        session.add(person)
        session.flush()

    sync_people_csv()

    return jsonify({"id": person.id, "name": name, "age": age}), 201


@app.route("/api/people/<int:person_id>", methods=["PUT", "DELETE"])
def person_api(person_id: int):
    if request.method == "DELETE":
        with get_db_session() as session:
            person = session.get(Person, person_id)
            if person is None:
                return jsonify({"error": "not found"}), 404
            session.delete(person)

        sync_people_csv()

        return jsonify({"message": "deleted"})

    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    age = payload.get("age")

    if not name or not isinstance(age, int):
        return jsonify({"error": "name and integer age are required"}), 400

    with get_db_session() as session:
        person = session.get(Person, person_id)
        if person is None:
            return jsonify({"error": "not found"}), 404
        person.name = name
        person.age = age

    sync_people_csv()

    return jsonify({"id": person_id, "name": name, "age": age})


init_db()
sync_people_csv()


if __name__ == "__main__":
    app.run(debug=True)
