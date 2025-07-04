from typing import Dict, Any, Optional
import requests
from services.gemini_ai import ask_gemini

class AIAnalyzer:
    def __init__(self):
        self.reference_ranges = {
            "6690-2": { # LOINC kodu: Beyaz Kan Hücresi (WBC)
                "display_name": "Beyaz Kan Hücresi (WBC)",
                "unit": "10*9/L",
                "normal_min": 4.0,
                "normal_max": 10.0,
                "high_threshold_alert": 11.0 # Kritik yüksek eşik
            },
            "718-7": {  # Hemoglobin
                "display_name": "Hemoglobin",
                "unit": "g/dL",
                "normal_min": 12.0,
                "normal_max": 17.0
            }
        }

    def get_loinc_info(self, loinc_code):
        url = "https://fhir.loinc.org/CodeSystem/$lookup"
        params = {
            "system": "http://loinc.org",
            "code": loinc_code,
            "_format": "json"
        }
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                result = {"loinc_code": loinc_code}
                for prop in data.get("parameter", []):
                    if prop.get("name") == "display":
                        result["display"] = prop.get("valueString")
                    if prop.get("name") == "property":
                        for part in prop.get("part", []):
                            if part.get("name") == "code" and part.get("valueCode") == "EXAMPLE_UNITS":
                                for p in prop.get("part", []):
                                    if p.get("name") == "valueString":
                                        result["unit"] = p.get("valueString")
                return result
            else:
                print(f"LOINC API error: {response.status_code}")
                return None
        except Exception as e:
            print(f"LOINC API exception: {e}")
            return None

    def get_reference_range(self, loinc_code):
        url = f"https://health-ai-assistant-panel.onrender.com/reference-range?loinc={loinc_code}"
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print("Referans API hatası:", e)
        return None

    def analyze_lab_result(self, lab_result_data: Dict[str, Any]) -> Optional[str]:
        loinc_code = lab_result_data.get("loinc_code")
        value = lab_result_data.get("value")
        unit = lab_result_data.get("unit")
        display_name = lab_result_data.get("display_name", "Test Sonucu")
        patient_id = lab_result_data.get("patient_id")

        # Referans aralığını bul
        if loinc_code in self.reference_ranges:
            ref_info = self.reference_ranges[loinc_code]
        else:
            ref_info = self.get_reference_range(loinc_code)
            if not ref_info:
                loinc_info = self.get_loinc_info(loinc_code)
                if loinc_info:
                    print(f"LOINC API'den çekilen bilgi: {loinc_info}")
                return None

        def normalize_unit(u):
            return u.replace(" ", "").lower() if isinstance(u, str) else u
        if normalize_unit(unit) != normalize_unit(ref_info["unit"]):
            print(f"Uyarı: Birim uyuşmazlığı - {display_name}. Beklenen: {ref_info['unit']}, Gelen: {unit}")
            return None

        # Hasta geçmişini ve temel bilgileri çek (örnek: son 5 test sonucu)
        patient_history = None  # Burada DB'den geçmiş sonuçlar çekilebilir
        patient_info = f"Hasta ID: {patient_id}"  # Gerekirse daha fazla bilgi eklenebilir

        # Gemini AI ile analiz
        try:
            return analyze_lab_result_with_gemini(
                test_name=display_name,
                value=value,
                unit=unit,
                ref_min=ref_info["normal_min"],
                ref_max=ref_info["normal_max"],
                patient_history=patient_history,
                patient_info=patient_info
            )
        except Exception as e:
            print(f"Gemini AI analiz hatası: {e}")
            return None

def analyze_lab_result_with_gemini(test_name, value, unit, ref_min, ref_max, patient_history=None, patient_info=None):
    """
    Laboratuvar sonucu ve geçmişiyle Gemini AI'dan açıklama alır.
    """
    prompt = f"""
    Bir hastanın laboratuvar sonucu için tıbbi açıklama ve öneri üret.
    Test adı: {test_name}
    Değer: {value} {unit}
    Referans aralığı: {ref_min} - {ref_max} {unit}
    """
    if patient_info:
        prompt += f"\nHasta bilgisi: {patient_info}"
    if patient_history:
        prompt += f"\nHastanın geçmiş sonuçları: {patient_history}"
    prompt += "\nKısa, anlaşılır, Türkçe ve tıbbi olarak doğru bir açıklama ve gerekirse öneri ver."
    return ask_gemini(prompt)
