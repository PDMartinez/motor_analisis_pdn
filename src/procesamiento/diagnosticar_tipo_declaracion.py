
import json
from pathlib import Path
from collections import Counter, defaultdict

BASE_DIR = Path(__file__).resolve().parents[2]
CARPETA_ORIGINALES = BASE_DIR / "datos" / "originales"

frecuencia_rutas = Counter()
valores_candidatos = defaultdict(Counter)

total_declaraciones = 0


def explorar(objeto, ruta="", profundidad=0):

    if profundidad > 12:
        return

    if isinstance(objeto, dict):

        for clave, valor in objeto.items():

            nueva_ruta = f"{ruta}.{clave}" if ruta else str(clave)

            clave_norm = str(clave).lower()

            # Identificar claves relacionadas con tipo,
            # declaración o modalidad.
            if any(palabra in clave_norm for palabra in [
                "tipo",
                "declaracion",
                "modalidad"
            ]):

                frecuencia_rutas[nueva_ruta] += 1

                # Solo recopilar valores de campos candidatos
                # relacionados con clasificación.
                if isinstance(valor, str):
                    if len(valor) <= 80:
                        valores_candidatos[nueva_ruta][valor] += 1

                elif isinstance(valor, dict):
                    for subclave in ["clave", "valor"]:
                        subvalor = valor.get(subclave)

                        if isinstance(subvalor, str) and len(subvalor) <= 80:
                            valores_candidatos[
                                nueva_ruta + "." + subclave
                            ][subvalor] += 1

            explorar(valor, nueva_ruta, profundidad + 1)

    elif isinstance(objeto, list):

        for elemento in objeto:
            explorar(elemento, ruta + "[]", profundidad + 1)


archivos = sorted(CARPETA_ORIGINALES.rglob("*.json"))

print("=" * 65)
print("DIAGNÓSTICO DE ESTRUCTURA DEL TIPO DE DECLARACIÓN")
print("=" * 65)

for archivo in archivos:

    try:
        with open(archivo, "r", encoding="utf-8") as f:
            contenido = json.load(f)

    except Exception:
        continue

    if isinstance(contenido, list):
        registros = contenido

    elif isinstance(contenido, dict):
        registros = contenido.get("declaraciones", [])

        if not isinstance(registros, list):
            registros = []

    else:
        continue

    for registro in registros:

        total_declaraciones += 1

        explorar(registro)


print("\nArchivos JSON:", len(archivos))
print("Declaraciones examinadas:", total_declaraciones)

print("\n--- RUTAS DE CAMPOS CANDIDATOS ---")

for ruta, cantidad in frecuencia_rutas.most_common():

    print(f"\nRuta: {ruta}")
    print("Frecuencia:", cantidad)

    if ruta in valores_candidatos:

        print("Valores encontrados:")

        for valor, frecuencia in valores_candidatos[ruta].most_common(15):
            print(f"  {valor}: {frecuencia}")


print("\n--- VALORES DE SUBCAMPOS ---")

for ruta, contador in valores_candidatos.items():

    if ruta in frecuencia_rutas:
        continue

    print(f"\nRuta: {ruta}")

    for valor, frecuencia in contador.most_common(15):
        print(f"  {valor}: {frecuencia}")


print("\n" + "=" * 65)
print("DIAGNÓSTICO FINALIZADO")
print("=" * 65)
