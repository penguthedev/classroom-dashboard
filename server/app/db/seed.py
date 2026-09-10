import secrets
from datetime import UTC, datetime, timedelta

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import (
    Building,
    Class,
    Department,
    Enrollment,
    Faculty,
    Notification,
    Programme,
    Room,
    Schedule,
    StaffProfile,
    StudentProfile,
    Subject,
    User,
)

PASSWORD = "Password123!"


def _monday_at(hour: int, weeks_ahead: int = 0, weekday: int = 0) -> datetime:
    today = datetime.now(UTC).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    monday = today - timedelta(days=today.weekday())
    return monday + timedelta(days=weekday, weeks=weeks_ahead)


def seed() -> None:
    db = SessionLocal()
    try:
        if db.query(Programme).count() > 0:
            print("Already seeded, skipping.")
            return

        faculties = [
            Faculty(code="FOE", name="Faculty of Engineering"),
            Faculty(code="FOS", name="Faculty of Science"),
            Faculty(code="FOB", name="Faculty of Business"),
        ]
        db.add_all(faculties)
        db.flush()
        foe, fos, fob = faculties

        departments = [
            Department(faculty_id=foe.id, code="CS", name="Computer Science"),
            Department(faculty_id=foe.id, code="EE", name="Electrical Engineering"),
            Department(faculty_id=fos.id, code="MATH", name="Mathematics"),
            Department(faculty_id=fos.id, code="PHYS", name="Physics"),
            Department(faculty_id=fob.id, code="MGT", name="Management"),
        ]
        db.add_all(departments)
        db.flush()
        cs, ee, math, phys, mgt = departments

        programmes = [
            Programme(department_id=cs.id, code="BCS", name="BSc Computer Science"),
            Programme(department_id=cs.id, code="BCY", name="BSc Cybersecurity"),
            Programme(department_id=ee.id, code="BEE", name="BEng Electrical Engineering"),
            Programme(department_id=math.id, code="BMA", name="BSc Mathematics"),
            Programme(department_id=mgt.id, code="BBA", name="BBA Management"),
        ]
        db.add_all(programmes)
        db.flush()
        bcs, bcy, bee, bma, bba = programmes

        subjects = [
            Subject(department_id=cs.id, code="CS101", name="Intro to Programming"),
            Subject(department_id=cs.id, code="CS201", name="Data Structures"),
            Subject(department_id=cs.id, code="CS301", name="Databases"),
            Subject(department_id=cs.id, code="CS401", name="Cybersecurity Fundamentals"),
            Subject(department_id=ee.id, code="EE101", name="Circuit Theory"),
            Subject(department_id=ee.id, code="EE201", name="Digital Electronics"),
            Subject(department_id=math.id, code="MA101", name="Calculus I"),
            Subject(department_id=math.id, code="MA201", name="Linear Algebra"),
            Subject(department_id=phys.id, code="PH101", name="Mechanics"),
            Subject(department_id=mgt.id, code="MG101", name="Principles of Management"),
        ]
        db.add_all(subjects)
        db.flush()

        buildings = [
            Building(code="A", name="Block A", address="North Campus"),
            Building(code="B", name="Block B", address="North Campus"),
            Building(code="C", name="Block C", address="South Campus"),
        ]
        db.add_all(buildings)
        db.flush()
        block_a, block_b, block_c = buildings

        rooms = [
            Room(building_id=block_a.id, code="A101", capacity=60, room_type="lecture_hall"),
            Room(building_id=block_a.id, code="A102", capacity=40, room_type="tutorial_room"),
            Room(building_id=block_b.id, code="B204", capacity=80, room_type="lecture_hall"),
            Room(building_id=block_b.id, code="B205", capacity=30, room_type="computer_lab"),
            Room(building_id=block_c.id, code="C301", capacity=50, room_type="laboratory"),
            Room(building_id=block_c.id, code="C302", capacity=25, room_type="seminar_room"),
        ]
        db.add_all(rooms)
        db.flush()

        admin = User(
            email="admin@university.edu",
            username="admin",
            name="Grace Lim",
            password_hash=hash_password(PASSWORD),
            role="admin",
            phone="+60123000001",
        )
        technical = User(
            email="tech@university.edu",
            username="tech",
            name="Ravi Kumar",
            password_hash=hash_password(PASSWORD),
            role="technical",
            phone="+60123000002",
        )
        db.add_all([admin, technical])
        db.flush()
        db.add_all(
            [
                StaffProfile(
                    user_id=admin.id,
                    department_id=mgt.id,
                    staff_number="ADM001",
                    position="Registrar",
                ),
                StaffProfile(
                    user_id=technical.id,
                    department_id=cs.id,
                    staff_number="TEC001",
                    position="Systems Engineer",
                    specialization="Network Administration",
                ),
            ]
        )

        lecturer_data = [
            ("John Smith", "jsmith", cs.id, "Senior Lecturer", "Cybersecurity"),
            ("Aisha Rahman", "arahman", cs.id, "Associate Professor", "Databases"),
            ("Marco Silva", "msilva", ee.id, "Lecturer", "Digital Systems"),
            ("Wei Chen", "wchen", math.id, "Professor", "Applied Mathematics"),
        ]
        lecturers = []
        for i, (full_name, uname, dept_id, position, spec) in enumerate(lecturer_data, start=1):
            u = User(
                email=f"{uname}@university.edu",
                username=uname,
                name=full_name,
                password_hash=hash_password(PASSWORD),
                role="lecturer",
                phone=f"+6012310000{i}",
            )
            db.add(u)
            db.flush()
            db.add(
                StaffProfile(
                    user_id=u.id,
                    department_id=dept_id,
                    staff_number=f"LEC00{i}",
                    position=position,
                    specialization=spec,
                    qualification="PhD",
                )
            )
            lecturers.append(u)

        tutor_data = [
            ("Nurul Aziz", "naziz", cs.id, "Graduate Tutor"),
            ("Daniel Ooi", "dooi", ee.id, "Graduate Tutor"),
        ]
        tutors = []
        for i, (full_name, uname, dept_id, position) in enumerate(tutor_data, start=1):
            u = User(
                email=f"{uname}@university.edu",
                username=uname,
                name=full_name,
                password_hash=hash_password(PASSWORD),
                role="tutor",
                phone=f"+6012320000{i}",
            )
            db.add(u)
            db.flush()
            db.add(
                StaffProfile(
                    user_id=u.id,
                    department_id=dept_id,
                    staff_number=f"TUT00{i}",
                    position=position,
                    qualification="MSc",
                )
            )
            tutors.append(u)

        student_data = [
            ("Ana Lopez", "alopez", bcs.id, 1),
            ("Ben Carter", "bcarter", bcs.id, 2),
            ("Chloe Ng", "cng", bcy.id, 2),
            ("Dmitri Volkov", "dvolkov", bee.id, 3),
            ("Eva Muller", "emuller", bma.id, 1),
            ("Farid Hassan", "fhassan", bba.id, 3),
        ]
        students = []
        for i, (full_name, uname, programme_id, year) in enumerate(student_data, start=1):
            u = User(
                email=f"{uname}@student.university.edu",
                username=uname,
                name=full_name,
                password_hash=hash_password(PASSWORD),
                role="student",
                phone=f"+6012330000{i}",
            )
            db.add(u)
            db.flush()
            db.add(
                StudentProfile(
                    user_id=u.id,
                    programme_id=programme_id,
                    student_number=f"S2026{i:04d}",
                    year_of_study=year,
                )
            )
            students.append(u)

        classes = [
            Class(
                subject_id=subjects[3].id,
                lecturer_id=lecturers[0].id,
                tutor_id=tutors[0].id,
                name="Cybersecurity Fundamentals - Section A",
                capacity=60,
                invite_code=secrets.token_hex(3),
            ),
            Class(
                subject_id=subjects[0].id,
                lecturer_id=lecturers[1].id,
                tutor_id=tutors[0].id,
                name="Python Foundations - Section A",
                capacity=40,
                invite_code=secrets.token_hex(3),
            ),
            Class(
                subject_id=subjects[2].id,
                lecturer_id=lecturers[1].id,
                name="Databases - Section B",
                capacity=30,
                invite_code=secrets.token_hex(3),
            ),
            Class(
                subject_id=subjects[5].id,
                lecturer_id=lecturers[2].id,
                tutor_id=tutors[1].id,
                name="Digital Electronics - Section A",
                capacity=50,
                invite_code=secrets.token_hex(3),
            ),
            Class(
                subject_id=subjects[7].id,
                lecturer_id=lecturers[3].id,
                name="Linear Algebra - Section A",
                capacity=80,
                invite_code=secrets.token_hex(3),
            ),
        ]
        db.add_all(classes)
        db.flush()

        schedules = [
            Schedule(
                class_id=classes[0].id,
                room_id=rooms[2].id,
                lecturer_id=lecturers[0].id,
                tutor_id=tutors[0].id,
                starts_at=_monday_at(10, weekday=0),
                ends_at=_monday_at(12, weekday=0),
            ),
            Schedule(
                class_id=classes[1].id,
                room_id=rooms[3].id,
                lecturer_id=lecturers[1].id,
                tutor_id=tutors[0].id,
                starts_at=_monday_at(14, weekday=0),
                ends_at=_monday_at(16, weekday=0),
            ),
            Schedule(
                class_id=classes[2].id,
                room_id=rooms[0].id,
                lecturer_id=lecturers[1].id,
                starts_at=_monday_at(9, weekday=1),
                ends_at=_monday_at(11, weekday=1),
            ),
            Schedule(
                class_id=classes[3].id,
                room_id=rooms[4].id,
                lecturer_id=lecturers[2].id,
                tutor_id=tutors[1].id,
                starts_at=_monday_at(13, weekday=2),
                ends_at=_monday_at(15, weekday=2),
            ),
            Schedule(
                class_id=classes[4].id,
                room_id=rooms[2].id,
                lecturer_id=lecturers[3].id,
                starts_at=_monday_at(9, weekday=3),
                ends_at=_monday_at(11, weekday=3),
            ),
        ]
        db.add_all(schedules)
        db.flush()

        enrollments = [
            Enrollment(student_id=students[0].id, class_id=classes[0].id),
            Enrollment(student_id=students[0].id, class_id=classes[1].id),
            Enrollment(student_id=students[1].id, class_id=classes[0].id),
            Enrollment(student_id=students[2].id, class_id=classes[0].id),
            Enrollment(student_id=students[2].id, class_id=classes[2].id),
            Enrollment(student_id=students[3].id, class_id=classes[3].id),
            Enrollment(student_id=students[4].id, class_id=classes[4].id),
            Enrollment(student_id=students[5].id, class_id=classes[4].id),
        ]
        db.add_all(enrollments)

        placeholder = db.query(Faculty).filter(Faculty.code == "GEN").one_or_none()
        if placeholder is not None and not placeholder.departments:
            db.delete(placeholder)

        db.add(
            Notification(
                user_id=students[0].id,
                schedule_id=schedules[0].id,
                type="schedule_created",
                title="Cybersecurity Fundamentals scheduled",
                body="Monday 10:00 - 12:00, Block B B204.",
            )
        )

        db.commit()
        print(
            "Seeded 3 faculties, 5 departments, 5 programmes, 10 subjects, "
            "3 buildings, 6 rooms, 1 admin, 1 technical, 4 lecturers, 2 tutors, "
            "6 students, 5 classes, 5 schedules, 8 enrollments."
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
