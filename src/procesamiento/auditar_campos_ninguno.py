
import json
from pathlib import Path
from collections import Counter

# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "datos" / "originales"
RESULTADOS_DIR = BASE_DIR / "resultados"

RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

ARCHIVO_INFORME = RESULTADOS_DIR / "informe_campos_ninguno.txt"

# Secciones que serán auditadas.
SECCIONES = {
    "bienes_inmuebles": (
        "situacionPatrimonial",
        "bienesInmuebles"
    ),
    "vehiculos": (
        "situacionPatrimonial",
        "vehiculos"
    ),
    "bienes_muebles": (
        "situacionPatrimonial",
        "bienesMuebles"
    ),
    "inversiones": (
        "situacionPatrimonial",
        "inversiones"
    ),
    "adeudos": (
        "situacionPatrimonial",
        "adeudos"
    ),
    "prestamos": (
        "situacionPatrimonial",
        "prestamoOComodato"
    ),
    "participaciones": (
        "interes",
        "participacion"
    ),
    "apoyos": (
        "interes",
        "apoyos"
    ),
    "beneficios_privados": (
        "interes",
        "beneficiosPrivados"
    ),
    "fideicomisos": (
        "interes",
        "fideicomisos"
    )
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def obtener_ruta(datos, ruta):
    """
    Obtiene un valor recorriendo una ruta de claves.
    """

    actual = datos

    for clave in ruta:
        if not isinstance(actual, dict):
            return None

        actual = actual.get(clave)

    return actual


def clasificar_valor(valor):
    """
    Clasifica el contenido del campo ninguno.
    """

    if valor is None:
        return "null"

    if isinstance(valor, bool):
        return "true" if valor else "false"

    if isinstance(valor, str):
        if not valor.strip():
            return "cadena_vacia"

        return "otro_valor: " + valor.strip()

    if isinstance(valor, (int, float)):
        return "otro_valor: " + str(valor)

    return "otro_tipo: " + type(valor).__name__


# ============================================================
# INICIALIZAR CONTADORES
# ============================================================

estadisticas = {}

for nombre in SECCIONES:
    estadisticas[nombre] = {
        "seccion_dict": 0,
        "seccion_ausente_o_invalida": 0,
        "campo_presente": 0,
        "campo_ausente": 0,
        "valores": Counter(),
        "elementos_no_vacios": 0
    }

total_archivos = 0
total_registros = 0
total_errores = 0


# ============================================================
# PROCESAMIENTO DE ARCHIVOS
# ============================================================

archivos = sorted(DATA_DIR.rglob("*.json"))

print("=" * 65)
print("AUDITORÍA DE CAMPOS NINGUNO - PDN")
print("=" * 65)

print(f"Archivos encontrados: {len(archivos)}")

for archivo in archivos:

    total_archivos += 1

    try:
        with open(archivo, "r", encoding="utf-8") as f:
            contenido = json.load(f)

        # Algunos archivos pueden contener una lista de registros
        # y otros un único registro.
        if isinstance(contenido, list):
            registros = contenido

        elif isinstance(contenido, dict):
            registros = contenido.get("data", [])

            if not isinstance(registros, list):
                registros = [contenido]

        else:
            continue

        for registro in registros:

            if not isinstance(registro, dict):
                continue

            total_registros += 1

            declaracion = registro.get("declaracion", {})

            if not isinstance(declaracion, dict):
                declaracion = {}

            for nombre, ruta in SECCIONES.items():

                # Obtener la sección correspondiente.
                seccion = obtener_ruta(declaracion, ruta)

                if not isinstance(seccion, dict):
                    estadisticas[nombre][
                        "seccion_ausente_o_invalida"
                    ] += 1
                    continue

                estadisticas[nombre]["seccion_dict"] += 1

                # Verificar si existe la clave ninguno.
                if "ninguno" in seccion:

                    estadisticas[nombre]["campo_presente"] += 1

                    valor = seccion.get("ninguno")

                    clasificacion = clasificar_valor(valor)

                    estadisticas[nombre]["valores"][
                        clasificacion
                    ] += 1

                else:
                    estadisticas[nombre]["campo_ausente"] += 1

                # Comprobar si existen elementos registrados.
                claves_elementos = [
                    clave for clave in seccion
                    if clave != "ninguno"
                ]

                tiene_elementos = False

                for clave in claves_elementos:

                    elementos = seccion.get(clave)

                    if isinstance(elementos, list):
                        if len(elementos) > 0:
                            tiene_elementos = True

                    elif isinstance(elementos, dict):
                        if len(elementos) > 0:
                            tiene_elementos = True

                if tiene_elementos:
                    estadisticas[nombre][
                        "elementos_no_vacios"
                    ] += 1

    except Exception as e:

        total_errores += 1

        print(f"Error en {archivo.name}: {e}")


# ============================================================
# GENERAR INFORME
# ============================================================

lineas = []

lineas.append("=" * 65)
lineas.append("INFORME DE AUDITORÍA DE CAMPOS NINGUNO")
lineas.append("PLATAFORMA DIGITAL NACIONAL")
lineas.append("=" * 65)

lineas.append("")
lineas.append(f"Archivos procesados: {total_archivos}")
lineas.append(f"Registros analizados: {total_registros}")
lineas.append(f"Errores: {total_errores}")

lineas.append("")
lineas.append("=" * 65)
lineas.append("RESULTADOS POR SECCIÓN")
lineas.append("=" * 65)

for nombre, datos in estadisticas.items():

    lineas.append("")
    lineas.append("-" * 55)
    lineas.append(f"SECCIÓN: {nombre.upper()}")
    lineas.append("-" * 55)

    lineas.append(
        f"Secciones tipo diccionario: {datos['seccion_dict']}"
    )

    lineas.append(
        "Secciones ausentes o inválidas: "
        f"{datos['seccion_ausente_o_invalida']}"
    )

    lineas.append(
        f"Campo ninguno presente: {datos['campo_presente']}"
    )

    lineas.append(
        f"Campo ninguno ausente: {datos['campo_ausente']}"
    )

    lineas.append(
        f"Registros con elementos no vacíos: "
        f"{datos['elementos_no_vacios']}"
    )

    lineas.append("")
    lineas.append("Distribución de valores del campo ninguno:")

    if datos["valores"]:

        for valor, cantidad in datos["valores"].most_common():

            porcentaje = (
                cantidad / total_registros * 100
                if total_registros > 0 else 0
            )

            lineas.append(
                f"  {valor}: {cantidad} ({porcentaje:.2f}%)"
            )

    else:
        lineas.append("  No se encontraron valores.")

# ============================================================
# GUARDAR Y MOSTRAR INFORME
# ============================================================

informe = "\n".join(lineas)

with open(ARCHIVO_INFORME, "w", encoding="utf-8") as f:
    f.write(informe)

print("")
print(informe)

print("")
print("=" * 65)
print("AUDITORÍA FINALIZADA")
print("=" * 65)

print(f"Informe guardado en: {ARCHIVO_INFORME}")
