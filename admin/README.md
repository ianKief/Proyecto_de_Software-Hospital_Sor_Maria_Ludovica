# Proyecto de Software - Sistema para la gestión del comedor del Hospital Sor Maria Ludovica 

## Requisitos previos
- [Python 3.14](https://www.python.org/downloads/)
- [Poetry](https://python-poetry.org/docs/#installation)
- PostgreSQL

---

## 🚀 Comandos Rápidos / Cheatsheet

### 1. Instalación y dependencias
Instalar o actualizar todas las librerías del proyecto. Debe correrse siempre que alguien modifique el `pyproject.toml` o haga un `git pull` con cambios en las dependencias.
```bash
poetry lock
poetry install
```

### 2. Base de Datos (Reset total)
Este comando sirve para resetear la base de datos al momento de hacer cambios en la estructura de la misma o crear nuevos seeds. Destruye TODAS las tablas de la base de datos, las vuelve a crear vacías y ejecuta los scripts seeders (`init_db.py` y los que se encuentren en la carpeta `seeders/`) para cargar los roles, permisos y al usuario Administrador por defecto.
```bash
poetry run flask --app main reset-db
```
**Usuario Admin por defecto:**
- **Email:** admin@hospital.com
- **Password:** admin123

### 3. Levantar el servidor Flask (Backend)
Inicia la aplicación de Flask.
```bash
poetry run flask --app main run
```

### 4. Compilar estilos Tailwind CSS (Frontend)
El código CSS fuente se escribe en el archivo `input.css`. Tailwind compila esos estilos y los traduce en `static/styles.css`.
*Nota: Nunca modificar manualmente el archivo `static/styles.css` ya que Tailwind lo sobrescribe.*

Para compilar de una sola vez:
```bash
poetry run tailwindcss -i ./input.css -o ./static/styles.css
```