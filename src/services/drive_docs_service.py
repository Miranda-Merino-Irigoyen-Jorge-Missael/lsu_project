import logging
import json
from googleapiclient.discovery import build
from src.services.auth_service import get_credentials

# ID de tu plantilla que me pasaste
TEMPLATE_ID = '1etakhSIxR6sQbGMfPzVO1CugPVBtL4RABjyedGiQRpk'
# Carpeta donde quieres que se guarden los reportes finales (usa la misma de tus settings)
from src.config.settings import DRIVE_FOLDER_ID

logger = logging.getLogger(__name__)

def generar_y_subir_documento(json_gemini: str, nombre_documento: str) -> str:
    """
    Toma el JSON de Gemini, clona la plantilla y reemplaza las etiquetas {{ }}.
    """
    try:
        credenciales = get_credentials()
        drive_service = build('drive', 'v3', credentials=credenciales)
        docs_service = build('docs', 'v1', credentials=credenciales)

        # 1. Limpiar el JSON (por si Gemini agregó backticks ```json)
        json_clean = json_gemini.strip().replace('```json', '').replace('```', '')
        datos = json.loads(json_clean)

        # 2. Copiar la plantilla
        copy_metadata = {
            'name': f"REPORTE_FINAL_{nombre_documento}",
            'parents': [DRIVE_FOLDER_ID]
        }
        documento_copiado = drive_service.files().copy(
            fileId=TEMPLATE_ID, 
            body=copy_metadata
        ).execute()
        
        doc_id = documento_copiado.get('id')
        logger.info(f"Copia de plantilla creada con ID: {doc_id}")

        # 3. Preparar los reemplazos
        requests = []
        for llave, valor in datos.items():
            requests.append({
                'replaceAllText': {
                    'containsText': {
                        'text': '{{' + llave + '}}',
                        'matchCase': True
                    },
                    'replaceText': str(valor)
                }
            })

        # 4. Ejecutar todos los reemplazos de un solo golpe (Batch Update)
        if requests:
            docs_service.documents().batchUpdate(
                documentId=doc_id, 
                body={'requests': requests}
            ).execute()
            logger.info("Inyección de datos completada exitosamente.")

        return f"[https://docs.google.com/document/d/](https://docs.google.com/document/d/){doc_id}/edit"

    except Exception as e:
        logger.error(f"Error crítico en el motor de inyección: {e}")
        raise e