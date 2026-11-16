
from pathlib import Path
import pandas as pd
import numpy as np
from pandas.testing import assert_frame_equal


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

ARCHIVO_ORIGINAL = (
    BASE_DIR
    / "datos"
    / "procesados"
    / "dataset_pdn_ingresos_validados.csv"
)

ARCHIVO_NORMALIZADO = (
    BASE_DIR
    / "datos"
    / "procesados"
    / "dataset_pdn_normalizado.csv"
)

INFORME = (
    BASE_DIR
    / "resultados"
    / "auditoria_normalizacion.txt"
)


# ============================================================
# AUDITORÍA
# ============================================================

def auditar():

    print("=" * 70)
    print("AUDITORÍA DEL DATASET NORMALIZADO")
    print("=" * 70)

    if not ARCHIVO_ORIGINAL.exists():
        raise FileNotFoundError(ARCHIVO_ORIGINAL)

    if not ARCHIVO_NORMALIZADO.exists():
        raise FileNotFoundError(ARCHIVO_NORMALIZADO)

    if INFORME.exists():
        raise FileExistsError(
            f"El informe ya existe y no será sobrescrito:\n{INFORME}"
        )

    print("\nLeyendo archivos...")

    original = pd.read_csv(ARCHIVO_ORIGINAL)
    normalizado = pd.read_csv(ARCHIVO_NORMALIZADO)

    # --------------------------------------------------------
    # 1. Verificar dimensiones
    # --------------------------------------------------------

    if len(original) != len(normalizado):
        raise ValueError("La cantidad de filas no coincide.")

    if len(original) != 208800:
        raise ValueError("La cantidad de filas no coincide con la esperada.")

    # --------------------------------------------------------
    # 2. Verificar conservación de columnas originales
    # --------------------------------------------------------

    columnas_originales = list(original.columns)

    faltantes = [
        c for c in columnas_originales
        if c not in normalizado.columns
    ]

    if faltantes:
        raise ValueError(
            "Faltan columnas originales: " + ", ".join(faltantes)
        )

    # Comparar los 34 campos originales, incluyendo el orden de filas.
    assert_frame_equal(
        original[columnas_originales],
        normalizado[columnas_originales],
        check_dtype=True,
        check_exact=True
    )

    print("Columnas originales: conservadas sin cambios.")

    # --------------------------------------------------------
    # 3. Verificar columnas nuevas
    # --------------------------------------------------------

    nuevas = [
        "ingreso_neto_anual_equivalente",
        "ingreso_neto_mensual_equivalente",
        "ingreso_neto_normalizacion",
    ]

    for columna in nuevas:
        if columna not in normalizado.columns:
            raise ValueError(f"Falta la columna: {columna}")

    if len(normalizado.columns) != 37:
        raise ValueError("La cantidad de columnas no es 37.")

    # --------------------------------------------------------
    # 4. Preparar datos
    # --------------------------------------------------------

    valor = pd.to_numeric(
        normalizado["ingreso_neto_valor"],
        errors="coerce"
    )

    anual = pd.to_numeric(
        normalizado["ingreso_neto_anual_equivalente"],
        errors="coerce"
    )

    mensual = pd.to_numeric(
        normalizado["ingreso_neto_mensual_equivalente"],
        errors="coerce"
    )

    tipo = (
        normalizado["tipo_declaracion"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    estado = (
        normalizado["ingreso_neto_validacion"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    metodo = (
        normalizado["ingreso_neto_normalizacion"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    validos = estado.eq("VALIDADO")

    inicial = validos & tipo.eq("INICIAL")
    modificacion = validos & tipo.eq("MODIFICACIÓN")
    conclusion = validos & tipo.eq("CONCLUSIÓN")

    # --------------------------------------------------------
    # 5. Verificar fórmulas
    # --------------------------------------------------------

    errores_inicial = (
        ~np.isclose(
            anual[inicial],
            valor[inicial] * 12,
            rtol=1e-10,
            atol=1e-8
        )
    ).sum()

    errores_mensual_inicial = (
        ~np.isclose(
            mensual[inicial],
            valor[inicial],
            rtol=1e-10,
            atol=1e-8
        )
    ).sum()

    mascara_anuales = modificacion | conclusion

    errores_anual = (
        ~np.isclose(
            anual[mascara_anuales],
            valor[mascara_anuales],
            rtol=1e-10,
            atol=1e-8
        )
    ).sum()

    errores_mensual_anual = (
        ~np.isclose(
            mensual[mascara_anuales],
            valor[mascara_anuales] / 12,
            rtol=1e-10,
            atol=1e-8
        )
    ).sum()

    # --------------------------------------------------------
    # 6. Verificar etiquetas de normalización
    # --------------------------------------------------------

    errores_etiquetas = 0

    errores_etiquetas += (
        metodo[inicial] != "MENSUAL_A_ANUAL_X12"
    ).sum()

    errores_etiquetas += (
        metodo[modificacion] != "ANUAL_CONSERVADO"
    ).sum()

    errores_etiquetas += (
        metodo[conclusion] != "ANUAL_CONSERVADO"
    ).sum()

    # --------------------------------------------------------
    # 7. Verificar registros sin ingreso validado
    # --------------------------------------------------------

    sin_validar = ~validos

    sin_valor_anual = anual[sin_validar].notna().sum()
    sin_valor_mensual = mensual[sin_validar].notna().sum()

    etiquetas_sin_validar = (
        metodo[sin_validar] == "NO_NORMALIZADO"
    ).sum()

    # --------------------------------------------------------
    # 8. Verificar valores negativos y nulos
    # --------------------------------------------------------

    negativos_anuales = (anual.dropna() < 0).sum()
    negativos_mensuales = (mensual.dropna() < 0).sum()

    cantidad_anual = anual.notna().sum()
    cantidad_mensual = mensual.notna().sum()

    # --------------------------------------------------------
    # 9. Resultado agregado
    # --------------------------------------------------------

    resultados = {
        "Filas originales": len(original),
        "Filas normalizadas": len(normalizado),
        "Columnas originales": len(columnas_originales),
        "Columnas finales": len(normalizado.columns),
        "Ingresos validados": validos.sum(),
        "Declaraciones iniciales": inicial.sum(),
        "Declaraciones de modificación": modificacion.sum(),
        "Declaraciones de conclusión": conclusion.sum(),
        "Valores anuales equivalentes": cantidad_anual,
        "Valores mensuales equivalentes": cantidad_mensual,
        "Errores fórmula anual inicial": errores_inicial,
        "Errores fórmula mensual inicial": errores_mensual_inicial,
        "Errores fórmula anual modificación/conclusión": errores_anual,
        "Errores fórmula mensual modificación/conclusión": errores_mensual_anual,
        "Errores de etiquetas": errores_etiquetas,
        "Registros sin validar": sin_validar.sum(),
        "Registros sin validar con valor anual": sin_valor_anual,
        "Registros sin validar con valor mensual": sin_valor_mensual,
        "Registros sin validar con etiqueta correcta": etiquetas_sin_validar,
        "Valores anuales negativos": negativos_anuales,
        "Valores mensuales negativos": negativos_mensuales,
    }

    # --------------------------------------------------------
    # 10. Crear informe
    # --------------------------------------------------------

    lineas = [
        "=" * 70,
        "INFORME DE AUDITORÍA DE NORMALIZACIÓN",
        "=" * 70,
        ""
    ]

    for descripcion, cantidad in resultados.items():
        lineas.append(f"{descripcion}: {cantidad:,}")

    errores_totales = (
        errores_inicial
        + errores_mensual_inicial
        + errores_anual
        + errores_mensual_anual
        + errores_etiquetas
        + sin_valor_anual
        + sin_valor_mensual
        + negativos_anuales
        + negativos_mensuales
    )

    lineas.append("")
    lineas.append("=" * 70)

    if errores_totales == 0:
        lineas.append("RESULTADO: AUDITORÍA SATISFACTORIA")
    else:
        lineas.append(
            f"RESULTADO: REVISAR. Se detectaron {errores_totales:,} "
            "posibles inconsistencias."
        )

    lineas.append("=" * 70)

    INFORME.parent.mkdir(parents=True, exist_ok=True)

    INFORME.write_text(
        "\n".join(lineas),
        encoding="utf-8"
    )

    print("\nRESULTADOS DE LA AUDITORÍA")
    print("-" * 70)

    for descripcion, cantidad in resultados.items():
        print(f"{descripcion}: {cantidad:,}")

    print("\n" + lineas[-2])
    print(f"\nInforme generado: {INFORME}")


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    try:
        auditar()

    except Exception as error:
        print("\nERROR DURANTE LA AUDITORÍA")
        print(error)
