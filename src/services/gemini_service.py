"""
Servicio de Vertex AI (Gemini).
Maneja la inyección de prompts, carga de contexto en JSON y reintentos automáticos.
"""
import logging
import concurrent.futures
import vertexai
from vertexai.generative_models import (
    GenerativeModel, 
    Part, 
    SafetySetting, 
    HarmCategory, 
    HarmBlockThreshold,
    GenerationConfig
)
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from google.api_core import exceptions as google_exceptions

from src.config.settings import GCP_PROJECT_ID, VERTEX_LOCATION, MODEL_NAME, VERTEX_TIMEOUT_SECONDS
from src.services.auth_service import get_credentials

logger = logging.getLogger(__name__)

# Definimos los errores ante los cuales el sistema debe intentar de nuevo automáticamente
RETRY_EXCEPTIONS = (
    google_exceptions.ResourceExhausted,      # Error 429 Quota
    google_exceptions.DeadlineExceeded,       # Error 504 Timeout
    google_exceptions.ServiceUnavailable,     # Error 503
    google_exceptions.InternalServerError,    # Error 500
    TimeoutError,
    concurrent.futures.TimeoutError           # Error de timeout forzado por nosotros
)

# Inicializamos Vertex AI una sola vez
_vertex_initialized = False

def _init_vertex():
    global _vertex_initialized
    if not _vertex_initialized:
        credentials = get_credentials()
        vertexai.init(project=GCP_PROJECT_ID, location=VERTEX_LOCATION, credentials=credentials)
        _vertex_initialized = True

@retry(
    retry=retry_if_exception_type(RETRY_EXCEPTIONS),
    wait=wait_exponential(multiplier=2, min=5, max=60), # Espera 5s, 10s, 20s... entre intentos
    stop=stop_after_attempt(5),                         # Máximo 5 intentos
    reraise=True
)
def _call_gemini_with_retry(model: GenerativeModel, contents: list) -> str:
    """Ejecuta la llamada a la IA con protección de reintentos y timeout explícito mediante hilos."""
    logger.info(f"Enviando análisis a Gemini... (Timeout configurado a {VERTEX_TIMEOUT_SECONDS}s)")
    
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        # Enviamos la tarea al hilo
        future = executor.submit(model.generate_content, contents)
        # Forzamos el timeout estricto de 350 segundos
        response = future.result(timeout=VERTEX_TIMEOUT_SECONDS)
        return response.text
    except concurrent.futures.TimeoutError:
        logger.error(f"Vertex tardó más de {VERTEX_TIMEOUT_SECONDS}s. Forzando reintento...")
        raise TimeoutError(f"Vertex AI timeout ({VERTEX_TIMEOUT_SECONDS}s)")
    finally:
        # Limpiamos el hilo para no saturar la memoria
        executor.shutdown(wait=False)

def analyze_case_documents(system_instruction: str, user_prompt_template: str, client_content, client_mime_type: str, form_pdf_uri: str = None) -> str:
    """
    Adjunta el documento del cliente (PDF o JSON) como parte del contenido,
    ensambla el documento de formulario opcional y llama a Gemini.
    - Si client_mime_type == "application/pdf"  → se envía como Part binario.
    - Si client_mime_type == "application/json" → se incrusta el texto JSON en el prompt.
    """
    _init_vertex()

    # 1. Configurar el modelo con sus instrucciones de sistema y CONFIGURACIÓN JSON
    model = GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=[system_instruction],
        generation_config=GenerationConfig(
            response_mime_type="application/json", # OBLIGA A DEVOLVER JSON NATIVO
            temperature=0.2 # BAJA TEMPERATURA PARA MAYOR PRECISIÓN Y EVITAR ALUCINACIONES
        ),
        # Relajamos filtros porque los testimonios legales pueden contener lenguaje sensible
        safety_settings=[
            SafetySetting(category=HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=HarmBlockThreshold.BLOCK_NONE),
            SafetySetting(category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=HarmBlockThreshold.BLOCK_NONE),
            SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=HarmBlockThreshold.BLOCK_NONE),
            SafetySetting(category=HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=HarmBlockThreshold.BLOCK_NONE),
        ]
    )

    # 2. Construir el prompt base reemplazando variables dinámicas
    if client_mime_type == "application/pdf":
        prompt_text = user_prompt_template.replace(
            "{pdf_cliente}", "[Ver Documento Adjunto: PDF del Cliente]"
        )
    else:
        # JSON: incrustamos el contenido directamente en el prompt como texto
        json_block = f"\n\n[DOCUMENTO DEL CLIENTE - JSON]:\n{client_content}\n[FIN DEL DOCUMENTO]"
        prompt_text = user_prompt_template.replace(
            "{pdf_cliente}", json_block
        )

    if form_pdf_uri:
        prompt_text = prompt_text.replace(
            "{pdf_formulario}", "[Ver Documento Adjunto: Template del Formulario]"
        )
    else:
        prompt_text = prompt_text.replace("{pdf_formulario}", "")

    # 3. Ensamblar los componentes del contenido
    if client_mime_type == "application/pdf":
        part_cliente = Part.from_data(data=client_content, mime_type="application/pdf")
        contents = [part_cliente, prompt_text]
    else:
        # Para JSON solo enviamos el prompt (el JSON ya está incrustado en el texto)
        contents = [prompt_text]

    # Agregamos el PDF del formulario solo si existe
    if form_pdf_uri:
        part_formulario = Part.from_uri(uri=form_pdf_uri, mime_type="application/pdf")
        contents.append(part_formulario)

    # 4. Ejecutar con reintentos
    resultado = _call_gemini_with_retry(model, contents)
    logger.info("¡Análisis de Gemini completado con éxito! Se obtuvo un JSON válido.")

    return resultado