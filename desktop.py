from database.database import crear_tablas
from ui.app import MoneyApp


if __name__ == "__main__":
    crear_tablas()
    app = MoneyApp()
    app.mainloop()
