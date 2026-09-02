# Automatize Histories

App web para programar Stories y publicarlas en **una** cuenta de Instagram Business/Creator con la Instagram Graph API.

Diseño: [diseño_app_automatizacion_stories.md](diseño_app_automatizacion_stories.md).

## Qué hace el MVP

- Login (usuario / contraseña, JWT).
- Subir imagen o video, elegir fecha/hora (`America/Bogota`).
- Cola con estados: pendiente, publicando, publicada, fallida. Cancelar solo si sigue pendiente.
- Worker que, a la hora, llama a Graph API: crear contenedor `media_type=STORIES` → poll `status_code` → `media_publish`.
- El archivo se sirve en `{APP_PUBLIC_BASE_URL}/media/{filename}` **por HTTPS público**. Instagram lo descarga; `localhost` no sirve para publicar de verdad.

## Requisitos

- Python 3.12+, Node 22+, Docker (PostgreSQL).
- Cuenta Instagram **Business o Creator** ligada a una Página de Facebook (o Instagram Login).
- App en [Meta for Developers](https://developers.facebook.com/) con permiso `instagram_content_publish` (Facebook Login) o `instagram_business_content_publish` (Instagram Login).
- Token de usuario **long-lived** (~60 días) e `IG_USER_ID` (id de la cuenta profesional, no el username).

## Arranque local

1. Copia variables y edítalas:

```bash
cp .env.example .env
```

2. Postgres:

```bash
docker compose up db -d
```

3. Backend (desde `backend/`):

```bash
python -m venv .venv
# Windows: py -3 -m venv .venv   luego   .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

En otra terminal, el worker:

```bash
# misma venv, carpeta backend/
python -m app.worker
```

4. Frontend:

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173` (si está ocupado, Vite usa 5174). Usuario/contraseña: los de `AUTH_USERNAME` / `AUTH_PASSWORD` (por defecto `admin` / `admin`). API docs: `http://127.0.0.1:8000/docs`.

Si el login muestra **Error 500**, el puerto **8000** suele estar ocupado por otro proceso. Arranca el API en 8001 y apunta Vite ahí:

```bash
# backend/
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

En `frontend/.env.local` (cópialo de `frontend/.env.example`):

```
VITE_API_ORIGIN=http://127.0.0.1:8001
```

Reinicia `npm run dev`. El proxy de Vite debe coincidir con el puerto de uvicorn.

Para levantar API + worker + Postgres juntos: `docker compose up --build` (el frontend sigue en Vite).

## Publicar de verdad (túnel HTTPS)

Instagram **no puede** descargar `http://localhost`. Para una Story real:

1. Expón el API en HTTPS (Cloudflare Tunnel o ngrok) hacia el puerto 8000.
2. Pon esa URL en `APP_PUBLIC_BASE_URL`, por ejemplo `https://tu-subdominio.trycloudflare.com` (sin barra final).
3. Reinicia API y worker.

Sin túnel puedes programar y ver la cola; al llegar la hora el worker fallará al crear el contenedor.

## Variables Instagram

| Variable | Uso |
|---|---|
| `IG_ACCESS_TOKEN` | Token long-lived |
| `IG_USER_ID` | Id numérico de la cuenta profesional |
| `IG_GRAPH_HOST` | Por defecto `https://graph.facebook.com` |
| `IG_GRAPH_VERSION` | Por defecto `v22.0` |
| `IG_APP_ID` / `IG_APP_SECRET` | Opcional: `debug_token` para avisar si el token vence en ≤ 7 días |

El tope de publicaciones Graph se consulta en `/{ig-user-id}/content_publishing_limit`. Si ese endpoint no responde, se usa el conteo local (100 / 24 h).
