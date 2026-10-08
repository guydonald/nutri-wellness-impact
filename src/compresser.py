from pathlib import Path
from PIL import Image

dossier = Path("websites/static/img")
for f in dossier.iterdir():
    if f.suffix.lower() not in (".jpg", ".jpeg", ".png"):
        continue
    avant = f.stat().st_size // 1024
    img = Image.open(f)
    taille_max = 256 if f.name == "logo.png" else 1200
    img.thumbnail((taille_max, taille_max))
    if f.suffix.lower() == ".png":
        img.save(f, optimize=True)
    else:
        img.convert("RGB").save(f, quality=78, optimize=True, progressive=True)
    print(f"{f.name}: {avant} Ko -> {f.stat().st_size // 1024} Ko")