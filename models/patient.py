# models/patient.py
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from models.base import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True, index=True) # FHIR subject reference'ı ile eşleşebilir
    name = Column(String, index=True)
    gender = Column(String)
    birth_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    doctor_id = Column(String, ForeignKey("doctors.id"), nullable=True)

    # Bir hastanın birden fazla laboratuvar sonucu olabilir
    lab_results = relationship("LabResult", back_populates="patient")
    doctor = relationship("Doctor")

    def __repr__(self):
        return f"<Patient(id='{self.id}', name='{self.name}')>"