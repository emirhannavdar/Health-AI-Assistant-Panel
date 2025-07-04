# services/db_service.py
from sqlalchemy.orm import Session
from models.patient import Patient
from models.lab_result import LabResult
from datetime import datetime

class DBService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_patient(self, patient_id: str, patient_data: dict):
        patient = self.db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            patient = Patient(
                id=patient_id,
                name=patient_data.get("name", "Bilinmiyor"), # FHIR Patient kaynağından gelecek
                gender=patient_data.get("gender", "unknown"), # FHIR Patient kaynağından gelecek
                birth_date=patient_data.get("birth_date"), # FHIR Patient kaynağından gelecek
                doctor_id=patient_data.get("doctor_id")
            )
            self.db.add(patient)
            self.db.commit()
            self.db.refresh(patient)
        else:
            # Eğer doctor_id gelirse güncelle
            if patient_data.get("doctor_id") and patient.doctor_id != patient_data.get("doctor_id"):
                patient.doctor_id = patient_data.get("doctor_id")
                self.db.commit()
                self.db.refresh(patient)
        return patient

    def create_lab_result(self, lab_result_data: dict):
        lab_result = LabResult(**lab_result_data)
        self.db.add(lab_result)
        self.db.commit()
        self.db.refresh(lab_result)
        return lab_result