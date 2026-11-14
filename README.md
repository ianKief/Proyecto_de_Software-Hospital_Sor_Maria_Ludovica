# Proyecto de Software 2026 - Grupo 47
**Sistema para la Gestión del Servicio de Alimentación — Hospital "Sor María Ludovica"**

## Integrantes

- Ian Kieferling
- Catalina Montes de Oca Altabe
- Julián Order
- Sebastián Paz
- Gerónimo Emanuel Basigalup

---

## Estructura del Repositorio

El proyecto está dividido en dos aplicaciones principales dentro de `code/`:

1. **`admin/` (Backend Flask + Aplicación Privada de Administración + API REST)**
   - Aplicación web privada renderizada en servidor (Jinja2 + Tailwind CSS), de acceso exclusivo para el rol **Administrador**.
   - Expone además la **API REST (`/api/*`)** consumida por el portal público.
2. **`portal/` (Aplicación Pública SPA en Vue 3 + Vite + Pinia)**
   - Aplicación web pública para los **roles operativos** del hospital:
     - **Jefe de Servicio** (carga y gestión de pedidos diarios de su sector).
     - **Servicio de Alimentación** (autorización/rechazo de pedidos y reportes).
     - **Sector Comedor** (modo Kiosco para validación de comensales por DNI).

---

## Requisitos Previos

- **Python 3.14** y **Poetry** (para `admin/`)
- **PostgreSQL**
- **Node.js** (`>= 20.19.0` o `>= 22.12.0`, recomendado gestionar con `fnm` o `nvm`) y **npm** (para `portal/`)

---

## Puesta en Marcha

### 1. Backend y Aplicación Privada (`admin/`)

```bash
cd admin

# 1. Instalar dependencias de Python
poetry install

# 2. Crear el archivo de variables de entorno a partir de la plantilla
cp .env.example .env
# (Editar .env con tus credenciales locales de PostgreSQL y GOOGLE_CLIENT_ID)

# 3. Inicializar / resetear la base de datos con datos semilla
poetry run flask --app main reset-db

# 4. Compilar estilos Tailwind CSS (si se modificó input.css o plantillas)
poetry run tailwindcss -i ./input.css -o ./static/styles.css

# 5. Levantar el servidor en http://localhost:5000
poetry run flask --app main run
```

**Credenciales por defecto en la base de datos (`reset-db`):**
- **Administrador** (acceso en `http://localhost:5000/auth/login`):
  - Email: `admin@hospital.com` | Contraseña: `admin123`
- **Roles operativos de prueba** (acceso en el portal público `http://localhost:5173/login`):
  - Jefe de Servicio: `jefe@hospital.com` | Contraseña: `user123`
  - Servicio de Alimentación: `alimentacion@hospital.com` | Contraseña: `user123`
  - Sector Comedor: `comedor@hospital.com` | Contraseña: `user123`

---

### 2. Aplicación Pública (`portal/`)

```bash
cd portal

# 1. Si usás fnm en PowerShell, activar Node en la sesión actual:
# fnm env --use-on-cd | Out-String | Invoke-Expression

# 2. Instalar dependencias de Node
npm install

# 3. Crear el archivo de variables de entorno a partir de la plantilla
cp .env.example .env

# 4. Iniciar el servidor de desarrollo en http://localhost:5173
npm run dev
```

---

## Configuración y Funcionamiento de la Autenticación con Google

El portal público (`portal/`) permite iniciar sesión tanto con **email y contraseña** como mediante **Google Identity Services (OAuth 2.0 / OpenID Connect)**.

### ¿Cómo funciona el flujo en el sistema?

1. **En el Frontend (`portal/`)**:
   - Se carga el SDK oficial de Google Identity Services (`https://accounts.google.com/gsi/client`) inicializado con el `VITE_GOOGLE_CLIENT_ID`.
   - Cuando el usuario hace clic en **"Iniciar sesión con Google"** y selecciona su cuenta, Google devuelve al navegador una credencial firmada criptográficamente (**ID Token** en formato JWT).
   - El frontend envía ese token al backend mediante `POST /api/auth/google` con el cuerpo `{ "id_token": "<token_de_google>" }`.
2. **En el Backend (`admin/` — `POST /api/auth/google`)**:
   - El servidor verifica la firma digital, fecha de expiración, emisor (`accounts.google.com`) y audiencia (`GOOGLE_CLIENT_ID`) del token usando la librería oficial `google-auth`.
   - Extrae el `email` verificado de la cuenta de Google y busca al usuario en la base de datos local.
   - **Importante (Sin autorregistro)**: El login con Google **no crea usuarios nuevos automáticamente**. El usuario debe haber sido dado de alta previamente por el Administrador en el sistema con ese mismo correo electrónico:
     - Si el correo no existe en la base de datos, devuelve `401 Unauthorized`.
     - Si el usuario está bloqueado/inactivo o tiene rol `Administrador`, devuelve `403 Forbidden`.
     - Si el usuario está activo y posee uno de los 3 roles operativos (`Jefe de Servicio`, `Servicio de Alimentación` o `Sector Comedor`), el backend emite el **JWT propio de la aplicación** (`token`, `expires_in`, `user`), igual que en el login tradicional.

### ¿Cómo obtener y configurar el `GOOGLE_CLIENT_ID`?

Un integrante del grupo puede crear la credencial en Google Cloud y compartir el **Client ID** con el resto del equipo (no se requiere Client Secret para este flujo):

1. Ingresar a [Google Cloud Console](https://console.cloud.google.com/).
2. Crear un proyecto (o seleccionar uno existente) e ir a **APIs y servicios > Pantalla de consentimiento de OAuth**:
   - Seleccionar tipo **Externo** (Modo de prueba / *Testing*).
   - En **Usuarios de prueba (*Test users*)**, agregar las cuentas de Gmail de los integrantes del grupo que vayan a probar el login.
3. Ir a **APIs y servicios > Credenciales** y hacer clic en **Crear credenciales > ID de cliente de OAuth**:
   - Tipo de aplicación: **Aplicación web**.
   - En **Orígenes de JavaScript autorizados** (*Authorized JavaScript origins*), agregar **ambas** URLs (Google exige incluir `http://localhost` sin puerto además del puerto de Vite para desarrollo local):
     - `http://localhost:5173`
     - `http://localhost`
4. Copiar el **ID de cliente** generado (tiene el formato `1234567890-abcdefg.apps.googleusercontent.com`).
5. Colocar ese mismo valor en ambos archivos `.env`:
   - En `admin/.env`:
     ```env
     GOOGLE_CLIENT_ID=1234567890-abcdefg.apps.googleusercontent.com
     ```
   - En `portal/.env`:
     ```env
     VITE_API_BASE_URL=http://localhost:5000/api
     VITE_GOOGLE_CLIENT_ID=1234567890-abcdefg.apps.googleusercontent.com
     ```
6. **Para probar el login con tu cuenta real de Google**:
   - Entrá a la aplicación privada (`http://localhost:5000/auth/login`) como Administrador (`admin@hospital.com` / `admin123`).
   - Creá un usuario nuevo (o editá uno existente) poniéndole tu correo `@gmail.com` real y asignale un rol operativo (por ejemplo, `Jefe de Servicio`).
   - Luego abrí `http://localhost:5173/login` y presioná **"Iniciar sesión con Google"**.
