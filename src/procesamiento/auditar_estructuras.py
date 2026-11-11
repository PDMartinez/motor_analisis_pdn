import json
from pathlib import Path
from collections import Counter, defaultdict


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "datos" / "originales"

SECCIONES = {
    "inmuebles": "situacionPatrimonial.bienesInmuebles",
    "vehiculos": "situacionPatrimonial.vehiculos",
    "bienes_muebles": "situacionPatrimonial.bienesMuebles",
    "inversiones": "situacionPatrimonial.inversiones",
    "adeudos": "situacionPatrimonial.adeudos",
    "prestamos": "situacionPatrimonial.prestamoOComodato",
    "participaciones": "interes.participacion",
    "apoyos": "interes.apoyos",
    "beneficios": "interes.beneficiosPrivados",
    "fideicomisos": "interes.fideicomisos"
}


# ==========================================================
# FUNCIONES
# ==========================================================

def obtener_ruta(objeto, ruta):
    valor = objeto

    for clave in ruta.split("."):
        if isinstance(valor, dict):
            valor = valor.get(clave)
        else:
            return None

        if valor is None:
            return None

    return valor


def obtener_claves(objeto, nivel=0, max_nivel=3):
    """
    Obtiene únicamente los nombres de las claves.
    No muestra información personal ni valores.
    """

    claves = set()

    if nivel >= max_nivel:
        return claves

    if isinstance(objeto, dict):

        for clave, valor in objeto.items():
            claves.add(str(clave))

            if isinstance(valor, (dict, list)):
                claves.update(
                    obtener_claves(valor, nivel + 1, max_nivel)
                )

    elif isinstance(objeto, list):

        for elemento in objeto[:3]:
            claves.update(
                obtener_claves(elemento, nivel + 1, max_nivel)
            )

    return claves


def procesar_archivo(archivo, estadisticas, ejemplos):

    try:
        with open(archivo, "r", encoding="utf-8-sig") as f:
            contenido = json.load(f)

    except Exception:
        return

    if isinstance(contenido, list):
        declaraciones = contenido

    elif isinstance(contenido, dict):
        declaraciones = [contenido]

    else:
        return

    for declaracion in declaraciones:

        if not isinstance(declaracion, dict):
            continue

        datos = declaracion.get("declaracion", {})

        if not isinstance(datos, dict):
            continue

        for nombre, ruta in SECCIONES.items():

            valor = obtener_ruta(datos, ruta)

            if valor is None:
                tipo = "AUSENTE"

            elif isinstance(valor, list):
                tipo = "LISTA"

            elif isinstance(valor, dict):
                tipo = "DICCIONARIO"

            else:
                tipo = type(valor).__name__.upper()

            estadisticas[nombre][tipo] += 1

            if valor is not None and nombre not in ejemplos:

                ejemplos[nombre] = {
                    "tipo": tipo,
                    "claves": sorted(obtener_claves(valor))
                }


# ==========================================================
# EJECUCIÓN
# ==========================================================

def auditar():

    print("=" * 65)
    print("AUDITORÍA DE ESTRUCTURAS JSON - PDN")
    print("=" * 65)

    archivos = sorted(DATA_DIR.rglob("*.json"))

    if not archivos:
        print("No se encontraron archivos JSON.")
        return

    estadisticas = defaultdict(Counter)
    ejemplos = {}

    for indice, archivo in enumerate(archivos, start=1):

        print(
            f"\rAnalizando archivo {indice}/{len(archivos)}",
            end="",
            flush=True
        )

        procesar_archivo(
            archivo,
            estadisticas,
            ejemplos
        )

    print("\n\nRESULTADOS POR SECCIÓN")
    print("-" * 65)

    for nombre in SECCIONES:

        print(f"\nSECCIÓN: {nombre.upper()}")

        print("Distribución de estructuras:")

        for tipo, cantidad in estadisticas[nombre].most_common():
            print(f"  {tipo}: {cantidad}")

        if nombre in ejemplos:

            print("Claves encontradas:")

            for clave in ejemplos[nombre]["claves"]:
                print(f"  - {clave}")

        else:
            print("No se encontró información en esta sección.")

    print("\n" + "=" * 65)
    print("AUDITORÍA FINALIZADA")
    print("=" * 65)


if __name__ == "__main__":
    auditar()