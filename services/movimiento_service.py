from database.database import conectar
from money import dinero, sumar
from models.movimiento import Movimiento


class MovimientoService:

    def crear(self, movimiento):
        movimiento.validar()
        self._validar_relaciones(movimiento)

        self._validar_participaciones(movimiento)

        conexion = conectar()

        try:
            self._validar_pago(conexion, movimiento)

            cursor = conexion.execute("""
                INSERT INTO movimientos (
                    tipo,
                    descripcion,
                    monto,
                    fecha,
                    persona_id,
                    pagado_por_id,
                    movimiento_origen_id,
                    gasto_origen_id,
                    categoria_id,
                    medio_pago
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                movimiento.tipo,
                movimiento.descripcion,
                movimiento.monto,
                movimiento.fecha,
                movimiento.persona_id,
                movimiento.pagado_por_id,
                movimiento.movimiento_origen_id,
                movimiento.gasto_origen_id,
                movimiento.categoria_id,
                movimiento.medio_pago
            ))

            movimiento.id = cursor.lastrowid

            for participacion in movimiento.participaciones:
                conexion.execute("""
                    INSERT INTO participaciones (
                        movimiento_id,
                        persona_id,
                        monto
                    )
                    VALUES (?, ?, ?)
                """, (
                    movimiento.id,
                    participacion["persona_id"],
                    participacion["monto"]
                ))

            self._crear_obligaciones_de_gasto(conexion, movimiento)

            conexion.commit()

            return movimiento

        except Exception:
            conexion.rollback()
            raise

        finally:
            conexion.close()

    def obtener_todos(self):
        return self.obtener_filtrados()

    def obtener_filtrados(
        self, categoria_id=None, fecha_desde=None, fecha_hasta=None,
        persona_id=None, tipo=None
    ):
        conexion = conectar()

        consulta = """
            SELECT
                id,
                tipo,
                descripcion,
                monto,
                fecha,
                persona_id,
                pagado_por_id,
                movimiento_origen_id,
                gasto_origen_id,
                categoria_id,
                medio_pago
            FROM movimientos
        """
        condiciones = []
        parametros = []

        if categoria_id is not None:
            condiciones.append("categoria_id = ?")
            parametros.append(categoria_id)

        if fecha_desde:
            condiciones.append("fecha >= ?")
            parametros.append(fecha_desde)

        if fecha_hasta:
            condiciones.append("fecha <= ?")
            parametros.append(fecha_hasta)

        if persona_id is not None:
            condiciones.append("""(
                persona_id = ? OR pagado_por_id = ?
                OR id IN (
                    SELECT movimiento_id FROM participaciones WHERE persona_id = ?
                )
            )""")
            parametros.extend([persona_id, persona_id, persona_id])

        if tipo is not None:
            condiciones.append("tipo = ?")
            parametros.append(tipo)

        if condiciones:
            consulta += " WHERE " + " AND ".join(condiciones)

        consulta += " ORDER BY fecha DESC, id DESC"
        filas = conexion.execute(consulta, parametros).fetchall()

        movimientos = []

        for fila in filas:
            movimiento = Movimiento(
                id=fila[0],
                tipo=fila[1],
                descripcion=fila[2],
                monto=fila[3],
                fecha=fila[4],
                persona_id=fila[5],
                pagado_por_id=fila[6],
                movimiento_origen_id=fila[7],
                gasto_origen_id=fila[8],
                categoria_id=fila[9],
                medio_pago=fila[10]
            )

            movimiento.participaciones = self._obtener_participaciones(
                conexion,
                movimiento.id
            )

            movimientos.append(movimiento)

        conexion.close()

        return movimientos

    def obtener_saldos_por_persona(self, persona_id=None):
        conexion = conectar()

        consulta = """
            SELECT
                persona.id,
                persona.nombre,
                movimiento.tipo,
                movimiento.monto - COALESCE(SUM(pago.monto), 0) AS saldo
            FROM movimientos AS movimiento
            INNER JOIN personas AS persona
                ON persona.id = movimiento.persona_id
            LEFT JOIN movimientos AS pago
                ON pago.movimiento_origen_id = movimiento.id
                AND pago.tipo = 'pago'
            WHERE movimiento.tipo IN ('prestamo', 'deuda')
                AND persona.nombre != 'Yo'
        """
        parametros = []

        if persona_id is not None:
            consulta += " AND persona.id = ?"
            parametros.append(persona_id)

        consulta += """
            GROUP BY movimiento.id
            HAVING saldo > 0.004
            ORDER BY persona.nombre
        """
        filas = conexion.execute(consulta, parametros).fetchall()

        conexion.close()

        saldos = {}

        for persona_id, nombre, tipo, saldo in filas:
            if persona_id not in saldos:
                saldos[persona_id] = {
                    "nombre": nombre,
                    "a_favor": dinero(0),
                    "debo": dinero(0)
                }

            if tipo == "prestamo":
                saldos[persona_id]["a_favor"] += dinero(saldo)
            else:
                saldos[persona_id]["debo"] += dinero(saldo)

        return list(saldos.values())

    def obtener_resumen_financiero(self):
        movimientos = self.obtener_todos()
        movimientos_por_id = {
            movimiento.id: movimiento
            for movimiento in movimientos
        }
        resumen = {
            "ingresos": dinero(0),
            "gastos": dinero(0),
            "prestamos_otorgados": dinero(0),
            "dinero_recibido_prestado": dinero(0),
            "cobros_recibidos": dinero(0),
            "pagos_realizados": dinero(0)
        }

        for movimiento in movimientos:
            if movimiento.tipo == "ingreso":
                resumen["ingresos"] += movimiento.monto

            elif movimiento.tipo == "gasto":
                resumen["gastos"] += movimiento.monto

            elif (
                movimiento.tipo == "prestamo"
                and not movimiento.gasto_origen_id
            ):
                resumen["prestamos_otorgados"] += movimiento.monto

            elif (
                movimiento.tipo == "deuda"
                and not movimiento.gasto_origen_id
            ):
                resumen["dinero_recibido_prestado"] += movimiento.monto

            elif movimiento.tipo == "pago":
                origen = movimientos_por_id.get(
                    movimiento.movimiento_origen_id
                )

                if origen and origen.tipo == "prestamo":
                    resumen["cobros_recibidos"] += movimiento.monto
                elif origen and origen.tipo == "deuda":
                    resumen["pagos_realizados"] += movimiento.monto

        resumen["disponible"] = (
            resumen["ingresos"]
            - resumen["gastos"]
            - resumen["prestamos_otorgados"]
            + resumen["dinero_recibido_prestado"]
            + resumen["cobros_recibidos"]
            - resumen["pagos_realizados"]
        )

        resumen["virtual"] = dinero(0)
        resumen["efectivo"] = dinero(0)
        for movimiento in movimientos:
            flujo = dinero(0)
            if movimiento.tipo == "ingreso":
                flujo = movimiento.monto
            elif movimiento.tipo == "gasto":
                flujo = -movimiento.monto
            elif movimiento.tipo == "prestamo" and not movimiento.gasto_origen_id:
                flujo = -movimiento.monto
            elif movimiento.tipo == "deuda" and not movimiento.gasto_origen_id:
                flujo = movimiento.monto
            elif movimiento.tipo == "pago":
                origen = movimientos_por_id.get(movimiento.movimiento_origen_id)
                if origen and origen.tipo == "prestamo":
                    flujo = movimiento.monto
                elif origen and origen.tipo == "deuda":
                    flujo = -movimiento.monto
            resumen[movimiento.medio_pago] += flujo

        saldos = self.obtener_saldos_por_persona()
        resumen["por_cobrar"] = sumar(
            saldo["a_favor"]
            for saldo in saldos
        )
        resumen["por_pagar"] = sumar(
            saldo["debo"]
            for saldo in saldos
        )
        resumen["balance_general"] = (
            resumen["disponible"]
            + resumen["por_cobrar"]
            - resumen["por_pagar"]
        )

        return resumen

    def obtener_por_id(self, movimiento_id):
        conexion = conectar()

        fila = conexion.execute("""
            SELECT
                id,
                tipo,
                descripcion,
                monto,
                fecha,
                persona_id,
                pagado_por_id,
                movimiento_origen_id,
                gasto_origen_id,
                categoria_id,
                medio_pago
            FROM movimientos
            WHERE id = ?
        """, (movimiento_id,)).fetchone()

        if fila is None:
            conexion.close()
            return None

        movimiento = Movimiento(
            id=fila[0],
            tipo=fila[1],
            descripcion=fila[2],
            monto=fila[3],
            fecha=fila[4],
            persona_id=fila[5],
            pagado_por_id=fila[6],
            movimiento_origen_id=fila[7],
            gasto_origen_id=fila[8],
            categoria_id=fila[9],
            medio_pago=fila[10]
        )

        movimiento.participaciones = self._obtener_participaciones(
            conexion,
            movimiento.id
        )

        conexion.close()

        return movimiento

    def actualizar(self, movimiento):
        movimiento.validar()
        self._validar_relaciones(movimiento)

        self._validar_participaciones(movimiento)

        conexion = conectar()

        try:
            self._validar_pago(conexion, movimiento, excluir_id=movimiento.id)
            self._validar_actualizacion(conexion, movimiento)

            conexion.execute("""
                UPDATE movimientos
                SET
                    tipo = ?,
                    descripcion = ?,
                    monto = ?,
                    fecha = ?,
                    persona_id = ?,
                    pagado_por_id = ?,
                    movimiento_origen_id = ?,
                    gasto_origen_id = ?,
                    categoria_id = ?,
                    medio_pago = ?
                WHERE id = ?
            """, (
                movimiento.tipo,
                movimiento.descripcion,
                movimiento.monto,
                movimiento.fecha,
                movimiento.persona_id,
                movimiento.pagado_por_id,
                movimiento.movimiento_origen_id,
                movimiento.gasto_origen_id,
                movimiento.categoria_id,
                movimiento.medio_pago,
                movimiento.id
            ))

            conexion.execute("""
                DELETE FROM participaciones
                WHERE movimiento_id = ?
            """, (movimiento.id,))

            for participacion in movimiento.participaciones:
                conexion.execute("""
                    INSERT INTO participaciones (
                        movimiento_id,
                        persona_id,
                        monto
                    )
                    VALUES (?, ?, ?)
                """, (
                    movimiento.id,
                    participacion["persona_id"],
                    participacion["monto"]
                ))

            if movimiento.tipo == "gasto":
                self._recrear_obligaciones_de_gasto(conexion, movimiento)

            conexion.commit()

        except Exception:
            conexion.rollback()
            raise

        finally:
            conexion.close()

    def obtener_pendientes_para_pago(self):
        conexion = conectar()

        filas = conexion.execute("""
            SELECT
                movimiento.id,
                movimiento.tipo,
                movimiento.descripcion,
                movimiento.monto,
                movimiento.fecha,
                movimiento.persona_id,
                movimiento.pagado_por_id,
                movimiento.gasto_origen_id,
                movimiento.monto - COALESCE(SUM(pago.monto), 0) AS saldo
            FROM movimientos AS movimiento
            LEFT JOIN movimientos AS pago
                ON pago.movimiento_origen_id = movimiento.id
                AND pago.tipo = 'pago'
            WHERE movimiento.tipo IN ('prestamo', 'deuda')
            GROUP BY movimiento.id
            HAVING saldo > 0.004
            ORDER BY movimiento.fecha, movimiento.id
        """).fetchall()

        conexion.close()

        return [
            (
                Movimiento(
                    id=fila[0], tipo=fila[1], descripcion=fila[2],
                    monto=fila[3], fecha=fila[4], persona_id=fila[5],
                    pagado_por_id=fila[6], gasto_origen_id=fila[7]
                ),
                dinero(fila[8])
            )
            for fila in filas
        ]

    def obtener_estado(self, movimiento):
        if movimiento.tipo not in {"prestamo", "deuda"}:
            return "completado", 0

        conexion = conectar()

        pagado = conexion.execute("""
            SELECT COALESCE(SUM(monto), 0)
            FROM movimientos
            WHERE tipo = 'pago' AND movimiento_origen_id = ?
        """, (movimiento.id,)).fetchone()[0]

        conexion.close()

        saldo = dinero(movimiento.monto - dinero(pagado))

        if saldo <= 0:
            return "completado", 0

        return "pendiente", saldo

    def eliminar(self, movimiento_id):
        conexion = conectar()

        try:
            movimiento = conexion.execute("""
                SELECT tipo, gasto_origen_id
                FROM movimientos
                WHERE id = ?
            """, (movimiento_id,)).fetchone()

            if movimiento is None:
                return False

            if movimiento[1]:
                raise ValueError(
                    "Este movimiento nació de un gasto compartido. "
                    "Edita o elimina el gasto original."
                )

            if movimiento[0] == "gasto":
                self._eliminar_obligaciones_de_gasto(conexion, movimiento_id)
            elif movimiento[0] in {"prestamo", "deuda"}:
                self._validar_sin_pagos(conexion, movimiento_id)

            cursor = conexion.execute("""
                DELETE FROM movimientos
                WHERE id = ?
            """, (movimiento_id,))

            conexion.commit()

            return cursor.rowcount > 0

        except Exception:
            conexion.rollback()
            raise

        finally:
            conexion.close()

    def _obtener_participaciones(self, conexion, movimiento_id):
        filas = conexion.execute("""
            SELECT persona_id, monto
            FROM participaciones
            WHERE movimiento_id = ?
            ORDER BY id
        """, (movimiento_id,)).fetchall()

        return [
            {
                "persona_id": fila[0],
                "monto": dinero(fila[1])
            }
            for fila in filas
        ]

    def _validar_participaciones(self, movimiento):
        if movimiento.tipo != "gasto":
            if movimiento.participaciones:
                raise ValueError(
                    "Solo los gastos pueden tener participaciones."
                )

            return

        if not movimiento.participaciones:
            return

        total = sumar(
            participacion["monto"]
            for participacion in movimiento.participaciones
        )

        if total != movimiento.monto:
            raise ValueError(
                f"Las participaciones ({total}) "
                f"deben sumar el total del gasto "
                f"({movimiento.monto})."
            )

        personas = [
            participacion["persona_id"]
            for participacion in movimiento.participaciones
        ]

        if len(personas) != len(set(personas)):
            raise ValueError(
                "Una persona no puede aparecer dos veces "
                "en el mismo gasto."
            )

        for participacion in movimiento.participaciones:
            if participacion["monto"] <= 0:
                raise ValueError(
                    "El monto de una participación debe ser mayor a 0."
                )

    def _validar_relaciones(self, movimiento):
        if movimiento.tipo == "ingreso" and (not movimiento.persona_id or not movimiento.categoria_id):
            raise ValueError("El ingreso requiere una persona y una categoría.")
        if movimiento.tipo == "gasto" and (not movimiento.pagado_por_id or not movimiento.categoria_id):
            raise ValueError("El gasto requiere quién pagó y una categoría.")
        if movimiento.tipo in {"prestamo", "deuda"} and not movimiento.persona_id:
            raise ValueError("El préstamo o deuda requiere una persona.")
        if movimiento.tipo == "pago" and not movimiento.persona_id:
            raise ValueError("El pago requiere una persona asociada.")

    def _validar_pago(self, conexion, movimiento, excluir_id=None):
        if movimiento.tipo != "pago":
            return

        origen = conexion.execute("""
            SELECT id, tipo, monto
            FROM movimientos
            WHERE id = ?
        """, (movimiento.movimiento_origen_id,)).fetchone()

        if origen is None or origen[1] not in {"prestamo", "deuda"}:
            raise ValueError(
                "El movimiento de origen debe ser un préstamo o una deuda."
            )

        consulta = """
            SELECT COALESCE(SUM(monto), 0)
            FROM movimientos
            WHERE tipo = 'pago' AND movimiento_origen_id = ?
        """
        parametros = [origen[0]]

        if excluir_id is not None:
            consulta += " AND id != ?"
            parametros.append(excluir_id)

        pagado = conexion.execute(consulta, parametros).fetchone()[0]

        pagado = dinero(pagado)
        origen_monto = dinero(origen[2])
        if pagado + movimiento.monto > origen_monto:
            raise ValueError(
                f"El pago supera el saldo pendiente ({origen_monto - pagado:.2f} Bs)."
            )

    def _validar_actualizacion(self, conexion, movimiento):
        actual = conexion.execute("""
            SELECT tipo, gasto_origen_id
            FROM movimientos
            WHERE id = ?
        """, (movimiento.id,)).fetchone()

        if actual is None:
            raise ValueError("Movimiento no encontrado.")

        if actual[1]:
            raise ValueError(
                "Los movimientos creados por un gasto compartido "
                "se editan desde el gasto original."
            )

        if actual[0] != movimiento.tipo:
            raise ValueError("No se puede cambiar el tipo de movimiento.")

        if movimiento.tipo in {"prestamo", "deuda"}:
            pagado = self._obtener_total_pagado(conexion, movimiento.id)

            if movimiento.monto < dinero(pagado):
                raise ValueError(
                    f"El monto no puede ser menor a lo ya pagado "
                    f"({dinero(pagado):.2f} Bs)."
                )

        if movimiento.tipo == "gasto":
            self._validar_obligaciones_sin_pagos(conexion, movimiento.id)

    def _obtener_total_pagado(self, conexion, movimiento_id):
        return conexion.execute("""
            SELECT COALESCE(SUM(monto), 0)
            FROM movimientos
            WHERE tipo = 'pago' AND movimiento_origen_id = ?
        """, (movimiento_id,)).fetchone()[0]

    def _validar_sin_pagos(self, conexion, movimiento_id):
        pagado = self._obtener_total_pagado(conexion, movimiento_id)

        if dinero(pagado) > 0:
            raise ValueError(
                "No se puede eliminar un préstamo o deuda que tiene pagos."
            )

    def _validar_obligaciones_sin_pagos(self, conexion, gasto_id):
        fila = conexion.execute("""
            SELECT 1
            FROM movimientos AS obligacion
            INNER JOIN movimientos AS pago
                ON pago.movimiento_origen_id = obligacion.id
                AND pago.tipo = 'pago'
            WHERE obligacion.gasto_origen_id = ?
            LIMIT 1
        """, (gasto_id,)).fetchone()

        if fila:
            raise ValueError(
                "No se puede modificar este gasto compartido porque "
                "una obligación ya tiene pagos."
            )

    def _eliminar_obligaciones_de_gasto(self, conexion, gasto_id):
        self._validar_obligaciones_sin_pagos(conexion, gasto_id)

        conexion.execute("""
            DELETE FROM movimientos
            WHERE gasto_origen_id = ?
        """, (gasto_id,))

    def _recrear_obligaciones_de_gasto(self, conexion, gasto):
        self._eliminar_obligaciones_de_gasto(conexion, gasto.id)
        self._crear_obligaciones_de_gasto(conexion, gasto)

    def _crear_obligaciones_de_gasto(self, conexion, gasto):
        if gasto.tipo != "gasto" or not gasto.participaciones:
            return

        yo = conexion.execute("""
            SELECT id FROM personas WHERE nombre = 'Yo'
        """).fetchone()

        if yo is None:
            raise ValueError("No se encontró la persona 'Yo'.")

        yo_id = yo[0]
        descripcion = f"Parte de gasto compartido: {gasto.descripcion}"

        if gasto.pagado_por_id == yo_id:
            for participacion in gasto.participaciones:
                if participacion["persona_id"] == yo_id:
                    continue

                self._insertar_obligacion(
                    conexion, "prestamo", descripcion,
                    participacion["monto"], gasto.fecha,
                    participacion["persona_id"], gasto.id
                )
            return

        parte_de_yo = next(
            (
                participacion["monto"]
                for participacion in gasto.participaciones
                if participacion["persona_id"] == yo_id
            ),
            None
        )

        if parte_de_yo:
            self._insertar_obligacion(
                conexion, "deuda", descripcion, parte_de_yo,
                gasto.fecha, gasto.pagado_por_id, gasto.id
            )

    def _insertar_obligacion(
        self, conexion, tipo, descripcion, monto, fecha,
        persona_id, gasto_origen_id
    ):
        conexion.execute("""
            INSERT INTO movimientos (
                tipo, descripcion, monto, fecha, persona_id, gasto_origen_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            tipo, descripcion, monto, fecha, persona_id, gasto_origen_id
        ))
