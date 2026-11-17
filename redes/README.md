# Publicación semanal – GA Desarrolladores Inmobiliarios

Herramientas para preparar cada video semanal antes de publicarlo.

- `armar.sh entrada.mp4 salida.mp4`: detecta cada lámina del video, le aplica zoom progresivo (1.00→1.10), une las láminas con fundido y reemplaza el audio por música original.
- `musica.py salida.wav segundos`: genera una pista instrumental original (piano + pad + beat suave) sin derechos de terceros.

Requiere `ffmpeg` y `python3` con `numpy`.

## Flujo semanal
1. En Google Drive, tomar la siguiente carpeta "N semana TikTok" que **no** tenga un archivo `FACEBOOK_PUBLICADO_*.txt`.
2. Descargar `TIKTOK_video.mp4` y `TIKTOK_texto.txt`.
3. `./redes/armar.sh TIKTOK_video.mp4 final.mp4`
4. Subir `final.mp4` a un hosting con URL directa y publicarlo en la página de Facebook **GA Desarrolladores Inmobiliarios** (ID 106637591522545) con el texto como descripción.
5. Crear `FACEBOOK_PUBLICADO_AAAA-MM-DD.txt` en la carpeta de esa semana.
