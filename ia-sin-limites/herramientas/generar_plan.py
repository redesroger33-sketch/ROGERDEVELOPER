"""Genera el plan de 120 shorts (Excel + Markdown) desde datos_plan.py."""
import datetime as dt
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from datos_plan import PILARES, SHORTS

# Orden de publicación: rota los 12 pilares para que cada día sea distinto
orden = []
for i in range(10):
    for p in range(12):
        orden.append((p, i))
inicio = dt.date(2026, 11, 3)
filas = []
for n, (p, i) in enumerate(orden, 1):
    t = SHORTS[p][i]
    assert len(t) == 7, (p, i)
    titulo, gancho, pasos, cta, desc, herr, visual = t
    assert len(desc) <= 100, (len(desc), desc)
    assert len(titulo) <= 100, titulo
    filas.append([n, (inicio + dt.timedelta(days=n - 1)).strftime("%d/%m/%Y"), PILARES[p][0], titulo, gancho,
                  pasos, cta, desc, len(desc), PILARES[p][1], herr, visual])

cab = ["N°", "Fecha sugerida", "Pilar", "Título (máx 100)", "Gancho 0-3 s", "Desarrollo 3-45 s (3 pasos)",
       "Cierre / CTA 45-55 s", "Descripción (máx 100)", "Caracteres", "Hashtags", "IAs a usar", "Visual clave"]
wb = Workbook()
ws = wb.active
ws.title = "Plan 120 shorts"
ws.append(cab)
for f in filas:
    ws.append(f)
anchos = [5, 12, 18, 45, 40, 60, 32, 50, 9, 32, 34, 34]
for k, a in enumerate(anchos):
    ws.column_dimensions[chr(65 + k)].width = a
for cell in ws[1]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="0B1020")
for row in ws.iter_rows(min_row=2):
    for cell in row:
        cell.alignment = Alignment(wrap_text=True, vertical="top")
ws.freeze_panes = "A2"
wb.save("../PLAN_120_SHORTS_IA_SIN_LIMITES.xlsx")

md = ["# IA sin límites — Plan de 120 shorts", "",
      "Duración: 48–55 s · Formato 9:16 · YouTube Shorts, TikTok y Facebook Reels · 1 short diario desde el 03/11/2026.", "",
      "## Estructura de cada short (48–55 s)",
      "| Tiempo | Bloque | Qué pasa |", "|---|---|---|",
      "| 0–3 s | Gancho | Frase o dato que detiene el scroll + visual impactante |",
      "| 3–10 s | Problema | Por qué importa (dolor o deseo del espectador) |",
      "| 10–40 s | Demostración | 3 pasos con la IA en pantalla (prompt, resultado, aplicación) |",
      "| 40–48 s | Resultado | Antes/después o número concreto |",
      "| 48–55 s | Cierre | CTA: comenta palabra clave + sígueme |", "",
      "## Flujo de producción",
      "1. **Guion y prompt**: ChatGPT / Gemini (verificar datos con 2 fuentes).",
      "2. **Imágenes y miniatura**: Ideogram (texto en imagen) y Gemini (edición de fotos).",
      "3. **Clips de video**: Flow (Veo).",
      "4. **Voz**: ElevenLabs (voz de Roger clonada con su permiso) o voces del motor propio.",
      "5. **Música**: ElevenLabs Music o biblioteca libre de CapCut.",
      "6. **Edición final**: CapCut Pro (subtítulos palabra por palabra, zoom, SFX, botones de like y follow).", "",
      "## Pilares (10 shorts cada uno)"]
for p, (nom, tags) in enumerate(PILARES):
    md.append(f"- **{nom}** · {tags}")
md += ["", "## Calendario y guiones", ""]
for f in filas:
    n, fecha, pilar, titulo, gancho, pasos, cta, desc, nc, tags, herr, visual = f
    md += [f"### {n}. {titulo}",
           f"**{fecha} · {pilar}** · IAs: {herr}", "",
           f"- **Gancho:** {gancho}", f"- **Desarrollo:** {pasos}", f"- **Cierre:** {cta}",
           f"- **Visual clave:** {visual}", f"- **Descripción ({nc}/100):** {desc}", f"- **Hashtags:** {tags} #Shorts", ""]
open("../PLAN_120_SHORTS_IA_SIN_LIMITES.md", "w", encoding="utf-8").write("\n".join(md))
print("OK", len(filas), "shorts")
