# Roadmap de mejoras — Automatize Histories

Plan de trabajo para llevar el MVP a un estado listo para producción y preparado
para escalar. Nace de la autocrítica del código actual (agosto 2026).

## Cómo usar este documento

- Cada tarea tiene un checkbox `- [ ]`. Márcalo `- [x]` al terminar.
- Trabaja **de arriba a abajo**: las fases están ordenadas por _impacto / esfuerzo_.
- No pases a la siguiente fase sin cerrar la anterior (salvo la Fase 6, que es un
  proyecto independiente).
- Cada tarea incluye **Qué**, **Por qué**, **Archivos** y **Criterio de aceptación**.

### Leyenda

| Etiqueta | Significado |
|---|---|
| 🔴 P0 | Riesgo real en producción. Hacer ya. |
| 🟠 P1 | Importante. Bloquea escalar o testear. |
| 🟡 P2 | Mejora de calidad / DX. |
| ⚪ P3 | Backlog / nice to have. |
| ⏱ S | < 2 h · ⏱ M | medio día · ⏱ L | 1-3 días · ⏱ XL | > 3 días |

### Progreso

| Fase | Estado | Objetivo |
|---|---|---|
| 0 — Higiene y seguridad inmediata | ☐ Pendiente | Cerrar agujeros de config/secretos |
| 1 — Robustez del worker | ☐ Pendiente | Que ninguna Story se pierda o se atasque |
| 2 — Tests y CI | ☐ Pendiente | Red de seguridad para tocar el resto |
| 3 — Observabilidad | ☐ Pendiente | Saber qué pasa cuando falla a las 3am |
| 4 — Almacenamiento de objetos | ☐ Pendiente | Quitar el túnel y habilitar multi-instancia |
| 5 — Token e infraestructura | ☐ Pendiente | Operación desatendida |
| 6 — Multi-cuenta (producto) | ☐ Pendiente | Solo si el producto lo pide |

---

## Fase 0 — Higiene y seguridad inmediata

> Objetivo: ningún secreto expuesto, ningún default peligroso en producción.

### 0.1 🔴 ⏱ S — Verificar que `.env` nunca se versionó y rotar tokens si hace falta

- **Qué**: comprobar que `.env` está en `.gitignore` y que ningún commit histórico
  lo incluye. Si un `IG_ACCESS_TOKEN` o `IG_APP_SECRET` real llegó a un repo
  remoto, **revocarlo y regenerarlo** en Meta for Developers.
- **Por qué**: el `.env` (785 B) vive en la carpeta del proyecto con credenciales.
- **Archivos**: `.gitignore`, `.env`, `.env.example`.
- **Criterio de aceptación**:
  - `git check-ignore .env` responde `.env` (cuando el repo esté inicializado).
  - `git log --all --full-history -- .env` no devuelve nada.
  - `.env.example` tiene todas las claves con valores de ejemplo, sin secretos.

### 0.2 🔴 ⏱ S — La app se niega a arrancar con config insegura en producción

- **Qué**: validación en `Settings` (o en el `lifespan`) que aborte si
  `ENVIRONMENT != "dev"` y se cumple alguna de:
  - `jwt_secret` es `"change-me"` o mide < 32 caracteres.
  - `auth_password` es `"admin"`.
  - `app_public_base_url` empieza por `http://localhost`.
- **Por qué**: hoy los defaults (`config.py:15-19`) permiten desplegar con
  `admin/admin` y firma de JWT trivial.
- **Archivos**: `backend/app/config.py`, `backend/app/main.py`.
- **Criterio de aceptación**: `uvicorn` con esos valores y `ENVIRONMENT=prod`
  termina con un error claro; en `dev` solo emite un warning.

### 0.3 🟡 ⏱ S — Quitar `allow_credentials=True` del CORS

- **Qué**: poner `allow_credentials=False` (o quitar el argumento).
- **Por qué**: la auth es por header `Bearer`, no por cookies; habilitar
  credenciales amplía la superficie sin beneficio (`main.py:35`).
- **Archivos**: `backend/app/main.py`.
- **Criterio de aceptación**: login y llamadas autenticadas siguen funcionando
  desde el frontend.

---

## Fase 1 — Robustez del worker

> Objetivo: una Story programada se publica, se reintenta o se marca `failed`
> con motivo — nunca se queda a medias ni bloquea a las demás.

### 1.1 🟠 ⏱ S — Añadir `updated_at` a `scheduled_stories`

- **Qué**: columna `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()` con
  `onupdate=utcnow`. Nueva migración Alembic.
- **Por qué**: prerrequisito del reaper (1.2) y de la observabilidad.
- **Archivos**: `backend/app/models.py`, `backend/alembic/versions/`.
- **Criterio de aceptación**: cambiar el `status` de una fila actualiza
  `updated_at`; `alembic upgrade head` y `downgrade` limpios.

### 1.2 🔴 ⏱ M — Reaper de filas `publishing` huérfanas

- **Qué**: al inicio de cada tick del worker, recuperar filas atascadas:
  `publishing` con `updated_at < now() - INTERVAL '15 minutes'` → volver a
  `pending` (con contador de intentos) o marcar `failed` con
  `error_message = "Timeout de publicación, el worker se reinició"`.
- **Por qué**: si el worker muere en pleno `publish_story`, la fila queda
  `publishing` para siempre: no la reclama nadie (`worker.py:23`) y `DELETE` la
  rechaza con 409 (`stories.py:148`).
- **Archivos**: `backend/app/worker.py`.
- **Criterio de aceptación**: test que crea una fila `publishing` con
  `updated_at` antiguo y verifica que un tick la recupera.

### 1.3 🟠 ⏱ M — Reintentos con backoff exponencial

- **Qué**: añadir `attempts INT NOT NULL DEFAULT 0` y `next_attempt_at TIMESTAMPTZ`.
  Ante error transitorio: `attempts += 1`, `status = pending`,
  `next_attempt_at = now() + backoff(attempts)` (p. ej. 1, 5, 15 min).
  Tras `MAX_ATTEMPTS` (3) → `failed`. El worker filtra también por
  `next_attempt_at <= now()`.
- **Por qué**: hoy un parpadeo de red = `failed` permanente (`worker.py:60`).
- **Archivos**: `backend/app/models.py`, `backend/app/worker.py`, migración.
- **Criterio de aceptación**: con un `InstagramClient` que falla 2 veces y luego
  responde, la Story acaba `published` con `attempts = 2`.

### 1.4 🟠 ⏱ S — Clasificar errores transitorios vs. definitivos

- **Qué**: en `InstagramError`, distinguir `transient` (timeout, 429, 5xx,
  `error.code` de rate-limit de Meta) de `permanent` (formato rechazado, token
  inválido, media no descargable). Solo los `transient` reintentan.
- **Por qué**: no tiene sentido reintentar un "el video dura 90s" tres veces.
- **Archivos**: `backend/app/instagram/client.py`, `backend/app/worker.py`.
- **Criterio de aceptación**: tests para ambos caminos.

### 1.5 🟠 ⏱ S — `ffprobe` obligatorio fuera de `dev`

- **Qué**: si `shutil.which("ffprobe")` es `None`: en `dev` loguear
  `WARNING: validación de video desactivada`; en `prod` lanzar error al
  arrancar (o rechazar subidas de video con 503).
- **Por qué**: hoy `_ffprobe` devuelve `{}` en silencio (`media_validation.py:73`)
  y los videos pasan sin validar duración/fps → fallan luego en Graph API.
- **Archivos**: `backend/app/media_validation.py`, `backend/app/main.py`.
- **Criterio de aceptación**: arrancar sin ffmpeg en `prod` falla con mensaje
  claro; en `dev` arranca con warning.

### 1.6 🟡 ⏱ L — Separar creación de contenedor y publicación en dos pasadas

- **Qué**: pasada A: coge `pending` due → crea contenedor → `status = processing`
  (guarda `creation_id`). Pasada B: coge `processing` → consulta `status_code`
  una vez (sin bloquear) → si `FINISHED`, `media_publish` → `published`; si sigue
  procesando, lo deja para el próximo tick.
- **Por qué**: `wait_for_container` bloquea el loop hasta 600 s para video
  (`instagram/client.py:85`); un video lento congela toda la cola.
- **Archivos**: `backend/app/worker.py`, `backend/app/instagram/client.py`,
  `backend/app/models.py` (nuevo estado `processing`, columna `creation_id`).
- **Criterio de aceptación**: con un video "en proceso" simulado, una imagen
  programada al minuto siguiente se publica sin esperar al video.
- **Nota**: si se hace la Fase 5.4 (cola de tareas), esto se resuelve solo. Elegir
  una de las dos, no ambas.

---

## Fase 2 — Tests y CI

> Objetivo: poder tocar el worker y la integración sin miedo.

### 2.1 🟠 ⏱ M — Infraestructura de tests

- **Qué**: `pytest`, `pytest-asyncio`, `httpx.AsyncClient` para la API,
  `app.dependency_overrides` para inyectar settings y BD de test. Postgres de test
  con `testcontainers-python` (necesario para `FOR UPDATE SKIP LOCKED`) o
  `docker compose` de test.
- **Archivos**: `backend/pyproject.toml` o `requirements-dev.txt`,
  `backend/tests/conftest.py`.
- **Criterio de aceptación**: `pytest` corre en verde con 0 tests reales todavía.

### 2.2 🟠 ⏱ M — Tests de `media_validation`

- **Casos**: PNG con alpha → JPEG sobre fondo blanco · imagen de 400 px de ancho
  → 400 · archivo vacío → 400 · archivo de 9 MB → 400 · `.txt` → 400 · MOV válido
  → `media_type = "video"`.
- **Archivos**: `backend/tests/test_media_validation.py`.

### 2.3 🟠 ⏱ S — Tests de `_parse_scheduled_at`

- **Casos**: fecha pasada → 400 · sin `tzinfo` → asume `America/Bogota` · sufijo
  `Z` → UTC · string no ISO → 400 · margen de 60 s de gracia.
- **Archivos**: `backend/tests/test_stories_schedule.py`.

### 2.4 🟠 ⏱ M — Tests de la máquina de estados del worker (IG mockeado)

- **Casos**: éxito → `published` + `instagram_media_id` · `InstagramError`
  permanente → `failed` + mensaje · error transitorio ×2 luego éxito →
  `published` con `attempts = 2` · fila `publishing` antigua → recuperada.
- **Archivos**: `backend/tests/test_worker.py` (con `InstagramClient` fake).

### 2.5 🟡 ⏱ S — Test de seguridad de `/media`

- **Casos**: `../../etc/passwd` → 404 · nombre no-UUID → 404 · UUID válido
  inexistente → 404 · archivo real → 200 con `Content-Type` correcto.
- **Archivos**: `backend/tests/test_media_route.py`.

### 2.6 🟠 ⏱ M — CI en GitHub Actions

- **Qué**: workflow en cada push/PR:
  - Backend: `ruff check`, `ruff format --check`, `mypy app`, `pytest`.
  - Frontend: `npm ci`, `tsc --noEmit`, `npm run build`.
  - Servicio Postgres para los tests.
- **Archivos**: `.github/workflows/ci.yml`, config de `ruff` y `mypy`.
- **Criterio de aceptación**: un PR con un fallo de tipos o un test roto se marca
  en rojo.

---

## Fase 3 — Observabilidad

> Objetivo: cuando algo falle de madrugada, que haya rastro.

### 3.1 🟠 ⏱ M — Logging estructurado con `story_id`

- **Qué**: logs en JSON (`structlog` o `logging` con formatter propio). Cada línea
  del worker y de los endpoints de Stories lleva `story_id`, `status`, `attempts`.
- **Archivos**: `backend/app/logging.py` (nuevo), `worker.py`, `routers/stories.py`.
- **Criterio de aceptación**: `grep story_id=<uuid>` reconstruye el ciclo de vida
  completo de una Story.

### 3.2 🟠 ⏱ S — Sentry (o equivalente) para excepciones

- **Qué**: `sentry-sdk` con integración FastAPI + el worker. DSN por env, opcional.
- **Archivos**: `backend/app/main.py`, `backend/app/worker.py`, `config.py`.
- **Criterio de aceptación**: una excepción no controlada en el worker aparece en
  el dashboard con traza y `story_id` como tag.

### 3.3 🟡 ⏱ M — Métricas básicas

- **Qué**: endpoint `GET /api/stats` (autenticado): publicadas/fallidas/pendientes
  por día en los últimos 30 días. Opcional: `/metrics` Prometheus.
- **Archivos**: `backend/app/routers/stats.py` (nuevo), frontend opcional.

### 3.4 🟠 ⏱ S — Rate limit en `/api/auth/login`

- **Qué**: `slowapi` o contador en memoria/Redis: máx. 5 intentos por IP cada
  15 min.
- **Archivos**: `backend/app/routers/auth.py`, `backend/app/main.py`.
- **Criterio de aceptación**: el 6º intento fallido devuelve 429.

---

## Fase 4 — Almacenamiento de objetos

> Objetivo: quitar el requisito del túnel HTTPS y permitir >1 instancia de API.

### 4.1 🟠 ⏱ M — Abstraer el almacenamiento tras una interfaz

- **Qué**: `MediaStorage` con `save(data, key) -> None`,
  `public_url(key) -> str`, `delete(key) -> None`, `exists(key) -> bool`.
  Implementación actual = `LocalDiskStorage` (mueve la lógica de hoy).
- **Archivos**: `backend/app/storage/` (nuevo), refactor de
  `media_validation.py`, `routers/stories.py`, `routers/media.py`, `worker.py`.
- **Criterio de aceptación**: los tests existentes pasan con `LocalDiskStorage`.

### 4.2 🟠 ⏱ M — Implementación S3 / Cloudflare R2 / GCS

- **Qué**: `S3Storage` con `boto3` (R2 es S3-compatible). Selección por env
  (`MEDIA_BACKEND=local|s3`).
- **Archivos**: `backend/app/storage/s3.py`, `config.py`, `requirements.txt`.
- **Criterio de aceptación**: subir una Story guarda el objeto en el bucket;
  `public_url` devuelve una URL accesible.

### 4.3 🟠 ⏱ S — Instagram descarga desde el bucket

- **Qué**: el worker pasa `storage.public_url(key)` a `create_story_container`
  en vez de `{APP_PUBLIC_BASE_URL}/media/...` (`worker.py:53`). URL pública del
  bucket o presigned GET con TTL de 1 h.
- **Archivos**: `backend/app/worker.py`.
- **Criterio de aceptación**: publicación real de una Story sin túnel activo.

### 4.4 🟡 ⏱ S — Limpieza de media publicada

- **Qué**: lifecycle rule del bucket (borrar a los 2 días) **o** job que borra
  objetos de Stories `published`/`failed` con > 48 h.
- **Por qué**: el diseño dice "borrar tras publicar"; hoy no ocurre.
- **Archivos**: `backend/app/worker.py` o config de infra.

### 4.5 🟡 ⏱ S — Documentar el fin del túnel

- **Qué**: actualizar `README.md` y `diseño_app_automatizacion_stories.md`: con
  storage de objetos, `APP_PUBLIC_BASE_URL` solo sirve al frontend/API, ya no a
  la descarga de media.
- **Archivos**: `README.md`, `diseño_app_automatizacion_stories.md`.

---

## Fase 5 — Token e infraestructura

> Objetivo: operación desatendida durante meses.

### 5.1 🔴 ⏱ M — Renovación automática del token long-lived

- **Qué**: job diario que, si al token le quedan < 10 días
  (`get_token_expires_at`), llama a `fb_exchange_token` para obtener uno nuevo y
  lo persiste (tabla `app_config` o secreto gestionado). Fallo → alerta ruidosa
  (Sentry + log `ERROR`), no solo el banner de UI.
- **Por qué**: hoy solo hay aviso (`instagram.py:24`); a los ~60 días deja de
  publicar.
- **Archivos**: `backend/app/instagram/client.py`, `backend/app/worker.py` (o
  nuevo `tasks/refresh_token.py`), migración para persistir el token.
- **Criterio de aceptación**: test con token próximo a caducar → se intercambia y
  se guarda el nuevo.

### 5.2 🟠 ⏱ S — Migraciones solo en el job de deploy

- **Qué**: quitar `alembic upgrade head` del arranque de `api` y `worker`
  (`Dockerfile:20`, `docker-compose.yml:37`). Ejecutarlo en un paso de deploy
  dedicado (o un contenedor `migrate` que corre una vez).
- **Por qué**: con >1 instancia, varias corren migraciones a la vez = carrera.
- **Archivos**: `backend/Dockerfile`, `docker-compose.yml`, script de deploy.

### 5.3 🟠 ⏱ S — `seed_user` fuera del `lifespan`

- **Qué**: mover `seed_user` (`main.py:19`) a un comando CLI
  (`python -m app.seed`) ejecutado en el deploy.
- **Por qué**: hoy corre en cada instancia de API al arrancar.
- **Archivos**: `backend/app/main.py`, `backend/app/seed.py`.

### 5.4 🟡 ⏱ XL — (Opcional) Cola de tareas real

- **Qué**: sustituir el loop artesanal por `procrastinate` (Postgres, sin infra
  nueva) o `arq` (Redis). Encolar `publish_story` con `eta = scheduled_at`;
  reintentos/backoff/dead-letter los da la librería. N workers en paralelo.
- **Por qué**: gratis obtienes lo de las tareas 1.3, 1.6 y concurrencia.
- **Archivos**: reescritura de `backend/app/worker.py`, `routers/stories.py`,
  `docker-compose.yml`.
- **Criterio de aceptación**: 50 Stories a la misma hora se publican en paralelo
  respetando el límite de Graph API.
- **Decisión pendiente**: ¿merece la pena la complejidad para 1 cuenta? Revisar
  tras Fase 4.

---

## Fase 6 — Multi-cuenta (proyecto de producto aparte)

> Solo si el producto lo pide. Es una reescritura, no una mejora incremental.

- [ ] ⚪ Añadir `account_id` (FK) a `scheduled_stories`; particionar la query del
      worker y el índice por cuenta.
- [ ] ⚪ Tabla `instagram_accounts` con credenciales **cifradas**
      (`cryptography.fernet` o KMS del proveedor), una fila por cuenta.
- [ ] ⚪ Flujo OAuth de Facebook Login en lugar de pegar el token a mano.
- [ ] ⚪ Gestión de usuarios real (registro, roles, relación usuario ↔ N cuentas).
- [ ] ⚪ Rate limit de Graph API **por cuenta** (hoy el conteo es global,
      `stories.py:64`).
- [ ] ⚪ Aislamiento en `GET /api/stories`: filtrar por las cuentas del usuario.
- [ ] ⚪ Revisar `/media`: el UUID opaco ya aísla, pero validar que no se filtran
      referencias entre cuentas.

---

## Backlog (P3, sin fase asignada)

- [ ] ⚪ Paginación en `GET /api/stories` (`stories.py:125`) — `limit`/`offset` o cursor.
- [ ] ⚪ `Error Boundary` en React para no mostrar pantalla en blanco ante un error de render.
- [ ] ⚪ Decidir `sessionStorage` vs `localStorage` para el token (`api.ts:6`):
      hoy abrir pestaña nueva desloguea.
- [ ] ⚪ `logout` real: lista de revocación o access tokens cortos + refresh token
      (`auth.py:30`).
- [ ] ⚪ Soft-delete de Stories en vez de `db.delete` + `unlink` (`stories.py:159`)
      para auditoría.
- [ ] ⚪ Quitar la llamada redundante a `me()` en `AppLayout` (`AppLayout.tsx:30`);
      `StoryProvider` ya trae los datos.
- [ ] ⚪ Backups automáticos de Postgres (point-in-time si el proveedor lo permite).
- [ ] ⚪ Frontend: reemplazar polling de 5 s por SSE cuando haya más de un usuario.
- [ ] ⚪ Test de _drift_ entre modelos SQLAlchemy y migraciones Alembic
      (`alembic check`).

---

## Orden recomendado (resumen ejecutable)

1. **Fase 0** completa (1-2 días).
2. **1.1 → 1.5** (robustez del worker sin el refactor grande).
3. **Fase 2** completa (tests + CI) — a partir de aquí todo lo demás es seguro.
4. **3.1, 3.2, 3.4** (logging, Sentry, rate limit).
5. **Fase 4** completa (storage de objetos → adiós túnel).
6. **5.1, 5.2, 5.3** (token + infra).
7. Reevaluar **1.6 vs 5.4** y **Fase 6** con datos de uso real.
