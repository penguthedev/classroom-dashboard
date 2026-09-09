from app.db.session import SessionLocal
from app.core.security import hash_password
from app.models import Department, Subject, User


def seed() -> None:
    db = SessionLocal()
    try:
        if db.query(Department).count() > 0:
            print("Already seeded, skipping.")
            return

        departments = [
            Department(code="CS", name="Computer Science", description="Computing and software."),
            Department(code="MATH", name="Mathematics", description="Pure and applied maths."),
            Department(code="PHYS", name="Physics", description="Classical and modern physics."),
            Department(code="BIO", name="Biology", description="Life sciences."),
        ]
        db.add_all(departments)
        db.flush()

        cs, math, phys, bio = departments

        db.add_all([
            Subject(department_id=cs.id, code="CS101", name="Intro to Programming", description="Python basics."),
            Subject(department_id=cs.id, code="CS201", name="Data Structures", description="Lists, trees, graphs."),
            Subject(department_id=cs.id, code="CS301", name="Databases", description="Relational modelling and SQL."),
            Subject(department_id=math.id, code="MA101", name="Calculus I", description="Limits and derivatives."),
            Subject(department_id=math.id, code="MA201", name="Linear Algebra", description="Vectors and matrices."),
            Subject(department_id=phys.id, code="PH101", name="Mechanics", description="Newtonian motion."),
            Subject(department_id=phys.id, code="PH201", name="Electromagnetism", description="Fields and circuits."),
            Subject(department_id=bio.id, code="BI101", name="Cell Biology", description="Cells and organelles."),
            Subject(department_id=bio.id, code="BI201", name="Genetics", description="Inheritance and DNA."),
            Subject(department_id=bio.id, code="BI301", name="Ecology", description="Ecosystems and populations."),
        ])

        teachers = ["Tom Ellis", "Aisha Rahman", "Marco Silva", "Wei Chen"]
        students = ["Ana Lopez", "Ben Carter", "Chloe Ng", "Dmitri Volkov", "Eva Muller", "Farid Hassan"]

        for i, full_name in enumerate(teachers, start=1):
            db.add(User(
                email=f"teacher{i}@example.com",
                name=full_name,
                password_hash=hash_password("password123"),
                role="teacher",
            ))

        for i, full_name in enumerate(students, start=1):
            db.add(User(
                email=f"student{i}@example.com",
                name=full_name,
                password_hash=hash_password("password123"),
                role="student",
            ))

        db.commit()
        print("Seeded 4 departments, 10 subjects, 4 teachers, 6 students.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
