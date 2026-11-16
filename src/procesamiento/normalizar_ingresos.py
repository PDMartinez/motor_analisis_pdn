
from pathlib import Path
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

ARCHIVO_ENTRADA = (
    BASE_DIR
    / "datos"
    / "procesados"
    / "dataset_pdn_ingresos_validados.csv"
)

ARCHIVO_SALIDA = (
    BASE_DIR
    / "datos"
    / "procesados"
    / "dataset_pdn_normalizado.csv"
)


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalizar_ingresos():

    print("=" * 70)
    print("NORMALIZACIÓN DE INGRESOS DE LA PDN")
    print("=" * 70)

    if not ARCHIVO_ENTRADA.exists():
        raise FileNotFoundError(
            f"No se encontró el dataset:\n{ARCHIVO_ENTRADA}"
        )

    if ARCHIVO_SALIDA.exists():
        raise FileExistsError(
            "El dataset normalizado ya existe. "
            "No será sobrescrito:\n"
            f"{ARCHIVO_SALIDA}"
        )

    print("\nLeyendo dataset original...")

    df = pd.read_csv(ARCHIVO_ENTRADA)

    filas_originales = len(df)

    print(f"Registros encontrados: {filas_originales:,}")

    # --------------------------------------------------------
    # 1. Verificar columnas
    # --------------------------------------------------------

    columnas_requeridas = [
        "tipo_declaracion",
        "ingreso_neto_valor",
        "ingreso_neto_moneda",
        "ingreso_neto_periodo",
        "ingreso_neto_validacion",
    ]

    faltantes = [
        columna
        for columna in columnas_requeridas
        if columna not in df.columns
    ]

    if faltantes:
        raise ValueError(
            "Faltan columnas necesarias: "
            + ", ".join(faltantes)
        )

    # --------------------------------------------------------
    # 2. Preparar los datos
    # --------------------------------------------------------

    valores = pd.to_numeric(
        df["ingreso_neto_valor"],
        errors="coerce"
    )

    tipos = (
        df["tipo_declaracion"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    periodos = (
        df["ingreso_neto_periodo"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    monedas = (
        df["ingreso_neto_moneda"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    estados = (
        df["ingreso_neto_validacion"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # --------------------------------------------------------
    # 3. Identificar registros válidos
    # --------------------------------------------------------

    validos = (
        estados.eq("VALIDADO")
        & valores.notna()
        & monedas.eq("MXN")
    )

    if validos.sum() != 208797:
        raise ValueError(
            "La cantidad de ingresos validados no coincide "
            "con la auditoría anterior. Se detiene el proceso."
        )

    # --------------------------------------------------------
    # 4. Verificar tipo y período
    # --------------------------------------------------------

    condiciones = {
        "INICIAL": "MENSUAL",
        "MODIFICACIÓN": "ANUAL",
        "CONCLUSIÓN": "ANUAL",
    }

    for tipo, periodo_esperado in condiciones.items():

        mascara = validos & tipos.eq(tipo)

        incorrectos = (
            mascara
            & ~periodos.eq(periodo_esperado)
        )

        if incorrectos.any():
            raise ValueError(
                f"Se encontraron períodos incorrectos "
                f"para {tipo}."
            )

    tipos_no_reconocidos = (
        validos
        & ~tipos.isin(condiciones.keys())
    )

    if tipos_no_reconocidos.any():
        raise ValueError(
            "Existen tipos de declaración no reconocidos."
        )

    # --------------------------------------------------------
    # 5. Crear columnas normalizadas
    # --------------------------------------------------------

    # Se mantienen los valores originales.
    # Los registros no validados permanecen como NaN.

    ingreso_anual = pd.Series(
        float("nan"),
        index=df.index,
        dtype="float64"
    )

    ingreso_mensual = pd.Series(
        float("nan"),
        index=df.index,
        dtype="float64"
    )

    # Declaraciones iniciales:
    # el valor original es mensual.
    iniciales = validos & tipos.eq("INICIAL")

    ingreso_anual.loc[iniciales] = (
        valores.loc[iniciales] * 12
    )

    ingreso_mensual.loc[iniciales] = (
        valores.loc[iniciales]
    )

    # Declaraciones de modificación:
    # el valor original es anual.
    modificaciones = (
        validos & tipos.eq("MODIFICACIÓN")
    )

    ingreso_anual.loc[modificaciones] = (
        valores.loc[modificaciones]
    )

    ingreso_mensual.loc[modificaciones] = (
        valores.loc[modificaciones] / 12
    )

    # Declaraciones de conclusión:
    # el valor original es anual.
    conclusiones = (
        validos & tipos.eq("CONCLUSIÓN")
    )

    ingreso_anual.loc[conclusiones] = (
        valores.loc[conclusiones]
    )

    ingreso_mensual.loc[conclusiones] = (
        valores.loc[conclusiones] / 12
    )

    # --------------------------------------------------------
    # 6. Incorporar columnas al dataset
    # --------------------------------------------------------

    df["ingreso_neto_anual_equivalente"] = ingreso_anual

    df["ingreso_neto_mensual_equivalente"] = ingreso_mensual

    df["ingreso_neto_normalizacion"] = "NO_NORMALIZADO"

    df.loc[iniciales, "ingreso_neto_normalizacion"] = (
        "MENSUAL_A_ANUAL_X12"
    )

    df.loc[modificaciones, "ingreso_neto_normalizacion"] = (
        "ANUAL_CONSERVADO"
    )

    df.loc[conclusiones, "ingreso_neto_normalizacion"] = (
        "ANUAL_CONSERVADO"
    )

    # --------------------------------------------------------
    # 7. Verificaciones finales
    # --------------------------------------------------------

    if len(df) != filas_originales:
        raise ValueError(
            "La cantidad de filas cambió durante el proceso."
        )

    if df["ingreso_neto_anual_equivalente"].notna().sum() != 208797:
        raise ValueError(
            "La cantidad de ingresos anuales normalizados "
            "no coincide con la cantidad esperada."
        )

    if df["ingreso_neto_mensual_equivalente"].notna().sum() != 208797:
        raise ValueError(
            "La cantidad de ingresos mensuales equivalentes "
            "no coincide con la cantidad esperada."
        )

    # Comprobar que no se generaron valores negativos.
    if (df["ingreso_neto_anual_equivalente"].dropna() < 0).any():
        raise ValueError(
            "Se detectaron ingresos anuales negativos."
        )

    if (df["ingreso_neto_mensual_equivalente"].dropna() < 0).any():
        raise ValueError(
            "Se detectaron ingresos mensuales negativos."
        )

    # --------------------------------------------------------
    # 8. Guardar nuevo dataset
    # --------------------------------------------------------

    df.to_csv(
        ARCHIVO_SALIDA,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # 9. Mostrar resultados
    # --------------------------------------------------------

    print("\nNORMALIZACIÓN COMPLETADA")
    print("-" * 70)

    print(f"Filas originales: {filas_originales:,}")
    print(f"Filas finales: {len(df):,}")
    print(f"Columnas finales: {len(df.columns)}")

    print("\nRegistros normalizados por tipo:")

    print(
        f"INICIAL: {iniciales.sum():,}"
    )

    print(
        f"MODIFICACIÓN: {modificaciones.sum():,}"
    )

    print(
        f"CONCLUSIÓN: {conclusiones.sum():,}"
    )

    print(
        f"\nIngresos normalizados: {validos.sum():,}"
    )

    print(
        f"Registros sin ingreso validado: {(~validos).sum():,}"
    )

    print("\nNuevas columnas:")

    print("- ingreso_neto_anual_equivalente")
    print("- ingreso_neto_mensual_equivalente")
    print("- ingreso_neto_normalizacion")

    print("\nArchivo generado:")
    print(ARCHIVO_SALIDA)

    print("\nLos archivos originales no fueron modificados.")


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    try:
        normalizar_ingresos()

    except Exception as error:
        print("\nERROR DURANTE LA NORMALIZACIÓN")
        print(error)
