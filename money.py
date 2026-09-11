from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


CENTAVO = Decimal("0.01")


def dinero(valor):
    """Normaliza cualquier importe a dos decimales sin usar float en cálculos."""
    try:
        return Decimal(str(valor)).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Ingresa un monto válido.")


def sumar(valores):
    return sum((dinero(valor) for valor in valores), Decimal("0.00"))
