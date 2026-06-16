"""
Orquestador Principal del Proyecto LSU.
Se conecta a Google Sheets, identifica casos pendientes, descarga los JSONs de Drive,
procesa la información con Gemini y genera los Google Docs correspondientes.
"""
import logging
import re
from googleapiclient.discovery import build

from src.config.settings import CASE_CONFIG
from src.services.auth_service import get_credentials
from src.services.firestore_service import get_prompts_from_firestore
from src.services.gemini_service import analyze_case_documents
from src.services.drive_docs_service import generar_y_subir_documento
from src.services.sheets_service import obtener_casos_pendientes, actualizar_status_y_link

logger = logging.getLogger(__name__)

def clasificar_caso(tipo_visa_str: str) -> str:
    """
    Clasifica el caso basado en la cadena de texto de la columna 'TYPE OF VISA'.
    """
    tipo_upper = tipo_visa_str.upper()
    if "VAWA DA" in tipo_upper:
        return "vawada"
    elif "VAWA AOS" in tipo_upper:
        return "vawaaos"
    elif "VISA T" in tipo_upper:
        return "visat"
    return None

def descargar_archivo_drive(drive_link: str) -> tuple:
    """
    Extrae el ID del archivo de un link de Google Drive, detecta si es PDF o JSON
    y devuelve una tupla (contenido, mime_type).
    - PDF  → (bytes, "application/pdf")
    - JSON → (str,   "application/json")
    """
    # Extraemos el ID del link (ej. https://drive.google.com/file/d/ID_DEL_ARCHIVO/view...)
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', drive_link)
    if not match:
        # Alternativa por si el formato es ?id=...
        match = re.search(r'id=([a-zA-Z0-9_-]+)', drive_link)

    if not match:
        raise ValueError(f"No se pudo extraer el ID del archivo desde el link: {drive_link}")

    file_id = match.group(1)

    creds = get_credentials()
    drive_service = build('drive', 'v3', credentials=creds)

    # Consultamos el MIME type real del archivo en Drive
    metadata = drive_service.files().get(fileId=file_id, fields='mimeType,name').execute()
    mime_type = metadata.get('mimeType', '')
    file_name = metadata.get('name', file_id)
    logger.info(f"Archivo detectado en Drive: '{file_name}' | MIME: {mime_type}")

    raw_bytes = drive_service.files().get_media(fileId=file_id).execute()

    if 'pdf' in mime_type:
        logger.info(f"Descargando como PDF ({len(raw_bytes)} bytes).")
        return raw_bytes, "application/pdf"
    elif 'json' in mime_type or mime_type in ('text/plain', 'application/octet-stream'):
        # Los archivos .json subidos manualmente a Drive pueden quedar como text/plain
        content_str = raw_bytes.decode('utf-8')
        logger.info(f"Descargando como JSON ({len(content_str)} chars).")
        return content_str, "application/json"
    else:
        raise ValueError(
            f"Tipo de archivo no soportado en Drive: '{mime_type}'. "
            "Solo se aceptan archivos PDF o JSON."
        )

def procesar_lote():
    """
    Orquesta el flujo principal leyendo desde la Spreadsheet.
    """
    casos = obtener_casos_pendientes()
    
    if not casos:
        logger.info("No hay casos pendientes ('PENDING') por procesar en la hoja de cálculo.")
        return

    for caso in casos:
        fila = caso["fila_excel"]
        id_cliente = caso["id_cliente"]
        nombre_cliente = caso["nombre_cliente"]
        tipo_visa = caso["tipo_visa"]
        pdf_link = caso["pdf_link"]

        logger.info(f"\n--- Evaluando caso fila {fila}: {id_cliente} - {nombre_cliente} ---")

        try:
            # 1. Clasificación
            tipo_caso = clasificar_caso(tipo_visa)
            if not tipo_caso:
                raise ValueError(f"Tipo de visa no reconocido o no soportado: '{tipo_visa}'.")

            config = CASE_CONFIG.get(tipo_caso)
            if not config:
                raise ValueError(f"Configuración no encontrada para el tipo de caso: '{tipo_caso}'.")

            logger.info(f"Clasificado como: {tipo_caso.upper()}")

            # 2. Descargar el archivo del cliente desde Google Drive (PDF o JSON)
            if not pdf_link:
                raise ValueError("La celda del link al archivo del cliente está vacía.")

            client_content, client_mime_type = descargar_archivo_drive(pdf_link)
            logger.info(f"Archivo del cliente descargado exitosamente (tipo: {client_mime_type}).")

            # 3. Descargar las instrucciones desde Firestore
            sys_inst, usr_prompt = get_prompts_from_firestore(
                config["fs_system_doc"],
                config["fs_prompt_doc"]
            )

            # 4. Enviar a Gemini (Vertex AI) pasando el archivo del cliente
            texto_resultado = analyze_case_documents(
                system_instruction=sys_inst,
                user_prompt_template=usr_prompt,
                client_content=client_content,
                client_mime_type=client_mime_type,
                form_pdf_uri=config["template_uri"]
            )
            
            # 6. Generar Google Doc en Drive
            # Nombramos el documento integrando ID, Nombre y Tipo de Visa
            nombre_doc_final = f"{id_cliente} - {nombre_cliente} - {tipo_visa}"
            
            link_drive = generar_y_subir_documento(
                json_content=texto_resultado, 
                nombre_documento=nombre_doc_final, 
                template_doc_id=config["template_doc_id"]
            )
            logger.info(f"Caso completado con éxito. Link del documento: {link_drive}")
            
            # 7. Actualizar estatus en Sheets a DONE y guardar el link
            actualizar_status_y_link(fila, "DONE", link_drive)
            
        except Exception as e:
            logger.error(f"Error crítico al procesar la fila {fila}: {str(e)}")
            # En caso de error, marcamos la fila con 'ERROR' para evitar ciclos infinitos
            # y registramos el mensaje de excepción en lugar del link para fines de auditoría.
            actualizar_status_y_link(fila, "ERROR", f"Error: {str(e)}")

if __name__ == "__main__":
    logger.info("=== Iniciando Sistema de Procesamiento LSU (Integración Sheets) ===")
    procesar_lote()
    logger.info("=== Proceso finalizado ===")