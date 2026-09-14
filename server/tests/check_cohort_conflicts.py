from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.schedules import find_cohort_conflicts, find_conflicts
from app.db.base import Base
from app.models import (
    Building,
    Class,
    Department,
    Enrollment,
    Faculty,
    Room,
    Schedule,
    Subject,
    User,
)

engine = create_engine("sqlite://")
Base.metadata.create_all(engine)

start = datetime(2026, 3, 2, 10, 0)
end = start + timedelta(hours=2)

with Session(engine) as db:
    faculty = Faculty(code="ENG", name="Engineering")
    building = Building(code="B", name="Block B")
    db.add_all([faculty, building])
    db.flush()

    department = Department(faculty_id=faculty.id, code="CS", name="Computer Science")
    db.add(department)
    db.flush()

    room_a = Room(building_id=building.id, code="B204", name="B204", capacity=40)
    room_b = Room(building_id=building.id, code="C301", name="C301", capacity=40)
    subject = Subject(department_id=department.id, code="CS101", name="Intro")
    lecturer = User(
        email="l@x.edu", username="lect", name="Lecturer One", password_hash="x",
        role="lecturer",
    )
    other_lecturer = User(
        email="l2@x.edu", username="lect2", name="Lecturer Two", password_hash="x",
        role="lecturer",
    )
    db.add_all([room_a, room_b, subject, lecturer, other_lecturer])
    db.flush()

    class_a = Class(
        subject_id=subject.id, lecturer_id=lecturer.id, name="Section A",
        capacity=30, invite_code="AAA111",
    )
    class_b = Class(
        subject_id=subject.id, lecturer_id=other_lecturer.id, name="Section B",
        capacity=30, invite_code="BBB222",
    )
    db.add_all([class_a, class_b])
    db.flush()

    students = [
        User(
            email=f"s{i}@x.edu", username=f"stu{i}", name=f"Student {i}",
            password_hash="x", role="student",
        )
        for i in range(3)
    ]
    db.add_all(students)
    db.flush()

    for student in students:
        db.add(Enrollment(student_id=student.id, class_id=class_a.id))
    for student in students[:2]:
        db.add(Enrollment(student_id=student.id, class_id=class_b.id))
    db.flush()

    existing = Schedule(
        class_id=class_b.id, room_id=room_b.id, lecturer_id=other_lecturer.id,
        starts_at=start, ends_at=end, status="scheduled",
    )
    db.add(existing)
    db.flush()

    hard = find_conflicts(db, room_a.id, lecturer.id, None, start, end)
    cohort = find_cohort_conflicts(db, class_a.id, start, end)
    later = find_cohort_conflicts(
        db, class_a.id, start + timedelta(hours=3), end + timedelta(hours=3)
    )

    assert hard == [], f"expected no room/lecturer clash, got {hard}"
    assert len(cohort) == 1, f"expected one cohort clash, got {cohort}"
    assert cohort[0].resource == "students"
    assert cohort[0].schedule_id == existing.id
    assert "2 enrolled students" in cohort[0].message, cohort[0].message
    assert later == [], f"expected no clash outside the window, got {later}"

    existing.status = "cancelled"
    db.flush()
    assert find_cohort_conflicts(db, class_a.id, start, end) == []

print("cohort conflict detection: ok")
print(" ", cohort[0].message)
