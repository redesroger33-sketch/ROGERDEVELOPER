"""Imprime los créditos de las fotos reales usadas en un guion (para la descripción del video).

Uso: python3 creditos_episodio.py ../doctor/episodios/<carpeta>/guion.json
Las licencias CC BY / CC BY-SA exigen nombrar autor y licencia: pega este bloque en la descripción.
"""
import json
import os
import re
import sys

guion = json.load(open(sys.argv[1], encoding="utf-8"))
cred = json.load(open(os.path.join(os.path.dirname(__file__), "..", "fotos", "creditos.json"), encoding="utf-8"))
claves = []
textos = [guion.get("pantalla_inicial", "")] + [sc.get("pantalla", "") for sc in guion["escenas"]]
for p in textos:
    m = re.match(r"(fotos?):([^|]+)", p or "")
    if m:
        for k in m.group(2).split(","):
            if k not in claves:
                claves.append(k)
print("📷 Fotos reales (Wikimedia Commons, licencias libres):")
for k in claves:
    c = cred.get(k)
    if c:
        autor = c.get("autor") or "Wikimedia Commons"
        print(f"• {c['title'].replace('File:', '')} — {autor} — {c['lic']} — {c['page']}")
