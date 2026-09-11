from database.database import conectar
from models.categoria import Categoria


class CategoriaService:

    def obtener_todas(self):
        conexion = conectar()
        filas = conexion.execute("""
            SELECT id, nombre FROM categorias ORDER BY id
        """).fetchall()
        conexion.close()

        return [Categoria(id=fila[0], nombre=fila[1]) for fila in filas]

    def obtener_por_id(self, categoria_id):
        conexion = conectar()
        fila = conexion.execute("""
            SELECT id, nombre FROM categorias WHERE id = ?
        """, (categoria_id,)).fetchone()
        conexion.close()

        return Categoria(id=fila[0], nombre=fila[1]) if fila else None

    def obtener_por_nombre(self, nombre):
        conexion = conectar()
        fila = conexion.execute("""
            SELECT id, nombre FROM categorias WHERE lower(nombre) = lower(?)
        """, (nombre.strip(),)).fetchone()
        conexion.close()

        return Categoria(id=fila[0], nombre=fila[1]) if fila else None

    def crear(self, categoria):
        conexion = conectar()

        try:
            cursor = conexion.execute("""
                INSERT INTO categorias (nombre) VALUES (?)
            """, (categoria.nombre,))
            conexion.commit()
            categoria.id = cursor.lastrowid
            return categoria
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.close()
