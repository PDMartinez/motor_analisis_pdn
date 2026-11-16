
import json
import csv
import re
import math

from pathlib import Path
from collections import Counter, defaultdict
from statistics import median, mean


# ============================================================
# 1. CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "datos" / "originales"
RESULTADOS_DIR = BASE_DIR / "resultados"

ARCHIVO_REPORTE = (
    RESULTADOS_DIR / "auditoria_detalle_inmuebles.txt"
)

ARCHIVO_CSV = (
    RESULTADOS_DIR / "auditoria_detalle_inmuebles.csv"
)

RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

TOTAL_INMUEBLES_ESPERADO = 11264

# Campos categóricos cuya distribución queremos conocer.
CAMPOS_CATEGORICOS = [
    "tipoOperacion",
    "formaPago",
    "valorConformeA"
]

CAMPOS_OBJETO_CATEGORICOS = [
    "tipoInmueble",
    "formaAdquisicion",
    "motivoBaja"
]

# Campos que contienen listas. Solo analizaremos su estructura.
CAMPOS_LISTAS = [
    "titular",
    "transmisor"
]


# ============================================================
# 2. FUNCIONES AUXILIARES
# ============================================================

def obtener_tipo(valor):

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
            declaraciones.append(registro)

    return declaraciones


def obtener_inmuebles(declaracion):

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


def convertir_numero(valor):
    """
    Convierte un valor a número cuando es posible.
    No acepta booleanos ni cadenas vacías.
    """

    if isinstance(valor, bool) or valor is None:
        return None

    if isinstance(valor, (int, float)):

        numero = float(valor)

        if math.isfinite(numero):
            return numero

        return None

    if isinstance(valor, str):

        texto = valor.strip()

        if not texto:
            return None

        try:
            numero = float(texto)

            if math.isfinite(numero):
                return numero

        except ValueError:
            return None

    return None


def resumir_numeros(valores):
    """
    Calcula estadísticas agregadas.
    Nunca devuelve valores individuales.
    """

    if not valores:
        return None

    return {
        "cantidad": len(valores),
        "minimo": min(valores),
        "mediana": median(valores),
        "media": mean(valores),
        "maximo": max(valores)
    }


def identificar_formato_fecha(valor):
    """
    Identifica formatos habituales sin conservar
    ni mostrar la fecha individual.
    """

    if not isinstance(valor, str):
        return "NO_ES_TEXTO"

    texto = valor.strip()

    if not texto:
        return "VACIO"

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto):
        return "AAAA-MM-DD"

    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", texto):
        return "DD/MM/AAAA"

    if re.fullmatch(r"\d{2}-\d{2}-\d{4}", texto):
        return "DD-MM-AAAA"

    if re.fullmatch(r"\d{4}/\d{2}/\d{2}", texto):
        return "AAAA/MM/DD"

    if re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T.*",
        texto
    ):
        return "FECHA_HORA_ISO"

    return "OTRO_FORMATO"


def valor_categoria(valor):
    """
    Convierte categorías a texto para contabilizarlas.
    Se utiliza únicamente en campos categóricos definidos.
    """

    if valor is None:
        return "NULL"

    if isinstance(valor, bool):
        return str(valor)

    if isinstance(valor, (str, int, float)):
        texto = str(valor).strip()

        if not texto:
            return "VACIO"

        # Evitar exportar cadenas excesivamente largas.
        if len(texto) > 100:
            return "TEXTO_LARGO_NO_MOSTRADO"

        return texto

    return obtener_tipo(valor)


# ============================================================
# 3. ESTRUCTURAS DE ACUMULACIÓN
# ============================================================

total_archivos = 0
total_declaraciones = 0
total_inmuebles = 0
declaraciones_con_inmuebles = 0

errores_lectura = 0
registros_invalidos = 0

tipos_declaracion = Counter()

# Estructura y frecuencia de los campos principales.
campos = defaultdict(lambda: {
    "presente": 0,
    "tipos": Counter()
})

# Distribuciones de categorías.
categorias = defaultdict(Counter)

# Estadísticas numéricas agrupadas.
numericos = defaultdict(list)

# Cantidad de valores que no pudieron interpretarse como números.
numericos_no_validos = Counter()

# Agrupación de valores por moneda o unidad.
monedas = Counter()
unidades_terreno = Counter()
unidades_construccion = Counter()

# Fechas de adquisición.
formatos_fecha = Counter()
fechas_vacias = 0

# Estructura de las listas titular y transmisor.
estructura_listas = defaultdict(lambda: {
    "elementos": 0,
    "tipos": Counter(),
    "claves": Counter()
})

# Claves internas de los objetos.
claves_objetos = defaultdict(Counter)

# Información de control.
inmuebles_por_declaracion = Counter()


# ============================================================
# 4. PROCESAR ARCHIVOS JSON
# ============================================================

archivos = sorted(DATA_DIR.rglob("*.json"))

print("=" * 70)
print("AUDITORÍA DETALLADA DE BIENES INMUEBLES")
print("=" * 70)

for archivo in archivos:

    total_archivos += 1

    try:

        with open(archivo, "r", encoding="utf-8") as f:
            contenido = json.load(f)

        declaraciones = obtener_declaraciones(contenido)

    except Exception as e:

        errores_lectura += 1
        print(f"Error en {archivo.name}: {e}")
        continue

    for declaracion in declaraciones:

        if not isinstance(declaracion, dict):
            registros_invalidos += 1
            continue

        total_declaraciones += 1

        tipo = declaracion.get(
            "tipoDeclaracion",
            "NO_IDENTIFICADO"
        )

        tipos_declaracion[str(tipo)] += 1

        inmuebles = obtener_inmuebles(declaracion)

        if inmuebles:
            declaraciones_con_inmuebles += 1

        inmuebles_por_declaracion[len(inmuebles)] += 1

        for inmueble in inmuebles:

            total_inmuebles += 1

            # ------------------------------------------------
            # 4.1 CAMPOS PRINCIPALES
            # ------------------------------------------------

            for campo, valor in inmueble.items():

                campos[campo]["presente"] += 1

                campos[campo]["tipos"][
                    obtener_tipo(valor)
                ] += 1

            # ------------------------------------------------
            # 4.2 CAMPOS CATEGÓRICOS SIMPLES
            # ------------------------------------------------

            for campo in CAMPOS_CATEGORICOS:

                valor = inmueble.get(campo)

                if campo in inmueble:

                    categorias[campo][
                        valor_categoria(valor)
                    ] += 1

            # ------------------------------------------------
            # 4.3 OBJETOS CON CLAVE Y VALOR
            # ------------------------------------------------

            for campo in CAMPOS_OBJETO_CATEGORICOS:

                objeto = inmueble.get(campo)

                if isinstance(objeto, dict):

                    for clave, valor in objeto.items():

                        claves_objetos[campo][
                            str(clave)
                        ] += 1

                    if "clave" in objeto:

                        categorias[
                            f"{campo}.clave"
                        ][
                            valor_categoria(objeto["clave"])
                        ] += 1

                    if "valor" in objeto:

                        categorias[
                            f"{campo}.valor"
                        ][
                            valor_categoria(objeto["valor"])
                        ] += 1

            # ------------------------------------------------
            # 4.4 SUPERFICIE DEL TERRENO
            # ------------------------------------------------

            terreno = inmueble.get("superficieTerreno")

            if isinstance(terreno, dict):

                valor = convertir_numero(
                    terreno.get("valor")
                )

                unidad = valor_categoria(
                    terreno.get("unidad")
                )

                if valor is not None:
                    numericos[
                        f"superficieTerreno|{unidad}"
                    ].append(valor)
                else:
                    numericos_no_validos[
                        "superficieTerreno"
                    ] += 1

                unidades_terreno[unidad] += 1

            # ------------------------------------------------
            # 4.5 SUPERFICIE DE CONSTRUCCIÓN
            # ------------------------------------------------

            construccion = inmueble.get(
                "superficieConstruccion"
            )

            if isinstance(construccion, dict):

                valor = convertir_numero(
                    construccion.get("valor")
                )

                unidad = valor_categoria(
                    construccion.get("unidad")
                )

                if valor is not None:
                    numericos[
                        f"superficieConstruccion|{unidad}"
                    ].append(valor)
                else:
                    numericos_no_validos[
                        "superficieConstruccion"
                    ] += 1

                unidades_construccion[unidad] += 1

            # ------------------------------------------------
            # 4.6 VALOR DE ADQUISICIÓN
            # ------------------------------------------------

            adquisicion = inmueble.get("valorAdquisicion")

            if isinstance(adquisicion, dict):

                valor = convertir_numero(
                    adquisicion.get("valor")
                )

                moneda = valor_categoria(
                    adquisicion.get("moneda")
                )

                monedas[moneda] += 1

                if valor is not None:

                    numericos[
                        f"valorAdquisicion|{moneda}"
                    ].append(valor)

                else:

                    numericos_no_validos[
                        "valorAdquisicion"
                    ] += 1

                for clave in adquisicion.keys():

                    claves_objetos[
                        "valorAdquisicion"
                    ][str(clave)] += 1

            # ------------------------------------------------
            # 4.7 PORCENTAJE DE PROPIEDAD
            # ------------------------------------------------

            porcentaje = convertir_numero(
                inmueble.get("porcentajePropiedad")
            )

            if porcentaje is not None:

                numericos[
                    "porcentajePropiedad"
                ].append(porcentaje)

            else:

                numericos_no_validos[
                    "porcentajePropiedad"
                ] += 1

            # ------------------------------------------------
            # 4.8 FECHA DE ADQUISICIÓN
            # ------------------------------------------------

            fecha = inmueble.get("fechaAdquiscion")

            formato = identificar_formato_fecha(fecha)

            formatos_fecha[formato] += 1

            if formato == "VACIO":
                fechas_vacias += 1

            # ------------------------------------------------
            # 4.9 LISTAS TITULAR Y TRANSMISOR
            # ------------------------------------------------

            for campo in CAMPOS_LISTAS:

                lista = inmueble.get(campo)

                if not isinstance(lista, list):
                    continue

                for elemento in lista:

                    estructura_listas[campo][
                        "elementos"
                    ] += 1

                    estructura_listas[campo][
                        "tipos"
                    ][obtener_tipo(elemento)] += 1

                    # Solo se registran nombres de claves.
                    # No se registran valores personales.
                    if isinstance(elemento, dict):

                        for clave in elemento.keys():

                            estructura_listas[campo][
                                "claves"
                            ][str(clave)] += 1


# ============================================================
# 5. PREPARAR REPORTE
# ============================================================

lineas = []

lineas.append("=" * 75)
lineas.append("AUDITORÍA DETALLADA DE BIENES INMUEBLES")
lineas.append("=" * 75)

lineas.append("")
lineas.append("1. RESUMEN GENERAL")
lineas.append("-" * 75)

lineas.append(f"Archivos procesados: {total_archivos}")
lineas.append(f"Declaraciones procesadas: {total_declaraciones}")
lineas.append(f"Declaraciones con inmuebles: {declaraciones_con_inmuebles}")
lineas.append(f"Inmuebles analizados: {total_inmuebles}")
lineas.append(f"Errores de lectura: {errores_lectura}")
lineas.append(f"Registros inválidos: {registros_invalidos}")
lineas.append(
    f"Total esperado: {TOTAL_INMUEBLES_ESPERADO}"
)

lineas.append(
    f"Diferencia: {total_inmuebles - TOTAL_INMUEBLES_ESPERADO}"
)


# ============================================================
# 6. TIPOS DE DECLARACIÓN
# ============================================================

lineas.append("")
lineas.append("2. DECLARACIONES POR TIPO")
lineas.append("-" * 75)

for tipo, cantidad in tipos_declaracion.most_common():

    lineas.append(f"{tipo}: {cantidad}")


# ============================================================
# 7. CAMPOS Y TIPOS
# ============================================================

lineas.append("")
lineas.append("3. ESTRUCTURA DE CAMPOS")
lineas.append("-" * 75)

for campo, datos in sorted(campos.items()):

    porcentaje = (
        datos["presente"] / total_inmuebles * 100
        if total_inmuebles else 0
    )

    tipos = ", ".join(
        f"{tipo}: {cantidad}"
        for tipo, cantidad in datos["tipos"].most_common()
    )

    lineas.append("")
    lineas.append(f"Campo: {campo}")
    lineas.append(f"Presencia: {datos['presente']} ({porcentaje:.2f}%)")
    lineas.append(f"Tipos: {tipos}")


# ============================================================
# 8. DISTRIBUCIONES CATEGÓRICAS
# ============================================================

lineas.append("")
lineas.append("4. DISTRIBUCIONES CATEGÓRICAS")
lineas.append("-" * 75)

for campo, distribucion in sorted(categorias.items()):

    lineas.append("")
    lineas.append(f"Campo: {campo}")

    for valor, cantidad in distribucion.most_common(30):

        porcentaje = (
            cantidad / total_inmuebles * 100
            if total_inmuebles else 0
        )

        lineas.append(
            f"  {valor}: {cantidad} ({porcentaje:.2f}%)"
        )

    if len(distribucion) > 30:

        lineas.append(
            f"  Otras categorías no mostradas: "
            f"{len(distribucion) - 30}"
        )


# ============================================================
# 9. CLAVES INTERNAS DE OBJETOS
# ============================================================

lineas.append("")
lineas.append("5. CLAVES INTERNAS DE OBJETOS")
lineas.append("-" * 75)

for campo, claves in sorted(claves_objetos.items()):

    lineas.append("")
    lineas.append(f"Objeto: {campo}")

    for clave, cantidad in claves.most_common():

        lineas.append(
            f"  {clave}: {cantidad}"
        )


# ============================================================
# 10. ESTADÍSTICAS NUMÉRICAS
# ============================================================

lineas.append("")
lineas.append("6. ESTADÍSTICAS NUMÉRICAS")
lineas.append("-" * 75)

for grupo, valores in sorted(numericos.items()):

    resumen = resumir_numeros(valores)

    if resumen is None:
        continue

    lineas.append("")
    lineas.append(f"Variable: {grupo}")
    lineas.append(f"Cantidad válida: {resumen['cantidad']}")
    lineas.append(f"Mínimo: {resumen['minimo']:.4f}")
    lineas.append(f"Mediana: {resumen['mediana']:.4f}")
    lineas.append(f"Media: {resumen['media']:.4f}")
    lineas.append(f"Máximo: {resumen['maximo']:.4f}")


lineas.append("")
lineas.append("7. VALORES NUMÉRICOS NO INTERPRETADOS")
lineas.append("-" * 75)

for campo, cantidad in numericos_no_validos.items():

    lineas.append(f"{campo}: {cantidad}")


# ============================================================
# 11. MONEDAS Y UNIDADES
# ============================================================

lineas.append("")
lineas.append("8. MONEDAS EN VALOR DE ADQUISICIÓN")
lineas.append("-" * 75)

for moneda, cantidad in monedas.most_common():

    lineas.append(f"{moneda}: {cantidad}")


lineas.append("")
lineas.append("9. UNIDADES DE SUPERFICIE")
lineas.append("-" * 75)

lineas.append("Superficie de terreno:")

for unidad, cantidad in unidades_terreno.most_common():

    lineas.append(f"  {unidad}: {cantidad}")

lineas.append("Superficie de construcción:")

for unidad, cantidad in unidades_construccion.most_common():

    lineas.append(f"  {unidad}: {cantidad}")


# ============================================================
# 12. FECHAS
# ============================================================

lineas.append("")
lineas.append("10. FORMATOS DE FECHA DE ADQUISICIÓN")
lineas.append("-" * 75)

for formato, cantidad in formatos_fecha.most_common():

    lineas.append(f"{formato}: {cantidad}")


# ============================================================
# 13. ESTRUCTURA DE TITULAR Y TRANSMISOR
# ============================================================

lineas.append("")
lineas.append("11. ESTRUCTURA DE LISTAS")
lineas.append("-" * 75)

for campo, datos in estructura_listas.items():

    lineas.append("")
    lineas.append(f"Campo: {campo}")
    lineas.append(f"Elementos encontrados: {datos['elementos']}")

    lineas.append("Tipos de elementos:")

    for tipo, cantidad in datos["tipos"].most_common():

        lineas.append(f"  {tipo}: {cantidad}")

    lineas.append("Claves de objetos:")

    for clave, cantidad in datos["claves"].most_common():

        lineas.append(f"  {clave}: {cantidad}")


# ============================================================
# 14. NOTAS METODOLÓGICAS
# ============================================================

lineas.append("")
lineas.append("12. NOTAS METODOLÓGICAS")
lineas.append("-" * 75)

lineas.append(
    "Las estadísticas numéricas son descriptivas y no constituyen "
    "evidencia de irregularidad."
)

lineas.append(
    "Los importes se agrupan por moneda y no se convierten entre monedas."
)

lineas.append(
    "Las superficies se agrupan por unidad y no se mezclan unidades."
)

lineas.append(
    "Los campos titular y transmisor se analizan solamente por estructura."
)

lineas.append(
    "No se exportan nombres, identificadores ni valores individuales."
)

lineas.append(
    "Las fechas se clasifican por formato sin mostrar fechas individuales."
)

lineas.append(
    "La ausencia de un dato no demuestra ausencia de patrimonio."
)

lineas.append(
    "El campo fechaAdquiscion conserva su nombre original del JSON."
)

lineas.append(
    "Esta auditoría no modifica los archivos originales."
)


# ============================================================
# 15. GUARDAR REPORTE TXT
# ============================================================

with open(
    ARCHIVO_REPORTE,
    "w",
    encoding="utf-8"
) as f:

    f.write("\n".join(lineas))


# ============================================================
# 16. GENERAR CSV AGREGADO
# ============================================================

with open(
    ARCHIVO_CSV,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    escritor = csv.writer(f)

    escritor.writerow([
        "tipo_registro",
        "campo",
        "detalle",
        "frecuencia",
        "porcentaje",
        "cantidad_numerica",
        "minimo",
        "mediana",
        "media",
        "maximo"
    ])

    # Distribuciones categóricas.
    for campo, distribucion in categorias.items():

        for valor, cantidad in distribucion.items():

            porcentaje = (
                cantidad / total_inmuebles * 100
                if total_inmuebles else 0
            )

            escritor.writerow([
                "CATEGORIA",
                campo,
                valor,
                cantidad,
                round(porcentaje, 2),
                "",
                "",
                "",
                "",
                ""
            ])

    # Estadísticas numéricas.
    for grupo, valores in numericos.items():

        resumen = resumir_numeros(valores)

        if resumen is None:
            continue

        escritor.writerow([
            "ESTADISTICA_NUMERICA",
            grupo,
            "RESUMEN_AGREGADO",
            resumen["cantidad"],
            "",
            resumen["cantidad"],
            resumen["minimo"],
            resumen["mediana"],
            resumen["media"],
            resumen["maximo"]
        ])

    # Monedas.
    for moneda, cantidad in monedas.items():

        escritor.writerow([
            "MONEDA",
            "valorAdquisicion",
            moneda,
            cantidad,
            "",
            "",
            "",
            "",
            "",
            ""
        ])

    # Unidades.
    for unidad, cantidad in unidades_terreno.items():

        escritor.writerow([
            "UNIDAD",
            "superficieTerreno",
            unidad,
            cantidad,
            "",
            "",
            "",
            "",
            "",
            ""
        ])

    for unidad, cantidad in unidades_construccion.items():

        escritor.writerow([
            "UNIDAD",
            "superficieConstruccion",
            unidad,
            cantidad,
            "",
            "",
            "",
            "",
            "",
            ""
        ])

    # Formatos de fecha.
    for formato, cantidad in formatos_fecha.items():

        escritor.writerow([
            "FORMATO_FECHA",
            "fechaAdquiscion",
            formato,
            cantidad,
            "",
            "",
            "",
            "",
            "",
            ""
        ])

    # Estructura de listas.
    for campo, datos in estructura_listas.items():

        for tipo, cantidad in datos["tipos"].items():

            escritor.writerow([
                "TIPO_ELEMENTO_LISTA",
                campo,
                tipo,
                cantidad,
                "",
                "",
                "",
                "",
                "",
                ""
            ])

        for clave, cantidad in datos["claves"].items():

            escritor.writerow([
                "CLAVE_INTERNA_LISTA",
                campo,
                clave,
                cantidad,
                "",
                "",
                "",
                "",
                "",
                ""
            ])


# ============================================================
# 17. RESULTADO FINAL
# ============================================================

print("\nAUDITORÍA DETALLADA FINALIZADA")
print("=" * 70)

print(f"Archivos procesados: {total_archivos}")
print(f"Declaraciones procesadas: {total_declaraciones}")
print(f"Declaraciones con inmuebles: {declaraciones_con_inmuebles}")
print(f"Inmuebles analizados: {total_inmuebles}")
print(f"Campos identificados: {len(campos)}")
print(f"Errores de lectura: {errores_lectura}")
print(f"Registros inválidos: {registros_invalidos}")

if total_inmuebles == TOTAL_INMUEBLES_ESPERADO:
    print("\nCONTROL DE CONSISTENCIA: CORRECTO")
else:
    print("\nCONTROL DE CONSISTENCIA: REVISAR")

    print(
        "Diferencia:",
        total_inmuebles - TOTAL_INMUEBLES_ESPERADO
    )

print("\nArchivos generados:")
print(ARCHIVO_REPORTE)
print(ARCHIVO_CSV)
