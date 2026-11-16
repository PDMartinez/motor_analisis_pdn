
import json
import csv
from pathlib import Path
from collections import Counter, defaultdict

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

CARPETA_ORIGINALES = BASE_DIR / "datos" / "originales"
CARPETA_RESULTADOS = (
    BASE_DIR / "resultados" / "auditoria_valores_ingresos"
)

CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)

ARCHIVO_REPORTE = CARPETA_RESULTADOS / "reporte_valores_ingresos.txt"
ARCHIVO_CSV = CARPETA_RESULTADOS / "estadisticas_valores_ingresos.csv"


# Cada tipo de declaración tiene un campo total diferente.
CAMPOS_INGRESOS = {
    "INICIAL": (
        "totalIngresosMensualesNetos",
        "MENSUAL"
    ),
    "MODIFICACIÓN": (
        "totalIngresosAnualesNetos",
        "ANUAL"
    ),
    "CONCLUSIÓN": (
        "totalIngresosConclusionNetos",
        "ANUAL"
    )
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def obtener_archivos_json():
    return list(CARPETA_ORIGINALES.rglob("*.json"))


def convertir_numero(valor):
    """
    Convierte valores numéricos sin asumir separadores
    de miles o decimales que no hayan sido validados.
    """

    if valor is None or isinstance(valor, bool):
        return None

    if isinstance(valor, (int, float)):
        numero = float(valor)
        return numero if np.isfinite(numero) else None

    if isinstance(valor, str):
        texto = valor.strip()

        if not texto:
            return None

        # No se eliminan comas ni puntos automáticamente:
        # su significado depende del formato de origen.
        try:
            numero = float(texto)
            return numero if np.isfinite(numero) else None
        except ValueError:
            return None

    return None


def cargar_declaraciones(datos):
    """
    Admite archivos JSON que contengan una declaración
    o una lista de declaraciones.
    """

    if isinstance(datos, list):
        return datos

    if isinstance(datos, dict):
        # Formatos habituales de contenedor.
        for clave in ("datos", "results", "resultados"):
            if isinstance(datos.get(clave), list):
                return datos[clave]

        return [datos]

    return []


def obtener_estadisticas(valores):
    serie = pd.Series(valores, dtype="float64")

    if serie.empty:
        return {
            "cantidad": 0,
            "minimo": None,
            "maximo": None,
            "media": None,
            "mediana": None,
            "p25": None,
            "p75": None,
            "p90": None,
            "p95": None,
            "p99": None
        }

    return {
        "cantidad": int(serie.count()),
        "minimo": float(serie.min()),
        "maximo": float(serie.max()),
        "media": float(serie.mean()),
        "mediana": float(serie.median()),
        "p25": float(serie.quantile(0.25)),
        "p75": float(serie.quantile(0.75)),
        "p90": float(serie.quantile(0.90)),
        "p95": float(serie.quantile(0.95)),
        "p99": float(serie.quantile(0.99))
    }


# ============================================================
# PROCESAMIENTO PRINCIPAL
# ============================================================

def auditar():

    archivos = obtener_archivos_json()

    print("=" * 65)
    print("AUDITORÍA DE VALORES DE INGRESOS")
    print("=" * 65)
    print(f"Archivos encontrados: {len(archivos)}")

    conteos = Counter()
    valores_por_grupo = defaultdict(list)
    registros_por_grupo = Counter()
    monedas_por_grupo = Counter()

    errores_json = 0
    total_declaraciones = 0

    for indice, archivo in enumerate(archivos, start=1):

        try:
            with open(archivo, "r", encoding="utf-8") as f:
                datos = json.load(f)

        except Exception:
            errores_json += 1
            continue

        declaraciones = cargar_declaraciones(datos)

        for registro in declaraciones:

            if not isinstance(registro, dict):
                continue

            total_declaraciones += 1
            conteos["declaraciones"] += 1

            metadata = registro.get("metadata", {})
            declaracion = registro.get("declaracion", {})

            if not isinstance(metadata, dict):
                metadata = {}

            if not isinstance(declaracion, dict):
                declaracion = {}

            tipo = metadata.get("tipo", "SIN_TIPO")

            if tipo not in CAMPOS_INGRESOS:
                conteos["tipo_no_reconocido"] += 1
                continue

            campo, periodo = CAMPOS_INGRESOS[tipo]

            situacion = declaracion.get("situacionPatrimonial", {})

            if not isinstance(situacion, dict):
                conteos["sin_situacion_patrimonial"] += 1
                continue

            ingresos = situacion.get("ingresos")

            if not isinstance(ingresos, dict):
                conteos["sin_nodo_ingresos"] += 1
                continue

            if campo not in ingresos:
                conteos[f"sin_campo_{tipo}"] += 1
                continue

            importe = ingresos.get(campo)

            if importe is None:
                conteos["campo_nulo"] += 1
                continue

            if not isinstance(importe, dict):
                conteos["campo_no_es_objeto"] += 1
                continue

            moneda = importe.get("moneda")

            if moneda is None or str(moneda).strip() == "":
                moneda = "SIN_MONEDA"
            else:
                moneda = str(moneda).strip().upper()

            valor_original = importe.get("valor")

            if valor_original is None:
                conteos["valor_nulo"] += 1
                continue

            if isinstance(valor_original, str) and not valor_original.strip():
                conteos["valor_vacio"] += 1
                continue

            valor = convertir_numero(valor_original)

            if valor is None:
                conteos["valor_no_numerico"] += 1
                continue

            conteos["valores_numericos"] += 1

            if valor == 0:
                conteos["valores_cero"] += 1
            elif valor < 0:
                conteos["valores_negativos"] += 1
            else:
                conteos["valores_positivos"] += 1

            grupo = (tipo, periodo, moneda)

            valores_por_grupo[grupo].append(valor)
            registros_por_grupo[grupo] += 1
            monedas_por_grupo[(tipo, moneda)] += 1

        if indice % 100 == 0:
            print(f"Procesados {indice}/{len(archivos)} archivos...")

    # ========================================================
    # GENERAR ESTADÍSTICAS AGREGADAS
    # ========================================================

    filas_csv = []

    for grupo, valores in sorted(valores_por_grupo.items()):

        tipo, periodo, moneda = grupo
        estadisticas = obtener_estadisticas(valores)

        filas_csv.append({
            "tipo_declaracion": tipo,
            "periodo": periodo,
            "moneda": moneda,
            **estadisticas
        })

    columnas = [
        "tipo_declaracion",
        "periodo",
        "moneda",
        "cantidad",
        "minimo",
        "maximo",
        "media",
        "mediana",
        "p25",
        "p75",
        "p90",
        "p95",
        "p99"
    ]

    with open(
        ARCHIVO_CSV,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as archivo_csv:

        escritor = csv.DictWriter(
            archivo_csv,
            fieldnames=columnas
        )

        escritor.writeheader()
        escritor.writerows(filas_csv)

    # ========================================================
    # GENERAR REPORTE TXT
    # ========================================================

    lineas = []

    lineas.append("=" * 70)
    lineas.append("REPORTE DE AUDITORÍA DE VALORES DE INGRESOS")
    lineas.append("=" * 70)

    lineas.append(f"Archivos encontrados: {len(archivos)}")
    lineas.append(f"Declaraciones procesadas: {total_declaraciones}")
    lineas.append(f"Errores al leer JSON: {errores_json}")

    lineas.append("")
    lineas.append("RESUMEN DE REGISTROS")
    lineas.append("-" * 70)

    for clave, cantidad in sorted(conteos.items()):
        lineas.append(f"{clave}: {cantidad}")

    lineas.append("")
    lineas.append("ESTADÍSTICAS POR TIPO, PERIODO Y MONEDA")
    lineas.append("-" * 70)

    for fila in filas_csv:

        lineas.append("")
        lineas.append(
            f"Tipo: {fila['tipo_declaracion']} | "
            f"Periodo: {fila['periodo']} | "
            f"Moneda: {fila['moneda']}"
        )

        for campo in columnas[3:]:
            valor = fila[campo]

            if valor is None:
                texto = "Sin datos"
            else:
                texto = f"{valor:,.2f}"

            lineas.append(f"  {campo}: {texto}")

    lineas.append("")
    lineas.append("OBSERVACIONES METODOLÓGICAS")
    lineas.append("-" * 70)
    lineas.append(
        "Los ingresos INICIALES corresponden a un campo mensual."
    )
    lineas.append(
        "Los ingresos de MODIFICACIÓN y CONCLUSIÓN corresponden "
        "a campos anuales."
    )
    lineas.append(
        "Las estadísticas se separan por moneda y tipo de declaración."
    )
    lineas.append(
        "No se realizó conversión de moneda ni normalización mensual/anual."
    )
    lineas.append(
        "Los valores no numéricos no fueron incluidos en las estadísticas."
    )
    lineas.append(
        "Este análisis describe los datos y no determina irregularidades."
    )

    with open(
        ARCHIVO_REPORTE,
        "w",
        encoding="utf-8"
    ) as archivo_txt:

        archivo_txt.write("\n".join(lineas))

    # ========================================================
    # RESULTADO FINAL
    # ========================================================

    print("\n" + "=" * 65)
    print("AUDITORÍA FINALIZADA")
    print("=" * 65)

    print(f"Declaraciones procesadas: {total_declaraciones}")
    print(f"Errores JSON: {errores_json}")
    print(f"Valores numéricos válidos: {conteos['valores_numericos']}")
    print(f"Valores cero: {conteos['valores_cero']}")
    print(f"Valores negativos: {conteos['valores_negativos']}")
    print(f"Valores positivos: {conteos['valores_positivos']}")

    print("\nArchivos generados:")
    print(ARCHIVO_REPORTE)
    print(ARCHIVO_CSV)


if __name__ == "__main__":
    auditar()
