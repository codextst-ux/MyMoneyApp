"""Interpretación local y predecible de notas de movimientos en español."""
import re
import unicodedata
from datetime import date


def _normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower())
                   if unicodedata.category(c) != "Mn")


def _monto(valor):
    return valor.replace(",", ".")


def interpretar(texto, categorias=None, personas=None):
    original = texto.strip()
    plano = _normalizar(original)
    numeros = re.findall(r"(?<![\w.])(\d+(?:[,.]\d{1,2})?)(?![\w.])", plano)
    if not numeros:
        raise ValueError("No pude encontrar el monto. Ejemplo: 'Gasté 50 en cena'.")

    # Cargar categorías y personas desde la base de datos si no se pasaron explícitamente
    if categorias is None:
        try:
            from services.categoria_service import CategoriaService
            categorias = [c.nombre for c in CategoriaService().obtener_todas()]
        except Exception:
            categorias = []

    if personas is None:
        try:
            from services.persona_service import PersonaService
            personas = [p.nombre for p in PersonaService().obtener_todas()]
        except Exception:
            personas = []

    # 1. Detección de tipo
    # Deuda (alguien me prestó o yo le debo a alguien)
    if re.search(r"\b(me\s+presto|me\s+prestaron|pedi\s+prestado|pedi\s+un\s+prestamo|quede\s+debiendo|le\s+debo\s+a|debo\s+a|deuda\s+con|deuda\s+a)\b", plano):
        tipo = "deuda"
    # Préstamo (yo presté, o le di dinero a alguien que debe devolverlo)
    elif re.search(r"\b(le\s+preste|le\s+di|le\s+transferi|le\s+pase|preste\s+a|prestamo\s+a|preste|prestamo)\b", plano):
        tipo = "prestamo"
    # Ingreso
    elif re.search(r"\b(ingrese|ingreso|recibi|cobre|cobro|sueldo|salario|me\s+pagaron|me\s+pago|deposito\s+recibido|ganancia|gane)\b", plano):
        tipo = "ingreso"
    elif re.search(r"\b(debo|deuda)\b", plano):
        tipo = "deuda"
    else:
        tipo = "gasto"

    # 2. Detección de persona
    persona_detectada = None
    for p_nom in personas:
        if p_nom.lower() != "yo" and re.search(r"\b" + re.escape(_normalizar(p_nom)) + r"\b", plano):
            persona_detectada = p_nom
            break

    if not persona_detectada:
        palabras_descartables = {
            "yo", "mi", "un", "una", "el", "la", "los", "las", "mis",
            "cena", "almuerzo", "desayuno", "taxi", "comida", "mercado",
            "casa", "ropa", "luz", "agua", "gas", "internet", "trabajo", "hoy", "ayer"
        }
        # Buscar al inicio: "Carlos me prestó...", "Juan me dio...", "Pedro pagó..."
        match_ini = re.search(r"^([a-záéíóúñ]+)\s+(?:me\s+|nos\s+|pago\b|presto\b|dio\b)", plano, re.I)
        if match_ini:
            posible = original.split()[0].capitalize()
            if posible.lower() not in palabras_descartables:
                persona_detectada = posible

        if not persona_detectada:
            match_p = re.search(r"\b(?:a|para|con|de)\s+([a-záéíóúñ]+)\b", original, re.I)
            if match_p:
                posible = match_p.group(1).capitalize()
                if posible.lower() not in palabras_descartables:
                    persona_detectada = posible


    # 3. Detección de categoría
    categoria_detectada = None
    for c_nom in categorias:
        if re.search(r"\b" + re.escape(_normalizar(c_nom)) + r"\b", plano):
            categoria_detectada = c_nom
            break

    if not categoria_detectada:
        familias = {
            "Alimentación": ("cena", "almuerzo", "comida", "desayuno", "restaurante", "mercado", "pizza", "hamburguesa", "cafe"),
            "Transporte": ("taxi", "uber", "bus", "micro", "gasolina", "pasaje", "pasajes"),
            "Vivienda": ("alquiler", "renta", "casa", "departamento", "cuarto"),
            "Salud": ("medico", "farmacia", "consulta", "medicina", "pastillas", "hospital", "dentista"),
            "Educación": ("curso", "universidad", "libro", "colegio", "fotocopias"),
            "Entretenimiento": ("cine", "fiesta", "juego", "netflix", "salida", "bar", "cerveza"),
            "Servicios": ("luz", "agua", "internet", "telefono", "gas", "wifi"),
            "Compras": ("ropa", "compra", "tienda", "zapatos", "supermercado"),
        }
        for nombre_familia, claves in familias.items():
            if any(re.search(r"\b" + re.escape(clave) + r"\b", plano) for clave in claves):
                coincide = next((c for c in categorias if _normalizar(c) == _normalizar(nombre_familia)), None)
                if coincide:
                    categoria_detectada = coincide
                    break

    if not categoria_detectada:
        categoria_detectada = categorias[0] if categorias else "Compras"

    # 4. Extracción de descripción limpia
    descripcion = original
    match_desc = re.search(r"\b(?:en|por)\s+(.+?)(?=\s*(?:,|;|\.|$)|\s+(?:mi|yo|de)\s+(?:pago|parte|es))", original, re.I)
    if match_desc:
        descripcion = match_desc.group(1).strip()
    elif tipo in {"prestamo", "deuda"} and persona_detectada:
        descripcion = f"{tipo.title()} a {persona_detectada}" if tipo == "prestamo" else f"Deuda con {persona_detectada}"

    # 5. Participaciones de gastos compartidos
    partes = []
    yo = re.search(r"\b(?:mi|yo)\s+(?:pago|parte)(?:\s+es)?\s*(\d+(?:[,.]\d{1,2})?)", plano)
    if yo:
        partes.append({"nombre": "Yo", "monto": _monto(yo.group(1))})
    for nombre, monto in re.findall(r"\bde\s+([a-záéíóúñ][a-záéíóúñ ]*?)\s+(?:es|son|pago|parte)\s*(\d+(?:[,.]\d{1,2})?)", original, re.I):
        limpio = " ".join(p.capitalize() for p in nombre.strip().split())
        if limpio.lower() not in {"mi", "yo"}:
            partes.append({"nombre": limpio, "monto": _monto(monto)})

    return {
        "tipo": tipo,
        "descripcion": descripcion[:180],
        "monto": _monto(numeros[0]),
        "fecha": date.today().isoformat(),
        "medio_pago": "virtual",
        "pagado_por": persona_detectada or "Yo",
        "persona": persona_detectada or "Yo",
        "categoria": categoria_detectada,
        "participaciones": partes,
    }

