class Categoria:

    def __init__(self, nombre, id=None):
        self.id = id
        self.nombre = nombre.strip()

        if not self.nombre:
            raise ValueError("El nombre de la categoría es obligatorio.")
