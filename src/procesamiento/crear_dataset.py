
import json
import re
from pathlib import Path

import pandas as pd


# ==========================================================
# CONFIGURACIÓN DE RUTAS
# ==========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "datos" / "originales"
OUTPUT_DIR = BASE_DIR / "datos" / "procesados"
OUTPUT_FILE = OUTPUT_DIR / "dataset_pdn.csv"


# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================

def obtener_ruta(diccionario, ruta):
    """Obtiene un valor mediante una ruta separada por puntos."""

    valor = diccionario

    for clave in ruta.split("."):
        if not isinstance(valor, dict):
            return None

        valor = valor.get(clave)

        if valor is None:
            return None

    return valor


def obtener_primero(diccionario, rutas):
    """Devuelve el primer valor disponible entre varias rutas."""

    for ruta in rutas:
        valor = obtener_ruta(diccionario, ruta)

        if valor is not None and valor != "":
            return valor

    return None


def limpiar_texto(valor):
    """Convierte valores simples a texto y elimina espacios."""

    if valor is None or isinstance(valor, (dict, list)):
        return None

    texto = str(valor).strip()

    return texto if texto else None


def normalizar_fecha(valor):
    """Normaliza fechas a formato YYYY-MM-DD."""

    if valor is None:
        return None

    if isinstance(valor, dict):
        valor = valor.get("fecha") or valor.get("valor")

    if not isinstance(valor, str):
        return None

    valor = valor.strip()

    if not valor:
        return None

    fecha = pd.to_datetime(
        valor,
        errors="coerce",
        dayfirst=True
    )

    if pd.isna(fecha):
        return None

    return fecha.strftime("%Y-%m-%d")


def convertir_numero(valor):
    """Convierte importes numéricos o estructuras de monto a float."""

    if valor is None or isinstance(valor, bool):
        return None

    if isinstance(valor, (int, float)):
        return float(valor)

    if isinstance(valor, dict):
        return convertir_numero(valor.get("valor"))

    if isinstance(valor, str):
        texto = valor.strip()

        if not texto:
            return None

        texto = re.sub(r"[^\d,.\-]", "", texto)

        if not texto:
            return None

        if "," in texto and "." in texto:
            if texto.rfind(",") > texto.rfind("."):
                texto = texto.replace(".", "").replace(",", ".")
            else:
                texto = texto.replace(",", "")

        elif "," in texto:
            partes = texto.split(",")

            if len(partes[-1]) == 2:
                texto = texto.replace(",", ".")
            else:
                texto = texto.replace(",", "")

        try:
            return float(texto)
        except ValueError:
            return None

    return None


def buscar_clave_recursiva(objeto, claves):
    """Busca la primera clave disponible dentro de una estructura."""

    if isinstance(objeto, dict):

        for clave in claves:
            if clave in objeto:
                valor = objeto[clave]

                if valor is not None and valor != "":
                    return valor

        for valor in objeto.values():
            resultado = buscar_clave_recursiva(valor, claves)

            if resultado is not None:
                return resultado

    elif isinstance(objeto, list):

        for elemento in objeto:
            resultado = buscar_clave_recursiva(elemento, claves)

            if resultado is not None:
                return resultado

    return None


def obtener_cantidad(datos, ruta, clave_elemento):
    """
    Cuenta los elementos de la clave específica de una sección.

    Ejemplo:
    ruta = 'bienesInmuebles'
    clave_elemento = 'bienInmueble'
    """

    seccion = obtener_ruta(datos, ruta)

    if not isinstance(seccion, dict):
        return 0

    elementos = seccion.get(clave_elemento)

    if elementos is None:
        return 0

    if isinstance(elementos, list):
        return len(elementos)

    if isinstance(elementos, dict):
        return 1 if elementos else 0

    return 0


# ==========================================================
# PROCESAMIENTO DE UNA DECLARACIÓN
# ==========================================================

def procesar_declaracion(datos, identificador_auxiliar):

    metadata = datos.get("metadata", {})
    declaracion = datos.get("declaracion", {})

    if not isinstance(metadata, dict):
        metadata = {}

    if not isinstance(declaracion, dict):
        declaracion = {}

    situacion = declaracion.get("situacionPatrimonial", {})

    if not isinstance(situacion, dict):
        situacion = {}

    empleo = situacion.get("datosEmpleoCargoComision", {})

    if not isinstance(empleo, dict):
        empleo = {}

    interes = declaracion.get("interes", {})

    if not isinstance(interes, dict):
        interes = {}

    # ------------------------------------------------------
    # IDENTIFICACIÓN
    # ------------------------------------------------------

    id_declaracion = limpiar_texto(datos.get("id"))

    if not id_declaracion:
        id_declaracion = identificador_auxiliar

    # ------------------------------------------------------
    # DATOS GENERALES
    # ------------------------------------------------------

    tipo_declaracion = limpiar_texto(
        metadata.get("tipo")
    )

    fecha_actualizacion = normalizar_fecha(
        metadata.get("actualizacion")
    )

    institucion = limpiar_texto(
        obtener_primero(metadata, [
            "institucion",
            "nombreInstitucion"
        ])
    )

    declaracion_completa = metadata.get(
        "declaracionCompleta"
    )

    if declaracion_completa is not None:
        declaracion_completa = str(declaracion_completa)

    # ------------------------------------------------------
    # DATOS DEL CARGO
    # ------------------------------------------------------

    cargo = limpiar_texto(
        obtener_primero(empleo, [
            "nombreCargo",
            "cargo",
            "nombreEmpleoCargoComision",
            "empleoCargoComision"
        ])
    )

    nivel_gobierno = limpiar_texto(
        obtener_primero(empleo, [
            "nivelOrdenGobierno",
            "nivelGobierno",
            "nivel"
        ])
    )

    fecha_posesion = normalizar_fecha(
        obtener_primero(empleo, [
            "fechaTomaPosesion",
            "fechaPosesion",
            "fechaInicio"
        ])
    )

    # ------------------------------------------------------
    # INGRESOS
    # ------------------------------------------------------

    ingresos = situacion.get("ingresos")

    ingreso_declarado = None

    if ingresos is not None:

        ingreso_valor = buscar_clave_recursiva(
            ingresos,
            [
                "totalIngresosNetos",
                "totalIngresos",
                "remuneracionNeta",
                "ingresoNeto",
                "valor"
            ]
        )

        ingreso_declarado = convertir_numero(
            ingreso_valor
        )

    # ------------------------------------------------------
    # BIENES Y OBLIGACIONES
    # ------------------------------------------------------

    cantidad_inmuebles = obtener_cantidad(
        situacion, "bienesInmuebles", "bienInmueble"
    )

    cantidad_vehiculos = obtener_cantidad(
        situacion, "vehiculos", "vehiculo"
    )

    cantidad_bienes_muebles = obtener_cantidad(
        situacion, "bienesMuebles", "bienMueble"
    )

    cantidad_inversiones = obtener_cantidad(
        situacion, "inversiones", "inversion"
    )

    cantidad_adeudos = obtener_cantidad(
        situacion, "adeudos", "adeudo"
    )

    cantidad_prestamos = obtener_cantidad(
        situacion, "prestamoOComodato", "prestamo"
    )

    # ------------------------------------------------------
    # INTERESES
    # ------------------------------------------------------

    cantidad_participaciones = obtener_cantidad(
        interes, "participacion", "participacion"
    )

    cantidad_apoyos = obtener_cantidad(
        interes, "apoyos", "apoyo"
    )

    cantidad_beneficios = obtener_cantidad(
        interes, "beneficiosPrivados", "beneficio"
    )

    cantidad_fideicomisos = obtener_cantidad(
        interes, "fideicomisos", "fideicomiso"
    )

    # ------------------------------------------------------
    # REGISTRO RESULTANTE
    # ------------------------------------------------------

    return {
        "id_declaracion": id_declaracion,
        "tipo_declaracion": tipo_declaracion,
        "fecha_actualizacion": fecha_actualizacion,
        "institucion": institucion,
        "cargo": cargo,
        "nivel_gobierno": nivel_gobierno,
        "fecha_posesion": fecha_posesion,
        "declaracion_completa": declaracion_completa,
        "ingreso_declarado": ingreso_declarado,

        "cantidad_inmuebles": cantidad_inmuebles,
        "cantidad_vehiculos": cantidad_vehiculos,
        "cantidad_bienes_muebles": cantidad_bienes_muebles,
        "cantidad_inversiones": cantidad_inversiones,
        "cantidad_adeudos": cantidad_adeudos,
        "cantidad_prestamos": cantidad_prestamos,

        "cantidad_participaciones": cantidad_participaciones,
        "cantidad_apoyos": cantidad_apoyos,
        "cantidad_beneficios": cantidad_beneficios,
        "cantidad_fideicomisos": cantidad_fideicomisos
    }


# ==========================================================
# PROCESAMIENTO DE TODOS LOS ARCHIVOS
# ==========================================================

def crear_dataset():

    print("=" * 60)
    print("MOTOR DE ANÁLISIS PDN - CREACIÓN DEL DATASET")
    print("=" * 60)

    if not DATA_DIR.exists():
        print(f"ERROR: No existe la carpeta: {DATA_DIR}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    archivos = sorted(DATA_DIR.rglob("*.json"))

    if not archivos:
        print("No se encontraron archivos JSON.")
        return

    print(f"\nArchivos JSON encontrados: {len(archivos)}")

    registros = []
    errores = 0
    total_registros = 0

    for indice, archivo in enumerate(archivos, start=1):

        print(
            f"\rProcesando archivo {indice}/{len(archivos)}",
            end="",
            flush=True
        )

        try:
            with open(
                archivo,
                "r",
                encoding="utf-8-sig"
            ) as f:

                contenido = json.load(f)

            if isinstance(contenido, list):
                declaraciones = contenido

            elif isinstance(contenido, dict):
                declaraciones = [contenido]

            else:
                errores += 1
                continue

            for posicion, datos in enumerate(declaraciones):

                if not isinstance(datos, dict):
                    errores += 1
                    continue

                try:
                    identificador_auxiliar = (
                        f"{archivo.relative_to(DATA_DIR)}#{posicion}"
                    )

                    registro = procesar_declaracion(
                        datos,
                        identificador_auxiliar
                    )

                    registros.append(registro)
                    total_registros += 1

                except Exception as error:
                    errores += 1

                    print(
                        f"\nError procesando registro "
                        f"en {archivo.name}: {error}"
                    )

        except (
            json.JSONDecodeError,
            OSError,
            UnicodeDecodeError
        ) as error:

            errores += 1

            print(
                f"\nError leyendo {archivo.name}: {error}"
            )

    print("\n\nProcesamiento finalizado.")

    if not registros:
        print("No se generaron registros. No se creó un CSV vacío.")
        return

    # ------------------------------------------------------
    # GENERAR DATAFRAME Y CSV
    # ------------------------------------------------------

    df = pd.DataFrame(registros)

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # ------------------------------------------------------
    # RESUMEN
    # ------------------------------------------------------

    print("\n" + "=" * 60)
    print("RESUMEN DEL DATASET")
    print("=" * 60)

    print(f"Archivos encontrados: {len(archivos)}")
    print(f"Registros procesados: {total_registros}")
    print(f"Errores: {errores}")
    print(f"Columnas generadas: {len(df.columns)}")

    print("\nArchivo generado:")
    print(OUTPUT_FILE)

    print("\nCantidad de registros por tipo de declaración:")

    print(
        df["tipo_declaracion"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("\nPorcentaje de valores faltantes por columna:")

    faltantes = (
        df.isnull()
        .mean()
        .mul(100)
        .round(2)
        .sort_values(ascending=False)
    )

    print(faltantes.to_string())

    # ------------------------------------------------------
    # FRECUENCIA DE ELEMENTOS DETECTADOS
    # ------------------------------------------------------

    columnas_cantidades = [
        "cantidad_inmuebles",
        "cantidad_vehiculos",
        "cantidad_bienes_muebles",
        "cantidad_inversiones",
        "cantidad_adeudos",
        "cantidad_prestamos",
        "cantidad_participaciones",
        "cantidad_apoyos",
        "cantidad_beneficios",
        "cantidad_fideicomisos"
    ]

    print("\nRegistros con elementos detectados por sección:")

    for columna in columnas_cantidades:

        cantidad = int((df[columna] > 0).sum())
        porcentaje = round(cantidad / len(df) * 100, 2)

        print(
            f"{columna}: {cantidad} "
            f"({porcentaje}%)"
        )

    print("\n" + "=" * 60)
    print("DATASET GENERADO CORRECTAMENTE")
    print("=" * 60)


# ==========================================================
# EJECUCIÓN PRINCIPAL
# ==========================================================

if __name__ == "__main__":
    crear_dataset()
