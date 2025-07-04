from models.lab_result import LabResult
from models.patient import Patient
from models.base import get_db
from models.doctor import Doctor
from models.lab_result import LabResult
from passlib.hash import bcrypt
import uuid

def add_admin_doctor(username, password, name):
    db = next(get_db())
    if db.query(Doctor).filter(Doctor.username == username).first():
        print(f"Kullanıcı adı zaten var: {username}")
        return
    doctor = Doctor(
        id=str(uuid.uuid4()),
        username=username,
        password_hash=bcrypt.hash(password),
        name=name,
        is_admin="1"
    )
    db.add(doctor)
    db.commit()
    print(f"Admin doktor eklendi: {username}")

if __name__ == "__main__":
    add_admin_doctor("admin", "admin123", "Admin Kullanıcı")