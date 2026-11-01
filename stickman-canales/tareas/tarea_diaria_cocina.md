Tarea diaria: STICKMAN COCINA para Roger Guevara ("Roy"). Escribe y notifica siempre en español de Latinoamérica. Roger aprueba cada video y lo sube él mismo: NO publiques nada en ninguna red.

1) PREPARAR
- cd /home/user/ROGERDEVELOPER (si no existe, clona redesroger33-sketch/rogerdeveloper ahí). git fetch origin claude/optimistic-franklin-ufuod8 && git checkout -B claude/optimistic-franklin-ufuod8 origin/claude/optimistic-franklin-ufuod8
- bash noticias-stickman/motor/instalar.sh
- Lee stickman-canales/README.md y los guiones de stickman-canales/cocina/episodios/ para NO repetir platos.

2) PLATO (cocina peruana real)
- Rota entre criollos, marinos, andinos, amazónicos, chifa/nikkei, postres y bebidas: ceviche, tiradito, ají de gallina, causa limeña, arroz con pollo, seco de res, anticuchos, papa a la huancaína, ocopa, rocoto relleno, carapulcra, tacu tacu, chupe de camarones, arroz chaufa, tallarines verdes, pollo a la brasa casero, olluquito, juane, tacacho con cecina, pachamanca a la olla, adobo arequipeño, cau cau, sudado de pescado, parihuela, leche de tigre, suspiro limeño, picarones, mazamorra morada, arroz con leche, chicha morada, entre otros.
- Receta con CANTIDADES reales (para 4) y pasos claros. Tips de chefs peruanos famosos (Gastón Acurio, Virgilio Martínez, Pía León, Mitsuharu Tsumura, Javier Wong, Rafael Osterling, Marisol Ruiz, Palmiro Ocampo, Flavio Solórzano, Teresa Ocampo…) SOLO si están publicados: búscalos con WebSearch y léelos completos desde COMPOSIO_REMOTE_WORKBENCH (requests + invoke_llm para extraer citas literales). REGLA DE ROGER: el nombre del chef SOLO se dice en la voz (campo "voz"); nunca se escribe en pantalla (globos "texto", tarjetas, titular, pantallas), ni en la miniatura, ni en el título, la descripción o los hashtags. En pantalla usa "el gran chef" o "el chef" y no pongas notas de fuente en las tarjetas. Las fuentes van solo en publicacion.md, en la sección "Fuentes (solo para ti, no pegar en la publicación)". Si no hay tip verificable de un chef, no lo inventes: usa la técnica tradicional.

3) GUION: stickman-canales/cocina/episodios/AAAA-MM-DD-plato/guion.json (plantilla: el del 2026-11-02, lomo saltado)
- "canal":"cocina", "locutor":"tito", "elenco":["rosita","tito","beto"], "programa":["STICKMAN","COCINA"], "duracion_max":119 (dura 2:00).
- Chef Tito explica; Rosita lee los insumos y pregunta; Beto se equivoca y bromea (1-2 chistes con "zoom" y "sonido":["rimshot"]). Saludo "¡Hola, cocineros!".
- 19 a 22 escenas, unas 290-310 palabras en total en "voz" (números en palabras). "fuego": true en las escenas de cocción. Usa "fotos:" para los insumos (con cantidades en las etiquetas), "lista:" para los pasos y "foto:" del plato terminado al inicio y al final.
- FOTOS REALES del plato e insumos: stickman-canales/fotos/ (claves en creditos.json). Si faltan, tráelas con herramientas/fotos_commons.py en el workbench → Drive redesoscio "Stickman Doctor y Cocina - Fotos" (id 1NOJVTNxGPVWHDXDQRaams38g-uOll4Tq, cuenta googledrive_pricky-prop) → Google_Drive download_file_content → bash stickman-canales/herramientas/importar_fotos.sh <archivo>. Revisa que cada foto sea del plato o insumo correcto (nada de marcas comerciales).

4) RENDER Y REVISIÓN
- cd noticias-stickman/motor && python3 render.py ../../stickman-canales/cocina/episodios/<carpeta>/guion.json
- Si el log dice velocidad mayor a x1.25, recorta texto y vuelve a renderizar. Duración final entre 1:55 y 2:00.
- Hoja de cuadros (ffmpeg fps=1/8, tile 7x2) y revísala; audio con volumedetect.
- miniatura.json (con "canal":"cocina" y "foto" del plato) → python3 miniatura_gen.py ... miniatura.jpg
- publicacion.md: título (máx. 100 caracteres, con #Shorts), descripción breve, receta completa con cantidades, hashtags, fuentes y el bloque de créditos de fotos (python3 stickman-canales/herramientas/creditos_episodio.py <guion>).

5) ENTREGA
- git add stickman-canales && git commit -m "Stickman Cocina <fecha>: <plato>" && git pull --rebase origin claude/optimistic-franklin-ufuod8 && git push -u origin claude/optimistic-franklin-ufuod8 (reintenta hasta 4 veces si falla la red).
- Envía con SendUserFile (status proactive) el video y la miniatura, y en el mensaje: título, descripción breve, receta resumida y "¿Le doy el OK?".
- Si la cuenta de Drive "ia.rguevarar" (googledrive_uca-algae u otra con alias ia.rguevarar) está ACTIVA en Composio y existe su carpeta "Stickman Cocina", sube también publicacion.md y la miniatura ahí (GOOGLEDRIVE_UPLOAD_FILE, máx. 5 MB). No toques la cuenta googledrive_kitcat-folie.
