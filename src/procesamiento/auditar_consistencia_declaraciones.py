
import json
from pathlib import Path
from collections import Counter, defaultdict

# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "datos" / "originales"
RESULTADOS_DIR = BASE_DIR / "resultados"

RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

ARCHIVO_INFORME = (
    RESULTADOS_DIR / "informe_consistencia_declaraciones.txt"
)

# Cada sección contiene la clave de sus elementos.
SECCIONES = {
    "bienes_inmuebles": (
        "situacionPatrimonial",
        "bienesInmuebles",
        "bienInmueble"
    ),
    "vehiculos": (
        "situacionPatrimonial",
        "vehiculos",
        "vehiculo"
    ),
    "bienes_muebles": (
        "situacionPatrimonial",
        "bienesMuebles",
        "bienMueble"
    ),
    "inversiones": (
        "situacionPatrimonial",
        "inversiones",
        "inversion"
    ),
    "adeudos": (
        "situacionPatrimonial",
        "adeudos",
        "adeudo"
    ),
    "prestamos": (
        "situacionPatrimonial",
        "prestamoOComodato",
        "prestamo"
    ),
    "participaciones": (
        "interes",
        "participacion",
        "participacion"
    ),
    "apoyos": (
        "interes",
        "apoyos",
        "apoyo"
    ),
    "beneficios_privados": (
        "interes",
        "beneficiosPrivados",
        "beneficio"
    ),
    "fideicomisos": (
        "interes",
        "fideicomisos",
        "fideicomiso"
    )
}

MAX_EJEMPLOS = 10


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


def tiene_contenido(valor):
    """
    Determina si un valor contiene información real.

    No considera como contenido:
    - None
    - Cadenas vacías
    - Diccionarios vacíos
    - Listas vacías

    Los valores numéricos, incluyendo cero, y los booleanos
    se consideran valores presentes.
    """

    if valor is None:
        return False

    if isinstance(valor, str):
        return bool(valor.strip())

    if isinstance(valor, dict):
        return any(
            tiene_contenido(v)
            for v in valor.values()
        )

    if isinstance(valor, list):
        return any(
            tiene_contenido(elemento)
            for elemento in valor
        )

    return True


def contar_elementos(contenedor, clave_elemento):
    """
    Cuenta los elementos con contenido de una sección.

    Si la colección es una lista, cuenta sus elementos
    que contienen información.

    Si es un diccionario, lo considera un único elemento
    cuando tiene contenido.
    """

    if not isinstance(contenedor, dict):
        return 0

    elementos = contenedor.get(clave_elemento)

    if isinstance(elementos, list):

        return sum(
            1 for elemento in elementos
            if tiene_contenido(elemento)
        )

    if isinstance(elementos, dict):

        return 1 if tiene_contenido(elementos) else 0

    return 0


def obtener_registros(contenido):
    """
    Admite archivos JSON que contienen una lista de registros,
    un objeto con clave data o un único registro.
    """

    if isinstance(contenido, list):
        return contenido

    if isinstance(contenido, dict):

        if isinstance(contenido.get("data"), list):
            return contenido["data"]

        return [contenido]

    return []


# ============================================================
# INICIALIZAR ESTADÍSTICAS
# ============================================================

estadisticas = {}

for nombre in SECCIONES:

    estadisticas[nombre] = {
        "total": 0,
        "true_sin_elementos": 0,
        "true_con_elementos": 0,
        "false_sin_elementos": 0,
        "false_con_elementos": 0,
        "campo_ausente": 0,
        "valor_no_booleano": 0,
        "seccion_invalida": 0,
        "otros_valores": Counter(),
        "ejemplos": defaultdict(list)
    }

total_archivos = 0
total_registros = 0
total_errores = 0


# ============================================================
# PROCESAMIENTO DE ARCHIVOS
# ============================================================

archivos = sorted(DATA_DIR.rglob("*.json"))

print("=" * 65)
print("AUDITORÍA DE CONSISTENCIA DE DECLARACIONES - PDN")
print("=" * 65)

print(f"Archivos encontrados: {len(archivos)}")

for archivo in archivos:

    total_archivos += 1

    try:

        with open(archivo, "r", encoding="utf-8") as f:
            contenido = json.load(f)

        registros = obtener_registros(contenido)

        for posicion, registro in enumerate(registros, start=1):

            if not isinstance(registro, dict):
                continue

            total_registros += 1

            declaracion = registro.get("declaracion", {})

            if not isinstance(declaracion, dict):
                declaracion = {}

            # Referencia técnica para localizar el registro.
            # No guardamos nombres ni datos personales.
            referencia = (
                f"{archivo.relative_to(DATA_DIR)}"
                f" | registro {posicion}"
            )

            for nombre, ruta in SECCIONES.items():

                datos_seccion = estadisticas[nombre]

                ruta_seccion = ruta[:2]
                clave_elemento = ruta[2]

                seccion = obtener_ruta(
                    declaracion,
                    ruta_seccion
                )

                if not isinstance(seccion, dict):

                    datos_seccion["seccion_invalida"] += 1
                    continue

                datos_seccion["total"] += 1

                # Obtener la cantidad real de elementos.
                cantidad = contar_elementos(
                    seccion,
                    clave_elemento
                )

                tiene_elementos = cantidad > 0

                # Obtener el campo ninguno.
                if "ninguno" not in seccion:

                    datos_seccion["campo_ausente"] += 1
                    continue

                valor_ninguno = seccion["ninguno"]

                # Solo se clasifican como válidos los booleanos.
                if not isinstance(valor_ninguno, bool):

                    datos_seccion["valor_no_booleano"] += 1

                    tipo_valor = type(valor_ninguno).__name__

                    datos_seccion["otros_valores"][tipo_valor] += 1

                    continue

                # ------------------------------------------------
                # CLASIFICAR CONSISTENCIA
                # ------------------------------------------------

                if valor_ninguno is True and not tiene_elementos:

                    datos_seccion["true_sin_elementos"] += 1

                elif valor_ninguno is True and tiene_elementos:

                    datos_seccion["true_con_elementos"] += 1

                    categoria = "true_con_elementos"

                elif valor_ninguno is False and not tiene_elementos:

                    datos_seccion["false_sin_elementos"] += 1

                    categoria = "false_sin_elementos"

                else:

                    datos_seccion["false_con_elementos"] += 1

                    categoria = "false_con_elementos"

                # Guardar hasta 10 ejemplos de cada inconsistencia.
                if valor_ninguno is True and tiene_elementos:

                    categoria = "true_con_elementos"

                elif valor_ninguno is False and not tiene_elementos:

                    categoria = "false_sin_elementos"

                else:
                    categoria = None

                if categoria is not None:

                    ejemplos = datos_seccion["ejemplos"][categoria]

                    if len(ejemplos) < MAX_EJEMPLOS:

                        ejemplos.append(
                            f"{referencia} | "
                            f"Cantidad de elementos: {cantidad}"
                        )

    except Exception as e:

        total_errores += 1

        print(f"Error en {archivo.name}: {e}")


# ============================================================
# GENERAR INFORME
# ============================================================

lineas = []

lineas.append("=" * 65)
lineas.append("INFORME DE CONSISTENCIA DE DECLARACIONES")
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
    lineas.append("-" * 60)
    lineas.append(f"SECCIÓN: {nombre.upper()}")
    lineas.append("-" * 60)

    total = datos["total"]

    lineas.append(f"Registros con sección válida: {total}")

    lineas.append(
        f"ninguno = true, sin elementos: "
        f"{datos['true_sin_elementos']}"
    )

    lineas.append(
        f"ninguno = true, con elementos: "
        f"{datos['true_con_elementos']}"
    )

    lineas.append(
        f"ninguno = false, sin elementos: "
        f"{datos['false_sin_elementos']}"
    )

    lineas.append(
        f"ninguno = false, con elementos: "
        f"{datos['false_con_elementos']}"
    )

    lineas.append(
        f"Campo ninguno ausente: {datos['campo_ausente']}"
    )

    lineas.append(
        f"Valor ninguno no booleano: "
        f"{datos['valor_no_booleano']}"
    )

    lineas.append(
        f"Sección ausente o inválida: "
        f"{datos['seccion_invalida']}"
    )

    # Calcular posibles inconsistencias.
    inconsistencias = (
        datos["true_con_elementos"]
        + datos["false_sin_elementos"]
    )

    porcentaje = (
        inconsistencias / total * 100
        if total > 0 else 0
    )

    lineas.append("")
    lineas.append(
        f"TOTAL DE POSIBLES INCONSISTENCIAS: {inconsistencias}"
    )

    lineas.append(
        f"Porcentaje sobre secciones válidas: {porcentaje:.4f}%"
    )

    if datos["otros_valores"]:

        lineas.append("")
        lineas.append("Otros tipos de valores:")

        for tipo, cantidad in datos["otros_valores"].items():

            lineas.append(f"  {tipo}: {cantidad}")

    # Mostrar ejemplos.
    if datos["ejemplos"]:

        lineas.append("")
        lineas.append("EJEMPLOS PARA REVISIÓN:")

        for categoria, ejemplos in datos["ejemplos"].items():

            lineas.append("")
            lineas.append(f"  {categoria}:")

            for ejemplo in ejemplos:
                lineas.append(f"    - {ejemplo}")


# ============================================================
# RESUMEN GENERAL
# ============================================================

total_inconsistencias = sum(
    datos["true_con_elementos"]
    + datos["false_sin_elementos"]
    for datos in estadisticas.values()
)

lineas.append("")
lineas.append("=" * 65)
lineas.append("RESUMEN GENERAL")
lineas.append("=" * 65)

lineas.append(
    f"Posibles inconsistencias encontradas: "
    f"{total_inconsistencias}"
)

lineas.append(
    "Nota: un mismo registro puede presentar inconsistencias "
    "en más de una sección."
)

lineas.append("")
lineas.append(
    "Las inconsistencias detectadas son casos para revisión, "
    "no pruebas de irregularidad."
)


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
