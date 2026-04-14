"""
Servicio de Google Cloud Storage.
Sube los PDFs locales al bucket para que Vertex AI pueda procesarlos por URI.
"""
import logging
import os
from google.cloud import storage
from src.config.settings import GCS_BUCKET_NAME, GCP_PROJECT_ID
from src.services.auth_service import get_credentials

logger = logging.getLogger(__name__)

def upload_pdf_to_gcs(local_pdf_path: str, destination_folder: str = "procesados") -> str:
    """
    Sube un PDF local al bucket de GCS y retorna su URI (gs://...)
    
    Args:
        local_pdf_path: Ruta del archivo en tu PC local.
        destination_folder: Subcarpeta en el bucket donde se guardará.
        
    Returns:
        str: La URI del archivo en GCS (ej. gs://tu-bucket/procesados/archivo.pdf)
    """
    if not os.path.exists(local_pdf_path):
        raise FileNotFoundError(f"No se encontró el PDF local en: {local_pdf_path}")
        
    filename = os.path.basename(local_pdf_path)
    destination_blob_name = f"{destination_folder}/{filename}"
    
    try:
        # Inicializamos el cliente de Storage con nuestras credenciales
        credentials = get_credentials()
        storage_client = storage.Client(credentials=credentials, project=GCP_PROJECT_ID)
        
        # Conectamos al bucket
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(destination_blob_name)
        
        # Subimos el archivo
        logger.info(f"Subiendo '{filename}' a GCS ({GCS_BUCKET_NAME}/{destination_blob_name})...")
        blob.upload_from_filename(local_pdf_path)
        
        # Construimos la URI de GCS que necesita Vertex AI
        gcs_uri = f"gs://{GCS_BUCKET_NAME}/{destination_blob_name}"
        logger.info(f"Subida exitosa. URI: {gcs_uri}")
        
        return gcs_uri
        
    except Exception as e:
        logger.error(f"Error al subir el archivo a Storage: {e}")
        raise