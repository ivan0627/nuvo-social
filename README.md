# Nuvo · publicaciones automáticas

Cada 3 días, a las 5 a.m. hora de Houston, GitHub Actions toma la siguiente publicación de `posts.json`, genera la imagen (1080×1350) con la marca de Nuvo y la publica en la página de Facebook **Nuvo Group** y en Instagram **@nuvo.group.co** usando la API de Meta.

## Cómo funciona

- `posts.json`: el banco de publicaciones (40, en español e inglés). Cada una trae plantilla, titular, texto, hashtags y, si lleva foto, el id de una foto de Pexels.
- `render.py`: dibuja la imagen con Playwright y la guarda en `out/`.
- `run.py`: decide si toca publicar, sube la imagen al repo (Instagram necesita una URL pública), publica en Facebook e Instagram y guarda el avance en `state.json`.
- `.github/workflows/publicar.yml`: corre todos los días a las 10:00 y 11:00 UTC. `run.py` solo publica si en Houston son las 5 a.m. (o hasta las 6:59 si GitHub arranca tarde) y ya pasaron 3 días.

## Configuración (una sola vez)

1. En **Settings → Secrets and variables → Actions → New repository secret**, crea `META_TOKEN` con el token de la página (o del usuario del sistema) con los permisos `pages_manage_posts`, `pages_read_engagement`, `instagram_basic` e `instagram_content_publish`.
2. Opcional, en **Variables**: `PAGE_ID` (por defecto 1362020253662270, el id de la página Nuvo Group en la API; el número de profile.php no sirve) y `GRAPH_VERSION` (por defecto v25.0).

## Probar o publicar a mano

**Actions → Publicar en Facebook e Instagram → Run workflow**:
- `dry-run`: solo genera la imagen y la sube a `out/`, sin publicar.
- `publish`: publica la siguiente ya mismo.

## Cuando se acabe el banco

Al llegar a la publicación 40, vuelve a empezar desde la 1. Para agregar más, sube un `posts.json` nuevo con el mismo formato.
