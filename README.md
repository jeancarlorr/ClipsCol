# ColClips

Descargador web de videos públicos de TikTok, Instagram y Facebook. Interfaz en español, adaptable a móviles y lista para desplegar como servicio Docker.

## Características
- Detección de enlaces compatibles.
- Análisis del título, miniatura y resolución disponible.
- Descarga MP4 en la mejor calidad disponible o con límite de 1080p, 720p, 480p o 360p.
- Backend Flask + yt-dlp + FFmpeg.
- Sin cuentas, cookies ni acceso a publicaciones privadas.

## Ejecutar localmente

Necesitas Python 3.10+ y FFmpeg instalado.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Abre http://localhost:5000

## Publicar en GitHub y desplegar

1. Crea un repositorio llamado `colclips` en GitHub.
2. Sube todos los archivos de esta carpeta.
3. En Render, crea un nuevo **Blueprint** y conecta el repositorio.
4. Render leerá `render.yaml` y construirá el contenedor.
5. Cuando termine, abre la URL pública generada.

También puedes desplegar el Dockerfile en cualquier hosting compatible con Docker.

## Importante
- GitHub Pages no puede ejecutar el backend Python. ColClips necesita un hosting para el servidor (por ejemplo Render, Railway, Fly.io o un VPS).
- La calidad HD depende de la resolución que la plataforma entregue para cada publicación. No se puede convertir un video de baja resolución en HD real.
- Solo procesa contenido público accesible sin iniciar sesión. Publicaciones privadas, restringidas por edad/región o eliminadas pueden fallar.
- Las plataformas cambian sus sistemas con frecuencia; actualiza yt-dlp si algún extractor deja de funcionar.
- Descarga únicamente contenido propio o para el que tengas permiso. Respeta derechos de autor y términos de cada plataforma.
- Para producción con tráfico alto, añade rate limiting persistente, límites de almacenamiento/ancho de banda, monitoreo y una política de privacidad.

## API
- `POST /api/info` con JSON `{ "url": "https://..." }`
- `POST /api/download` con JSON `{ "url": "https://...", "quality": "best" }`
- `GET /health`
