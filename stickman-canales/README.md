# Stickman Doctor y Stickman Cocina

Dos canales nuevos de shorts verticales (1080x1920) hechos con el mismo motor de Noticias Stickman
(`noticias-stickman/motor/render.py`). El guion elige el canal con `"canal": "doctor"` o `"canal": "cocina"`.

| Canal | Duración | Elenco | Set |
|---|---|---|---|
| **Stickman Doctor** | 1:45 (`duracion_max` 104) | **Dr. Bruno** (voz gruesa, locutor) y **Dra. Vita** (voz delgada). Batas blancas coloridas, espejo frontal en la cabeza y estetoscopio al cuello | Consultorio menta con monitor grande |
| **Stickman Cocina** | 2:00 (`duracion_max` 119) | **Chef Tito** (gorro, bigote, cucharón), **Rosita** y **Beto** (preguntan y bromean) | Cocina real de fondo (foto de la cocina de Central, Lima), mesón, wok con fuego animado |

## Fotos reales
Platos, insumos, lugares y cocinas son **fotos reales con licencia libre de Wikimedia Commons** (CC BY, CC BY-SA, CC0, dominio público).
Viven en `fotos/<clave>.jpg` con autor y licencia en `fotos/creditos.json`. El video muestra el crédito en cada foto y
`herramientas/creditos_episodio.py` arma el bloque para la descripción (obligatorio por la licencia).

Cómo traer fotos nuevas (el contenedor de render no llega a Wikimedia): ver `herramientas/fotos_commons.py`
(Commons → workbench de Composio → Drive redesoscio "Stickman Doctor y Cocina - Fotos" → conector Google_Drive → `herramientas/importar_fotos.sh`).

## Pantallas disponibles en el guion
- `"foto:clave|TÍTULO"` foto grande con zoom lento y crédito.
- `"fotos:c1,c2,c3[,c4]|ETIQUETA1|ETIQUETA2|..."` grilla de 2 a 4 insumos con etiquetas.
- `"lista:TÍTULO|paso 1|paso 2|..."` lista numerada animada (receta, pasos, recomendaciones).
- `"fuego": true` en una escena de cocina enciende la hornilla y mueve el wok.
- El texto del globo (`texto`) puede ser más corto que lo que se dice (`voz`).

## Reglas editoriales
**Doctor (medicina natural, sin fármacos):** solo hábitos, alimentos y plantas con respaldo científico (PubMed, Cochrane, OMS, MINSA, NIH/NCCIH, Mayo Clinic).
Cifras con estudio, revista y año. Nunca decir que se dejen medicamentos ni prometer curas: siempre la línea "esto suma, no reemplaza a tu médico".
El aviso "Información educativa · No reemplaza tu consulta médica" sale en pantalla todo el video.

**Cocina:** recetas peruanas reales con cantidades; los tips de chefs (Gastón Acurio, Virgilio Martínez, Pía León, Mitsuharu Tsumura,
Javier Wong, Rafael Osterling, Marisol Ruiz…) solo si están publicados en medios (El Comercio, RPP, La República, Infobae, sitios oficiales), citando medio y año.

## Render
```bash
bash ../noticias-stickman/motor/instalar.sh
cd ../noticias-stickman/motor
python3 render.py ../../stickman-canales/<canal>/episodios/<carpeta>/guion.json
python3 miniatura_gen.py ../../stickman-canales/<canal>/episodios/<carpeta>/miniatura.json ../../stickman-canales/<canal>/episodios/<carpeta>/miniatura.jpg
```
Velocidad de voz: ~270 palabras entran en 1:45 y ~300 en 2:00 a ritmo natural; si el log dice "velocidad x1.3" o más, recorta texto.
