# Publicación semanal – GA Desarrolladores Inmobiliarios

Herramientas para preparar cada video semanal antes de publicarlo.

- `armar.sh entrada.mp4 salida.mp4`: detecta cada lámina del video, le aplica zoom progresivo (1.00→1.10), une las láminas con fundido y reemplaza el audio por música original. Si no detecta cortes (transiciones a oscuro), pásalos a mano: `CORTES="4 9 14 19 24" ./redes/armar.sh entrada.mp4 salida.mp4`.
- `musica.py salida.wav segundos`: genera una pista instrumental original (piano + pad + beat suave) sin derechos de terceros.

Requiere `ffmpeg` y `python3` con `numpy`.

## Flujo semanal
1. En Google Drive, tomar la siguiente carpeta "N semana TikTok" que **no** tenga un archivo `FACEBOOK_PUBLICADO_*.txt`.
2. Descargar `TIKTOK_video.mp4` y `TIKTOK_texto.txt`.
3. `./redes/armar.sh TIKTOK_video.mp4 final.mp4`
4. Subir `final.mp4` a un hosting con URL directa y publicarlo en la página de Facebook **GA Desarrolladores Inmobiliarios** (ID 106637591522545) con el texto como descripción.
5. Crear `FACEBOOK_PUBLICADO_AAAA-MM-DD.txt` en la carpeta de esa semana.

## Reel desde láminas (Instagram)
`TRANSPONER=3 ./redes/reel_desde_laminas.sh reel.mp4 lamina_1.png ... lamina_N.png`
Cada lámina 1080x1350 centrada sobre fondo desenfocado 1080x1920, zoom 1.00→1.10, fundido y música original. `TRANSPONER` (semitonos, -5 a 6) cambia la tonalidad para que la música no suene igual cada semana.
