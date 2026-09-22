# GA Desarrolladores Inmobiliarios — sitio de recursos

Sitio estático de recursos de análisis inmobiliario: cinco calculadoras, un checklist de 52 puntos,
un glosario de 42 términos, tres artículos largos y tres plantillas descargables.

No usa framework, no tiene dependencias en tiempo de ejecución y no manda ningún dato a un servidor:
todo el cálculo corre en el navegador del visitante.

---

## Cómo se ve y por qué

La paleta y la tipografía vienen del sistema de diseño **GA Desarrolladores**
(marfil, arena, salvia, terracota, espresso y champagne; Fraunces para títulos, Inter para texto).
Los seis colores de marca están en `assets/css/styles.css` con sus valores exactos.

Hay tres tonos derivados que no están en la marca, y existen por una razón medible: tres
combinaciones de marca no alcanzan la relación de contraste 4.5:1 que necesita el texto
(medido con el algoritmo de WCAG 2.1).

| Combinación de marca | Contraste | Qué se usa en su lugar |
| --- | --- | --- |
| Blanco sobre terracota `#C47758` | 3.43:1 | Botones en `#A85F42` — 4.79:1 |
| Terracota `#C47758` sobre marfil | 3.04:1 | Enlaces en `#9A5236` — 5.13:1 |
| Champagne sobre marfil | 2.09:1 | Nunca como texto: solo bordes, íconos y detalles |

El terracota de marca sigue usándose tal cual donde sí cumple: títulos grandes, bordes,
íconos y superficies. El tema oscuro usa espresso como fondo y terracota claro como acento
(6.83:1).

---

## Estructura

```
├── index.html               ← páginas generadas (son las que se publican)
├── recursos.html
├── calculadoras.html
├── checklist.html
├── glosario.html
├── articulos.html
├── producto.html
├── contacto.html
├── articulos/
│   ├── analizar-propiedad-renta.html
│   ├── errores-comprador-primerizo.html
│   └── ia-para-bienes-raices.html
│
├── src/                     ← AQUÍ SE EDITA
│   ├── layout.html          ← encabezado, pie, menú y metadatos (una sola copia)
│   └── pages/               ← el contenido de cada página, sin encabezado ni pie
│
├── assets/
│   ├── css/styles.css       ← paleta, componentes, tema oscuro, estilos de impresión
│   ├── js/site.js           ← tema, menú, filtros, checklists, copiar al portapapeles
│   ├── js/calculadoras.js   ← toda la matemática financiera
│   ├── img/favicon.svg
│   └── descargas/           ← las plantillas que descarga el visitante
│
└── tools/
    ├── build.js             ← arma las páginas: layout + fragmento = HTML final
    └── validar.js           ← revisa enlaces, anclas, ids y correspondencia con el JS
```

## Cómo editar

**Para cambiar texto de una página:** edita el archivo en `src/pages/` y corre `npm run build`.
Nunca edites los `.html` de la raíz: se sobrescriben en cada build.

**Para cambiar el menú, el pie o los metadatos:** edita `src/layout.html` (y el arreglo `NAV`
de `tools/build.js` si agregas un enlace al menú). Un solo cambio se propaga a las 11 páginas.

**Para agregar una página:** crea el fragmento en `src/pages/`, añade su entrada al arreglo
`PAGES` de `tools/build.js` con título y descripción, y corre el build.

```bash
npm run build      # genera las 11 páginas
npm run validar    # genera y después revisa enlaces, anclas e ids
npm run servir     # levanta el sitio en http://localhost:8080
```

El validador revisa que cada enlace interno exista, que cada `#ancla` apunte a un id real,
que no haya ids duplicados, que cada `<label for>` tenga su campo y que los ids que lee
`calculadoras.js` estén definidos en el HTML. Córrelo antes de publicar.

## Antes de publicar: qué hay que reemplazar

Estos son los marcadores de posición que quedan pendientes de tus datos reales:

| Archivo | Qué reemplazar |
| --- | --- |
| `src/pages/contacto.html` | Número de WhatsApp (`https://wa.me/51000000000`), correo y los cuatro enlaces de redes (`href="#"`) |
| `src/pages/producto.html` | El enlace de pago de El Mapa (hoy apunta a contacto) |
| `src/layout.html` | `og:url` y `canonical` cuando tengas dominio |

## Publicar en GitHub Pages

1. En el repositorio: **Settings → Pages → Source: Deploy from a branch**.
2. Elige la rama y la carpeta `/ (root)`.
3. Las páginas generadas están en la raíz, así que funciona sin configuración extra.

Como el sitio es estático también sirve tal cual en Netlify, Vercel, Cloudflare Pages
o cualquier hosting con solo subir la carpeta.

## Las calculadoras

| Calculadora | Qué responde | Fórmula principal |
| --- | --- | --- |
| Hipoteca | Cuota real, incluyendo predial, seguros y mantenimiento | Sistema francés: `P · i / (1 − (1+i)⁻ⁿ)` |
| Renta | Si la propiedad deja dinero en alquiler | NOI, cap rate, cash-on-cash, DSCR, GRM, punto de equilibrio |
| Capacidad de compra | Hasta cuánto alcanza hoy | Cruza cuota máxima sobre ingreso con el ahorro y el LTV del banco |
| Rentar vs. comprar | Cuál deja más patrimonio | Simulación mes a mes con el capital alternativo invertido |
| Remodelar y vender | Cuánto ofertar y qué utilidad queda | Regla del 70 %, utilidad neta, ROI anualizado, punto de equilibrio |

Los supuestos están explicados en `calculadoras.html#metodologia` y el código está comentado.
Las tasas anuales se convierten a mensuales con `(1 + r)^(1/12) − 1` donde corresponde,
no dividiendo entre 12.

Monedas disponibles: soles, dólares, pesos mexicanos, colombianos, chilenos, argentinos y euros.
La elección se guarda en el navegador del visitante.

## Accesibilidad

- Contraste verificado en los dos temas (ver la tabla de arriba).
- Navegación por teclado con enlace de salto al contenido y anillos de foco visibles.
- `aria-pressed` en los filtros, `aria-current` en el enlace de la página actual,
  `aria-live` en el contador de resultados.
- Respeta `prefers-reduced-motion` y `prefers-color-scheme`.
- Sin scroll horizontal a 390 px de ancho, verificado en las 11 páginas.
- Estilos de impresión: el checklist y el glosario salen legibles en papel.

## Aviso

El contenido es informativo y educativo. No constituye asesoría financiera, legal ni tributaria.
Los nombres de documentos y los tributos corresponden a la práctica peruana.
