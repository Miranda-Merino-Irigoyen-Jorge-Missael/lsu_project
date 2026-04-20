import logging
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from src.services.auth_service import get_credentials
from src.config.settings import DRIVE_FOLDER_ID

logger = logging.getLogger(__name__)

def generar_y_subir_documento(contenido: str, nombre_documento: str) -> str:
    """
    Toma el contenido HTML generado por Gemini y lo sube a Drive.
    Drive automáticamente convierte las etiquetas <b>, <h1>, etc. en formato de Google Docs.
    """
    try:
        credenciales = get_credentials()
        drive_service = build('drive', 'v3', credentials=credenciales)

        # 1. Limpiar el contenido (por si Gemini pone backticks como ```html o ```markdown)
        limpio = contenido.replace('```html', '').replace('```markdown', '').replace('```', '').strip()

        # 2. Metadatos: Le decimos a Drive explícitamente que lo convierta a Google Doc
        file_metadata = {
            'name': f"REPORTE_FINAL_{nombre_documento}",
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [DRIVE_FOLDER_ID]
        }

        # 3. Convertimos el texto a un archivo en memoria indicando que es texto HTML
        fh = io.BytesIO(limpio.encode('utf-8'))
        media = MediaIoBaseUpload(fh, mimetype='text/html', resumable=True)

        # 4. Crear y subir el archivo a Drive
        documento = drive_service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id'
        ).execute()
        
        doc_id = documento.get('id')
        logger.info(f"Nuevo Google Doc creado con formato nativo. ID: {doc_id}")

        return f"[https://docs.google.com/document/d/](https://docs.google.com/document/d/){doc_id}/edit"

    except Exception as e:
        logger.error(f"Error crítico al generar el Google Doc: {e}")
        raise e