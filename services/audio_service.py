import os
import shutil
import uuid


def transcribir(ruta):
    """Transcribe usando la librería gratuita y multiplataforma SpeechRecognition."""
    try:
        import speech_recognition as sr
    except ImportError as exc:
        raise ValueError("Instala las dependencias: pip install -r requirements.txt") from exc

    import tempfile
    import soundfile as sf

    archivo_a_usar = ruta
    temp_wav = None

    # Si no es un WAV estándar, convertirlo a WAV temporal usando soundfile
    if not ruta.lower().endswith(".wav"):
        try:
            data, samplerate = sf.read(ruta)
            descriptor, temp_wav = tempfile.mkstemp(suffix=".wav")
            os.close(descriptor)
            sf.write(temp_wav, data, samplerate)
            archivo_a_usar = temp_wav
        except Exception:
            archivo_a_usar = ruta

    try:
        r = sr.Recognizer()
        with sr.AudioFile(archivo_a_usar) as fuente:
            audio = r.record(fuente)

        texto = r.recognize_google(audio, language="es-ES")
        return texto.strip()
    except sr.UnknownValueError:
        raise ValueError("No se pudo entender el audio. Intenta hablar más claro o cerca del micrófono.")
    except sr.RequestError as exc:
        raise ValueError(f"No se pudo conectar al servicio de reconocimiento de voz: {exc}")
    finally:
        if temp_wav and os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except OSError:
                pass



def guardar_audio(ruta):
    """Conserva una copia para que la nota no dependa del archivo original."""
    carpeta = os.path.join(os.getcwd(), "audios")
    os.makedirs(carpeta, exist_ok=True)
    extension = os.path.splitext(ruta)[1].lower() or ".audio"
    destino = os.path.join(carpeta, f"nota-{uuid.uuid4().hex}{extension}")
    shutil.copy2(ruta, destino)
    return destino
