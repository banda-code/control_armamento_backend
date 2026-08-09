# Backend — Sistema de Control de Armamento

Primera etapa del backend institucional:

- PostgreSQL.
- Usuario personalizado identificado mediante TIN.
- Inicio de sesión con correo `@armada.mil.bo`.
- Recuperación de contraseña por webmail institucional.
- Roles:
  - Administrador.
  - Comando de la Armada.
  - Comandante de Unidad.
  - Jefe de Cuarta Sección - Logística.
  - Encargado de Armamento.
- Alcance global para Administrador y Comando.
- Alcance exclusivo de la propia unidad para los demás niveles.
- Auditoría de accesos, usuarios y catálogos.
- Catálogos de institución, unidades, grados, cargos y secciones.

Esta entrega todavía no incluye armamento, salidas, entradas ni novedades.
Esos módulos se agregarán sobre esta base.

---

## 1. Estructura

```text
control_armamento_backend/
├── apps/
│   ├── accounts/
│   ├── organization/
│   └── audit/
├── config/
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 2. Preparación

Copie el archivo de variables:

```bash
cp .env.example .env
```

En Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Cambie como mínimo:

```env
SECRET_KEY=una-clave-larga-y-segura
DB_PASSWORD=una-clave-segura
```

Para ejecutar Django desde su computadora:

```env
DB_HOST=localhost
```

Para ejecutarlo dentro de Docker Compose:

```env
DB_HOST=db
```

---

## 3. Ejecución local

Cree un entorno virtual:

```bash
python -m venv .venv
```

Linux:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Instale dependencias:

```bash
pip install -r requirements.txt
```

Levante PostgreSQL:

```bash
docker compose up -d db
```

Cree las migraciones. Este paso debe hacerse antes del primer `migrate`,
porque el proyecto utiliza un modelo de usuario personalizado:

```bash
python manage.py makemigrations organization accounts audit
python manage.py migrate
```

Cree los datos iniciales y el Administrador:

```bash
python manage.py seed_initial_data \
  --admin-email administrador@armada.mil.bo \
  --admin-tin TIN-ADMIN \
  --admin-password "Cambiar-Esta-Clave-123!"
```

En Windows PowerShell, coloque el comando en una sola línea:

```powershell
python manage.py seed_initial_data --admin-email administrador@armada.mil.bo --admin-tin TIN-ADMIN --admin-password "Cambiar-Esta-Clave-123!"
```

Inicie el servidor:

```bash
python manage.py runserver
```

Prueba de salud:

```text
GET http://localhost:8000/api/health/
```

---

## 4. Ejecución completa con Docker

Después de crear `.env`:

```bash
docker compose build
docker compose up -d
```

En la primera instalación, cree las migraciones:

```bash
docker compose exec backend \
  python manage.py makemigrations organization accounts audit
```

Luego:

```bash
docker compose exec backend python manage.py migrate
```

Cree el Administrador:

```bash
docker compose exec backend \
  python manage.py seed_initial_data \
  --admin-email administrador@armada.mil.bo \
  --admin-tin TIN-ADMIN \
  --admin-password "Cambiar-Esta-Clave-123!"
```

---

## 5. Endpoints disponibles

### Autenticación

```text
GET  /api/auth/csrf/
POST /api/auth/login/
POST /api/auth/logout/
GET  /api/auth/me/
POST /api/auth/password/change/
POST /api/auth/password/reset/
POST /api/auth/password/reset/confirm/
```

### Usuarios — solo Administrador

```text
GET   /api/users/
POST  /api/users/
GET   /api/users/{uuid}/
PATCH /api/users/{uuid}/
POST  /api/users/{uuid}/activate/
POST  /api/users/{uuid}/deactivate/
POST  /api/users/{uuid}/temporary-password/
```

### Organización

```text
/api/organization/institutions/
/api/organization/units/
/api/organization/ranks/
/api/organization/positions/
/api/organization/sections/
```

Todos los usuarios autenticados pueden consultar los catálogos permitidos.
Solo el Administrador puede crear o modificar.

### Auditoría

```text
GET /api/audit/
```

Administrador y Comando observan todas las unidades. Los demás usuarios
solo observan eventos de su unidad.

Filtros opcionales:

```text
/api/audit/?action=LOGIN_SUCCESS
/api/audit/?outcome=FAILED
/api/audit/?unit={uuid}
/api/audit/?actor={uuid}
```

---

## 6. Login desde React

Consulte la sección **AUTENTICACIÓN JWT** al final del documento.


## 7. Crear un usuario desde la API

Solo el Administrador puede hacerlo.

```json
{
  "tin": "123456",
  "email": "encargado.unidad@armada.mil.bo",
  "first_name": "Juan",
  "paternal_last_name": "Pérez",
  "maternal_last_name": "Mamani",
  "rank": "UUID_DEL_GRADO",
  "position": "UUID_DEL_CARGO",
  "unit": "UUID_DE_LA_UNIDAD",
  "section": "UUID_DE_LA_SECCION",
  "role": "ARMAMENT_OFFICER",
  "temporary_password": "Clave-Temporal-123!"
}
```

Roles aceptados:

```text
ADMINISTRATOR
NAVY_COMMAND
UNIT_COMMANDER
LOGISTICS_CHIEF
ARMAMENT_OFFICER
```

Los usuarios con roles de Comandante, Logística y Encargado deben tener
una unidad obligatoriamente.

---

## 8. Configurar webmail institucional

Durante desarrollo se usa:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

El enlace de recuperación se imprimirá en la terminal.

Para producción, solicite al administrador del webmail:

- Servidor SMTP.
- Puerto.
- TLS o SSL.
- Usuario remitente.
- Contraseña o credencial de aplicación.

Ejemplo:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.armada.mil.bo
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=sistema.armamento@armada.mil.bo
EMAIL_HOST_PASSWORD=CLAVE_PROTEGIDA
```

No suba el archivo `.env` a GitHub.

---

## 9. Próxima aplicación

Cuando esta primera etapa funcione, la siguiente aplicación será:

```text
apps/inventory/
```

Ahí se crearán:

- Tipo de armamento.
- Marca.
- Modelo.
- Número de serie.
- Accesorios.
- Estado actual.
- Unidad y depósito responsable.
- Fotografías.
- Historial.

Después se agregará:

```text
apps/movements/
```

para salidas, entradas, entrega, devolución y custodia, y:

```text
apps/incidents/
```

para novedades, observaciones, evidencias y responsables.


---

# AUTENTICACIÓN JWT

Esta versión utiliza:

- Access token de corta duración en la respuesta JSON.
- Refresh token en una cookie `HttpOnly`.
- Rotación del refresh token.
- Lista negra de refresh tokens revocados.
- Invalidación de tokens cuando cambia la contraseña.
- Límite de solicitudes para login, refresh y recuperación.

El frontend no debe guardar el refresh token en `localStorage`.
El access token puede mantenerse en memoria y enviarse así:

```javascript
fetch("http://localhost:8000/api/auth/me/", {
  headers: {
    Authorization: `Bearer ${accessToken}`,
  },
  credentials: "include",
});
```

Para login, refresh y logout primero obtenga el CSRF token y envíe:

```javascript
credentials: "include"
```

Endpoints:

```text
GET  /api/auth/csrf/
POST /api/auth/login/
POST /api/auth/token/refresh/
POST /api/auth/logout/
GET  /api/auth/me/
```

El login devuelve:

```json
{
  "access": "TOKEN_DE_ACCESO",
  "token_type": "Bearer",
  "expires_in": 600,
  "must_change_password": true,
  "user": {}
}
```

El refresh token no aparece en el JSON porque se guarda en cookie HttpOnly.

Después de agregar Simple JWT, ejecute nuevamente:

```bash
python manage.py migrate
```

También programe diariamente en producción:

```bash
python manage.py flushexpiredtokens
```

Ese comando elimina registros de tokens expirados de la tabla de blacklist.

---

# CREAR POSTGRESQL EN PGADMIN

## Mediante la interfaz

1. Abra pgAdmin.
2. Expanda `Servers`.
3. Conéctese al servidor PostgreSQL con el usuario `postgres`.
4. Clic derecho en `Login/Group Roles`.
5. Seleccione `Create` → `Login/Group Role`.
6. En `General`, escriba `armamento_user`.
7. En `Definition`, coloque la misma contraseña de `DB_PASSWORD`.
8. En `Privileges`, active solamente `Can login?`.
9. Mantenga desactivados Superuser, Create roles y Create databases.
10. Guarde.
11. Clic derecho en `Databases`.
12. Seleccione `Create` → `Database`.
13. Database: `control_armamento`.
14. Owner: `armamento_user`.
15. Encoding: `UTF8`.
16. Guarde.

También puede abrir Query Tool conectado a la base `postgres` y ejecutar:

```text
crear_base_pgadmin.sql
```

La contraseña del SQL coincide con la del archivo `.env` entregado.

---

# ORDEN DE EJECUCIÓN

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Instale:

```bash
pip install -r requirements.txt
```

Cree migraciones:

```bash
python manage.py makemigrations organization accounts audit
```

Aplique migraciones, incluyendo las tablas JWT blacklist:

```bash
python manage.py migrate
```

Cree el administrador inicial:

```powershell
python manage.py seed_initial_data --admin-email administrador@armada.mil.bo --admin-tin TIN-ADMIN --admin-password "Cambiar-Esta-Clave-123!"
```

Inicie:

```bash
python manage.py runserver
```


1. Usuarios, roles y autenticación       ✅
2. Organización institucional            ✅
3. Auditoría inicial                      ✅
4. Documentos personales                 ✅
5. Inventario de armamento               ✅
6. Personnel / personal militar                ← SIGUIENTE
7. Movements / entradas, salidas, devoluciones
8. Assignments / dotación individual
9. Inspections / inspecciones
10. Novelties / novedades y observaciones
11. Maintenance / mantenimiento
12. Reports / partes y reportes