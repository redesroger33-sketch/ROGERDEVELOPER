"""Buscador de FOTOS REALES con licencia libre (Wikimedia Commons) para Stickman Doctor y Stickman Cocina.

Este código se pega y se ejecuta en el COMPOSIO_REMOTE_WORKBENCH (que sí tiene internet).
El contenedor de render no llega a Wikimedia, así que las fotos viajan así:

    Commons -> workbench -> Drive redesoscio, carpeta "Stickman Doctor y Cocina - Fotos"
    (id 1NOJVTNxGPVWHDXDQRaams38g-uOll4Tq, compartida como lector con redesroger33)
    -> conector Google_Drive (download_file_content) -> base64 -> stickman-canales/fotos/

Uso en el workbench (una celda por paso, cada celda tiene límite de 180 s):
    1) exec(open("/home/user/fotos_commons.py").read())   # o pegar este archivo completo
    2) cands = buscar("ceviche peruano")   -> revisa títulos/licencias, elige índices
    3) bajar_en_hilo({"ceviche": ("ceviche peruano", 0), "limon": ("key lime fruit", 1)})
    4) cuando exista /home/user/fotos/DONE -> ids = subir_zip()   (lotes de ~1.3 MB)
Luego, en el contenedor: download_file_content(fileId) por cada lote y
    bash stickman-canales/herramientas/importar_fotos.sh <archivo_guardado_por_la_herramienta.txt>

Solo se aceptan licencias CC BY, CC BY-SA, CC0 y dominio público; el crédito (autor + licencia)
queda en fotos/creditos.json y se muestra en el video y en la descripción.
"""
import io
import json
import os
import re
import threading
import time
import zipfile

import requests
from PIL import Image

WH = {"User-Agent": "StickmanCanales/1.0 (redesroger33)"}
OKLIC = ("cc by", "cc0", "public domain", "pd", "cc-by")
DIR = "/home/user/fotos"
CARPETA_DRIVE = "1NOJVTNxGPVWHDXDQRaams38g-uOll4Tq"
CUENTA_DRIVE = "googledrive_pricky-prop"


def buscar(q, n=10):
    for intento in range(4):
        try:
            r = requests.get("https://commons.wikimedia.org/w/api.php", params=dict(
                action="query", generator="search", gsrsearch=q + " filetype:bitmap", gsrnamespace=6,
                gsrlimit=n, prop="imageinfo", iiprop="url|extmetadata|size|mime", iiurlwidth=1000,
                format="json"), headers=WH, timeout=30).json()
            break
        except Exception:
            time.sleep(3 + 3 * intento)
    else:
        return []
    out = []
    for p in sorted(r.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99)):
        ii = p["imageinfo"][0]
        m = ii["extmetadata"]
        lic = m.get("LicenseShortName", {}).get("value", "")
        if ii["mime"] != "image/jpeg" or ii["width"] < 700 or not lic.lower().startswith(OKLIC):
            continue
        autor = re.sub(r"<[^>]+>", "", m.get("Artist", {}).get("value", "")).strip()[:60]
        out.append(dict(title=p["title"], w=ii["width"], h=ii["height"], lic=lic, autor=autor,
                        thumb=ii["thumburl"], page=ii["descriptionurl"]))
    for i, c in enumerate(out):
        print(i, c["title"][5:70], c["w"], c["h"], c["lic"])
    return out


def _bajar(pedidos):
    os.makedirs(DIR, exist_ok=True)
    cp = os.path.join(DIR, "creditos.json")
    cred = json.load(open(cp)) if os.path.exists(cp) else {}
    for clave, (q, idx) in pedidos.items():
        cands = buscar(q)
        if idx >= len(cands):
            print("sin resultado:", clave)
            continue
        c = cands[idx]
        for intento in range(4):
            try:
                b = requests.get(c["thumb"], headers=WH, timeout=40).content
                im = Image.open(io.BytesIO(b)).convert("RGB")
                im.thumbnail((1000, 1000))
                im.save(os.path.join(DIR, clave + ".jpg"), quality=84)
                break
            except Exception:
                time.sleep(3)
        cred[clave] = dict(title=c["title"], autor=c["autor"], lic=c["lic"], page=c["page"])
        json.dump(cred, open(cp, "w"), ensure_ascii=False, indent=1)
        time.sleep(1.5)
    open(os.path.join(DIR, "DONE"), "w").write("ok")


def bajar_en_hilo(pedidos):
    """pedidos = {"clave_foto": ("búsqueda", índice_elegido)}; corre en segundo plano."""
    if os.path.exists(os.path.join(DIR, "DONE")):
        os.remove(os.path.join(DIR, "DONE"))
    th = threading.Thread(target=_bajar, args=(pedidos,), daemon=True)
    th.start()
    return th


def subir_zip(prefijo="fotos_lote", limite=1_300_000):
    """Empaqueta las fotos (más creditos.json) en zips de ~1.3 MB y los sube a la carpeta de Drive."""
    fs = sorted(f for f in os.listdir(DIR) if f.endswith(".jpg"))
    grupos, cur, sz = [], [], 0
    for f in fs:
        s = os.path.getsize(os.path.join(DIR, f))
        if cur and sz + s > limite:
            grupos.append(cur)
            cur, sz = [], 0
        cur.append(f)
        sz += s
    if cur:
        grupos.append(cur)
    ids = []
    stamp = time.strftime("%Y%m%d_%H%M")
    for i, g in enumerate(grupos):
        zp = f"/home/user/{prefijo}_{stamp}_{i + 1}.zip"
        with zipfile.ZipFile(zp, "w") as z:
            for f in g:
                z.write(os.path.join(DIR, f), f)
            z.write(os.path.join(DIR, "creditos.json"), "creditos.json")
        res, err = upload_local_file(zp)  # noqa: F821 (helper del workbench)
        r, e = run_composio_tool("GOOGLEDRIVE_UPLOAD_FILE", {  # noqa: F821
            "file_to_upload": {"name": os.path.basename(zp), "mimetype": "application/zip", "s3key": res["s3key"]},
            "folder_to_upload_to": CARPETA_DRIVE}, account=CUENTA_DRIVE)
        ids.append((os.path.basename(zp), (r or {}).get("data", {}).get("id"), e))
    print(ids)
    return ids
