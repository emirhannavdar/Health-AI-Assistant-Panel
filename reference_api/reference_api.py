import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

with open("reference_data.json") as f:
    REFERENCE_RANGES = json.load(f)

app = FastAPI()

# CORS middleware ekle
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Gerekirse sadece http://127.0.0.1:8000 yazabilirsin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/reference-range")
def get_reference_range(loinc: str):
    if loinc in REFERENCE_RANGES:
        return REFERENCE_RANGES[loinc]
    else:
        raise HTTPException(status_code=404, detail="LOINC kodu bulunamadı") 