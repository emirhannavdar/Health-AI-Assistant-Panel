# models/base.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL

# Veritabanı motorunu oluştur
engine = create_engine(DATABASE_URL)

# Bildirimsel taban sınıfını oluştur
Base = declarative_base()

# Bir oturum sınıfı oluştur
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Veritabanı bağımlılığı (FastAPI için)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()