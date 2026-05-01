"""
Configuración central del proyecto LSU.
Versión corregida para procesamiento basado en Markdown y nuevo template.
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Localizar el archivo .env en la raíz del proyecto
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# --- Configuración de Logging ---
LOG_LEVEL = logging.INFO
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Google Cloud & Proyecto ---
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")

# --- Google Cloud Storage ---
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "lsu_tmlf")
LOCAL_PDF_DIR = os.getenv("LOCAL_PDF_DIR", r"C:\Users\missa\OneDrive\Documentos\LSU")

# --- Firestore ---
FIRESTORE_COLLECTION = os.getenv("FIRESTORE_COLLECTION", "prompt_LSU")

# --- Google Drive ---
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "1Q5dmcT7q6wx8xw6PBiKYo5kCDrfxFjd4")
TEMPLATE_DOC_ID = os.getenv("TEMPLATE_DOC_ID", "1etakhSIxR6sQbGMfPzVO1CugPVBtL4RABjyedGiQRpk")

# --- Vertex AI & Gemini ---
VERTEX_TIMEOUT_SECONDS = 350
# Actualizado a 1.5 Pro para mejor manejo de estructuras Markdown y documentos largos
MODEL_NAME = "gemini-3.1-pro-preview" 

# ==============================================================================
# ENRUTADOR DE CASOS (MODO PRUEBA: SÓLO VISA T)
# ==============================================================================
# Se actualiza el nombre del template según tu .env: "VISA T (LSC REPORT).pdf"
TEMPLATE_NAME = os.getenv('TEMPLATE_VISAT_NAME', 'VISA T (LSC REPORT).pdf')

CASE_CONFIG = {
    "visat": {
        "template_uri": f"gs://{GCS_BUCKET_NAME}/templates/{TEMPLATE_NAME}",
        "fs_system_doc": "system_instruction_visat",
        "fs_prompt_doc": "prompt_visat_pdfs"
    }
}

# Validación de seguridad de arranque
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    raise ValueError("ERROR CRÍTICO: No se encontró la ruta de GOOGLE_APPLICATION_CREDENTIALS en el .env")