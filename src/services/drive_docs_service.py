import logging
import json
from googleapiclient.discovery import build
from src.services.auth_service import get_credentials
from src.config.settings import DRIVE_FOLDER_ID, TEMPLATE_DOC_ID

logger = logging.getLogger(__name__)

def generar_y_subir_documento(json_content: str, nombre_documento: str) -> str:
    """
    Toma el JSON generado por Gemini, clona el template de Google Docs
    y reemplaza las etiquetas con los datos extraídos manteniendo el formato.
    """
    try:
        credenciales = get_credentials()
        # Necesitamos ambos servicios: Drive (para copiar) y Docs (para editar)
        drive_service = build('drive', 'v3', credentials=credenciales)
        docs_service = build('docs', 'v1', credentials=credenciales)

        # 1. Parsear el JSON devuelto por Gemini
        # Limpiamos los backticks por si el modelo los incluyó como markdown
        limpio = json_content.replace('```json', '').replace('```', '').strip()
        datos = json.loads(limpio)

        # 2. Copiar el Template de Google Docs
        body = {
            'name': f"REPORTE_FINAL_{nombre_documento}",
            'parents': [DRIVE_FOLDER_ID]
        }
        
        copia = drive_service.files().copy(
            fileId=TEMPLATE_DOC_ID, 
            body=body
        ).execute()
        
        nuevo_doc_id = copia.get('id')
        logger.info(f"Template copiado exitosamente. ID: {nuevo_doc_id}")

        # 3. Preparar los reemplazos masivos (Batch Update)
        requests = []
        for llave, valor in datos.items():
            # Construimos la etiqueta exacta que está en el Doc: {{LLAVE}}
            etiqueta = f"{{{{{llave}}}}}" 
            
            # Aseguramos que el valor sea un string
            valor_str = str(valor) if valor is not None else ""
            
            requests.append({
                'replaceAllText': {
                    'containsText': {
                        'text': etiqueta,
                        'matchCase': True
                    },
                    'replaceText': valor_str
                }
            })

        # 4. Inyectar los datos en el documento copiado
        if requests:
            docs_service.documents().batchUpdate(
                documentId=nuevo_doc_id,
                body={'requests': requests}
            ).execute()
            
        logger.info("Inyección de datos completada respetando el formato original.")

        return f"https://docs.google.com/document/d/{nuevo_doc_id}/edit"

    except json.JSONDecodeError as e:
        logger.error(f"Error al decodificar el JSON de Gemini: {e}")
        logger.error(f"Contenido crudo: {json_content}")
        raise e
    except Exception as e:
        logger.error(f"Error crítico al clonar/editar el Google Doc: {e}")
        raise e