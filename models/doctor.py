from sqlalchemy import Column, String, DateTime
from datetime import datetime
from models.base import Base
from sqlalchemy.orm import relationship

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_admin = Column(String, default="0")  # '1' ise admin, '0' ise normal doktor

    # patients = relationship("Patient", back_populates="doctor")  # Circular import hatası için yoruma alındı
    lab_results = relationship("LabResult", back_populates="doctor")

    def __repr__(self):
        return f"<Doctor(id='{self.id}', username='{self.username}', name='{self.name}')>"