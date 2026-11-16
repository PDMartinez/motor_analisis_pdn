import json
from pathlib import Path
import pandas as pd

# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]
CARPETA_ORIGINALES = BASE_DIR / "datos" / "originales"
ARCHIVO_BASE = BASE_DIR / "datos" / "procesados" / "dataset_pdn_enriquecido.csv"
ARCHIVO_SALIDA = BASE_DIR / "datos" / "procesados" / "dataset_pdn_ingresos_validados.csv"

CAMPOS = {
    "INICIAL": ("totalIngresosMensualesNetos", "MENSUAL"),
    "MODIFICACIÓN": ("totalIngresosAnualesNetos", "ANUAL"),
    "CONCLUSIÓN": ("totalIngresosConclusionNetos", "ANUAL"),
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def limpiar_texto(valor):
    if valor is None or isinstance(valor, (dict, list)):
        return None
    texto = str(valor).strip()
    return texto if texto else None


def convertir_numero(valor):
    """
    Conversión estricta: no interpreta separadores ambiguos.
    Sigue el mismo criterio usado en la auditoría de ingresos.
    """
    if valor is None or isinstance(valor, bool):
        return None

    if isinstance(valor, (int, float)):
        numero = float(valor)
        return numero if pd.notna(numero) else None

    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return None
        try:
            numero = float(texto)
            return numero if pd.notna(numero) else None
        except ValueError:
            return None

    return None


def obtener_declaraciones(contenido):
    if isinstance(contenido, list):
        return contenido
    if isinstance(contenido, dict):
        return [contenido]
    raise ValueError("El JSON no contiene una lista ni un objeto válido.")


def extraer_ingreso(datos, identificador_auxiliar):
    metadata = datos.get("metadata")
    declaracion = datos.get("declaracion")

    metadata = metadata if isinstance(metadata, dict) else {}
    declaracion = declaracion if isinstance(declaracion, dict) else {}

    id_declaracion = limpiar_texto(datos.get("id"))
    if not id_declaracion:
        id_declaracion = identificador_auxiliar

    tipo = limpiar_texto(metadata.get("tipo"))

    resultado = {
        "id_declaracion": id_declaracion,
        "tipo_declaracion_json": tipo,
        "ingreso_neto_valor": None,
        "ingreso_neto_moneda": None,
        "ingreso_neto_periodo": None,
        "ingreso_neto_campo_origen": None,
        "ingreso_neto_validacion": None,
    }

    if tipo not in CAMPOS:
        resultado["ingreso_neto_validacion"] = "TIPO_NO_RECONOCIDO"
        return resultado

    campo, periodo = CAMPOS[tipo]
    resultado["ingreso_neto_periodo"] = periodo
    resultado["ingreso_neto_campo_origen"] = (
        f"declaracion.situacionPatrimonial.ingresos.{campo}"
    )

    situacion = declaracion.get("situacionPatrimonial")
    if not isinstance(situacion, dict):
        resultado["ingreso_neto_validacion"] = "SIN_SITUACION_PATRIMONIAL"
        return resultado

    ingresos = situacion.get("ingresos")
    if not isinstance(ingresos, dict):
        resultado["ingreso_neto_validacion"] = "SIN_NODO_INGRESOS"
        return resultado

    if campo not in ingresos:
        resultado["ingreso_neto_validacion"] = "SIN_CAMPO_ESPERADO"
        return resultado

    importe = ingresos.get(campo)
    if importe is None:
        resultado["ingreso_neto_validacion"] = "CAMPO_NULO"
        return resultado

    if not isinstance(importe, dict):
        resultado["ingreso_neto_validacion"] = "CAMPO_NO_ES_OBJETO"
        return resultado

    moneda = limpiar_texto(importe.get("moneda"))
    resultado["ingreso_neto_moneda"] = moneda.upper() if moneda else None

    valor_original = importe.get("valor")
    if valor_original is None:
        resultado["ingreso_neto_validacion"] = "VALOR_NULO"
        return resultado

    if isinstance(valor_original, str) and not valor_original.strip():
        resultado["ingreso_neto_validacion"] = "VALOR_VACIO"
        return resultado

    valor = convertir_numero(valor_original)
    if valor is None:
        resultado["ingreso_neto_validacion"] = "VALOR_NO_NUMERICO"
        return resultado

    resultado["ingreso_neto_valor"] = valor
    resultado["ingreso_neto_validacion"] = (
        "VALIDADO" if moneda else "NUMERICO_SIN_MONEDA"
    )
    return resultado


# ============================================================
# PROCESAMIENTO PRINCIPAL
# ============================================================

def crear_dataset():
    print("=" * 70)
    print("CREACIÓN DEL DATASET DE INGRESOS VALIDADOS")
    print("=" * 70)

    if not CARPETA_ORIGINALES.exists():
        raise FileNotFoundError(f"No existe la carpeta: {CARPETA_ORIGINALES}")

    if not ARCHIVO_BASE.exists():
        raise FileNotFoundError(f"No existe el dataset base: {ARCHIVO_BASE}")

    if ARCHIVO_SALIDA.exists():
        raise FileExistsError(
            "El archivo de salida ya existe y no se sobrescribirá:\n"
            f"{ARCHIVO_SALIDA}"
        )

    # --------------------------------------------------------
    # 1. Cargar dataset enriquecido
    # --------------------------------------------------------

    df_base = pd.read_csv(
        ARCHIVO_BASE,
        dtype={"id_declaracion": "string"},
        encoding="utf-8-sig"
    )

    columnas_requeridas = ["id_declaracion", "tipo_declaracion"]
    faltantes = [c for c in columnas_requeridas if c not in df_base.columns]
    if faltantes:
        raise ValueError(
            "Faltan columnas en el dataset base: " + ", ".join(faltantes)
        )

    df_base["id_declaracion"] = df_base["id_declaracion"].astype("string")

    duplicados = int(
        df_base["id_declaracion"].duplicated(keep=False).sum()
    )

    print(f"Filas del dataset enriquecido: {len(df_base)}")
    print(f"Filas involucradas en IDs duplicados: {duplicados}")
    print("Los IDs duplicados no impedirán la unión por orden verificado.")

    # --------------------------------------------------------
    # 2. Recorrer JSON en el mismo orden que crear_dataset.py
    # --------------------------------------------------------

    archivos = sorted(CARPETA_ORIGINALES.rglob("*.json"))
    if not archivos:
        raise FileNotFoundError("No se encontraron archivos JSON.")

    registros = []
    errores = []

    print(f"Archivos JSON encontrados: {len(archivos)}")

    for indice, archivo in enumerate(archivos, start=1):
        try:
            with open(archivo, "r", encoding="utf-8-sig") as f:
                contenido = json.load(f)

            declaraciones = obtener_declaraciones(contenido)

            for posicion, datos in enumerate(declaraciones):
                if not isinstance(datos, dict):
                    raise ValueError(
                        f"Registro no válido en {archivo.name}, "
                        f"posición {posicion}"
                    )

                id_auxiliar = (
                    f"{archivo.relative_to(CARPETA_ORIGINALES)}#{posicion}"
                )

                registros.append(
                    extraer_ingreso(datos, id_auxiliar)
                )

        except Exception as error:
            errores.append(f"{archivo}: {error}")

        if indice % 100 == 0:
            print(f"Procesados {indice}/{len(archivos)} archivos...")

    if errores:
        print("\nErrores encontrados (primeros 10):")
        for error in errores[:10]:
            print(f" - {error}")
        raise RuntimeError(
            f"Proceso detenido: {len(errores)} archivos con errores. "
            "No se generó el dataset."
        )

    df_ingresos = pd.DataFrame(registros)

    print(f"Registros extraídos de JSON: {len(df_ingresos)}")

    # --------------------------------------------------------
    # 3. Verificar correspondencia por posición
    # --------------------------------------------------------

    if len(df_base) != len(df_ingresos):
        raise ValueError(
            "La cantidad de filas no coincide.\n"
            f"Dataset enriquecido: {len(df_base)}\n"
            f"JSON: {len(df_ingresos)}\n"
            "No se realizará la unión."
        )

    ids_base = df_base["id_declaracion"].fillna("").astype(str).str.strip()
    ids_json = df_ingresos["id_declaracion"].fillna("").astype(str).str.strip()

    diferencias_id = ids_base.ne(ids_json)
    cantidad_diferencias_id = int(diferencias_id.sum())

    if cantidad_diferencias_id:
        posiciones = diferencias_id[diferencias_id].index[:10].tolist()
        raise ValueError(
            "Los identificadores no coinciden en el mismo orden. "
            f"Filas diferentes: {cantidad_diferencias_id}. "
            f"Primeras posiciones: {posiciones}. No se generó el CSV."
        )

    tipos_base = (
        df_base["tipo_declaracion"].fillna("").astype(str).str.strip()
    )
    tipos_json = (
        df_ingresos["tipo_declaracion_json"].fillna("").astype(str).str.strip()
    )

    diferencias_tipo = tipos_base.ne(tipos_json)
    cantidad_diferencias_tipo = int(diferencias_tipo.sum())

    if cantidad_diferencias_tipo:
        posiciones = diferencias_tipo[diferencias_tipo].index[:10].tolist()
        raise ValueError(
            "Los tipos de declaración no coinciden en el mismo orden. "
            f"Filas diferentes: {cantidad_diferencias_tipo}. "
            f"Primeras posiciones: {posiciones}. No se generó el CSV."
        )

    print("Cantidad de filas: coincide.")
    print("Secuencia de identificadores: coincide.")
    print("Secuencia de tipos de declaración: coincide.")

    # --------------------------------------------------------
    # 4. Incorporar columnas por posición verificada
    # --------------------------------------------------------

    columnas_nuevas = [
        "ingreso_neto_valor",
        "ingreso_neto_moneda",
        "ingreso_neto_periodo",
        "ingreso_neto_campo_origen",
        "ingreso_neto_validacion",
    ]

    df_final = df_base.copy()

    for columna in columnas_nuevas:
        df_final[columna] = df_ingresos[columna].to_numpy()

    if len(df_final) != len(df_base):
        raise ValueError("Cambió la cantidad de filas al incorporar ingresos.")

    # --------------------------------------------------------
    # 5. Validar y guardar
    # --------------------------------------------------------

    conteos = df_final["ingreso_neto_validacion"].value_counts(dropna=False)

    df_final.to_csv(
        ARCHIVO_SALIDA,
        index=False,
        encoding="utf-8-sig"
    )

    print("\n" + "=" * 70)
    print("DATASET DE INGRESOS VALIDADOS GENERADO")
    print("=" * 70)
    print(f"Archivos JSON: {len(archivos)}")
    print(f"Filas base: {len(df_base)}")
    print(f"Filas extraídas: {len(df_ingresos)}")
    print(f"Filas finales: {len(df_final)}")
    print(f"Columnas finales: {len(df_final.columns)}")

    print("\nEstados de validación:")
    print(conteos.to_string())

    print("\nTipos de declaración:")
    print(df_final["tipo_declaracion"].value_counts(dropna=False).to_string())

    print(f"\nArchivo generado: {ARCHIVO_SALIDA}")
    print("No se modificaron los JSON originales ni el dataset enriquecido.")
    print("=" * 70)


if __name__ == "__main__":
    crear_dataset()
