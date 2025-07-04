# main.py
from fastapi import FastAPI, HTTPException, Depends, Request, Body, Query, UploadFile, File, Header
from fastapi.responses import HTMLResponse, JSONResponse  # HTML yanıtları için
from fastapi.templating import Jinja2Templates  # Jinja2 şablon motoru için
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import uuid
from dateutil.parser import isoparse
import tempfile
import os
import mimetypes
import PyPDF2
import pytesseract
from PIL import Image
from jose import jwt
from passlib.hash import bcrypt

# fhir.resources kütüphanesinden import ediyoruz
from fhir.resources.observation import Observation
from fhir.resources.reference import Reference
# Diğer FHIR import'ları (eğer Patient kaynağını da alıyorsak kullanışlı olabilir)
# from fhir.resources.patient import Patient as FHIRPatient
# from fhir.resources.codeableconcept import CodeableConcept
# from fhir.resources.quantity import Quantity

from models.base import Base, engine, get_db
from models.patient import Patient  # DB modelini Patient olarak import ediyoruz
from models.lab_result import LabResult  #
from services.db_service import DBService  #
from services.ai_analyzer import AIAnalyzer  #
from datetime import datetime
from services.gemini_ai import ask_gemini
from models.doctor import Doctor


from models.base import SessionLocal
from models.doctor import Doctor
from passlib.hash import bcrypt


# --- burdan ---
def create_initial_admin():
    db = SessionLocal()
    admin_id = "admin"
    admin_name = "Admin"
    admin_password = "admin123"  # Sonra değiştir!
    admin_role = "admin"
    if not db.query(Doctor).filter_by(id=admin_id).first():
        hashed_pw = bcrypt.hash(admin_password)
        admin = Doctor(id=admin_id, name=admin_name, password=hashed_pw, role=admin_role)
        db.add(admin)
        db.commit()
        print("Admin kullanıcı başarıyla eklendi!")
    else:
        print("Admin zaten mevcut.")
    db.close()

create_initial_admin()
# --- GEÇİCİ ADMIN EKLEME BLOĞU SONU ---








# Veritabanı tablolarını oluştur
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sağlık AI Asistanı MCP Sunucusu",
    description="Hasta verilerini alıp AI analizine hazırlayan platform."
)

ai_analyzer = AIAnalyzer()  #

# Jinja2Templates'ı başlat
templates = Jinja2Templates(directory="templates")

SECRET_KEY = "supersecretkey123"  # Gerçek projede .env'den alınmalı
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None

@app.get("/")
async def read_root():
    return {"message": "Sağlık AI Asistanı MCP Sunucusuna Hoş Geldiniz! Yönetim paneli için /dashboard adresine gidin."}


@app.post("/fhir/observation")
async def receive_fhir_observation(
        observation: Observation,  # fhir.resources.observation.Observation kullanıyoruz
        db: Session = Depends(get_db),
        doctor_id: str = None
):
    """
    HL7/FHIR Observation kaynağını alır, veritabanına kaydeder ve AI analizi yapar.
    """
    db_service = DBService(db)
    analysis_message = None  # Analiz sonucunu tutacak değişken

    # Eğer subject veya reference yoksa otomatik üret
    if observation.subject and observation.subject.reference:
        patient_reference_str = observation.subject.reference
    else:
        generated_patient_id = str(uuid.uuid4())[:8]
        patient_reference_str = f"Patient/{generated_patient_id}"
        observation.subject = Reference.construct(reference=patient_reference_str)

    if not patient_reference_str or not patient_reference_str.startswith("Patient/"):
        raise HTTPException(status_code=400, detail="Geçersiz hasta referansı.")

    patient_id = patient_reference_str.split("/")[1]

    # Şimdilik hasta verilerini FHIRPatient kaynağından almadan örnek oluşturalım.
    patient_db_instance = db_service.get_or_create_patient(
        patient_id=patient_id,
        patient_data={
            "name": f"Hasta {patient_id}",
            "gender": "unknown",
            "birth_date": None,
            "doctor_id": doctor_id
        }
    )

    if observation.valueQuantity:  #
        loinc_code = None
        display_name = None

        if observation.code and observation.code.coding:
            for coding in observation.code.coding:
                if coding.system == "http://loinc.org":  #
                    loinc_code = coding.code  #
                    display_name = coding.display  #
                    break
            if not display_name and observation.code.text:
                display_name = observation.code.text

        if not loinc_code:
            print(f"Uyarı: LOINC kodu bulunamadı veya uygun kodlama yok: {observation.code}")
            loinc_code = "UNKNOWN_LOINC"
            if not display_name:
                display_name = "Bilinmeyen Test"

        # id yoksa otomatik üret
        lab_result_id = observation.id if observation.id else f"obs_{uuid.uuid4()}"

        lab_result_data_for_db = {
            "id": lab_result_id,
            "patient_id": patient_db_instance.id,
            "loinc_code": loinc_code,
            "display_name": display_name,
            "value": observation.valueQuantity.value,
            "unit": observation.valueQuantity.unit,
            "effective_date_time": isoparse(observation.effectiveDateTime) if observation.effectiveDateTime else datetime.now(timezone.utc),
            "status": observation.status,
            "doctor_id": doctor_id
        }

        try:
            lab_result_data_for_ai = {
                "patient_id": patient_db_instance.id,
                "loinc_code": loinc_code,
                "display_name": display_name,
                "value": observation.valueQuantity.value,
                "unit": observation.valueQuantity.unit
            }
            analysis_message = ai_analyzer.analyze_lab_result(lab_result_data_for_ai)  #
            lab_result_data_for_db["ai_analysis"] = analysis_message
            lab_result = db_service.create_lab_result(lab_result_data_for_db)  #
            print(f"Laboratuvar sonucu veritabanına kaydedildi: {lab_result}")
            if analysis_message:
                print(f"AI Analiz Sonucu: {analysis_message}")
            else:
                print("AI Analizi: Herhangi bir anormallik bulunamadı veya bilinmeyen test.")

        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"İşlem sırasında hata oluştu: {e}")

    return {
        "status": "success",
        "message": "FHIR Observation başarıyla alındı, kaydedildi ve analiz edildi.",
        "patient_id": patient_id,
        "ai_analysis": analysis_message  # Analiz sonucunu API yanıtına ekle
    }


@app.post("/lab/text")
async def receive_lab_text(
        text: str = Body(..., media_type="text/plain"),
        db: Session = Depends(get_db),
        authorization: str = Header(None)
):
    # Token'dan doctor_id'yi al
    doctor_id = None
    if authorization and authorization.startswith('Bearer '):
        token = authorization.split(' ', 1)[1]
        payload = verify_token(token)
        if payload:
            doctor_id = payload.get('doctor_id')
    loinc_map = {
        "Hemoglobin": "718-7",
        "Beyaz Kan Hücresi (WBC)": "6690-2",
        "Trombosit (Platelet)": "777-3",
        "Hematokrit": "789-8",
        "Sodyum": "2951-2",
        "Potasyum": "2823-3",
        "Kreatinin": "2075-0",
        "Glukoz (Açlık)": "2345-7",
        "Total Kolesterol": "2093-3",
        "HDL Kolesterol": "2085-9",
        "LDL Kolesterol": "13457-7",
        "Trigliserid": "2571-8",
        "ALT (SGPT)": "4548-4",
        "AST (SGOT)": "1920-8",
        "Alkalin Fosfataz": "2885-2",
        "Üre Azotu (BUN)": "3094-0",
        "Bilirubin Total": "1751-7",
        "Albumin": "1925-7",
        "TSH (Tiroid Stimulan Hormon)": "14957-5",
        "Serbest T4": "14647-2",
        "Serbest T3": "14598-7",
        "CRP (C-Reaktif Protein)": "1986-5",
        "Vitamin D (25-OH)": "30000-4",
        "Ferritin": "10466-1",
        "HbA1c": "14979-9"
    }
    if not text or text.strip() == "?":
        return {"info": "Kullanabileceğiniz test adları:", "available_tests": list(loinc_map.keys())}
    try:
        parts = text.split(",")
        test_name = parts[0].split(":")[0].strip()
        value_unit = parts[0].split(":")[1].strip().split(" ")
        value = float(value_unit[0])
        unit = value_unit[1]
        patient_id = parts[1].split(":")[1].strip()
        from datetime import datetime, timezone
        if len(parts) > 2 and ":" in parts[2]:
            date_str = parts[2].split(":")[1].strip()
            try:
                effective_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
            except Exception:
                effective_date = datetime.now(timezone.utc)
        else:
            effective_date = datetime.now(timezone.utc)

        from fhir.resources.observation import Observation
        from fhir.resources.codeableconcept import CodeableConcept
        from fhir.resources.coding import Coding
        from fhir.resources.quantity import Quantity
        from fhir.resources.reference import Reference

        loinc_code = loinc_map.get(test_name, "UNKNOWN")

        obs = Observation.construct(
            status="final",
            code=CodeableConcept.construct(
                coding=[Coding.construct(system="http://loinc.org", code=loinc_code, display=test_name)],
                text=test_name
            ),
            subject=Reference.construct(reference=f"Patient/{patient_id}"),
            effectiveDateTime=effective_date.isoformat(),
            valueQuantity=Quantity.construct(value=value, unit=unit)
        )

        return await receive_fhir_observation(obs, db, doctor_id=doctor_id)
    except Exception as e:
        return {"error": f"Metin parse edilemedi: {e}", "available_tests": list(loinc_map.keys())}


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    db_service = DBService(db)
    lab_results = db.query(LabResult).order_by(LabResult.effective_date_time.desc()).all()
    current_year = datetime.now().year
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "lab_results": lab_results,
            "current_year": current_year  # <-- Bunu ekleyin
        }
    )

@app.get("/patient/results")
async def get_patient_results_filtered(
    patient_id: str = Query(None),
    date_start: str = Query(None),
    date_end: str = Query(None),
    db: Session = Depends(get_db)
):
    if not (patient_id or date_start or date_end):
        return {"info": "hasta id veya tarih bilgisi giriniz"}
    query = db.query(LabResult)
    from datetime import datetime, timedelta
    if patient_id:
        query = query.filter(LabResult.patient_id == patient_id)
    if date_start:
        try:
            start_dt = datetime.strptime(date_start, "%Y-%m-%d")
            query = query.filter(LabResult.effective_date_time >= start_dt)
        except Exception:
            pass
    if date_end:
        try:
            end_dt = datetime.strptime(date_end, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(LabResult.effective_date_time < end_dt)
        except Exception:
            pass
    results = query.order_by(LabResult.effective_date_time.desc()).all()
    # Doktor adını bulmak için id->ad eşlemesi
    doctor_map = {}
    for r in results:
        if r.doctor_id and r.doctor_id not in doctor_map:
            doc = db.query(Doctor).filter(Doctor.id == r.doctor_id).first()
            doctor_map[r.doctor_id] = doc.name if doc else None
    return [
        {
            "patient_id": r.patient_id,
            "test_name": r.display_name,
            "value": r.value,
            "unit": r.unit,
            "date": r.effective_date_time,
            "ai_analysis": r.ai_analysis,
            "doctor_id": r.doctor_id,
            "doctor_name": doctor_map.get(r.doctor_id)
        } for r in results
    ]

@app.get("/lab/tests")
async def get_available_tests():
    loinc_map = {
        "Hemoglobin": "718-7",
        "Beyaz Kan Hücresi (WBC)": "6690-2",
        "Trombosit (Platelet)": "777-3",
        "Hematokrit": "789-8",
        "Sodyum": "2951-2",
        "Potasyum": "2823-3",
        "Kreatinin": "2075-0",
        "Glukoz (Açlık)": "2345-7",
        "Total Kolesterol": "2093-3",
        "HDL Kolesterol": "2085-9",
        "LDL Kolesterol": "13457-7",
        "Trigliserid": "2571-8",
        "ALT (SGPT)": "4548-4",
        "AST (SGOT)": "1920-8",
        "Alkalin Fosfataz": "2885-2",
        "Üre Azotu (BUN)": "3094-0",
        "Bilirubin Total": "1751-7",
        "Albumin": "1925-7",
        "TSH (Tiroid Stimulan Hormon)": "14957-5",
        "Serbest T4": "14647-2",
        "Serbest T3": "14598-7",
        "CRP (C-Reaktif Protein)": "1986-5",
        "Vitamin D (25-OH)": "30000-4",
        "Ferritin": "10466-1",
        "HbA1c": "14979-9"
    }
    return {"available_tests": list(loinc_map.keys())}

@app.get("/panel", response_class=HTMLResponse)
async def user_panel(request: Request):
    return templates.TemplateResponse("panel.html", {"request": request})

@app.post("/ask-ai")
async def ask_ai_endpoint(payload: dict = Body(...)):
    question = payload.get("question")
    if not question or not question.strip():
        return JSONResponse({"answer": None, "error": "Soru boş olamaz."}, status_code=400)
    try:
        answer = ask_gemini(question)
        return {"answer": answer}
    except Exception as e:
        return JSONResponse({"answer": None, "error": str(e)}, status_code=500)

@app.post("/patient/advice")
async def patient_advice(payload: dict = Body(...), db: Session = Depends(get_db)):
    patient_id = payload.get("patient_id")
    if not patient_id:
        return JSONResponse({"advice": None, "error": "Hasta ID gerekli."}, status_code=400)
    # Hastanın tüm lab sonuçlarını çek
    from models.lab_result import LabResult
    results = db.query(LabResult).filter(LabResult.patient_id == patient_id).order_by(LabResult.effective_date_time.desc()).all()
    if not results:
        return JSONResponse({"advice": None, "error": "Bu hastaya ait laboratuvar sonucu bulunamadı."}, status_code=404)
    # Sonuçları özetle
    summary = "\n".join([
        f"{r.display_name}: {r.value} {r.unit} ({r.effective_date_time.strftime('%Y-%m-%d')})" for r in results
    ])
    prompt = f"""
    Bir hastanın laboratuvar geçmişine göre kişiselleştirilmiş sağlık tavsiyesi ve gerekirse uyarı ver.
    Hasta ID: {patient_id}
    Sonuçlar:\n{summary}
    Kısa, anlaşılır, Türkçe ve tıbbi olarak doğru bir öneri/uyarı üret.
    """
    try:
        advice = ask_gemini(prompt)
        return {"advice": advice}
    except Exception as e:
        return JSONResponse({"advice": None, "error": str(e)}, status_code=500)

@app.post("/patient/report")
async def patient_report(payload: dict = Body(...), db: Session = Depends(get_db)):
    patient_id = payload.get("patient_id")
    if not patient_id:
        return JSONResponse({"report": None, "error": "Hasta ID gerekli."}, status_code=400)
    from models.lab_result import LabResult
    results = db.query(LabResult).filter(LabResult.patient_id == patient_id).order_by(LabResult.effective_date_time.desc()).all()
    if not results:
        return JSONResponse({"report": None, "error": "Bu hastaya ait laboratuvar sonucu bulunamadı."}, status_code=404)
    summary = "\n".join([
        f"{r.display_name}: {r.value} {r.unit} ({r.effective_date_time.strftime('%Y-%m-%d')})" for r in results
    ])
    prompt = f"""
    Bir hastanın laboratuvar geçmişini özetleyen, önemli değişiklikleri ve dikkat edilmesi gereken noktaları vurgulayan kısa bir tıbbi rapor oluştur.
    Hasta ID: {patient_id}
    Sonuçlar:\n{summary}
    Türkçe, anlaşılır ve tıbbi olarak doğru bir özet/rapor üret.
    """
    try:
        report = ask_gemini(prompt)
        return {"report": report}
    except Exception as e:
        return JSONResponse({"report": None, "error": str(e)}, status_code=500)

@app.post("/patient/risk")
async def patient_risk(payload: dict = Body(...), db: Session = Depends(get_db)):
    patient_id = payload.get("patient_id")
    if not patient_id:
        return JSONResponse({"risk": None, "error": "Hasta ID gerekli."}, status_code=400)
    from models.lab_result import LabResult
    results = db.query(LabResult).filter(LabResult.patient_id == patient_id).order_by(LabResult.effective_date_time.desc()).all()
    if not results:
        return JSONResponse({"risk": None, "error": "Bu hastaya ait laboratuvar sonucu bulunamadı."}, status_code=404)
    summary = "\n".join([
        f"{r.display_name}: {r.value} {r.unit} ({r.effective_date_time.strftime('%Y-%m-%d')})" for r in results
    ])
    prompt = f"""
    Bir hastanın laboratuvar geçmişi ve mevcut sonuçlarına göre, sadece referans aralığına bakmadan, geçmiş değerler ve ilişkili testlerle riskli durumları tespit et ve tıbbi uyarı ver.
    Hasta ID: {patient_id}
    Sonuçlar:\n{summary}
    Türkçe, kısa, anlaşılır ve tıbbi olarak doğru bir risk analizi/uyarı üret.
    """
    try:
        risk = ask_gemini(prompt)
        return {"risk": risk}
    except Exception as e:
        return JSONResponse({"risk": None, "error": str(e)}, status_code=500)

@app.post("/report/analyze")
async def report_analyze(file: UploadFile = File(...)):
    explanation = None
    try:
        # Dosya türünü belirle
        content_type = file.content_type or mimetypes.guess_type(file.filename)[0]
        # Dosyayı geçici olarak kaydet
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        text = None
        if content_type and 'pdf' in content_type:
            # PDF'den metin çıkar
            with open(tmp_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = "\n".join([page.extract_text() or '' for page in reader.pages])
        elif content_type and ('image' in content_type or file.filename.lower().endswith(('.jpg','.jpeg','.png','.bmp','.tiff','.gif'))):
            # Görselden OCR ile metin çıkar
            img = Image.open(tmp_path)
            text = pytesseract.image_to_string(img, lang='tur')
        else:
            # Düz metin dosyası
            with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        os.unlink(tmp_path)
        if not text or not text.strip():
            return {"explanation": None, "error": "Dosyadan metin çıkarılamadı."}
        prompt = f"""
        Aşağıdaki tıbbi raporu veya dökümanı özetle, önemli noktaları ve tıbbi anlamını açıkla:
        ---
        {text[:4000]}
        ---
        Türkçe, anlaşılır ve tıbbi olarak doğru bir açıklama/özet üret.
        """
        explanation = ask_gemini(prompt)
        return {"explanation": explanation}
    except Exception as e:
        return {"explanation": None, "error": str(e)}

@app.post("/symptom/analyze")
async def symptom_analyze(payload: dict = Body(...)):
    text = payload.get("text")
    if not text or not text.strip():
        return {"analysis": None, "error": "Semptom metni boş olamaz."}
    prompt = f"""
    Bir hastanın aşağıdaki semptomlarını analiz et. Olası nedenleri, hangi testlerin yapılması gerektiğini ve gerekirse acil durum uyarısı ver.
    Semptomlar: {text}
    Türkçe, kısa, anlaşılır ve tıbbi olarak doğru bir analiz/öneri üret.
    """
    try:
        analysis = ask_gemini(prompt)
        return {"analysis": analysis}
    except Exception as e:
        return {"analysis": None, "error": str(e)}

@app.post("/clinical/decision")
async def clinical_decision(payload: dict = Body(...)):
    history = payload.get("history", "").strip()
    labs = payload.get("labs", "").strip()
    if not history and not labs:
        return {"suggestion": None, "error": "Hasta öyküsü veya laboratuvar sonucu girilmelidir."}
    prompt = f"""
    Bir hastanın aşağıdaki öyküsü ve laboratuvar sonuçlarına göre olası tanı ve tedavi önerileri üret. Klinik rehberlere uygun, kısa ve anlaşılır şekilde yaz.
    Hasta öyküsü: {history or '-'}
    Laboratuvar sonuçları: {labs or '-'}
    Türkçe, tıbbi olarak doğru ve pratik öneriler sun.
    """
    try:
        suggestion = ask_gemini(prompt)
        return {"suggestion": suggestion}
    except Exception as e:
        return {"suggestion": None, "error": str(e)}

@app.post("/login")
async def login(payload: dict = Body(...), db: Session = Depends(get_db)):
    username = payload.get("username")
    password = payload.get("password")
    if not username or not password:
        return {"error": "Kullanıcı adı ve şifre zorunlu."}
    doctor = db.query(Doctor).filter(Doctor.username == username).first()
    if not doctor or not bcrypt.verify(password, doctor.password_hash):
        return {"error": "Kullanıcı adı veya şifre hatalı."}
    token = create_access_token({"doctor_id": doctor.id, "username": doctor.username, "name": doctor.name, "is_admin": doctor.is_admin})
    return {"access_token": token, "doctor": {"id": doctor.id, "username": doctor.username, "name": doctor.name, "is_admin": doctor.is_admin}}

def require_admin(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=403, detail="Admin yetkisi gerekli.")
    token = authorization.split(' ', 1)[1]
    payload = verify_token(token)
    if not payload or payload.get('is_admin') != '1':
        raise HTTPException(status_code=403, detail="Admin yetkisi gerekli.")
    return True

@app.get("/admin/doctors")
async def admin_list_doctors(db: Session = Depends(get_db), admin=Depends(require_admin)):
    doctors = db.query(Doctor).all()
    return [
        {"id": d.id, "username": d.username, "name": d.name, "created_at": d.created_at, "is_admin": d.is_admin} for d in doctors
    ]

@app.post("/admin/doctors")
async def admin_add_doctor(payload: dict = Body(...), db: Session = Depends(get_db), admin=Depends(require_admin)):
    username = payload.get("username")
    password = payload.get("password")
    name = payload.get("name")
    is_admin = payload.get("is_admin", "0")
    if not username or not password or not name:
        return JSONResponse({"error": "Tüm alanlar zorunlu."}, status_code=400)
    if db.query(Doctor).filter(Doctor.username == username).first():
        return JSONResponse({"error": "Bu kullanıcı adı zaten mevcut."}, status_code=400)
    import uuid
    doctor = Doctor(
        id=str(uuid.uuid4()),
        username=username,
        password_hash=bcrypt.hash(password),
        name=name,
        is_admin=is_admin
    )
    db.add(doctor)
    db.commit()
    return {"status": "success", "doctor": {"id": doctor.id, "username": doctor.username, "name": doctor.name, "is_admin": doctor.is_admin}}

@app.delete("/admin/doctors/{doctor_id}")
async def admin_delete_doctor(doctor_id: str, request: Request, db: Session = Depends(get_db), admin=Depends(require_admin)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        return JSONResponse({"error": "Doktor bulunamadı."}, status_code=404)
    try:
        data = await request.json()
    except Exception:
        data = {}
    new_doctor_id = data.get("new_doctor_id")
    if new_doctor_id:
        # Yeni doktorun varlığını kontrol et
        new_doc = db.query(Doctor).filter(Doctor.id == new_doctor_id).first()
        if not new_doc:
            return JSONResponse({"error": "Atanacak doktor bulunamadı."}, status_code=404)
        from models.patient import Patient
        patients = db.query(Patient).filter(Patient.doctor_id == doctor_id).all()
        for p in patients:
            p.doctor_id = new_doctor_id
    else:
        # Eğer bağlı hasta varsa hata döndür
        from models.patient import Patient
        count = db.query(Patient).filter(Patient.doctor_id == doctor_id).count()
        if count > 0:
            return JSONResponse({"error": "Bu doktora bağlı hastalar var. Lütfen yeni bir doktor seçin."}, status_code=400)
    db.delete(doctor)
    db.commit()
    return {"status": "success"}

@app.post("/admin/doctors/{doctor_id}/reset_password")
async def admin_reset_doctor_password(doctor_id: str, payload: dict = Body(...), db: Session = Depends(get_db), admin=Depends(require_admin)):
    new_password = payload.get("new_password")
    if not new_password:
        return JSONResponse({"error": "Yeni şifre zorunlu."}, status_code=400)
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        return JSONResponse({"error": "Doktor bulunamadı."}, status_code=404)
    doctor.password_hash = bcrypt.hash(new_password)
    db.commit()
    return {"status": "success"}

@app.get("/doctor/my-patients-results")
async def doctor_my_patients_results(
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    # Token'dan doctor_id al
    doctor_id = None
    if authorization and authorization.startswith('Bearer '):
        token = authorization.split(' ', 1)[1]
        payload = verify_token(token)
        if payload:
            doctor_id = payload.get('doctor_id')
    if not doctor_id:
        return JSONResponse({"error": "Yetki yok."}, status_code=403)
    from models.patient import Patient
    from models.lab_result import LabResult
    # Bu doktora bağlı hastaları bul
    patients = db.query(Patient).filter(Patient.doctor_id == doctor_id).all()
    patient_ids = [p.id for p in patients]
    results = db.query(LabResult).filter(LabResult.patient_id.in_(patient_ids)).order_by(LabResult.effective_date_time.desc()).all()
    return [
        {
            "patient_id": r.patient_id,
            "test_name": r.display_name,
            "value": r.value,
            "unit": r.unit,
            "date": r.effective_date_time,
            "ai_analysis": r.ai_analysis,
            "doctor_id": r.doctor_id
        } for r in results
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=False)
