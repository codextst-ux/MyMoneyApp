from datetime import datetime
from money import dinero


class Movimiento:

    TIPOS_VALIDOS = {
        "ingreso",
        "gasto",
        "prestamo",
        "deuda",
        "pago"
    }

    def __init__(
        self,
        tipo,
        descripcion,
        monto,
        fecha,
        persona_id=None,
        pagado_por_id=None,
        movimiento_origen_id=None,
        gasto_origen_id=None,
        categoria_id=None,
        medio_pago="virtual",
        id=None
    ):
        self.id = id
        self.tipo = tipo
        self.descripcion = descripcion
        self.monto = dinero(monto)
        self.fecha = fecha
        self.persona_id = persona_id
        self.pagado_por_id = pagado_por_id
        self.movimiento_origen_id = movimiento_origen_id
        self.gasto_origen_id = gasto_origen_id
        self.categoria_id = categoria_id
        self.medio_pago = medio_pago
        self.participaciones = []

        self.validar()

    def validar(self):
        if self.tipo not in self.TIPOS_VALIDOS:
            raise ValueError("Tipo de movimiento inválido.")

        if self.medio_pago not in {"virtual", "efectivo"}:
            raise ValueError("El medio de pago debe ser virtual o efectivo.")

        if not self.descripcion or not self.descripcion.strip():
            raise ValueError("La descripción es obligatoria.")

        if self.monto <= 0:
            raise ValueError("El monto debe ser mayor a 0.")

        if self.tipo == "pago" and not self.movimiento_origen_id:
            raise ValueError(
                "El pago debe estar asociado a un préstamo o deuda."
            )

        if self.tipo != "pago" and self.movimiento_origen_id:
            raise ValueError(
                "Solo los pagos pueden tener un movimiento de origen."
            )

        if self.gasto_origen_id and self.tipo not in {"prestamo", "deuda"}:
            raise ValueError(
                "Solo los préstamos y deudas pueden originarse en un gasto."
            )

        try:
            datetime.strptime(self.fecha, "%Y-%m-%d")
        except ValueError:
            raise ValueError(
                "La fecha debe tener el formato YYYY-MM-DD."
            )

        self.descripcion = self.descripcion.strip()
