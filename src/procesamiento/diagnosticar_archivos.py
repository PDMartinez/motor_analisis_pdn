
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

CARPETAS = [
    BASE_DIR / "datos",
    BASE_DIR / "datos" / "originales",
]

print("=" * 60)
print("DIAGNÓSTICO DE ARCHIVOS JSON")
print("=" * 60)

for carpeta in CARPETAS:

    print(f"\nCarpeta: {carpeta}")
    print("Existe:", carpeta.exists())

    if not carpeta.exists():
        continue

    archivos = list(carpeta.rglob("*.json"))

    print("Cantidad de JSON:", len(archivos))

    for archivo in archivos[:10]:
        print(" -", archivo.relative_to(BASE_DIR))

    if len(archivos) > 10:
        print(f" ... y {len(archivos) - 10} archivos más")

    archivos_zip = list(carpeta.rglob("*.zip"))

    print("Cantidad de ZIP:", len(archivos_zip))

    for archivo in archivos_zip[:5]:
        print(" -", archivo.relative_to(BASE_DIR))

print("\n" + "=" * 60)
print("DIAGNÓSTICO FINALIZADO")
print("=" * 60)
