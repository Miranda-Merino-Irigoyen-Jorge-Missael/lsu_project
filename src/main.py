"""
Orquestador Principal del Proyecto LSU.
Lee los archivos JSON locales, extrae las notas, clasifica por nombre, procesa con Gemini y genera Google Docs.
"""
import os
import json
import logging
from src.config.settings import LOCAL_PDF_DIR, CASE_CONFIG
from src.services.firestore_service import get_prompts_from_firestore
from src.services.gemini_service import analyze_case_documents
from src.services.drive_docs_service import generar_y_subir_documento

logger = logging.getLogger(__name__)

def clasificar_archivo(nombre_archivo: str) -> str:
    """
    Clasifica el archivo basado en si contiene las cadenas de texto clave.
    """
    nombre_upper = nombre_archivo.upper()
    if "VAWA DA" in nombre_upper:
        return "vawada"
    elif "VAWA AOS" in nombre_upper:
        return "vawaaos"
    elif "VISA T" in nombre_upper:
        return "visat"
    return None

def procesar_lote():
    """
    Lee la carpeta local y procesa cada archivo JSON válido.
    """
    # Nota: Se mantiene LOCAL_PDF_DIR de settings.py por compatibilidad, pero ahora busca JSONs. 
    # Te sugiero renombrarla a LOCAL_INPUT_DIR en tus settings en el futuro.
    if not os.path.exists(LOCAL_PDF_DIR):
        logger.error(f"CRÍTICO: El directorio local no existe: {LOCAL_PDF_DIR}")
        return

    archivos = [f for f in os.listdir(LOCAL_PDF_DIR) if f.lower().endswith('.json')]
    
    if not archivos:
        logger.warning(f"No se encontraron archivos JSON en la ruta: {LOCAL_PDF_DIR}")
        return

    logger.info(f"Se encontraron {len(archivos)} JSONs en la carpeta local. Evaluando...")

    for archivo in archivos:
        logger.info(f"\n--- Evaluando documento: {archivo} ---")
        
        # 1. Clasificación
        tipo_caso = clasificar_archivo(archivo)
        if not tipo_caso:
            logger.info(f"Saltando '{archivo}': No contiene 'VISA T', 'VAWA DA' o 'VAWA AOS' en el título.")
            continue
            
        config = CASE_CONFIG[tipo_caso]
        ruta_local = os.path.join(LOCAL_PDF_DIR, archivo)
        
        try:
            logger.info(f"Clasificado como: {tipo_caso.upper()}")
            
            # 2. Leer JSON y extraer notas
            with open(ruta_local, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            texto_notas_procesado = ""
            if "notes" in data and isinstance(data["notes"], list):
                logger.info(f"Extrayendo {len(data['notes'])} notas del JSON...")
                for index, note in enumerate(data["notes"], start=1):
                    subject = note.get("subject", "Sin asunto")
                    body = note.get("body", "Sin contenido")
                    # Concatenamos cada nota en un formato legible para Gemini
                    texto_notas_procesado += f"--- NOTA {index} ---\nASUNTO: {subject}\nCONTENIDO:\n{body}\n\n"
            else:
                logger.warning(f"Saltando '{archivo}': No se encontró el arreglo 'notes' en el JSON.")
                continue
            
            # 3. Descargar las instrucciones desde Firestore
            sys_inst, usr_prompt = get_prompts_from_firestore(
                config["fs_system_doc"], 
                config["fs_prompt_doc"]
            )
            
            # 4. Enviar a Gemini (Vertex AI) pasando el texto extraído
            texto_resultado = analyze_case_documents(
                system_instruction=sys_inst,
                user_prompt_template=usr_prompt,
                client_notes_json=texto_notas_procesado,
                form_pdf_uri=config["template_uri"]
            )
            
            # 5. Generar Google Doc en Drive
            # Quitamos la extensión .json para nombrar el Google Doc de forma limpia
            nombre_base = os.path.splitext(archivo)[0]
            nombre_doc_final = f"LSC REPORT AI_{nombre_base}"
            
            link_drive = generar_y_subir_documento(texto_resultado, nombre_doc_final)
            logger.info(f"=== ÉXITO: Caso completado. Link del documento: {link_drive} ===")
            
        except Exception as e:
            # Si un documento falla, capturamos el error pero el loop continúa con el siguiente JSON
            logger.error(f"❌ Error crítico al procesar '{archivo}': {str(e)}")
            continue

if __name__ == "__main__":
    logger.info("=== Iniciando Sistema de Procesamiento LSU ===")
    procesar_lote()
    logger.info("=== Proceso por lotes finalizado ===")