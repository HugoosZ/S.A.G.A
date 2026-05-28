import re
from typing import Dict, Any
from email.utils import parseaddr

REQUIRED_FIELDS = ['sender', 'subject', 'body', 'message_id', 'timestamp']

def validate_email_data(data: Dict[str, Any]) -> bool:
    for field in REQUIRED_FIELDS:
        if field not in data or not data[field]:
            return False
    return True


def extract_email_addresses(sender: str) -> str:
    """
    Extrae la dirección de mail del remitente
    """
    if not sender:
        return ""

    _, email = parseaddr(sender)
    return email.lower() if email else sender.lower()

def clean_subject(subject: str) -> str:
    """
    Limpia el asunto del correo eliminando caracteres especiales y los prefijos.
    """
    subject = subject.strip()
    # Elimina prefijos comunes
    subject = re.sub(r'^(Re|re|Fw|Aw):\s*', '', subject)
    subject = re.sub(r'[^\w\s]', '', subject)  # Elimina caracteres especiales
    return subject.lower()

def clean_body(body: str) -> str:
    """
    Limpia el cuerpo del correo eliminando espacios en blanco y caracteres especiales.
    """
    body = body.strip()
    body = re.sub(r'\s+', ' ', body)  # Reemplaza múltiples espacios por uno solo
    return body

def normalizar_email_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza los datos del correo 
    """
    data['sender'] = extract_email_addresses(data['sender'])
    data['subject'] = clean_subject(data['subject'])
    data['body'] = clean_body(data['body'])
    return data

def asignar_hilo(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Asigna un hilo al correo basandose en el asunto y el remitente
    """
    in_reply_to = data.get('in_reply_to')

    if in_reply_to:
        return{
            **data,
            'hilo_id': in_reply_to,
            "is_reply": True
        }

    return {
        **data,
        'hilo_id': data['message_id'],
        "is_reply": False
    }

def is_valid_email_content(data: dict) -> bool:
    subject = data.get("subject", "").lower()
    body = data.get("body", "").lower()

    spam_keywords = [
        "unsubscribe",
          "suscripción",
         "newsletter",
         "oferta",
         "promoción",
         "click aquí",
          "haz clic",
           "privacy",
          "terms",
        ]

    # descarta si contiene palabras típicas de spam
    if any(word in subject for word in spam_keywords):
        return False

    if any(word in body for word in spam_keywords):
           return False

    return True