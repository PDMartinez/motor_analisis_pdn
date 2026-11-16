
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path

# ============================================================
# 1. CONFIGURACIÓN DE RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

ARCHIVO_DATASET = (
    BASE_DIR / "datos" / "procesados" /
    "dataset_pdn_enriquecido.csv"
)

CARPETA_RESULTADOS = BASE_DIR / "resultados"
CARPETA_GRAFICOS = CARPETA_RESULTADOS / "graficos"

CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)
CARPETA_GRAFICOS.mkdir(parents=True, exist_ok=True)

ARCHIVO_INFORME = CARPETA_RESULTADOS / "informe_eda.txt"


# ============================================================
# 2. CARGAR DATASET
# ============================================================

def cargar_dataset():

    if not ARCHIVO_DATASET.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo: {ARCHIVO_DATASET}"
        )

    df = pd.read_csv(ARCHIVO_DATASET)

    print("\n========================================")
    print("ANÁLISIS EXPLORATORIO DE DATOS - PDN")
    print("========================================")

    print(f"Registros: {len(df):,}")
    print(f"Columnas: {len(df.columns)}")

    return df


# ============================================================
# 3. PREPARAR INFORME
# ============================================================

def agregar_informe(texto):

    with open(
        ARCHIVO_INFORME,
        "a",
        encoding="utf-8"
    ) as archivo:

        archivo.write(texto + "\n")


# ============================================================
# 4. INFORMACIÓN GENERAL
# ============================================================

def analizar_informacion_general(df):

    print("\n[1] INFORMACIÓN GENERAL")

    agregar_informe("ANÁLISIS EXPLORATORIO DE DATOS - PDN")
    agregar_informe("=" * 60)

    agregar_informe(f"Registros: {len(df):,}")
    agregar_informe(f"Columnas: {len(df.columns)}")

    agregar_informe("\nValores faltantes por columna:")

    faltantes = df.isnull().sum()

    for columna, cantidad in faltantes.items():

        agregar_informe(
            f"{columna}: {cantidad:,}"
        )

    print("Información general procesada.")


# ============================================================
# 5. DISTRIBUCIÓN DE TIPOS DE DECLARACIONES
# ============================================================

def analizar_tipos_declaraciones(df):

    print("\n[2] TIPOS DE DECLARACIONES")

    distribucion = df["tipo_declaracion"].value_counts(
        dropna=False
    )

    print(distribucion)

    agregar_informe("\nDISTRIBUCIÓN DE TIPOS DE DECLARACIONES")
    agregar_informe(str(distribucion))

    plt.figure(figsize=(9, 5))

    distribucion.plot(kind="bar")

    plt.title("Distribución de tipos de declaraciones")
    plt.xlabel("Tipo de declaración")
    plt.ylabel("Cantidad de registros")
    plt.xticks(rotation=0)
    plt.tight_layout()

    plt.savefig(
        CARPETA_GRAFICOS / "tipos_declaraciones.png"
    )

    plt.close()


# ============================================================
# 6. FRECUENCIA DE BIENES Y ACTIVOS
# ============================================================

def analizar_bienes(df):

    print("\n[3] FRECUENCIA DE BIENES Y ACTIVOS")

    columnas = [
        "tiene_inmuebles",
        "tiene_vehiculos",
        "tiene_bienes_muebles",
        "tiene_inversiones",
        "tiene_adeudos",
        "tiene_prestamos",
        "tiene_participaciones",
        "tiene_apoyos",
        "tiene_beneficios_privados",
        "tiene_fideicomisos"
    ]

    resultados = {}

    for columna in columnas:

        if columna in df.columns:

            resultados[columna] = int(
                df[columna].fillna(False).sum()
            )

    serie = pd.Series(resultados)

    print(serie)

    agregar_informe("\nFRECUENCIA DE BIENES Y ACTIVOS")
    agregar_informe(str(serie))

    plt.figure(figsize=(12, 6))

    serie.plot(kind="bar")

    plt.title("Frecuencia de bienes y activos declarados")
    plt.xlabel("Categoría")
    plt.ylabel("Cantidad de declaraciones")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    plt.savefig(
        CARPETA_GRAFICOS / "frecuencia_bienes_activos.png"
    )

    plt.close()


# ============================================================
# 7. CANTIDAD DE CATEGORÍAS PATRIMONIALES
# ============================================================

def analizar_categorias_patrimoniales(df):

    print("\n[4] CATEGORÍAS PATRIMONIALES")

    columnas = [
        "tiene_inmuebles",
        "tiene_vehiculos",
        "tiene_bienes_muebles",
        "tiene_inversiones",
        "tiene_adeudos",
        "tiene_prestamos",
        "tiene_participaciones",
        "tiene_apoyos",
        "tiene_beneficios_privados",
        "tiene_fideicomisos"
    ]

    disponibles = [
        columna for columna in columnas
        if columna in df.columns
    ]

    # No convertir valores desconocidos en False.
    cantidad = df[disponibles].sum(
        axis=1,
        min_count=1
    )

    distribucion = cantidad.value_counts().sort_index()

    print(distribucion)

    agregar_informe(
        "\nCANTIDAD DE CATEGORÍAS PATRIMONIALES POR DECLARACIÓN"
    )

    agregar_informe(str(distribucion))

    plt.figure(figsize=(9, 5))

    distribucion.plot(kind="bar")

    plt.title("Categorías patrimoniales por declaración")
    plt.xlabel("Cantidad de categorías")
    plt.ylabel("Cantidad de declaraciones")
    plt.tight_layout()

    plt.savefig(
        CARPETA_GRAFICOS / "categorias_patrimoniales.png"
    )

    plt.close()


# ============================================================
# 8. ANÁLISIS PRELIMINAR DE INGRESOS
# ============================================================

def analizar_ingresos(df):

    print("\n[5] ANÁLISIS PRELIMINAR DE INGRESOS")

    if "ingreso_declarado" not in df.columns:
        print("No existe la columna ingreso_declarado.")
        return

    ingresos = pd.to_numeric(
        df["ingreso_declarado"],
        errors="coerce"
    )

    validos = ingresos.dropna()

    agregar_informe("\nANÁLISIS PRELIMINAR DE INGRESOS")

    agregar_informe(
        f"Valores numéricos válidos: {len(validos):,}"
    )

    agregar_informe(
        f"Valores no interpretables como número: {ingresos.isna().sum():,}"
    )

    if validos.empty:
        print("No hay valores numéricos para analizar.")
        return

    estadisticas = validos.describe(
        percentiles=[0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
    )

    print(estadisticas)

    agregar_informe(str(estadisticas))

    agregar_informe(
        "\nADVERTENCIA: Los ingresos son preliminares. "
        "Debe validarse la extracción y el significado del campo "
        "antes de interpretar los importes."
    )

    plt.figure(figsize=(9, 5))

    plt.hist(validos, bins=30)

    plt.title("Distribución preliminar de ingresos declarados")
    plt.xlabel("Valor extraído")
    plt.ylabel("Frecuencia")
    plt.tight_layout()

    plt.savefig(
        CARPETA_GRAFICOS / "distribucion_ingresos.png"
    )

    plt.close()


# ============================================================
# 9. DISTRIBUCIÓN POR INSTITUCIONES
# ============================================================

def analizar_instituciones(df):

    print("\n[6] INSTITUCIONES")

    if "institucion" not in df.columns:
        return

    top = df["institucion"].value_counts().head(15)

    print(top)

    agregar_informe("\nTOP 15 INSTITUCIONES")
    agregar_informe(str(top))

    plt.figure(figsize=(12, 7))

    top.sort_values().plot(kind="barh")

    plt.title("15 instituciones con mayor cantidad de declaraciones")
    plt.xlabel("Cantidad de declaraciones")
    plt.ylabel("Institución")
    plt.tight_layout()

    plt.savefig(
        CARPETA_GRAFICOS / "top_instituciones.png"
    )

    plt.close()


# ============================================================
# 10. ANÁLISIS TEMPORAL
# ============================================================

def analizar_fechas(df):

    print("\n[7] ANÁLISIS TEMPORAL")

    if "fecha_actualizacion" not in df.columns:
        return

    fechas = pd.to_datetime(
        df["fecha_actualizacion"],
        errors="coerce"
    )

    anios = fechas.dt.year.value_counts().sort_index()

    print(anios)

    agregar_informe("\nREGISTROS POR AÑO DE ACTUALIZACIÓN")
    agregar_informe(str(anios))

    plt.figure(figsize=(10, 5))

    anios.plot(kind="bar")

    plt.title("Declaraciones por año de actualización del registro")
    plt.xlabel("Año")
    plt.ylabel("Cantidad de registros")
    plt.tight_layout()

    plt.savefig(
        CARPETA_GRAFICOS / "registros_por_anio.png"
    )

    plt.close()

    agregar_informe(
        "\nNOTA: fecha_actualizacion representa la actualización "
        "del registro y no necesariamente la fecha de adquisición "
        "de un bien."
    )


# ============================================================
# 11. EJECUCIÓN PRINCIPAL
# ============================================================

def main():

    # Reiniciar el informe
    if ARCHIVO_INFORME.exists():
        ARCHIVO_INFORME.unlink()

    df = cargar_dataset()

    analizar_informacion_general(df)
    analizar_tipos_declaraciones(df)
    analizar_bienes(df)
    analizar_categorias_patrimoniales(df)
    analizar_ingresos(df)
    analizar_instituciones(df)
    analizar_fechas(df)

    print("\n========================================")
    print("ANÁLISIS FINALIZADO")
    print("========================================")

    print(f"Informe: {ARCHIVO_INFORME}")
    print(f"Gráficos: {CARPETA_GRAFICOS}")

    agregar_informe(
        "\n\nANÁLISIS EXPLORATORIO FINALIZADO."
    )


if __name__ == "__main__":
    main()
