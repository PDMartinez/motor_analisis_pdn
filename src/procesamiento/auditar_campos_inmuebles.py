
import json
import csv
from pathlib import Path
from collections import Counter, defaultdict


# ============================================================
# 1. CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "datos" / "originales"
RESULTADOS_DIR = BASE_DIR / "resultados"

ARCHIVO_REPORTE = (
    RESULTADOS_DIR / "auditoria_campos_inmuebles.txt"
)

ARCHIVO_CSV = (
    RESULTADOS_DIR / "auditoria_campos_inmuebles_campos.csv"
)

RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

# Total de elementos identificado en la auditoría estructural.
TOTAL_INMUEBLES_ESPERADO = 11264


# ============================================================
# 2. FUNCIONES AUXILIARES
# ============================================================

def obtener_tipo(valor):
    """Identifica el tipo de dato de un campo."""

    if valor is None:
        return "null"

    if isinstance(valor, bool):
        return "boolean"

    if isinstance(valor, str):
        return "string"

    if isinstance(valor, int):
        return "integer"

    if isinstance(valor, float):
        return "float"

    if isinstance(valor, list):
        return "list"

    if isinstance(valor, dict):
        return "dict"

    return type(valor).__name__


def obtener_declaraciones(contenido):
    """
    Extrae las declaraciones desde los archivos JSON.

    La estructura esperada puede contener:
        registro
          └── declaracion
                ├── tipoDeclaracion
                └── situacionPatrimonial
    """

    if isinstance(contenido, list):
        registros = contenido

    elif isinstance(contenido, dict):

        registros = None

        for clave in ["declaraciones", "data", "datos"]:

            if isinstance(contenido.get(clave), list):
                registros = contenido[clave]
                break

        if registros is None:
            registros = [contenido]

    else:
        return []

    declaraciones = []

    for registro in registros:

        if not isinstance(registro, dict):
            continue

        declaracion = registro.get("declaracion")

        if isinstance(declaracion, dict):
            declaraciones.append(declaracion)

        else:
            # Compatibilidad con registros que ya contienen
            # directamente los campos de la declaración.
            declaraciones.append(registro)

    return declaraciones


def obtener_inmuebles(declaracion):
    """
    Obtiene los bienes inmuebles de una declaración.
    """

    situacion = declaracion.get("situacionPatrimonial", {})

    if not isinstance(situacion, dict):
        return []

    seccion = situacion.get("bienesInmuebles", {})

    if not isinstance(seccion, dict):
        return []

    inmuebles = seccion.get("bienInmueble", [])

    if isinstance(inmuebles, list):

        return [
            item for item in inmuebles
            if isinstance(item, dict)
        ]

    if isinstance(inmuebles, dict):
        return [inmuebles]

    return []


# ============================================================
# 3. ESTRUCTURAS DE ACUMULACIÓN
# ============================================================

estadisticas = defaultdict(lambda: {
    "presente": 0,
    "ausente": 0,
    "tipos": Counter(),
    "claves_internas": Counter()
})

total_archivos = 0
total_declaraciones = 0
total_inmuebles = 0
declaraciones_con_inmuebles = 0
errores_lectura = 0
registros_invalidos = 0

tipos_declaracion = Counter()


# ============================================================
# 4. PROCESAMIENTO DE LOS JSON
# ============================================================

archivos = sorted(DATA_DIR.rglob("*.json"))

print("=" * 70)
print("AUDITORÍA DE CAMPOS INTERNOS DE BIENES INMUEBLES")
print("=" * 70)

for archivo in archivos:

    total_archivos += 1

    try:

        with open(archivo, "r", encoding="utf-8") as f:
            contenido = json.load(f)

        declaraciones = obtener_declaraciones(contenido)

    except Exception as e:

        errores_lectura += 1

        print(
            f"Error al leer {archivo.name}: {e}"
        )

        continue

    for declaracion in declaraciones:

        if not isinstance(declaracion, dict):

            registros_invalidos += 1
            continue

        total_declaraciones += 1

        # Tipo de declaración.
        tipo = declaracion.get(
            "tipoDeclaracion",
            "NO_IDENTIFICADO"
        )

        tipos_declaracion[str(tipo)] += 1

        # Obtener inmuebles.
        inmuebles = obtener_inmuebles(declaracion)

        if len(inmuebles) > 0:
            declaraciones_con_inmuebles += 1

        # Analizar cada inmueble.
        for inmueble in inmuebles:

            total_inmuebles += 1

            # Analizar todos los campos presentes.
            for campo, valor in inmueble.items():

                estadisticas[campo]["presente"] += 1

                tipo_valor = obtener_tipo(valor)

                estadisticas[campo]["tipos"][tipo_valor] += 1

                # Registrar las claves internas de los objetos.
                # No se guardan ni se muestran sus valores.
                if isinstance(valor, dict):

                    for clave_interna in valor.keys():

                        estadisticas[campo][
                            "claves_internas"
                        ][str(clave_interna)] += 1


# ============================================================
# 5. CALCULAR AUSENCIAS Y PORCENTAJES
# ============================================================

for campo, datos in estadisticas.items():

    datos["ausente"] = (
        total_inmuebles - datos["presente"]
    )


# ============================================================
# 6. GENERAR REPORTE TXT
# ============================================================

lineas = []

lineas.append("=" * 75)
lineas.append(
    "AUDITORÍA DE CAMPOS INTERNOS DE BIENES INMUEBLES"
)
lineas.append("=" * 75)

lineas.append("")
lineas.append("1. RESUMEN GENERAL")
lineas.append("-" * 75)

lineas.append(
    f"Archivos JSON encontrados: {total_archivos}"
)

lineas.append(
    f"Declaraciones procesadas: {total_declaraciones}"
)

lineas.append(
    f"Declaraciones con inmuebles: {declaraciones_con_inmuebles}"
)

lineas.append(
    f"Total de inmuebles analizados: {total_inmuebles}"
)

lineas.append(
    f"Registros inválidos: {registros_invalidos}"
)

lineas.append(
    f"Errores de lectura: {errores_lectura}"
)

lineas.append(
    f"Total esperado según auditoría anterior: "
    f"{TOTAL_INMUEBLES_ESPERADO}"
)

lineas.append(
    f"Diferencia respecto al total esperado: "
    f"{total_inmuebles - TOTAL_INMUEBLES_ESPERADO}"
)


# ============================================================
# 7. DISTRIBUCIÓN POR TIPO DE DECLARACIÓN
# ============================================================

lineas.append("")
lineas.append("2. DECLARACIONES POR TIPO")
lineas.append("-" * 75)

for tipo, cantidad in tipos_declaracion.most_common():

    lineas.append(
        f"{tipo}: {cantidad}"
    )


# ============================================================
# 8. FRECUENCIA DE CAMPOS
# ============================================================

lineas.append("")
lineas.append("3. FRECUENCIA DE CAMPOS")
lineas.append("-" * 75)

for campo, datos in sorted(
    estadisticas.items(),
    key=lambda x: x[1]["presente"],
    reverse=True
):

    porcentaje = (
        datos["presente"] / total_inmuebles * 100
        if total_inmuebles > 0 else 0
    )

    lineas.append("")
    lineas.append(f"Campo: {campo}")

    lineas.append(
        f"  Presente: {datos['presente']}"
    )

    lineas.append(
        f"  Ausente: {datos['ausente']}"
    )

    lineas.append(
        f"  Porcentaje de presencia: {porcentaje:.2f}%"
    )

    tipos = ", ".join(
        f"{nombre}: {cantidad}"
        for nombre, cantidad in datos["tipos"].most_common()
    )

    lineas.append(
        f"  Tipos de datos: {tipos}"
    )

    if datos["claves_internas"]:

        claves = ", ".join(
            f"{nombre}: {cantidad}"
            for nombre, cantidad
            in datos["claves_internas"].most_common()
        )

        lineas.append(
            f"  Claves internas de objetos: {claves}"
        )


# ============================================================
# 9. NOTAS METODOLÓGICAS
# ============================================================

lineas.append("")
lineas.append("4. NOTAS METODOLÓGICAS")
lineas.append("-" * 75)

lineas.append(
    "La presencia de un campo indica que aparece en la estructura JSON."
)

lineas.append(
    "La ausencia no implica que el declarante carezca de ese bien o dato."
)

lineas.append(
    "Los tipos de datos describen la estructura técnica, "
    "no la validez semántica de la información."
)

lineas.append(
    "No se exportaron nombres, identificadores ni valores individuales."
)

lineas.append(
    "Esta auditoría no modifica los archivos JSON originales."
)

lineas.append(
    "El total esperado se utiliza como control de consistencia "
    "con la auditoría estructural anterior."
)

with open(
    ARCHIVO_REPORTE,
    "w",
    encoding="utf-8"
) as f:

    f.write("\n".join(lineas))


# ============================================================
# 10. GENERAR ARCHIVO CSV
# ============================================================

with open(
    ARCHIVO_CSV,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    escritor = csv.writer(f)

    escritor.writerow([
        "campo",
        "presente",
        "ausente",
        "porcentaje_presencia",
        "tipos_datos",
        "claves_internas"
    ])

    for campo, datos in sorted(
        estadisticas.items(),
        key=lambda x: x[1]["presente"],
        reverse=True
    ):

        porcentaje = (
            datos["presente"] / total_inmuebles * 100
            if total_inmuebles > 0 else 0
        )

        tipos = "; ".join(
            f"{nombre}: {cantidad}"
            for nombre, cantidad in datos["tipos"].most_common()
        )

        claves = "; ".join(
            f"{nombre}: {cantidad}"
            for nombre, cantidad
            in datos["claves_internas"].most_common()
        )

        escritor.writerow([
            campo,
            datos["presente"],
            datos["ausente"],
            round(porcentaje, 2),
            tipos,
            claves
        ])


# ============================================================
# 11. RESULTADO FINAL
# ============================================================

print("\nAUDITORÍA FINALIZADA")
print("=" * 70)

print(f"Archivos procesados: {total_archivos}")

print(
    f"Declaraciones procesadas: {total_declaraciones}"
)

print(
    f"Declaraciones con inmuebles: {declaraciones_con_inmuebles}"
)

print(
    f"Inmuebles analizados: {total_inmuebles}"
)

print(
    f"Campos diferentes identificados: {len(estadisticas)}"
)

print(
    f"Errores de lectura: {errores_lectura}"
)

print(
    f"Registros inválidos: {registros_invalidos}"
)

if total_inmuebles == TOTAL_INMUEBLES_ESPERADO:

    print("\nCONTROL DE CONSISTENCIA: CORRECTO")

else:

    print("\nCONTROL DE CONSISTENCIA: REVISAR")

    print(
        "El total de inmuebles no coincide con "
        "la auditoría estructural anterior."
    )

print("\nArchivos generados:")
print(ARCHIVO_REPORTE)
print(ARCHIVO_CSV)
