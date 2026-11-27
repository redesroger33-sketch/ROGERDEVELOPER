Tarea diaria: STICKMAN COCINA para Roger Guevara ("Roy"). Escribe y notifica siempre en español de Latinoamérica. Roger aprueba cada video y lo sube él mismo: NO publiques nada en ninguna red.

1) PREPARAR
- cd /home/user/ROGERDEVELOPER (si no existe, clona redesroger33-sketch/rogerdeveloper ahí). git fetch origin claude/optimistic-franklin-ufuod8 && git checkout -B claude/optimistic-franklin-ufuod8 origin/claude/optimistic-franklin-ufuod8
- bash noticias-stickman/motor/instalar.sh
- Lee stickman-canales/README.md y los guiones de stickman-canales/cocina/episodios/ para NO repetir platos.

2) PLATO (cocina peruana real)
- Rota entre criollos, marinos, andinos, amazónicos, chifa/nikkei, postres y bebidas: ceviche, tiradito, ají de gallina, causa limeña, arroz con pollo, seco de res, anticuchos, papa a la huancaína, ocopa, rocoto relleno, carapulcra, tacu tacu, chupe de camarones, arroz chaufa, tallarines verdes, pollo a la brasa casero, olluquito, juane, tacacho con cecina, pachamanca a la olla, adobo arequipeño, cau cau, sudado de pescado, parihuela, leche de tigre, suspiro limeño, picarones, mazamorra morada, arroz con leche, chicha morada, entre otros.
- Receta con CANTIDADES reales (para 4) y pasos claros. Tips de chefs peruanos famosos (Gastón Acurio, Virgilio Martínez, Pía León, Mitsuharu Tsumura, Javier Wong, Rafael Osterling, Marisol Ruiz, Palmiro Ocampo, Flavio Solórzano, Teresa Ocampo…) SOLO si están publicados: búscalos con WebSearch y léelos completos desde COMPOSIO_REMOTE_WORKBENCH (requests + invoke_llm para extraer citas literales). REGLA DE ROGER: el nombre del chef SOLO se dice en la voz (campo "voz"); nunca se escribe en pantalla (globos "texto", tarjetas, titular, pantallas), ni en la miniatura, ni en el título, la descripción o los hashtags. En pantalla usa "el gran chef" o "el chef" y no pongas notas de fuente en las tarjetas. Las fuentes van solo en publicacion.md, en la sección "Fuentes (solo para ti, no pegar en la publicación)". Si no hay tip verificable de un chef, no lo inventes: usa la técnica tradicional.

2b) GANCHO DE INTRIGA (OBLIGATORIO, pedido de Roger el 26 nov 2026: que se queden a ver todo el video)
- La PRIMERA escena (0-3 s) es el gancho y va ANTES del saludo "¡Hola, cocineros!". Muestra la "foto:" del plato terminado en primer plano y una frase corta (máx. 12 palabras) que cause intriga y antojo. Escribe 5 opciones y usa la más fuerte. Rota entre estos ángulos (no repitas el mismo dos días seguidos):
  · Antojo/dolor de no probarlo: "Si nunca probaste un ají de gallina así… te estás perdiendo la vida."
  · La mamá: "Tu mamá no lo hace así… y por eso no te queda igual."
  · La suegra: "Con esta receta, tu suegra te va a pedir el secreto."
  · El secreto: "El truco que nadie te dice para que el ceviche no quede amargo."
  · El error: "Casi todos arruinan el lomo saltado en este paso."
  · El reto: "Hazlo una vez así y nunca más lo vas a pedir en restaurante."
  Humor cariñoso, nunca ofensivo con mamás o suegras.
- Bucle abierto en la escena 2 (3-6 s): promete revelar el secreto o el paso clave AL FINAL ("y quédate hasta el final, que el secreto viene al último"). Cúmplelo en el último tercio con "zoom" y sonido "redoble".
- SONIDOS LLAMATIVOS en los primeros segundos (campo "sonido" de la escena; el motor ya los tiene): escena 1 con ["chisporroteo","golpe"] (sartén chisporroteando + golpe grave al aparecer el texto) o ["cuchillo","golpe"] según el plato; escena 2 con ["uau"]. Disponibles: "chisporroteo", "cuchillo", "golpe", "redoble", "uau", "rimshot", "aplausos". Usa "chisporroteo" también en las escenas de cocción con "fuego": true, y "redoble" antes de revelar el secreto. No satures: máximo 1-2 sonidos por escena.
- Título y miniatura con el mismo gancho de intriga (curiosidad + emoji, máx. 100 caracteres con #Shorts); texto de miniatura de 3-5 palabras grandes (ej. "¿TU MAMÁ LO HACE ASÍ?").
- Antes de entregar, revisa que los primeros 3 s tengan: plato en primer plano + frase de intriga + sonido llamativo. Si no, corrige y vuelve a renderizar. En el mensaje a Roger di en 1 línea cuál fue el gancho.

3) GUION: stickman-canales/cocina/episodios/AAAA-MM-DD-plato/guion.json (plantilla: el del 2026-11-02, lomo saltado)
- "canal":"cocina", "locutor":"tito", "elenco":["rosita","tito","beto"], "programa":["COCINA","STICKMAN"], "duracion_max":119 (dura 2:00).
- Chef Tito explica; Rosita lee los insumos y pregunta; Beto se equivoca y bromea (1-2 chistes con "zoom" y "sonido":["rimshot"]). Saludo "¡Hola, cocineros!" (DESPUÉS del gancho del punto 2b).
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
- SUBIR A SU DRIVE (después del push): en COMPOSIO_REMOTE_WORKBENCH usa GOOGLEDRIVE_UPLOAD_FROM_URL con la cuenta googledrive_slough-madman (ia.rguevarar@gmail.com; en run_composio_tool pasa account="ia.rguevarar", y en GET_FILE_METADATA el campo es fileId) y parent_folder_id 1a_d4u8rva-17DWHr1HNJuvOqjkW9MoNa (carpeta "Stickman Cocina"). source_url = https://raw.githubusercontent.com/redesroger33-sketch/rogerdeveloper/claude/optimistic-franklin-ufuod8/stickman-canales/<ruta del archivo>. Sube el video .mp4 (sin límite de 5 MB por esta vía), la miniatura como "<Canal>_<fecha>_miniatura.jpg" y publicacion.md como "<Canal>_<fecha>_publicacion.txt". Verifica con GOOGLEDRIVE_GET_FILE_METADATA que el tamaño del video coincide. Si la cuenta aparece desconectada o con permisos insuficientes, avísale a Roger que hay que reconectar ia.rguevarar en Composio. No toques la cuenta googledrive_kitcat-folie.
