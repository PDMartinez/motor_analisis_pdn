
import json
from pathlib import Path
from collections import Counter, defaultdict
import csv

# ============================================================
# 1. CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

CARPETA_ORIGINALES = BASE_DIR / "datos" / "originales"

CARPETA_RESULTADOS = BASE_DIR / "resultados" / "auditoria_ingresos"

CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)

ARCHIVO_REPORTE = CARPETA_RESULTADOS / "reporte_ingresos.txt"
ARCHIVO_CSV = CARPETA_RESULTADOS / "estructuras_ingresos.csv"

# Palabras que identifican posibles campos relacionados
# con ingresos y remuneraciones.
TERMINOS_INGRESOS = [
    "ingreso",
    "remuneracion",
    "remuneración",
    "sueldo",
    "salario",
    "percepcion",
    "percepción",
    "honorario"
]


# ============================================================
# 2. IDENTIFICAR DECLARACIONES
# ============================================================

def obtener_declaraciones(objeto):

    if isinstance(objeto, dict):

        if "metadata" in objeto and "declaracion" in objeto:
            yield objeto
            return

        for valor in objeto.values():
            yield from obtener_declaraciones(valor)

    elif isinstance(objeto, list):

        for elemento in objeto:
            yield from obtener_declaraciones(elemento)


# ============================================================
# 3. IDENTIFICAR TIPOS DE VALORES
# ============================================================

def obtener_tipo(valor):

    if isinstance(valor, dict):
        return "diccionario"

    if isinstance(valor, list):
        return "lista"

    if isinstance(valor, bool):
        return "booleano"

    if isinstance(valor, (int, float)):
        return "numero"

    if isinstance(valor, str):
        return "texto"

    if valor is None:
        return "nulo"

    return type(valor).__name__


# ============================================================
# 4. RECORRER LA ESTRUCTURA JSON
# ============================================================

def recorrer_json(objeto, ruta=""):

    if isinstance(objeto, dict):

        for clave, valor in objeto.items():

            nueva_ruta = (
                f"{ruta}.{clave}" if ruta else clave
            )

            yield clave, valor, nueva_ruta

            yield from recorrer_json(
                valor,
                nueva_ruta
            )

    elif isinstance(objeto, list):

        for elemento in objeto:

            nueva_ruta = f"{ruta}[*]"

            yield from recorrer_json(
                elemento,
                nueva_ruta
            )


# ============================================================
# 5. DESCRIBIR LA ESTRUCTURA DE UN CAMPO
# ============================================================

def describir_estructura(valor):

    if isinstance(valor, dict):

        claves = sorted(str(clave) for clave in valor.keys())

        return "Claves: " + ", ".join(claves[:30])

    if isinstance(valor, list):

        if not valor:
            return "Lista vacía"

        primer_elemento = valor[0]

        if isinstance(primer_elemento, dict):

            claves = sorted(
                str(clave)
                for clave in primer_elemento.keys()
            )

            return (
                "Lista de objetos. Claves del primer elemento: "
                + ", ".join(claves[:30])
            )

        return (
            "Lista de elementos tipo: "
            + obtener_tipo(primer_elemento)
        )

    return "Campo simple"


# ============================================================
# 6. AUDITORÍA PRINCIPAL
# ============================================================

def auditar():

    if not CARPETA_ORIGINALES.exists():

        raise FileNotFoundError(
            f"No existe la carpeta: {CARPETA_ORIGINALES}"
        )

    archivos = list(
        CARPETA_ORIGINALES.rglob("*.json")
    )

    print("\n========================================")
    print("AUDITORÍA DE ESTRUCTURAS DE INGRESOS")
    print("========================================")

    print(f"Archivos encontrados: {len(archivos):,}")

    # Estadísticas generales
    total_declaraciones = 0
    archivos_procesados = 0
    errores = []

    # Estadísticas de campos
    ocurrencias = Counter()
    tipos_valores = defaultdict(Counter)
    tipos_declaracion = defaultdict(Counter)
    estructuras = defaultdict(Counter)

    # ========================================================
    # PROCESAR ARCHIVOS
    # ========================================================

    for indice, archivo in enumerate(archivos, start=1):

        try:

            with open(
                archivo,
                "r",
                encoding="utf-8"
            ) as f:

                datos = json.load(f)

            declaraciones = list(
                obtener_declaraciones(datos)
            )

            archivos_procesados += 1

            for declaracion in declaraciones:

                total_declaraciones += 1

                metadata = declaracion.get(
                    "metadata", {}
                )

                tipo_declaracion = (
                    metadata.get("tipo", "NO ESPECIFICADO")
                    if isinstance(metadata, dict)
                    else "NO ESPECIFICADO"
                )

                contenido = declaracion.get(
                    "declaracion", {}
                )

                for clave, valor, ruta in recorrer_json(
                    contenido
                ):

                    clave_normalizada = str(clave).lower()

                    coincide = any(
                        termino in clave_normalizada
                        for termino in TERMINOS_INGRESOS
                    )

                    if not coincide:
                        continue

                    clave_estadistica = ruta

                    ocurrencias[clave_estadistica] += 1

                    tipo_valor = obtener_tipo(valor)

                    tipos_valores[clave_estadistica][tipo_valor] += 1

                    tipos_declaracion[clave_estadistica][
                        str(tipo_declaracion)
                    ] += 1

                    estructuras[clave_estadistica][
                        describir_estructura(valor)
                    ] += 1

            if indice % 50 == 0:
                print(
                    f"Archivos revisados: {indice:,}/{len(archivos):,}"
                )

        except Exception as error:

            errores.append(
                f"{archivo.name}: {str(error)}"
            )

    # ========================================================
    # GENERAR REPORTE
    # ========================================================

    with open(
        ARCHIVO_REPORTE,
        "w",
        encoding="utf-8"
    ) as reporte:

        reporte.write(
            "AUDITORÍA DE ESTRUCTURAS DE INGRESOS - PDN\n"
        )

        reporte.write("=" * 65 + "\n\n")

        reporte.write(
            f"Archivos encontrados: {len(archivos):,}\n"
        )

        reporte.write(
            f"Archivos procesados: {archivos_procesados:,}\n"
        )

        reporte.write(
            f"Declaraciones revisadas: {total_declaraciones:,}\n"
        )

        reporte.write(
            f"Errores: {len(errores):,}\n\n"
        )

        reporte.write("=" * 65 + "\n")
        reporte.write("CAMPOS RELACIONADOS CON INGRESOS\n")
        reporte.write("=" * 65 + "\n\n")

        for ruta, cantidad in ocurrencias.most_common():

            reporte.write(f"\nRUTA: {ruta}\n")
            reporte.write(f"OCURRENCIAS: {cantidad:,}\n")

            reporte.write(
                "TIPOS DE VALORES:\n"
            )

            for tipo, total in tipos_valores[ruta].items():

                reporte.write(
                    f"  - {tipo}: {total:,}\n"
                )

            reporte.write(
                "TIPOS DE DECLARACIONES:\n"
            )

            for tipo, total in tipos_declaracion[ruta].items():

                reporte.write(
                    f"  - {tipo}: {total:,}\n"
                )

            reporte.write(
                "ESTRUCTURAS DETECTADAS:\n"
            )

            for estructura, total in estructuras[ruta].most_common(5):

                reporte.write(
                    f"  - {estructura} ({total:,})\n"
                )

        reporte.write("\n\nERRORES DE LECTURA\n")
        reporte.write("=" * 65 + "\n")

        for error in errores:
            reporte.write(error + "\n")

    # ========================================================
    # GENERAR CSV
    # ========================================================

    with open(
        ARCHIVO_CSV,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as archivo_csv:

        escritor = csv.writer(archivo_csv)

        escritor.writerow([
            "ruta",
            "ocurrencias",
            "tipos_valores",
            "tipos_declaraciones",
            "estructuras"
        ])

        for ruta, cantidad in ocurrencias.most_common():

            escritor.writerow([
                ruta,
                cantidad,
                str(dict(tipos_valores[ruta])),
                str(dict(tipos_declaracion[ruta])),
                str(dict(estructuras[ruta]))
            ])

    # ========================================================
    # RESULTADO FINAL
    # ========================================================

    print("\n========================================")
    print("AUDITORÍA FINALIZADA")
    print("========================================")

    print(f"Archivos procesados: {archivos_procesados:,}")
    print(f"Declaraciones revisadas: {total_declaraciones:,}")
    print(f"Errores: {len(errores):,}")
    print(f"Campos identificados: {len(ocurrencias):,}")

    print("\nArchivos generados:")

    print(ARCHIVO_REPORTE)
    print(ARCHIVO_CSV)


# ============================================================
# 7. EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    auditar()
