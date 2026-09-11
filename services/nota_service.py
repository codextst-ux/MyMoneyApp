import json

from database.database import conectar


class NotaService:
    """Persistencia de notas que aún no son movimientos financieros."""

    def crear(self, texto_original, datos, transcripcion=None, audio_path=None):
        if not texto_original or not texto_original.strip():
            raise ValueError("Escribe una nota o selecciona un audio.")
        conexion = conectar()
        try:
            cursor = conexion.execute("""
                INSERT INTO notas_movimiento
                    (texto_original, transcripcion, audio_path, datos_json)
                VALUES (?, ?, ?, ?)
            """, (texto_original.strip(), transcripcion, audio_path,
                  json.dumps(datos, ensure_ascii=False)))
            conexion.commit()
            return cursor.lastrowid
        finally:
            conexion.close()

    def obtener_pendientes(self):
        conexion = conectar()
        filas = conexion.execute("""
            SELECT id, texto_original, transcripcion, audio_path, datos_json, creado_en
            FROM notas_movimiento WHERE estado = 'pendiente'
            ORDER BY id DESC
        """).fetchall()
        conexion.close()
        return [
            {"id": f[0], "texto_original": f[1], "transcripcion": f[2],
             "audio_path": f[3], "datos": json.loads(f[4]), "creado_en": f[5]}
            for f in filas
        ]

    def confirmar(self, nota_id):
        self._cambiar_estado(nota_id, "confirmada")

    def descartar(self, nota_id):
        self._cambiar_estado(nota_id, "descartada")

    @staticmethod
    def _cambiar_estado(nota_id, estado):
        conexion = conectar()
        try:
            conexion.execute("UPDATE notas_movimiento SET estado = ? WHERE id = ?", (estado, nota_id))
            conexion.commit()
        finally:
            conexion.close()
