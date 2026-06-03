"""
Orquestador Principal del Proyecto LSU.
Se conecta a Google Sheets, identifica casos pendientes, descarga los JSONs de Drive,
procesa la información con Gemini y genera los Google Docs correspondientes.
"""
import json
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

def descargar_json_drive(drive_link: str) -> dict:
    """
    Extrae el ID del archivo de un link de Google Drive y descarga su contenido JSON.
    """
    # Extraemos el ID del link (ej. https://drive.google.com/file/d/ID_DEL_ARCHIVO/view...)
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', drive_link)
    if not match:
        # Alternativa por si el formato es ?id=...
        match = re.search(r'id=([a-zA-Z0-9_-]+)', drive_link)
        
    if not match:
        raise ValueError(f"No se pudo extraer el ID del archivo desde el link: {drive_link}")
        
    file_id = match.group(1)
    logger.info(f"Descargando JSON con ID de Drive: {file_id}")
    
    creds = get_credentials()
    drive_service = build('drive', 'v3', credentials=creds)
    
    request = drive_service.files().get_media(fileId=file_id)
    file_content = request.execute()
    
    return json.loads(file_content.decode('utf-8'))

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
        link_json = caso["json_link"]
        
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
            
            # 2. Descargar y parsear JSON desde Google Drive
            if not link_json:
                raise ValueError("La celda del link al JSON está vacía.")
                
            data = descargar_json_drive(link_json)
            
            # 3. Extraer notas
            texto_notas_procesado = ""
            if "notes" in data and isinstance(data["notes"], list):
                logger.info(f"Extrayendo {len(data['notes'])} notas del JSON descargado...")
                for index, note in enumerate(data["notes"], start=1):
                    subject = note.get("subject", "Sin asunto")
                    body = note.get("body", "Sin contenido")
                    texto_notas_procesado += f"--- NOTA {index} ---\nASUNTO: {subject}\nCONTENIDO:\n{body}\n\n"
            else:
                raise ValueError("No se encontró el arreglo 'notes' en el JSON descargado.")
            
            # 4. Descargar las instrucciones desde Firestore
            sys_inst, usr_prompt = get_prompts_from_firestore(
                config["fs_system_doc"], 
                config["fs_prompt_doc"]
            )
            
            # 5. Enviar a Gemini (Vertex AI) pasando el texto extraído
            texto_resultado = analyze_case_documents(
                system_instruction=sys_inst,
                user_prompt_template=usr_prompt,
                client_notes_json=texto_notas_procesado,
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