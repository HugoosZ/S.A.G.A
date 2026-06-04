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
    subject = re.sub(r'^(Re|re|Fw|Aw):\s*', '', subject, flags=re.IGNORECASE)
    return subject.lower()

def clean_body(body: str) -> str:
    """
    Limpia el cuerpo del correo eliminando espacios en blanco y caracteres especiales.
    """
    body = body.strip()
    body = re.sub(r'http\S+', '', body)  # Elimina URLs
    body = re.sub(r'\[[^\]]*\]', '', body)  # Elimina texto entre corchetes
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

def asignar_hilo(data: dict) -> dict:
    references = data.get("references")
    in_reply_to = data.get("in_reply_to")

    if references:
        refs = references.strip().split()
        hilo_id = refs[0]

        return {
            **data,
            "hilo_id": hilo_id,
            "is_reply": True
        }

    if in_reply_to:
        return {
            **data,
            "hilo_id": in_reply_to,
            "is_reply": True
        }

    return {
        **data,
        "hilo_id": data["message_id"],
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

def clean_reply_history(body: str) -> str:
    import re

    if not body:
        return ""

    # cortar en patrones típicos de respuesta
    patterns = [
        r"On .* wrote:",
        r"El .* escribió:",
        r"From: .*",
        r"De: .*"
    ]

    for pattern in patterns:
        parts = re.split(pattern, body, maxsplit=1)
        if len(parts) > 1:
            body = parts[0]

    return body.strip()