# Metricas de calidad MultiBur

Scripts de consulta y medicion para evidenciar metricas de calidad del sistema MultiBur.

## Reglas

- No modifican datos.
- No guardan credenciales.
- Muestran evidencia por consola.
- Usan `DATABASE_URL` desde variables de entorno o `.env`.

## Ejecucion

Desde la carpeta del backend:

```powershell
venv\Scripts\python.exe scripts\metricas_calidad\run_all.py
```

O ejecutar una metrica especifica:

```powershell
venv\Scripts\python.exe scripts\metricas_calidad\06_ot_sin_inconsistencias.py
```

## Variables opcionales para endpoints protegidos

Para medir endpoints del backend desplegado:

```powershell
$env:METRICAS_API_URL="https://multibur-backend.onrender.com/api/v1"
$env:METRICAS_ADMIN_EMAIL="admin@multibur.com"
$env:METRICAS_ADMIN_PASSWORD="Admin1234"
```

Tambien puedes usar un token ya generado:

```powershell
$env:METRICAS_TOKEN="TOKEN_ADMIN"
```

No coloques credenciales dentro de los scripts.

## Nota sobre Supabase

Si una metrica de base de datos muestra que no puede resolver `db.<proyecto>.supabase.co`,
usa la URL del Transaction Pooler de Supabase en `DATABASE_URL` o ejecuta la metrica desde
un entorno que tenga resolucion DNS hacia ese host. Los scripts no imprimen la URL ni las
credenciales.
