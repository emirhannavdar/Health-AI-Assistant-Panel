import uuid
from models.base import SessionLocal, Base, engine
from models.doctor import Doctor
from passlib.hash import bcrypt

Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    username = "drdemo"
    password = "demo1234"
    name = "Dr. Demo"
    password_hash = bcrypt.hash(password)
    doctor = Doctor(
        id=str(uuid.uuid4()),
        username=username,
        password_hash=password_hash,
        name=name,
        is_admin=1
    )
    db.add(doctor)
    db.commit()
    print(f"Demo doktor eklendi: {username} / {password}")
finally:
    db.close()