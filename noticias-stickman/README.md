# Noticias Stickman

Shorts verticales (1080x1920, 35–50 s) con las noticias del día en Perú y lo viral del mundo.
Personajes: **Paco** (locutor con micrófono), **Lucha** (reportera, datos serios) y **Chato** (vecino con chullo, humor).
Saludo fijo: "¡Buenos días, Stickmatas!". Cierre: botones LIKE, corazón y SÍGUEME.

## Flujo diario
1. `bash motor/instalar.sh` (voces y librerías; solo si el servidor se reinició).
2. Crear `episodios/AAAA-MM-DD-tema/guion.json` (copiar el del 01 NOV como plantilla).
3. `cd motor && python3 render.py ../episodios/<carpeta>/guion.json`
4. Miniatura: adaptar `motor/miniatura.py`.
5. Título, descripción y fuentes en `publicacion.md`.

Voces: Paco y Chato (masculinas), Lucha (femenina), con tono subido (`TONO` en render.py) para sonar más alegres.
