
import pandas as pd
from pathlib import Path

# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

ARCHIVO_ORIGINAL = (
    BASE_DIR / "datos" / "procesados" / "dataset_pdn.csv"
)

ARCHIVO_ENRIQUECIDO = (
    BASE_DIR / "datos" / "procesados" / "dataset_pdn_enriquecido.csv"
)

# Relación entre las columnas de cantidades y las nuevas variables.
VARIABLES = {
    "cantidad_inmuebles": "tiene_inmuebles",
    "cantidad_vehiculos": "tiene_vehiculos",
    "cantidad_bienes_muebles": "tiene_bienes_muebles",
    "cantidad_inversiones": "tiene_inversiones",
    "cantidad_adeudos": "tiene_adeudos",
    "cantidad_prestamos": "tiene_prestamos",
    "cantidad_participaciones": "tiene_participaciones",
    "cantidad_apoyos": "tiene_apoyos",
    "cantidad_beneficios": "tiene_beneficios_privados",
    "cantidad_fideicomisos": "tiene_fideicomisos"
}


# ============================================================
# 1. VERIFICAR ARCHIVO ORIGINAL
# ============================================================

print("=" * 65)
print("ENRIQUECIMIENTO DEL DATASET PDN")
print("=" * 65)

if not ARCHIVO_ORIGINAL.exists():

    raise FileNotFoundError(
        f"No se encontró el archivo: {ARCHIVO_ORIGINAL}"
    )

print("\nArchivo original encontrado correctamente.")


# ============================================================
# 2. CARGAR DATASET
# ============================================================

df = pd.read_csv(ARCHIVO_ORIGINAL)

print(f"\nRegistros originales: {len(df)}")
print(f"Columnas originales: {len(df.columns)}")


# ============================================================
# 3. VERIFICAR COLUMNAS NECESARIAS
# ============================================================

columnas_faltantes = [
    columna
    for columna in VARIABLES
    if columna not in df.columns
]

if columnas_faltantes:

    raise ValueError(
        "Faltan columnas necesarias en el dataset: "
        + ", ".join(columnas_faltantes)
    )


# ============================================================
# 4. CREAR VARIABLES BOOLEANAS
# ============================================================

print("\nCreando variables derivadas...")

for columna_origen, columna_nueva in VARIABLES.items():

    # Convertir a valores numéricos.
    # Los valores faltantes se mantienen como desconocidos.
    cantidades = pd.to_numeric(
        df[columna_origen],
        errors="coerce"
    )

    # No convertir automáticamente los valores faltantes en False.
    # Una cantidad desconocida no equivale a ausencia de bienes.
    df[columna_nueva] = (
        cantidades.gt(0).where(cantidades.notna())
    ).astype("boolean")

    print(f"  Variable creada: {columna_nueva}")


# ============================================================
# 5. VALIDAR VARIABLES GENERADAS
# ============================================================

print("\nValidación de variables:")

for columna in VARIABLES.values():

    cantidad_true = int(
        (df[columna] == True).sum()
    )

    cantidad_false = int(
        (df[columna] == False).sum()
    )

    cantidad_desconocida = int(
        df[columna].isna().sum()
    )

    print(f"\n{columna}")
    print(f"  True: {cantidad_true}")
    print(f"  False: {cantidad_false}")
    print(f"  Desconocidos: {cantidad_desconocida}")


# ============================================================
# 6. VALIDAR ESTRUCTURA DEL DATASET
# ============================================================

print("\nValidación general:")

print(f"Registros: {len(df)}")
print(f"Columnas: {len(df.columns)}")

columnas_esperadas = 19 + len(VARIABLES)

if len(df.columns) != columnas_esperadas:

    raise ValueError(
        f"Se esperaban {columnas_esperadas} columnas, "
        f"pero se encontraron {len(df.columns)}."
    )

if df.columns.duplicated().any():

    raise ValueError(
        "Se encontraron nombres de columnas duplicados."
    )


# ============================================================
# 7. GUARDAR DATASET ENRIQUECIDO
# ============================================================

df.to_csv(
    ARCHIVO_ENRIQUECIDO,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 8. RESUMEN FINAL
# ============================================================

print("\n" + "=" * 65)
print("RESUMEN DEL ENRIQUECIMIENTO")
print("=" * 65)

print(f"Registros procesados: {len(df)}")
print(f"Columnas originales: 19")
print(f"Variables nuevas: {len(VARIABLES)}")
print(f"Total de columnas: {len(df.columns)}")

print("\nNuevas variables incorporadas:")

for variable in VARIABLES.values():
    print(f"  - {variable}")

print("\nArchivo generado:")
print(ARCHIVO_ENRIQUECIDO)

print("\n" + "=" * 65)
print("DATASET ENRIQUECIDO CORRECTAMENTE")
print("=" * 65)
