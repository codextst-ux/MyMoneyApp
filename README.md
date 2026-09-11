# Mi App de Dinero

Ejecuta la aplicación de escritorio con:

```bash
python3 desktop.py
```

## Notas por mensaje y audio

Usa **+ Nota** para escribir un mensaje libre, adjuntar un audio o grabar diez segundos. La nota queda en **Revisar notas** y no modifica saldos hasta pulsar **Guardar** en su revisión.

Ejemplo:

```text
Gasté 50 en cena, mi pago es 15 y de Aaron es 35
```

La propuesta crea un gasto compartido con Yo (15 Bs) y Aaron (35 Bs). Aaron solo se crea al confirmar el movimiento si todavía no existe.

Para audio instala las dependencias y configura una clave de OpenAI:

```bash
python3 -m pip install -r requirements.txt
export OPENAI_API_KEY="tu_clave"
```

La transcripción usa el endpoint oficial de audio de OpenAI con `gpt-4o-mini-transcribe`. Los audios enviados se conservan en `audios/`.


