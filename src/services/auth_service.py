import os
import logging
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

# Definimos los alcances (Scopes) para Drive, Firestore y Vertex AI
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/cloud-platform'
]

def get_credentials():
    """Gestiona credenciales OAuth2 usando token.json."""
    token_path = 'token.json'
    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Si no hay credenciales válidas, pedimos al usuario que inicie sesión
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refrescando token de acceso expirado...")
            creds.refresh(Request())
        else:
            logger.error("Token no válido o inexistente. Ejecuta generar_token.py")
            raise Exception("Requiere re-autenticación con generar_token.py")

        # Guardamos el token refrescado
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return creds