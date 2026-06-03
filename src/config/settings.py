"""
Configuración central del proyecto LSU.
Versión corregida para procesamiento basado en Markdown, nuevo template y Sheets.
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
# Actualizado con el ID de la nueva carpeta del Workspace
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "1AdG_BmzrVivhtAyAYhN_WfnlAO4PobiT")

# --- Google Sheets ---
# IDs para lectura y escritura de base de datos
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1tCxLAc5fLsYn2NqyRJq4anzrXOgAyLuVzqKVhlh-Of8")
SHEET_NAME = os.getenv("SHEET_NAME", "procesar")

# IDs de los Templates de Google Docs extraídos del .env
TEMPLATE_VISAT_ID = os.getenv("TEMPLATE_DOC_ID")
TEMPLATE_VAWAAOS_ID = os.getenv("TEMPLATE_VAWAAOS_ID")

# --- Vertex AI & Gemini ---
VERTEX_TIMEOUT_SECONDS = 350
MODEL_NAME = "gemini-3.1-pro-preview" 

# ==============================================================================
# ENRUTADOR DE CASOS
# ==============================================================================
TEMPLATE_VISAT_FILE = os.getenv('TEMPLATE_VISAT_NAME', 'VISA T (LSC REPORT).pdf')
TEMPLATE_VAWAAOS_FILE = os.getenv('TEMPLATE_VAWAAOS_NAME', 'VAWA AOS (LSC REPORT).pdf')

CASE_CONFIG = {
    "visat": {
        "template_uri": f"gs://{GCS_BUCKET_NAME}/templates/{TEMPLATE_VISAT_FILE}",
        "template_doc_id": TEMPLATE_VISAT_ID,
        "fs_system_doc": "system_instruction_visat",
        "fs_prompt_doc": "prompt_visat_pdfs"
    },
    "vawaaos": {
        "template_uri": f"gs://{GCS_BUCKET_NAME}/templates/{TEMPLATE_VAWAAOS_FILE}",
        "template_doc_id": TEMPLATE_VAWAAOS_ID,
        "fs_system_doc": "system_instruction_vawaaos",
        "fs_prompt_doc": "prompt_vawaaos_pdfs"
    }
}

# Validación de seguridad de arranque
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    raise ValueError("ERROR CRÍTICO: No se encontró la ruta de GOOGLE_APPLICATION_CREDENTIALS en el .env")

if not TEMPLATE_VISAT_ID or not TEMPLATE_VAWAAOS_ID:
    logging.warning("ADVERTENCIA: Algunos IDs de templates de Google Drive no están definidos en el .env")