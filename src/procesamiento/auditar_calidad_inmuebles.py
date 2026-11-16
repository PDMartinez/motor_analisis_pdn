
import json
import csv
import math
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime


# ============================================================
# CONFIGURACIÓN DE RUTAS
# ============================================================

# Este archivo se encuentra en:
# motor_analisis_pdn/src/procesamiento/
# parents[2] apunta a la carpeta raíz del proyecto.

BASE_DIR = Path(__file__).resolve().parents[2]

CARPETA_ORIGINALES = BASE_DIR / "datos" / "originales"
CARPETA_RESULTADOS = BASE_DIR / "resultados"

CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)

ARCHIVO_AUDITORIA = (
    CARPETA_RESULTADOS / "auditoria_calidad_inmuebles.csv"
)

ARCHIVO_TIPOS = (
    CARPETA_RESULTADOS / "auditoria_rutas_tipo_declaracion.csv"
)

ARCHIVO_INFORME = (
    CARPETA_RESULTADOS / "informe_calidad_inmuebles.txt"
)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def obtener_numero(valor):
    """
    Convierte un valor a número decimal.

    Acepta números enteros, flotantes y cadenas numéricas.
    Devuelve None cuando el valor no puede interpretarse.
    """

    if valor is None or isinstance(valor, bool):
        return None

    try:
        numero = float(str(valor).strip())

        if not math.isfinite(numero):
            return None

        return numero

    except (ValueError, TypeError):
        return None


def obtener_valor_diccionario(dato, campo):
    """
    Obtiene el valor de una estructura del tipo:
    {"valor": 100, "unidad": "m2"}
    """

    if not isinstance(dato, dict):
        return None

    return dato.get(campo)


def obtener_registros(contenido):
    """
    Permite procesar archivos JSON que contengan:
    - Una lista de declaraciones.
    - Un único registro.
    - Una lista dentro de una clave contenedora habitual.
    """

    if isinstance(contenido, list):
        return contenido

    if isinstance(contenido, dict):

        claves_contenedoras = [
            "data",
            "datos",
            "registros",
            "declaraciones",
            "results",
            "resultados"
        ]

        for clave in claves_contenedoras:
            valor = contenido.get(clave)

            if isinstance(valor, list):
                return valor

        if "metadata" in contenido and "declaracion" in contenido:
            return [contenido]

    return []


def obtener_lista_inmuebles(seccion):
    """
    Identifica la lista de inmuebles dentro de bienesInmuebles.

    En la estructura habitual de PDN se utiliza 'bienInmueble'.
    Se contemplan también nombres alternativos para evitar que
    una variación de estructura impida procesar los registros.
    """

    if not isinstance(seccion, dict):
        return []

    posibles_claves = [
        "bienInmueble",
        "bienesInmuebles",
        "inmuebles"
    ]

    for clave in posibles_claves:
        valor = seccion.get(clave)

        if isinstance(valor, list):
            return valor

    # Alternativa: buscar una lista dentro de la sección,
    # excluyendo la propiedad de control "ninguno".
    for clave, valor in seccion.items():
        if clave != "ninguno" and isinstance(valor, list):
            return valor

    return []


def validar_fecha(fecha):
    """
    Valida fechas con formato AAAA-MM-DD.
    """

    if fecha is None:
        return "VACIA"

    fecha = str(fecha).strip()

    if fecha == "":
        return "VACIA"

    try:
        datetime.strptime(fecha, "%Y-%m-%d")
        return "VALIDA"

    except ValueError:
        return "INVALIDA"


def calcular_limite_iqr(valores):
    """
    Calcula el límite superior de valores atípicos
    utilizando el rango intercuartílico (IQR).

    Se consideran solamente valores numéricos positivos.
    """

    valores = sorted(
        valor for valor in valores
        if valor is not None and valor > 0
    )

    if len(valores) < 4:
        return None

    n = len(valores)

    def percentil(datos, p):
        posicion = (len(datos) - 1) * p
        inferior = int(posicion)
        superior = min(inferior + 1, len(datos) - 1)

        if inferior == superior:
            return datos[inferior]

        fraccion = posicion - inferior

        return (
            datos[inferior] * (1 - fraccion)
            + datos[superior] * fraccion
        )

    q1 = percentil(valores, 0.25)
    q3 = percentil(valores, 0.75)

    iqr = q3 - q1

    return q3 + (1.5 * iqr)


# ============================================================
# CONTADORES GENERALES
# ============================================================

archivos_encontrados = 0
archivos_procesados = 0
errores_json = 0
registros_sin_estructura = 0

total_declaraciones = 0
declaraciones_con_inmuebles = 0
total_inmuebles = 0

tipos_declaracion = Counter()

declaraciones_con_inmuebles_por_tipo = Counter()
inmuebles_por_tipo = Counter()

rutas_tipo = Counter()


# ============================================================
# CONTADORES DE CALIDAD
# ============================================================

calidad = Counter()

monedas = Counter()
unidades_superficie = Counter()
fechas = Counter()

valores_superficie_terreno = []
valores_superficie_construccion = []
valores_adquisicion_mxn = []

# Se almacenarán temporalmente los registros de inmuebles
# sin datos personales para construir el CSV final.
filas_auditoria = []


# ============================================================
# BÚSQUEDA RECURSIVA DE ARCHIVOS JSON
# ============================================================

archivos_json = sorted(CARPETA_ORIGINALES.rglob("*.json"))

archivos_encontrados = len(archivos_json)

print("=" * 65)
print("AUDITORÍA DE CALIDAD DE BIENES INMUEBLES - PDN")
print("=" * 65)

print(f"Carpeta de origen: {CARPETA_ORIGINALES}")
print(f"Archivos JSON encontrados: {archivos_encontrados}")

if not archivos_json:
    print("\nNo se encontraron archivos JSON.")
    print("Verifica la ruta de la carpeta datos/originales.")
    raise SystemExit(1)


# ============================================================
# PROCESAMIENTO DE LOS ARCHIVOS
# ============================================================

for archivo in archivos_json:

    try:
        with open(archivo, "r", encoding="utf-8") as archivo_json:
            contenido = json.load(archivo_json)

        registros = obtener_registros(contenido)

        if not registros:
            registros_sin_estructura += 1
            continue

        archivos_procesados += 1

    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as error:
        errores_json += 1
        print(f"Error al leer {archivo.name}: {error}")
        continue

    for registro in registros:

        if not isinstance(registro, dict):
            registros_sin_estructura += 1
            continue

        total_declaraciones += 1

        # ----------------------------------------------------
        # TIPO DE DECLARACIÓN
        # ----------------------------------------------------

        metadata = registro.get("metadata", {})

        if not isinstance(metadata, dict):
            metadata = {}

        tipo_declaracion = metadata.get(
            "tipo",
            "NO_IDENTIFICADO"
        )

        if tipo_declaracion is None:
            tipo_declaracion = "NO_IDENTIFICADO"

        tipo_declaracion = str(tipo_declaracion).strip().upper()

        if not tipo_declaracion:
            tipo_declaracion = "NO_IDENTIFICADO"

        tipos_declaracion[tipo_declaracion] += 1

        # Auditoría de la ruta del tipo de declaración.
        rutas_tipo["metadata.tipo"] += 1

        # ----------------------------------------------------
        # ACCESO A LA DECLARACIÓN PATRIMONIAL
        # ----------------------------------------------------

        declaracion = registro.get("declaracion", {})

        if not isinstance(declaracion, dict):
            continue

        situacion = declaracion.get(
            "situacionPatrimonial",
            {}
        )

        if not isinstance(situacion, dict):
            continue

        seccion_inmuebles = situacion.get(
            "bienesInmuebles",
            {}
        )

        if not isinstance(seccion_inmuebles, dict):
            continue

        lista_inmuebles = obtener_lista_inmuebles(
            seccion_inmuebles
        )

        # ----------------------------------------------------
        # DECLARACIONES CON INMUEBLES
        # ----------------------------------------------------

        inmuebles_validos = [
            inmueble
            for inmueble in lista_inmuebles
            if isinstance(inmueble, dict)
        ]

        if not inmuebles_validos:
            continue

        declaraciones_con_inmuebles += 1

        declaraciones_con_inmuebles_por_tipo[
            tipo_declaracion
        ] += 1

        # ----------------------------------------------------
        # PROCESAMIENTO DE CADA INMUEBLE
        # ----------------------------------------------------

        for indice, inmueble in enumerate(inmuebles_validos, start=1):

            total_inmuebles += 1

            inmuebles_por_tipo[tipo_declaracion] += 1

            # ................................................
            # SUPERFICIE DEL TERRENO
            # ................................................

            superficie_terreno = obtener_numero(
                obtener_valor_diccionario(
                    inmueble.get("superficieTerreno"),
                    "valor"
                )
            )

            unidad_terreno = obtener_valor_diccionario(
                inmueble.get("superficieTerreno"),
                "unidad"
            )

            # ................................................
            # SUPERFICIE DE CONSTRUCCIÓN
            # ................................................

            superficie_construccion = obtener_numero(
                obtener_valor_diccionario(
                    inmueble.get("superficieConstruccion"),
                    "valor"
                )
            )

            unidad_construccion = obtener_valor_diccionario(
                inmueble.get("superficieConstruccion"),
                "unidad"
            )

            # ................................................
            # PORCENTAJE DE PROPIEDAD
            # ................................................

            porcentaje_propiedad = obtener_numero(
                inmueble.get("porcentajePropiedad")
            )

            # ................................................
            # VALOR DE ADQUISICIÓN
            # ................................................

            valor_adquisicion = obtener_numero(
                obtener_valor_diccionario(
                    inmueble.get("valorAdquisicion"),
                    "valor"
                )
            )

            moneda = obtener_valor_diccionario(
                inmueble.get("valorAdquisicion"),
                "moneda"
            )

            if moneda is None or str(moneda).strip() == "":
                moneda = "SIN_MONEDA"
            else:
                moneda = str(moneda).strip().upper()

            monedas[moneda] += 1

            # ................................................
            # FECHA DE ADQUISICIÓN
            # ................................................

            fecha_adquisicion = inmueble.get(
                "fechaAdquiscion"
            )

            estado_fecha = validar_fecha(fecha_adquisicion)

            fechas[estado_fecha] += 1

            # ................................................
            # CONTROLES DE CALIDAD
            # ................................................

            if superficie_terreno is None:
                calidad["terreno_sin_valor_numerico"] += 1

            elif superficie_terreno < 0:
                calidad["terreno_negativo"] += 1

            elif superficie_terreno == 0:
                calidad["terreno_cero"] += 1

            else:
                valores_superficie_terreno.append(
                    superficie_terreno
                )

            if superficie_construccion is None:
                calidad["construccion_sin_valor_numerico"] += 1

            elif superficie_construccion < 0:
                calidad["construccion_negativa"] += 1

            elif superficie_construccion == 0:
                calidad["construccion_cero"] += 1

            else:
                valores_superficie_construccion.append(
                    superficie_construccion
                )

            if porcentaje_propiedad is None:
                calidad["porcentaje_sin_valor"] += 1

            elif porcentaje_propiedad == 0:
                calidad["propiedad_cero"] += 1

            elif porcentaje_propiedad < 0 or porcentaje_propiedad > 100:
                calidad["propiedad_fuera_rango"] += 1

            elif porcentaje_propiedad == 100:
                calidad["propiedad_100"] += 1

            else:
                calidad["propiedad_intermedia"] += 1

            if valor_adquisicion is None:
                calidad["valor_adquisicion_sin_valor"] += 1

            elif valor_adquisicion < 0:
                calidad["valor_adquisicion_negativo"] += 1

            elif valor_adquisicion == 0:
                calidad["valor_adquisicion_cero"] += 1

            if valor_adquisicion is not None and moneda == "MXN":
                if valor_adquisicion > 0:
                    valores_adquisicion_mxn.append(
                        valor_adquisicion
                    )

            if estado_fecha == "VACIA":
                calidad["fecha_vacia"] += 1

            elif estado_fecha == "INVALIDA":
                calidad["fecha_invalida"] += 1

            # ................................................
            # UNIDADES DE SUPERFICIE
            # ................................................

            if unidad_terreno:
                unidades_superficie[
                    str(unidad_terreno).strip().upper()
                ] += 1

            if unidad_construccion:
                unidades_superficie[
                    str(unidad_construccion).strip().upper()
                ] += 1

            # ................................................
            # REGISTRO ANÓNIMO PARA EL CSV
            # ................................................

            filas_auditoria.append({
                "tipo_declaracion": tipo_declaracion,
                "numero_inmueble": indice,
                "superficie_terreno": superficie_terreno,
                "unidad_terreno": unidad_terreno,
                "superficie_construccion": superficie_construccion,
                "unidad_construccion": unidad_construccion,
                "porcentaje_propiedad": porcentaje_propiedad,
                "valor_adquisicion": valor_adquisicion,
                "moneda": moneda,
                "fecha_adquisicion_estado": estado_fecha,
                "terreno_negativo": (
                    superficie_terreno is not None
                    and superficie_terreno < 0
                ),
                "construccion_negativa": (
                    superficie_construccion is not None
                    and superficie_construccion < 0
                ),
                "propiedad_fuera_rango": (
                    porcentaje_propiedad is not None
                    and (
                        porcentaje_propiedad < 0
                        or porcentaje_propiedad > 100
                    )
                ),
                "valor_adquisicion_negativo": (
                    valor_adquisicion is not None
                    and valor_adquisicion < 0
                )
            })


# ============================================================
# CÁLCULO DE VALORES ATÍPICOS MEDIANTE IQR
# ============================================================

limite_terreno = calcular_limite_iqr(
    valores_superficie_terreno
)

limite_construccion = calcular_limite_iqr(
    valores_superficie_construccion
)

limite_adquisicion_mxn = calcular_limite_iqr(
    valores_adquisicion_mxn
)


def contar_superiores(valores, limite):
    if limite is None:
        return 0

    return sum(
        1 for valor in valores
        if valor > limite
    )


superficies_terreno_atipicas = contar_superiores(
    valores_superficie_terreno,
    limite_terreno
)

superficies_construccion_atipicas = contar_superiores(
    valores_superficie_construccion,
    limite_construccion
)

adquisiciones_mxn_atipicas = contar_superiores(
    valores_adquisicion_mxn,
    limite_adquisicion_mxn
)


# ============================================================
# GENERACIÓN DEL CSV DE AUDITORÍA
# ============================================================

if filas_auditoria:

    columnas = list(filas_auditoria[0].keys())

    with open(
        ARCHIVO_AUDITORIA,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as archivo_csv:

        escritor = csv.DictWriter(
            archivo_csv,
            fieldnames=columnas
        )

        escritor.writeheader()
        escritor.writerows(filas_auditoria)


# ============================================================
# GENERACIÓN DEL CSV POR TIPO DE DECLARACIÓN
# ============================================================

tipos_conocidos = sorted(
    set(tipos_declaracion.keys())
    | set(declaraciones_con_inmuebles_por_tipo.keys())
    | set(inmuebles_por_tipo.keys())
)

with open(
    ARCHIVO_TIPOS,
    "w",
    newline="",
    encoding="utf-8-sig"
) as archivo_csv:

    columnas = [
        "tipo_declaracion",
        "total_declaraciones",
        "declaraciones_con_inmuebles",
        "inmuebles_registrados"
    ]

    escritor = csv.DictWriter(
        archivo_csv,
        fieldnames=columnas
    )

    escritor.writeheader()

    for tipo in tipos_conocidos:

        escritor.writerow({
            "tipo_declaracion": tipo,
            "total_declaraciones": tipos_declaracion[tipo],
            "declaraciones_con_inmuebles": (
                declaraciones_con_inmuebles_por_tipo[tipo]
            ),
            "inmuebles_registrados": inmuebles_por_tipo[tipo]
        })


# ============================================================
# GENERACIÓN DEL INFORME DE TEXTO
# ============================================================

lineas = []

lineas.append("=" * 70)
lineas.append("INFORME DE AUDITORÍA DE CALIDAD DE BIENES INMUEBLES - PDN")
lineas.append("=" * 70)

lineas.append("")
lineas.append("1. RESUMEN GENERAL")
lineas.append("-" * 70)

lineas.append(f"Archivos JSON encontrados: {archivos_encontrados}")
lineas.append(f"Archivos procesados: {archivos_procesados}")
lineas.append(f"Errores de lectura JSON: {errores_json}")
lineas.append(
    f"Archivos sin estructura reconocida: {registros_sin_estructura}"
)
lineas.append(f"Total de declaraciones procesadas: {total_declaraciones}")
lineas.append(
    f"Declaraciones con inmuebles: {declaraciones_con_inmuebles}"
)
lineas.append(f"Total de inmuebles registrados: {total_inmuebles}")

lineas.append("")
lineas.append("2. DISTRIBUCIÓN POR TIPO DE DECLARACIÓN")
lineas.append("-" * 70)

for tipo, cantidad in tipos_declaracion.most_common():

    porcentaje = (
        cantidad / total_declaraciones * 100
        if total_declaraciones else 0
    )

    lineas.append(
        f"{tipo}: {cantidad:,} ({porcentaje:.2f}%)"
    )

lineas.append("")
lineas.append("3. DECLARACIONES CON INMUEBLES POR TIPO")
lineas.append("-" * 70)

for tipo in tipos_conocidos:

    total_tipo = tipos_declaracion[tipo]

    con_inmuebles = declaraciones_con_inmuebles_por_tipo[tipo]

    porcentaje = (
        con_inmuebles / total_tipo * 100
        if total_tipo else 0
    )

    lineas.append(
        f"{tipo}: {con_inmuebles:,} de {total_tipo:,} "
        f"declaraciones ({porcentaje:.2f}%)"
    )

lineas.append("")
lineas.append("4. CANTIDAD DE INMUEBLES POR TIPO")
lineas.append("-" * 70)

for tipo in tipos_conocidos:

    lineas.append(
        f"{tipo}: {inmuebles_por_tipo[tipo]:,} inmuebles"
    )

lineas.append("")
lineas.append("5. CALIDAD DE SUPERFICIES")
lineas.append("-" * 70)

lineas.append(
    f"Terrenos con valor negativo: "
    f"{calidad['terreno_negativo']:,}"
)

lineas.append(
    f"Terrenos con valor cero: "
    f"{calidad['terreno_cero']:,}"
)

lineas.append(
    f"Terrenos sin valor numérico: "
    f"{calidad['terreno_sin_valor_numerico']:,}"
)

lineas.append(
    f"Construcciones con valor negativo: "
    f"{calidad['construccion_negativa']:,}"
)

lineas.append(
    f"Construcciones con valor cero: "
    f"{calidad['construccion_cero']:,}"
)

lineas.append(
    f"Construcciones sin valor numérico: "
    f"{calidad['construccion_sin_valor_numerico']:,}"
)

lineas.append("")
lineas.append("6. PORCENTAJE DE PROPIEDAD")
lineas.append("-" * 70)

lineas.append(
    f"Porcentaje igual a 0: {calidad['propiedad_cero']:,}"
)

lineas.append(
    f"Porcentaje igual a 100: {calidad['propiedad_100']:,}"
)

lineas.append(
    f"Porcentaje intermedio (mayor a 0 y menor a 100): "
    f"{calidad['propiedad_intermedia']:,}"
)

lineas.append(
    f"Porcentaje fuera del rango 0-100: "
    f"{calidad['propiedad_fuera_rango']:,}"
)

lineas.append(
    f"Porcentaje sin valor numérico: "
    f"{calidad['porcentaje_sin_valor']:,}"
)

lineas.append("")
lineas.append("7. VALOR DE ADQUISICIÓN")
lineas.append("-" * 70)

lineas.append(
    f"Valores sin dato numérico: "
    f"{calidad['valor_adquisicion_sin_valor']:,}"
)

lineas.append(
    f"Valores negativos: "
    f"{calidad['valor_adquisicion_negativo']:,}"
)

lineas.append(
    f"Valores iguales a cero: "
    f"{calidad['valor_adquisicion_cero']:,}"
)

lineas.append("")
lineas.append("Distribución por moneda:")

for moneda, cantidad in monedas.most_common():

    lineas.append(f"{moneda}: {cantidad:,}")

lineas.append("")
lineas.append("8. FECHAS DE ADQUISICIÓN")
lineas.append("-" * 70)

for estado, cantidad in fechas.most_common():

    lineas.append(f"{estado}: {cantidad:,}")

lineas.append("")
lineas.append("9. UNIDADES DE SUPERFICIE")
lineas.append("-" * 70)

for unidad, cantidad in unidades_superficie.most_common():

    lineas.append(f"{unidad}: {cantidad:,}")

lineas.append("")
lineas.append("10. DETECCIÓN EXPLORATORIA DE VALORES ATÍPICOS (IQR)")
lineas.append("-" * 70)

lineas.append(
    f"Límite superior de superficie de terreno: "
    f"{limite_terreno if limite_terreno is not None else 'No calculable'}"
)

lineas.append(
    f"Terrenos por encima del límite: "
    f"{superficies_terreno_atipicas:,}"
)

lineas.append(
    f"Límite superior de superficie de construcción: "
    f"{limite_construccion if limite_construccion is not None else 'No calculable'}"
)

lineas.append(
    f"Construcciones por encima del límite: "
    f"{superficies_construccion_atipicas:,}"
)

lineas.append(
    f"Límite superior de valor de adquisición MXN: "
    f"{limite_adquisicion_mxn if limite_adquisicion_mxn is not None else 'No calculable'}"
)

lineas.append(
    f"Adquisiciones MXN por encima del límite: "
    f"{adquisiciones_mxn_atipicas:,}"
)

lineas.append("")
lineas.append("11. OBSERVACIONES METODOLÓGICAS")
lineas.append("-" * 70)

lineas.append(
    "- El tipo de declaración se obtiene de metadata.tipo."
)

lineas.append(
    "- Los inmuebles se cuentan por registro, no por persona única."
)

lineas.append(
    "- El valor de adquisición no representa necesariamente "
    "el valor actual del inmueble."
)

lineas.append(
    "- No se convierten monedas ni se mezclan importes de "
    "monedas diferentes."
)

lineas.append(
    "- Los valores negativos, cero y atípicos requieren "
    "revisión contextual; no demuestran irregularidades."
)

lineas.append(
    "- La fecha de adquisición vacía no demuestra ausencia "
    "de adquisición."
)

lineas.append(
    "- Los límites IQR son criterios exploratorios y no "
    "constituyen evidencia de conducta indebida."
)

lineas.append(
    "- El informe no incluye nombres, RFC ni identificadores "
    "personales de declarantes o terceros."
)

lineas.append("")
lineas.append("=" * 70)
lineas.append("FIN DEL INFORME")
lineas.append("=" * 70)


with open(
    ARCHIVO_INFORME,
    "w",
    encoding="utf-8"
) as archivo:

    archivo.write("\n".join(lineas))


# ============================================================
# RESULTADO EN CONSOLA
# ============================================================

print("\n" + "=" * 65)
print("PROCESAMIENTO FINALIZADO")
print("=" * 65)

print(f"Archivos encontrados: {archivos_encontrados:,}")
print(f"Archivos procesados: {archivos_procesados:,}")
print(f"Errores JSON: {errores_json:,}")
print(f"Declaraciones: {total_declaraciones:,}")
print(f"Declaraciones con inmuebles: {declaraciones_con_inmuebles:,}")
print(f"Inmuebles registrados: {total_inmuebles:,}")

print("\nDISTRIBUCIÓN POR TIPO DE DECLARACIÓN")

for tipo, cantidad in tipos_declaracion.most_common():
    print(f"  {tipo}: {cantidad:,}")

print("\nDECLARACIONES CON INMUEBLES POR TIPO")

for tipo in tipos_conocidos:
    print(
        f"  {tipo}: "
        f"{declaraciones_con_inmuebles_por_tipo[tipo]:,}"
    )

print("\nINMUEBLES POR TIPO")

for tipo in tipos_conocidos:
    print(
        f"  {tipo}: "
        f"{inmuebles_por_tipo[tipo]:,}"
    )

print("\nARCHIVOS GENERADOS")

print(f"1. {ARCHIVO_AUDITORIA}")
print(f"2. {ARCHIVO_TIPOS}")
print(f"3. {ARCHIVO_INFORME}")

print("\nAuditoría finalizada correctamente.")
