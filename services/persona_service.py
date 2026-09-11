from database.database import conectar
from models.persona import Persona


class PersonaService:

    def crear(self, persona):
        persona.validar()

        conexion = conectar()

        try:
            cursor = conexion.execute("""
                INSERT INTO personas (nombre)
                VALUES (?)
            """, (persona.nombre,))

            conexion.commit()

            persona.id = cursor.lastrowid

            return persona

        except Exception:
            conexion.rollback()
            raise

        finally:
            conexion.close()

    def obtener_todas(self):
        conexion = conectar()

        filas = conexion.execute("""
            SELECT id, nombre
            FROM personas
            ORDER BY id
        """).fetchall()

        conexion.close()

        return [
            Persona(
                id=fila[0],
                nombre=fila[1]
            )
            for fila in filas
        ]

    def obtener_por_id(self, persona_id):
        conexion = conectar()

        fila = conexion.execute("""
            SELECT id, nombre
            FROM personas
            WHERE id = ?
        """, (persona_id,)).fetchone()

        conexion.close()

        if fila is None:
            return None

        return Persona(
            id=fila[0],
            nombre=fila[1]
        )

    def buscar_por_nombre(self, nombre):
        conexion = conectar()

        filas = conexion.execute("""
            SELECT id, nombre
            FROM personas
            WHERE nombre LIKE ?
            ORDER BY nombre
        """, (f"%{nombre}%",)).fetchall()

        conexion.close()

        return [
            Persona(
                id=fila[0],
                nombre=fila[1]
            )
            for fila in filas
        ]

    def actualizar(self, persona):
        persona.validar()

        conexion = conectar()

        try:
            conexion.execute("""
                UPDATE personas
                SET nombre = ?
                WHERE id = ?
            """, (
                persona.nombre,
                persona.id
            ))

            conexion.commit()

        except Exception:
            conexion.rollback()
            raise

        finally:
            conexion.close()

    def eliminar(self, persona_id):
        conexion = conectar()

        try:
            cursor = conexion.execute("""
                DELETE FROM personas
                WHERE id = ?
            """, (persona_id,))

            conexion.commit()

            return cursor.rowcount > 0

        except Exception:
            conexion.rollback()
            raise

        finally:
            conexion.close()