"""
Orquestador Principal del Proyecto LSU.
Lee los PDFs locales, clasifica por nombre, procesa con Gemini y genera Google Docs.
"""
import os
import logging
from src.config.settings import LOCAL_PDF_DIR, CASE_CONFIG
from src.services.storage_service import upload_pdf_to_gcs
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
    Lee la carpeta local y procesa cada PDF válido.
    """
    if not os.path.exists(LOCAL_PDF_DIR):
        logger.error(f"CRÍTICO: El directorio local no existe: {LOCAL_PDF_DIR}")
        return

    archivos = [f for f in os.listdir(LOCAL_PDF_DIR) if f.lower().endswith('.pdf')]
    
    if not archivos:
        logger.warning(f"No se encontraron archivos PDF en la ruta: {LOCAL_PDF_DIR}")
        return

    logger.info(f"Se encontraron {len(archivos)} PDFs en la carpeta local. Evaluando...")

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
            
            # 2. Subir PDF del cliente a Google Cloud Storage
            uri_cliente = upload_pdf_to_gcs(ruta_local, destination_folder=f"clientes_{tipo_caso}")
            
            # 3. Descargar las instrucciones desde Firestore
            sys_inst, usr_prompt = get_prompts_from_firestore(
                config["fs_system_doc"], 
                config["fs_prompt_doc"]
            )
            
            # 4. Enviar a Gemini (Vertex AI) cruzando con el template correcto
            texto_resultado = analyze_case_documents(
                system_instruction=sys_inst,
                user_prompt_template=usr_prompt,
                client_pdf_uri=uri_cliente,
                form_pdf_uri=config["template_uri"]
            )
            
            # 5. Generar Google Doc en Drive
            # Quitamos la extensión .pdf para nombrar el Google Doc de forma limpia
            nombre_base = os.path.splitext(archivo)[0]
            nombre_doc_final = f"LSC REPORT AI_{nombre_base}"
            
            link_drive = generar_y_subir_documento(texto_resultado, nombre_doc_final)
            logger.info(f"=== ÉXITO: Caso completado. Link del documento: {link_drive} ===")
            
        except Exception as e:
            # Si un documento falla, capturamos el error pero el loop continúa con el siguiente PDF
            logger.error(f"❌ Error crítico al procesar '{archivo}': {str(e)}")
            continue

if __name__ == "__main__":
    logger.info("=== Iniciando Sistema de Procesamiento LSU ===")
    procesar_lote()
    logger.info("=== Proceso por lotes finalizado ===")