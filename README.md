# 💰 MoneyApp - Mi App de Dinero

Aplicación de escritorio moderna, ligera e intuitiva para la gestión de finanzas personales, control de gastos, préstamos, deudas y gastos compartidos con soporte de registro rápido por notas de texto o voz.

---

## ✨ Características Principales

* **Balance en tiempo real:** Visualización de saldo virtual (QR/Transferencia), efectivo en mano, montos por cobrar y por pagar.
* **Registro de movimientos:** Ingresos, gastos, préstamos otorgados, deudas y pagos/abonos.
* **Gastos compartidos:** Distribución personalizada de un gasto entre amigos o familiares, generando obligaciones automáticas para cada persona.
* **Saldos interactivos:** Vista detallada por persona con desglose individual de cada préstamo, deuda o gasto compartido pendiente.
* **Gestión de categorías:** Creación, edición y eliminación de categorías personalizadas protegidas contra borrados accidentales de movimientos asociados.
* **Notas rápidas por texto o audio (100% gratuito):**
  * Dicta o escribe en lenguaje natural cotidiano (ej.: *"Le di 50 a Carlos para almuerzo"*, *"Carlos me prestó 100"*, *"Pagué 120 de luz"*).
  * Transcripción de audio automática sin costo ni necesidad de claves de API de OpenAI.
  * Flujo de revisión seguro: la nota no modifica tus saldos hasta que la revises y confirmes.
* **Base de datos local SQLite:** Toda tu información vive en tu computadora de forma privada, rápida y sin depender de servidores externos.

---

## 📋 Requisitos Previos

* **Python 3.10** o superior instalado en tu sistema.
* En **Windows** y **macOS**, la interfaz gráfica (*Tkinter*) ya viene incluida con la instalación oficial de Python.
* En **Linux (Ubuntu/Debian)**, si no tienes Tkinter instalado, puedes agregarlo con:
  ```bash
  sudo apt install python3-tk
  ```

---

## 🚀 Guía de Instalación y Ejecución

Sigue estos sencillos pasos para clonar y levantar la aplicación en cualquier computadora:

### 1. Clonar el repositorio
Abre tu terminal o consola y ejecuta:
```bash
git clone https://github.com/TU_USUARIO/MoneyApp.git
cd MoneyApp
```
*(Reemplaza `TU_USUARIO` con tu usuario de GitHub o la URL correspondiente).*

### 2. Crear y activar un entorno virtual (Recomendado)
Aislar las dependencias evita conflictos con otras versiones de Python en tu sistema:

* **En Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
  *(Si usas CMD: `venv\Scripts\activate.bat`)*

* **En macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Instalar las dependencias
Instala los paquetes necesarios listados en `requirements.txt`:
```bash
pip install -r requirements.txt
```

> **Nota:** Las dependencias instaladas son:
> * `SpeechRecognition`: Transcripción de audio gratuita y multiplataforma.
> * `sounddevice` y `soundfile`: Grabación y procesamiento de audio local por micrófono.

### 4. Ejecutar la aplicación
Inicia la app de escritorio con:

* **En Windows:**
  ```bash
  python desktop.py
  ```

* **En macOS / Linux:**
  ```bash
  python3 desktop.py
  ```

La primera vez que arranques, la aplicación creará automáticamente la base de datos local `dinero.db` con las categorías iniciales y tablas necesarias.

---

## 🎙️ ¿Cómo funciona el registro por notas?

1. En la barra superior, haz clic en **+ Nota**.
2. Puedes **escribir un mensaje libre** o **grabar 10 segundos** de audio con tu micrófono.
   * *Ejemplo 1:* `"Pagué 45 en almuerzo"` (se detecta como Gasto y categoría Alimentación).
   * *Ejemplo 2:* `"Le presté 50 a Juan"` (se detecta como Préstamo a Juan).
   * *Ejemplo 3:* `"Cena 120, mi parte es 40 y de Carlos es 80"` (se detecta como Gasto compartido).
3. Haz clic en **Enviar a revisar**.
4. Ve al botón **Revisar notas**: verás la propuesta lista. Al hacer clic en **Revisar y confirmar**:
   * Puedes corregir o cambiar el tipo de movimiento en cualquier momento.
   * Puedes crear nuevas categorías o personas directamente con los botones `+`.
   * Tus saldos solo se actualizarán cuando hagas clic en **Confirmar movimiento**.

---

## 📁 Estructura del Proyecto

```text
MoneyApp/
├── database/
│   └── database.py          # Conexión SQLite, esquema de tablas y migraciones
├── models/
│   ├── categoria.py         # Modelo de datos de categorías
│   ├── movimiento.py        # Modelo de ingresos, gastos, préstamos, deudas y pagos
│   └── persona.py           # Modelo de personas
├── services/
│   ├── audio_service.py     # Transcripción gratuita con SpeechRecognition
│   ├── categoria_service.py # CRUD de categorías
│   ├── interprete_nota.py   # Intérprete inteligente de lenguaje natural
│   ├── movimiento_service.py# Lógica financiera, balances, saldos y pagos
│   ├── nota_service.py      # Gestión de notas pendientes
│   └── persona_service.py   # Gestión de personas
├── ui/
│   └── app.py               # Interfaz gráfica de escritorio (Tkinter)
├── desktop.py               # Punto de entrada principal de la aplicación
├── money.py                 # Utilidades de precisión monetaria
├── requirements.txt         # Dependencias del proyecto
└── README.md                # Documentación del proyecto
```
