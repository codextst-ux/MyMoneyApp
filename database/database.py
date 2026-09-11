import sqlite3
from decimal import Decimal


DB_NAME = "dinero.db"

sqlite3.register_adapter(Decimal, lambda valor: format(valor, "f"))


def conectar():
    conexion = sqlite3.connect(DB_NAME)

    conexion.execute("PRAGMA foreign_keys = ON")

    return conexion


def crear_tablas():
    conexion = conectar()

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    """)

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            monto REAL NOT NULL,
            fecha TEXT NOT NULL,
            persona_id INTEGER,
            pagado_por_id INTEGER,
            movimiento_origen_id INTEGER,
            gasto_origen_id INTEGER,
            categoria_id INTEGER,
            medio_pago TEXT NOT NULL DEFAULT 'virtual',

            FOREIGN KEY (persona_id)
                REFERENCES personas(id),

            FOREIGN KEY (pagado_por_id)
                REFERENCES personas(id),

            FOREIGN KEY (movimiento_origen_id)
                REFERENCES movimientos(id),

            FOREIGN KEY (gasto_origen_id)
                REFERENCES movimientos(id),

            FOREIGN KEY (categoria_id)
                REFERENCES categorias(id)
        )
    """)

    migrar_movimientos(conexion)

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    """)

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS participaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movimiento_id INTEGER NOT NULL,
            persona_id INTEGER NOT NULL,
            monto REAL NOT NULL,

            FOREIGN KEY (movimiento_id)
                REFERENCES movimientos(id)
                ON DELETE CASCADE,

            FOREIGN KEY (persona_id)
                REFERENCES personas(id),

            UNIQUE (movimiento_id, persona_id)
        )
    """)

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS notas_movimiento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            texto_original TEXT NOT NULL,
            transcripcion TEXT,
            audio_path TEXT,
            datos_json TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conexion.commit()

    crear_persona_yo(conexion)
    crear_categorias_predeterminadas(conexion)

    conexion.close()


def migrar_movimientos(conexion):
    columnas = {
        fila[1]
        for fila in conexion.execute("PRAGMA table_info(movimientos)")
    }

    if "movimiento_origen_id" not in columnas:
        conexion.execute("""
            ALTER TABLE movimientos
            ADD COLUMN movimiento_origen_id INTEGER
        """)
        conexion.commit()

    if "gasto_origen_id" not in columnas:
        conexion.execute("""
            ALTER TABLE movimientos
            ADD COLUMN gasto_origen_id INTEGER
        """)
        conexion.commit()

    if "categoria_id" not in columnas:
        conexion.execute("""
            ALTER TABLE movimientos
            ADD COLUMN categoria_id INTEGER
        """)
        conexion.commit()

    if "medio_pago" not in columnas:
        conexion.execute("""
            ALTER TABLE movimientos
            ADD COLUMN medio_pago TEXT NOT NULL DEFAULT 'virtual'
        """)
        conexion.commit()


def crear_persona_yo(conexion):
    conexion.execute("""
        INSERT OR IGNORE INTO personas (nombre)
        VALUES ('Yo')
    """)

    conexion.commit()


def crear_categorias_predeterminadas(conexion):
    categorias = [
        "Alimentación", "Transporte", "Vivienda",
        "Educación", "Entretenimiento", "Servicios", "Compras"
    ]

    conexion.executemany("""
        INSERT OR IGNORE INTO categorias (nombre)
        VALUES (?)
    """, [(categoria,) for categoria in categorias])
    conexion.commit()
