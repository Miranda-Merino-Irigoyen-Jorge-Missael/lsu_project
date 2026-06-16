import logging
from googleapiclient.discovery import build
from src.services.auth_service import get_credentials
from src.config.settings import SPREADSHEET_ID, SHEET_NAME

logger = logging.getLogger(__name__)

def obtener_casos_pendientes() -> list:
    """
    Lee la hoja de cálculo y devuelve una lista de diccionarios con los casos 
    cuyo 'STATUS REPORTE' (Columna G) es 'PENDING'.
    """
    logger.info("Conectando con Google Sheets para buscar casos pendientes...")
    try:
        creds = get_credentials()
        service = build('sheets', 'v4', credentials=creds)
        
        # Leemos el rango A:H. Asumimos que la fila 1 contiene los encabezados.
        rango = f"{SHEET_NAME}!A:H"
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=rango).execute()
        values = result.get('values', [])
        
        casos_pendientes = []
        
        if not values:
            logger.warning("No se encontraron datos en la hoja de cálculo.")
            return casos_pendientes

        # Iteramos saltando la fila 1 (encabezados). start=2 alinea el índice con la fila real en Sheets.
        for index, row in enumerate(values[1:], start=2):
            # Verificamos que la fila tenga al menos datos hasta la columna G (índice 6)
            if len(row) > 6:
                status = str(row[6]).strip().upper()
                if status == 'PENDING':
                    # Extraemos datos basándonos en los índices de columna (A=0, B=1, C=2... F=5)
                    caso = {
                        "fila_excel": index,
                        "id_cliente": row[0].strip() if len(row) > 0 else "SIN_ID",
                        "nombre_cliente": row[1].strip() if len(row) > 1 else "SIN_NOMBRE",
                        "tipo_visa": row[2].strip() if len(row) > 2 else "",
                        "pdf_link": row[5].strip() if len(row) > 5 else ""
                    }
                    casos_pendientes.append(caso)
                    
        logger.info(f"Se encontraron {len(casos_pendientes)} casos en estatus PENDING.")
        return casos_pendientes

    except Exception as e:
        logger.error(f"Error al leer la Google Sheet: {e}")
        raise e

def actualizar_status_y_link(fila_excel: int, nuevo_status: str, link_reporte: str = ""):
    """
    Actualiza el 'STATUS REPORTE' (Columna G) y el Link del Reporte (Columna H) 
    para una fila específica en la hoja de cálculo.
    """
    try:
        creds = get_credentials()
        service = build('sheets', 'v4', credentials=creds)
        
        # El rango G:H para la fila específica
        rango = f"{SHEET_NAME}!G{fila_excel}:H{fila_excel}"
        
        body = {
            'values': [
                [nuevo_status, link_reporte]
            ]
        }
        
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, 
            range=rango,
            valueInputOption="USER_ENTERED", 
            body=body
        ).execute()
        
        logger.info(f"Fila {fila_excel} de Sheets actualizada -> Estatus: {nuevo_status}")
        
    except Exception as e:
        logger.error(f"Error al actualizar la fila {fila_excel} en Sheets: {e}")
        raise e