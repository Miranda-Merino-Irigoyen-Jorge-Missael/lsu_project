"""
Servicio de Firestore.
Recupera las instrucciones de sistema y los prompts dinámicos según el tipo de caso.
"""
import logging
from google.cloud import firestore
from src.config.settings import GCP_PROJECT_ID, FIRESTORE_COLLECTION
from src.services.auth_service import get_credentials

logger = logging.getLogger(__name__)

def get_prompts_from_firestore(system_doc_id: str, prompt_doc_id: str) -> tuple:
    """
    Busca los documentos en Firestore y extrae el valor exacto del campo 'template'.
    """
    logger.info(f"Recuperando prompts de Firestore: [{system_doc_id}] y [{prompt_doc_id}]")
    try:
        credentials = get_credentials()
        db = firestore.Client(credentials=credentials, project=GCP_PROJECT_ID)
        
        system_ref = db.collection(FIRESTORE_COLLECTION).document(system_doc_id)
        prompt_ref = db.collection(FIRESTORE_COLLECTION).document(prompt_doc_id)
        
        system_snap = system_ref.get()
        prompt_snap = prompt_ref.get()
        
        if not system_snap.exists:
            raise ValueError(f"CRÍTICO: No se encontró el documento '{system_doc_id}' en Firestore.")
        if not prompt_snap.exists:
            raise ValueError(f"CRÍTICO: No se encontró el documento '{prompt_doc_id}' en Firestore.")
            
        system_instruction = system_snap.to_dict().get("template", "")
        user_prompt = prompt_snap.to_dict().get("template", "")
        
        return system_instruction, user_prompt
        
    except Exception as e:
        logger.error(f"Error al recuperar datos de Firestore: {e}")
        raise