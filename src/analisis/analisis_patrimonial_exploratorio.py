
from pathlib import Path
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

ARCHIVO_DATASET = (
    BASE_DIR
    / "datos"
    / "procesados"
    / "dataset_pdn_normalizado.csv"
)

DIRECTORIO_RESULTADOS = BASE_DIR / "resultados"

ARCHIVO_INFORME = (
    DIRECTORIO_RESULTADOS
    / "informe_analisis_patrimonial.txt"
)

ARCHIVO_RESUMEN = (
    DIRECTORIO_RESULTADOS
    / "resumen_patrimonial_por_categoria.csv"
)

ARCHIVO_POR_TIPO = (
    DIRECTORIO_RESULTADOS
    / "resumen_patrimonial_por_tipo.csv"
)


# ============================================================
# CATEGORÍAS PATRIMONIALES
# ============================================================

CATEGORIAS = {
    "Inmuebles": {
        "flag": "tiene_inmuebles",
        "cantidad": "cantidad_inmuebles",
    },
    "Vehículos": {
        "flag": "tiene_vehiculos",
        "cantidad": "cantidad_vehiculos",
    },
    "Bienes muebles": {
        "flag": "tiene_bienes_muebles",
        "cantidad": "cantidad_bienes_muebles",
    },
    "Inversiones": {
        "flag": "tiene_inversiones",
        "cantidad": "cantidad_inversiones",
    },
    "Adeudos": {
        "flag": "tiene_adeudos",
        "cantidad": "cantidad_adeudos",
    },
    "Préstamos o comodatos": {
        "flag": "tiene_prestamos",
        "cantidad": "cantidad_prestamos",
    },
    "Participaciones": {
        "flag": "tiene_participaciones",
        "cantidad": "cantidad_participaciones",
    },
    "Apoyos": {
        "flag": "tiene_apoyos",
        "cantidad": "cantidad_apoyos",
    },
    "Beneficios privados": {
        "flag": "tiene_beneficios_privados",
        "cantidad": "cantidad_beneficios",
    },
    "Fideicomisos": {
        "flag": "tiene_fideicomisos",
        "cantidad": "cantidad_fideicomisos",
    },
}

TIPOS_ESPERADOS = [
    "INICIAL",
    "MODIFICACIÓN",
    "CONCLUSIÓN",
]


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def validar_archivos():

    if not ARCHIVO_DATASET.exists():
        raise FileNotFoundError(
            f"No se encontró el dataset:\n{ARCHIVO_DATASET}"
        )

    archivos_salida = [
        ARCHIVO_INFORME,
        ARCHIVO_RESUMEN,
        ARCHIVO_POR_TIPO,
    ]

    existentes = [
        archivo for archivo in archivos_salida
        if archivo.exists()
    ]

    if existentes:
        raise FileExistsError(
            "Ya existen archivos de resultados y no serán "
            "sobrescritos:\n"
            + "\n".join(str(a) for a in existentes)
        )


def validar_columnas(df):

    requeridas = [
        "tipo_declaracion",
        "ingreso_neto_validacion",
        "ingreso_neto_anual_equivalente",
        "ingreso_neto_moneda",
    ]

    for categoria in CATEGORIAS.values():
        requeridas.append(categoria["flag"])
        requeridas.append(categoria["cantidad"])

    faltantes = [
        columna for columna in requeridas
        if columna not in df.columns
    ]

    if faltantes:
        raise ValueError(
            "Faltan columnas necesarias:\n"
            + ", ".join(faltantes)
        )


def normalizar_tipo(serie):

    return (
        serie.fillna("SIN TIPO")
        .astype(str)
        .str.strip()
        .str.upper()
    )


def escribir_seccion(lineas, titulo):

    lineas.append("")
    lineas.append("=" * 70)
    lineas.append(titulo.upper())
    lineas.append("=" * 70)


# ============================================================
# ANÁLISIS PRINCIPAL
# ============================================================

def analizar():

    print("=" * 70)
    print("ANÁLISIS EXPLORATORIO PATRIMONIAL")
    print("=" * 70)

    validar_archivos()

    print("\nLeyendo dataset normalizado...")

    df = pd.read_csv(ARCHIVO_DATASET)

    validar_columnas(df)

    total = len(df)

    tipos = normalizar_tipo(df["tipo_declaracion"])

    print(f"Declaraciones encontradas: {total:,}")

    # --------------------------------------------------------
    # 1. Distribución de tipos de declaración
    # --------------------------------------------------------

    distribucion_tipos = (
        tipos.value_counts(dropna=False)
        .rename_axis("tipo_declaracion")
        .reset_index(name="declaraciones")
    )

    # --------------------------------------------------------
    # 2. Análisis general por categoría
    # --------------------------------------------------------

    resumen_categorias = []
    resumen_tipo = []
    inconsistencias = []

    for nombre, columnas in CATEGORIAS.items():

        flag_col = columnas["flag"]
        cantidad_col = columnas["cantidad"]

        flag = df[flag_col].astype("boolean")

        cantidad = pd.to_numeric(
            df[cantidad_col],
            errors="coerce"
        )

        # Valores de presencia
        presentes = int((flag == True).sum())
        ausentes = int((flag == False).sum())
        sin_dato_flag = int(flag.isna().sum())

        # Valores de cantidad
        cantidades_validas = cantidad.dropna()

        cantidad_cero = int(
            (cantidades_validas == 0).sum()
        )

        cantidad_positiva = int(
            (cantidades_validas > 0).sum()
        )

        cantidad_negativa = int(
            (cantidades_validas < 0).sum()
        )

        cantidad_sin_dato = int(cantidad.isna().sum())

        # Comparar flag con cantidad > 0.
        comparables = flag.notna() & cantidad.notna()

        discrepancias = int(
            (
                comparables
                & (flag.astype("boolean") != cantidad.gt(0))
            ).sum()
        )

        resumen_categorias.append({
            "categoria": nombre,
            "declaraciones_con_categoria": presentes,
            "declaraciones_sin_categoria": ausentes,
            "flags_sin_dato": sin_dato_flag,
            "cantidades_en_cero": cantidad_cero,
            "cantidades_positivas": cantidad_positiva,
            "cantidades_negativas": cantidad_negativa,
            "cantidades_sin_dato": cantidad_sin_dato,
            "discrepancias_flag_cantidad": discrepancias,
            "porcentaje_presencia": round(
                presentes / total * 100, 4
            ),
        })

        if discrepancias > 0:
            inconsistencias.append(
                f"{nombre}: {discrepancias} discrepancias "
                "entre indicador y cantidad."
            )

        # ----------------------------------------------------
        # 3. Análisis por tipo de declaración
        # ----------------------------------------------------

        for tipo in TIPOS_ESPERADOS:

            mascara = tipos.eq(tipo)

            total_tipo = int(mascara.sum())

            if total_tipo == 0:
                continue

            presentes_tipo = int(
                (flag[mascara] == True).sum()
            )

            cantidades_tipo = cantidad[mascara].dropna()

            resumen_tipo.append({
                "tipo_declaracion": tipo,
                "categoria": nombre,
                "total_declaraciones": total_tipo,
                "declaraciones_con_categoria": presentes_tipo,
                "declaraciones_sin_categoria": int(
                    (flag[mascara] == False).sum()
                ),
                "porcentaje_presencia": round(
                    presentes_tipo / total_tipo * 100,
                    4
                ),
                "cantidad_media": (
                    round(cantidades_tipo.mean(), 4)
                    if len(cantidades_tipo) else None
                ),
                "cantidad_mediana": (
                    round(cantidades_tipo.median(), 4)
                    if len(cantidades_tipo) else None
                ),
                "cantidad_maxima": (
                    cantidades_tipo.max()
                    if len(cantidades_tipo) else None
                ),
            })

    resumen_df = pd.DataFrame(resumen_categorias)

    resumen_tipo_df = pd.DataFrame(resumen_tipo)

    # --------------------------------------------------------
    # 4. Cantidad de categorías presentes por declaración
    # --------------------------------------------------------

    columnas_flags = [
        datos["flag"]
        for datos in CATEGORIAS.values()
    ]

    flags = df[columnas_flags].astype("boolean")

    categorias_presentes = flags.eq(True).sum(axis=1)

    distribucion_categorias = (
        categorias_presentes.value_counts()
        .sort_index()
    )

    # --------------------------------------------------------
    # 5. Análisis de ingresos normalizados
    # --------------------------------------------------------

    ingresos = pd.to_numeric(
        df["ingreso_neto_anual_equivalente"],
        errors="coerce"
    )

    ingreso_valido = (
        df["ingreso_neto_validacion"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
        .eq("VALIDADO")
    )

    ingresos_validos = ingresos[ingreso_valido].dropna()

    # --------------------------------------------------------
    # 6. Construir informe
    # --------------------------------------------------------

    lineas = []

    lineas.append("=" * 70)
    lineas.append("INFORME DE ANÁLISIS EXPLORATORIO PATRIMONIAL")
    lineas.append("=" * 70)

    escribir_seccion(lineas, "1. Dimensiones del dataset")

    lineas.append(f"Total de declaraciones: {total:,}")
    lineas.append(f"Total de columnas: {len(df.columns)}")

    escribir_seccion(lineas, "2. Tipos de declaración")

    for _, fila in distribucion_tipos.iterrows():

        porcentaje = fila["declaraciones"] / total * 100

        lineas.append(
            f"{fila['tipo_declaracion']}: "
            f"{fila['declaraciones']:,} "
            f"({porcentaje:.2f} %)"
        )

    escribir_seccion(lineas, "3. Presencia de categorías patrimoniales")

    for _, fila in resumen_df.iterrows():

        lineas.append("")
        lineas.append(f"Categoría: {fila['categoria']}")
        lineas.append(
            f"Con categoría: "
            f"{fila['declaraciones_con_categoria']:,}"
        )
        lineas.append(
            f"Sin categoría según indicador: "
            f"{fila['declaraciones_sin_categoria']:,}"
        )
        lineas.append(
            f"Porcentaje de presencia: "
            f"{fila['porcentaje_presencia']:.2f} %"
        )
        lineas.append(
            f"Cantidad cero: {fila['cantidades_en_cero']:,}"
        )
        lineas.append(
            f"Cantidad positiva: {fila['cantidades_positivas']:,}"
        )
        lineas.append(
            f"Cantidad negativa: {fila['cantidades_negativas']:,}"
        )
        lineas.append(
            f"Cantidad sin dato: {fila['cantidades_sin_dato']:,}"
        )
        lineas.append(
            f"Discrepancias flag/cantidad: "
            f"{fila['discrepancias_flag_cantidad']:,}"
        )

    escribir_seccion(
        lineas,
        "4. Categorías presentes por declaración"
    )

    for numero, cantidad in distribucion_categorias.items():

        lineas.append(
            f"{numero} categorías: {cantidad:,} declaraciones "
            f"({cantidad / total * 100:.2f} %)"
        )

    escribir_seccion(
        lineas,
        "5. Categorías patrimoniales por tipo de declaración"
    )

    for tipo in TIPOS_ESPERADOS:

        lineas.append("")
        lineas.append(f"TIPO: {tipo}")

        datos_tipo = resumen_tipo_df[
            resumen_tipo_df["tipo_declaracion"] == tipo
        ]

        for _, fila in datos_tipo.iterrows():

            lineas.append(
                f"{fila['categoria']}: "
                f"{fila['declaraciones_con_categoria']:,} "
                f"de {fila['total_declaraciones']:,} "
                f"({fila['porcentaje_presencia']:.2f} %)"
            )

    escribir_seccion(lineas, "6. Ingresos anuales equivalentes")

    lineas.append(
        f"Registros con ingreso validado: {len(ingresos_validos):,}"
    )

    if len(ingresos_validos) > 0:

        lineas.append(
            f"Mediana: {ingresos_validos.median():,.2f} MXN"
        )

        lineas.append(
            f"Media: {ingresos_validos.mean():,.2f} MXN"
        )

        lineas.append(
            f"Percentil 95: "
            f"{ingresos_validos.quantile(0.95):,.2f} MXN"
        )

        lineas.append(
            f"Máximo: {ingresos_validos.max():,.2f} MXN"
        )

    lineas.append(
        "Nota: estos importes son equivalentes anualizados. "
        "No representan necesariamente ingresos efectivamente "
        "percibidos durante un mismo período."
    )

    escribir_seccion(lineas, "7. Observaciones de consistencia")

    if inconsistencias:
        for observacion in inconsistencias:
            lineas.append(observacion)
    else:
        lineas.append(
            "No se detectaron discrepancias entre los indicadores "
            "booleanos y las cantidades extraídas."
        )

    lineas.append("")
    lineas.append(
        "NOTA METODOLÓGICA: la presencia o ausencia de una categoría "
        "se refiere a los indicadores extraídos del dataset. "
        "No demuestra por sí sola la existencia o inexistencia "
        "real de patrimonio."
    )

    lineas.append("")
    lineas.append("=" * 70)
    lineas.append("FIN DEL INFORME")
    lineas.append("=" * 70)

    # --------------------------------------------------------
    # 7. Guardar resultados
    # --------------------------------------------------------

    DIRECTORIO_RESULTADOS.mkdir(
        parents=True,
        exist_ok=True
    )

    resumen_df.to_csv(
        ARCHIVO_RESUMEN,
        index=False,
        encoding="utf-8-sig"
    )

    resumen_tipo_df.to_csv(
        ARCHIVO_POR_TIPO,
        index=False,
        encoding="utf-8-sig"
    )

    ARCHIVO_INFORME.write_text(
        "\n".join(lineas),
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # 8. Mostrar resumen en terminal
    # --------------------------------------------------------

    print("\nANÁLISIS COMPLETADO")
    print("-" * 70)

    print("\nPresencia por categoría:")

    print(
        resumen_df[
            [
                "categoria",
                "declaraciones_con_categoria",
                "porcentaje_presencia",
                "discrepancias_flag_cantidad",
            ]
        ].to_string(index=False)
    )

    print("\nDistribución de categorías por declaración:")

    for numero, cantidad in distribucion_categorias.items():
        print(f"{numero} categorías: {cantidad:,}")

    print("\nArchivos generados:")

    print(ARCHIVO_INFORME)
    print(ARCHIVO_RESUMEN)
    print(ARCHIVO_POR_TIPO)


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    try:
        analizar()

    except Exception as error:
        print("\nERROR DURANTE EL ANÁLISIS")
        print(error)
