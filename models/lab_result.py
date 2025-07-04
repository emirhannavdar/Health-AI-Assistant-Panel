# models/lab_result.py
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base

class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.id"))
    loinc_code = Column(String, index=True)
    display_name = Column(String)
    value = Column(Float)
    unit = Column(String)
    effective_date_time = Column(DateTime)
    status = Column(String)
    ai_analysis = Column(String, nullable=True) # Yeni eklenen alan
    doctor_id = Column(String, ForeignKey("doctors.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="lab_results") # Burada 'Patient' doğru, çünkü models/patient.py'deki sınıf adı bu.
    doctor = relationship("Doctor", back_populates="lab_results")

    def __repr__(self):
        return f"<LabResult(id='{self.id}', patient_id='{self.patient_id}', loinc='{self.loinc_code}', value='{self.value}{self.unit}')>"