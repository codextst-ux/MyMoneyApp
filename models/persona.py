class Persona:

    def __init__(self, nombre, id=None):
        self.id = id
        self.nombre = nombre

        self.validar()

    def validar(self):
        if not self.nombre or not self.nombre.strip():
            raise ValueError("El nombre es obligatorio.")

        self.nombre = self.nombre.strip()