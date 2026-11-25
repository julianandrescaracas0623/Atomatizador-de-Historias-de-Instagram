# MCP de Stories

Servidor MCP delgado sobre la API de Stories. Permite que Claude programe, liste y cancele historias.

**No publica de inmediato ni aprueba borradores.** La publicación la hace el worker a la hora programada, y la aprobación es humana, desde la web.

## Herramientas

| Herramienta | Qué hace |
|---|---|
| `instagram_status` | Estado de la cuenta, cuota de publicación y vencimiento del token. |
| `list_stories(status?)` | Lista historias. `status`: `pending`, `publishing`, `published` o `failed`. |
| `schedule_story(file_path, scheduled_at)` | Programa una historia desde la carpeta permitida. Hora local de Bogotá, ISO 8601. |
| `cancel_story(story_id)` | Elimina una historia que no esté publicándose. |

## Variables de entorno

| Variable | Uso |
|---|---|
| `MCP_API_BASE_URL` | URL del API. Por defecto `http://127.0.0.1:8000`. |
| `MCP_USERNAME` / `MCP_PASSWORD` | Credenciales de la app. |
| `MCP_UPLOAD_DIR` | Única carpeta de la que se pueden subir archivos. Sin esta variable, `schedule_story` no funciona. |

Solo se aceptan archivos `jpg`, `jpeg`, `mp4` y `mov` dentro de `MCP_UPLOAD_DIR`. Una ruta que salga de esa carpeta se rechaza, incluso con `..`.

## Instalación y pruebas

```bash
cd mcp
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q tests
```

## Conectar a Claude Code

Agrega a la configuración MCP del proyecto (por ejemplo `.mcp.json`):

```json
{
  "mcpServers": {
    "atomatizador-stories": {
      "command": "/ruta/a/mcp/.venv/bin/python",
      "args": ["/ruta/a/mcp/stories_server.py"],
      "env": {
        "MCP_API_BASE_URL": "http://127.0.0.1:8000",
        "MCP_USERNAME": "admin",
        "MCP_PASSWORD": "tu-contraseña",
        "MCP_UPLOAD_DIR": "/ruta/a/carpeta/de/contenido"
      }
    }
  }
}
```

Las credenciales van en tu configuración local, nunca en el repositorio.

## Decisiones de seguridad

- El MCP no tiene herramienta para aprobar ni para publicar de inmediato. Un agente no puede aprobar su propio contenido.
- El acceso a archivos está limitado a `MCP_UPLOAD_DIR`, para que un agente no pueda subir archivos sensibles del equipo.
- Si el token del API caduca, el MCP vuelve a iniciar sesión una sola vez y reintenta.
