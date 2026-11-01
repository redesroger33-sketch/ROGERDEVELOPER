Tarea diaria: STICKMAN DOCTOR para Roger Guevara ("Roy"). Escribe y notifica siempre en español de Latinoamérica. Roger aprueba cada video y lo sube él mismo: NO publiques nada en ninguna red.

1) PREPARAR
- cd /home/user/ROGERDEVELOPER (si no existe, clona redesroger33-sketch/rogerdeveloper ahí). git fetch origin claude/optimistic-franklin-ufuod8 && git checkout -B claude/optimistic-franklin-ufuod8 origin/claude/optimistic-franklin-ufuod8
- bash noticias-stickman/motor/instalar.sh
- Lee stickman-canales/README.md (reglas, pantallas, render) y los guiones de stickman-canales/doctor/episodios/ para NO repetir temas.

2) TEMA (medicina moderna + natural, SIN fármacos)
- Un hábito, alimento o planta con respaldo científico reciente, útil para Perú/Latinoamérica. Rota pilares: sueño, movimiento, alimentación (súper alimentos peruanos: quinua, kiwicha, tarwi, camu camu, maca, cacao, sacha inchi, kion, ajo, cúrcuma, linaza), hidratación, estrés y respiración, sol y vitamina D, intestino y fibra, presión arterial, corazón, cerebro y memoria, piel, huesos, y novedades de la medicina moderna (prevención, longevidad).
- Investiga con WebSearch y confirma CADA cifra en la fuente original. Para estudios usa PubMed desde COMPOSIO_REMOTE_WORKBENCH (eutils esearch/efetch, como en la tarea anterior) y cita revista, año y tamaño del estudio. Fuentes válidas: PubMed, Cochrane, OMS, MINSA, NIH/NCCIH, Mayo Clinic, Harvard Health, revistas indexadas. Nada de blogs sin fuente.
- PROHIBIDO: decir que se dejen o cambien medicamentos, prometer curas, dosis peligrosas, temas para menores o embarazadas sin advertencia. Siempre una escena con "esto suma, pero no reemplaza a tu médico" y, si hay plantas, avisar de interacciones (p. ej. anticoagulantes) cuando aplique.

3) GUION: stickman-canales/doctor/episodios/AAAA-MM-DD-tema/guion.json (copia el del 2026-11-02 como plantilla)
- "canal":"doctor", "locutor":"bruno", "elenco":["bruno","vita"], "programa":["STICKMAN","DOCTOR"], "duracion_max":104 (dura 1:45).
- Dr. Bruno (voz gruesa) explica; Dra. Vita (voz delgada) pregunta, da datos y hace 1 chiste con "zoom", "sonido":["rimshot"]. Saludo "¡Hola, familia sana!".
- 18 a 21 escenas, unas 260-280 palabras en total en los campos "voz" (números escritos en palabras). Tarjetas con las cifras, una "lista:" con la receta natural y fotos reales en casi todas las escenas.
- FOTOS REALES: usa stickman-canales/fotos/ (claves en fotos/creditos.json). Si faltan fotos del tema, tráelas con herramientas/fotos_commons.py en el workbench → Drive redesoscio carpeta "Stickman Doctor y Cocina - Fotos" (id 1NOJVTNxGPVWHDXDQRaams38g-uOll4Tq, cuenta googledrive_pricky-prop) → baja cada zip con Google_Drive download_file_content → bash stickman-canales/herramientas/importar_fotos.sh <archivo>. Revisa una hoja de contacto: cada foto debe coincidir con su etiqueta.

4) RENDER Y REVISIÓN
- cd noticias-stickman/motor && python3 render.py ../../stickman-canales/doctor/episodios/<carpeta>/guion.json
- Si el log dice velocidad mayor a x1.25, recorta texto y vuelve a renderizar. Duración final entre 1:40 y 1:45.
- Hoja de cuadros (ffmpeg fps=1/8, tile 7x2) y revísala; audio con volumedetect.
- miniatura.json (con "canal":"doctor" y "foto") → python3 miniatura_gen.py ... miniatura.jpg
- publicacion.md: título (máx. 100 caracteres, con #Shorts), descripción breve, aviso médico, hashtags, fuentes con enlace y el bloque de créditos de fotos (python3 stickman-canales/herramientas/creditos_episodio.py <guion>).

5) ENTREGA
- git add stickman-canales && git commit -m "Stickman Doctor <fecha>: <tema>" && git pull --rebase origin claude/optimistic-franklin-ufuod8 && git push -u origin claude/optimistic-franklin-ufuod8 (reintenta hasta 4 veces si falla la red).
- Envía con SendUserFile (status proactive) el video y la miniatura, y en el mensaje: título, descripción breve, las 2-3 fuentes principales y "¿Le doy el OK?".
- Si la cuenta de Drive "ia.rguevarar" (googledrive_uca-algae u otra con alias ia.rguevarar) está ACTIVA en Composio y existe su carpeta "Stickman Doctor", sube también publicacion.md y la miniatura ahí (GOOGLEDRIVE_UPLOAD_FILE, máx. 5 MB). No toques la cuenta googledrive_kitcat-folie.
