"""Explora archivos JSON en datos/originales y muestra su estructura básica."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "datos" / "originales"

def resumir(valor, nivel=0, max_nivel=3):
    if nivel > max_nivel:
        return "..."
    if isinstance(valor, dict):
        return {
            clave: resumir(contenido, nivel + 1, max_nivel)
            for clave, contenido in list(valor.items())[:30]
        }
    if isinstance(valor, list):
        muestra = valor[0] if valor else None
        return {
            "tipo": "lista",
            "cantidad_elementos": len(valor),
            "primer_elemento": resumir(muestra, nivel + 1, max_nivel)
        }
    if isinstance(valor, str):
        return f"texto (ejemplo: {valor[:80]})"
    if valor is None:
        return "null"
    return f"{type(valor).__name__} (ejemplo: {valor})"

def main():
    archivos = sorted(DATA_DIR.glob("*.json"))
    if not archivos:
        print(f"No se encontraron archivos JSON en: {DATA_DIR}")
        print("Copiá los JSON de la PDN en esa carpeta y volvé a ejecutar.")
        return

    print(f"Archivos encontrados: {len(archivos)}")
    for archivo in archivos:
        print("\n" + "=" * 80)
        print(f"Archivo: {archivo.name}")
        try:
            with archivo.open("r", encoding="utf-8-sig") as f:
                contenido = json.load(f)
            print(f"Tipo principal: {type(contenido).__name__}")
            if isinstance(contenido, list):
                print(f"Cantidad de registros: {len(contenido)}")
            elif isinstance(contenido, dict):
                print(f"Claves principales: {list(contenido.keys())[:50]}")
            print("Estructura de muestra:")
            print(json.dumps(resumir(contenido), ensure_ascii=False, indent=2)[:12000])
        except json.JSONDecodeError as exc:
            print(f"JSON inválido: {exc}")
        except Exception as exc:
            print(f"No se pudo leer el archivo: {exc}")

if __name__ == "__main__":
    main()
