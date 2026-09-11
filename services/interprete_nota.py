"""Interpretación local y predecible de notas de movimientos en español."""
import re
import unicodedata
from datetime import date


def _normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower())
                   if unicodedata.category(c) != "Mn")


def _monto(valor):
    return valor.replace(",", ".")


def interpretar(texto):
    original = texto.strip()
    plano = _normalizar(original)
    numeros = re.findall(r"(?<![\w.])(\d+(?:[,.]\d{1,2})?)(?![\w.])", plano)
    if not numeros:
        raise ValueError("No pude encontrar el monto. Ejemplo: 'Gasté 50 en cena'.")

    if re.search(r"\b(ingrese|ingreso|recibi|cobre|cobro|sueldo|salario)\b", plano):
        tipo = "ingreso"
    elif re.search(r"\b(preste|prestamo)\b", plano):
        tipo = "prestamo"
    elif re.search(r"\b(debo|deuda)\b", plano):
        tipo = "deuda"
    else:
        tipo = "gasto"

    categorias = {
        "Alimentación": ("cena", "almuerzo", "comida", "desayuno", "restaurante", "mercado"),
        "Transporte": ("taxi", "uber", "bus", "micro", "gasolina", "pasaje"),
        "Vivienda": ("alquiler", "renta", "casa"),
        "Salud": ("medico", "farmacia", "consulta", "medicina"),
        "Educación": ("curso", "universidad", "libro", "colegio"),
        "Entretenimiento": ("cine", "fiesta", "juego", "netflix"),
        "Servicios": ("luz", "agua", "internet", "telefono"),
        "Compras": ("ropa", "compra", "tienda"),
        "Trabajo": ("trabajo", "cliente", "oficina"),
    }
    categoria = next((nombre for nombre, claves in categorias.items()
                      if any(clave in plano for clave in claves)), "Compras")
    descripcion = original
    match = re.search(r"\b(?:en|por)\s+(.+?)(?=\s*(?:,|;|\.|$)|\s+(?:mi|yo|de)\s+(?:pago|parte|es))", original, re.I)
    if match:
        descripcion = match.group(1).strip()

    partes = []
    yo = re.search(r"\b(?:mi|yo)\s+(?:pago|parte)(?:\s+es)?\s*(\d+(?:[,.]\d{1,2})?)", plano)
    if yo:
        partes.append({"nombre": "Yo", "monto": _monto(yo.group(1))})
    for nombre, monto in re.findall(r"\bde\s+([a-záéíóúñ][a-záéíóúñ ]*?)\s+(?:es|son|pago|parte)\s*(\d+(?:[,.]\d{1,2})?)", original, re.I):
        limpio = " ".join(p.capitalize() for p in nombre.strip().split())
        if limpio.lower() not in {"mi", "yo"}:
            partes.append({"nombre": limpio, "monto": _monto(monto)})

    return {
        "tipo": tipo, "descripcion": descripcion[:180], "monto": _monto(numeros[0]),
        "fecha": date.today().isoformat(), "medio_pago": "virtual", "pagado_por": "Yo",
        "categoria": categoria, "participaciones": partes,
    }
