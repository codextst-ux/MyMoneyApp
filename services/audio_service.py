import os
import shutil
import uuid


def transcribir(ruta):
    """Transcribe con OpenAI solo cuando el usuario configuró el entorno."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("Configura OPENAI_API_KEY para transcribir audio.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ValueError("Instala las dependencias: python3 -m pip install -r requirements.txt") from exc
    with open(ruta, "rb") as archivo:
        resultado = OpenAI().audio.transcriptions.create(
            model="gpt-4o-mini-transcribe", file=archivo
        )
    return resultado.text.strip()


def guardar_audio(ruta):
    """Conserva una copia para que la nota no dependa del archivo original."""
    carpeta = os.path.join(os.getcwd(), "audios")
    os.makedirs(carpeta, exist_ok=True)
    extension = os.path.splitext(ruta)[1].lower() or ".audio"
    destino = os.path.join(carpeta, f"nota-{uuid.uuid4().hex}{extension}")
    shutil.copy2(ruta, destino)
    return destino
