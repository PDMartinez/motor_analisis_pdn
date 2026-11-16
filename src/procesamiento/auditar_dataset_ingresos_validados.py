from pathlib import Path
from datetime import datetime
import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATASET_FILE = (
    BASE_DIR
    / "datos"
    / "procesados"
    / "dataset_pdn_ingresos_validados.csv"
)

RESULTADOS_DIR = BASE_DIR / "resultados"

INFORME_FILE = (
    RESULTADOS_DIR
    / "auditoria_ingresos_validados.txt"
)

COLUMNAS_NECESARIAS = [
    "tipo_declaracion",
    "ingreso_neto_valor",
    "ingreso_neto_moneda",
    "ingreso_neto_periodo",
    "ingreso_neto_campo_origen",
    "ingreso_neto_validacion",
]

PERIODOS_ESPERADOS = {
    "INICIAL": "MENSUAL",
    "MODIFICACIÓN": "ANUAL",
    "CONCLUSIÓN": "ANUAL",
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def agregar_linea(informe, texto=""):
    informe.append(str(texto))


def formato_numero(valor):
    if pd.isna(valor):
        return "N/D"

    return f"{valor:,.2f}"


def guardar_informe(informe):
    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

    if INFORME_FILE.exists():
        raise FileExistsError(
            f"El informe ya existe y no será sobrescrito:\n"
            f"{INFORME_FILE}"
        )

    INFORME_FILE.write_text(
        "\n".join(informe),
        encoding="utf-8"
    )


# ============================================================
# AUDITORÍA PRINCIPAL
# ============================================================

def auditar_dataset():

    print("=" * 70)
    print("AUDITORÍA DEL DATASET DE INGRESOS VALIDADOS")
    print("=" * 70)

    if not DATASET_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo:\n{DATASET_FILE}"
        )

    print("\nLeyendo dataset...")

    df = pd.read_csv(DATASET_FILE)

    print(f"Filas encontradas: {len(df)}")
    print(f"Columnas encontradas: {len(df.columns)}")

    # --------------------------------------------------------
    # 1. Verificar columnas
    # --------------------------------------------------------

    faltantes = [
        columna
        for columna in COLUMNAS_NECESARIAS
        if columna not in df.columns
    ]

    if faltantes:
        raise ValueError(
            "Faltan columnas necesarias para la auditoría: "
            + ", ".join(faltantes)
        )

    # --------------------------------------------------------
    # 2. Preparar valores
    # --------------------------------------------------------

    valores = pd.to_numeric(
        df["ingreso_neto_valor"],
        errors="coerce"
    )

    tipos = (
        df["tipo_declaracion"]
        .fillna("SIN TIPO")
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
        .fillna("SIN ESTADO")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    campos_origen = (
        df["ingreso_neto_campo_origen"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------------
    # 3. Contadores generales
    # --------------------------------------------------------

    total = len(df)

    validado = estados.eq("VALIDADO")
    sin_nodo = estados.eq("SIN_NODO_INGRESOS")

    valores_numericos = valores.notna()
    valores_cero = valores.eq(0)
    valores_negativos = valores.lt(0)
    valores_positivos = valores.gt(0)

    monedas_vacias = monedas.eq("")
    periodos_vacios = periodos.eq("")
    campos_origen_vacios = campos_origen.eq("")

    estados_no_esperados = ~estados.isin([
        "VALIDADO",
        "SIN_NODO_INGRESOS",
    ])

    # --------------------------------------------------------
    # 4. Verificar coherencia del período
    # --------------------------------------------------------

    periodo_esperado = tipos.map(PERIODOS_ESPERADOS)

    periodo_incorrecto = (
        periodo_esperado.notna()
        & periodos.ne(periodo_esperado.fillna(""))
    )

    tipos_no_reconocidos = periodo_esperado.isna()

    # --------------------------------------------------------
    # 5. Verificar coherencia de los registros validados
    # --------------------------------------------------------

    validado_sin_valor = validado & ~valores_numericos
    validado_sin_moneda = validado & monedas_vacias
    validado_sin_periodo = validado & periodos_vacios
    validado_sin_campo = validado & campos_origen_vacios

    validado_con_valor_negativo = validado & valores_negativos

    # --------------------------------------------------------
    # 6. Estadísticas por tipo de declaración
    # --------------------------------------------------------

    estadisticas = []

    for tipo in sorted(tipos.unique()):

        mascara = tipos.eq(tipo)
        serie = valores[mascara].dropna()

        if len(serie) > 0:
            estadisticas.append({
                "tipo": tipo,
                "registros": int(mascara.sum()),
                "valores_numericos": int(valores[mascara].notna().sum()),
                "ceros": int(valores[mascara].eq(0).sum()),
                "positivos": int(valores[mascara].gt(0).sum()),
                "negativos": int(valores[mascara].lt(0).sum()),
                "minimo": serie.min(),
                "mediana": serie.median(),
                "media": serie.mean(),
                "p95": serie.quantile(0.95),
                "maximo": serie.max(),
            })
        else:
            estadisticas.append({
                "tipo": tipo,
                "registros": int(mascara.sum()),
                "valores_numericos": 0,
                "ceros": 0,
                "positivos": 0,
                "negativos": 0,
                "minimo": None,
                "mediana": None,
                "media": None,
                "p95": None,
                "maximo": None,
            })

    # --------------------------------------------------------
    # 7. Construir informe agregado
    # --------------------------------------------------------

    informe = []

    agregar_linea(informe, "=" * 70)
    agregar_linea(informe, "INFORME DE AUDITORÍA DE INGRESOS VALIDADOS")
    agregar_linea(
        informe,
        f"Fecha de ejecución: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )
    agregar_linea(informe, "=" * 70)

    agregar_linea(informe, "\n1. DIMENSIONES DEL DATASET")
    agregar_linea(informe, f"Total de registros: {total}")
    agregar_linea(informe, f"Total de columnas: {len(df.columns)}")

    agregar_linea(informe, "\n2. ESTADOS DE VALIDACIÓN")

    for estado, cantidad in estados.value_counts(dropna=False).items():
        agregar_linea(
            informe,
            f"{estado}: {cantidad:,} "
            f"({cantidad / total * 100:.4f} %)"
        )

    agregar_linea(informe, "\n3. VALORES DE INGRESOS")

    agregar_linea(
        informe,
        f"Valores numéricos: {valores_numericos.sum():,}"
    )
    agregar_linea(
        informe,
        f"Valores positivos: {valores_positivos.sum():,}"
    )
    agregar_linea(
        informe,
        f"Valores iguales a cero: {valores_cero.sum():,}"
    )
    agregar_linea(
        informe,
        f"Valores negativos: {valores_negativos.sum():,}"
    )
    agregar_linea(
        informe,
        f"Valores no numéricos o vacíos: {(~valores_numericos).sum():,}"
    )

    agregar_linea(informe, "\n4. MONEDAS")

    for moneda, cantidad in monedas.value_counts().items():
        etiqueta = moneda if moneda else "SIN MONEDA"
        agregar_linea(
            informe,
            f"{etiqueta}: {cantidad:,}"
        )

    agregar_linea(informe, "\n5. PERÍODOS")

    for periodo, cantidad in periodos.value_counts().items():
        etiqueta = periodo if periodo else "SIN PERÍODO"
        agregar_linea(
            informe,
            f"{etiqueta}: {cantidad:,}"
        )

    agregar_linea(informe, "\n6. COHERENCIA DEL PERÍODO POR TIPO")

    for tipo, esperado in PERIODOS_ESPERADOS.items():

        mascara = tipos.eq(tipo)

        correctos = (
            mascara
            & periodos.eq(esperado)
        ).sum()

        incorrectos = (
            mascara
            & periodos.ne(esperado)
        ).sum()

        agregar_linea(
            informe,
            f"{tipo}: esperado={esperado}, "
            f"correctos={correctos:,}, "
            f"incorrectos={incorrectos:,}"
        )

    agregar_linea(
        informe,
        f"Tipos de declaración no reconocidos: "
        f"{tipos_no_reconocidos.sum():,}"
    )

    agregar_linea(informe, "\n7. ESTADÍSTICAS POR TIPO DE DECLARACIÓN")

    for item in estadisticas:

        agregar_linea(informe, "")
        agregar_linea(informe, f"Tipo: {item['tipo']}")
        agregar_linea(informe, f"Registros: {item['registros']:,}")
        agregar_linea(
            informe,
            f"Valores numéricos: {item['valores_numericos']:,}"
        )
        agregar_linea(informe, f"Ceros: {item['ceros']:,}")
        agregar_linea(informe, f"Positivos: {item['positivos']:,}")
        agregar_linea(informe, f"Negativos: {item['negativos']:,}")
        agregar_linea(informe, f"Mínimo: {formato_numero(item['minimo'])}")
        agregar_linea(informe, f"Mediana: {formato_numero(item['mediana'])}")
        agregar_linea(informe, f"Media: {formato_numero(item['media'])}")
        agregar_linea(informe, f"Percentil 95: {formato_numero(item['p95'])}")
        agregar_linea(informe, f"Máximo: {formato_numero(item['maximo'])}")

    agregar_linea(informe, "\n8. INCONSISTENCIAS DETECTADAS")

    inconsistencias = {
        "Registros VALIDADO sin valor numérico": validado_sin_valor.sum(),
        "Registros VALIDADO sin moneda": validado_sin_moneda.sum(),
        "Registros VALIDADO sin período": validado_sin_periodo.sum(),
        "Registros VALIDADO sin campo de origen": validado_sin_campo.sum(),
        "Registros VALIDADO con ingreso negativo": validado_con_valor_negativo.sum(),
        "Registros con período incorrecto": periodo_incorrecto.sum(),
        "Registros con estado no esperado": estados_no_esperados.sum(),
    }

    for descripcion, cantidad in inconsistencias.items():
        agregar_linea(
            informe,
            f"{descripcion}: {cantidad:,}"
        )

    agregar_linea(informe, "\n9. RESULTADO GENERAL")

    total_inconsistencias = sum(inconsistencias.values())

    if total_inconsistencias == 0:
        agregar_linea(
            informe,
            "No se detectaron inconsistencias en las verificaciones realizadas."
        )
    else:
        agregar_linea(
            informe,
            "Se detectaron posibles inconsistencias que requieren revisión."
        )

    agregar_linea(informe, "")
    agregar_linea(informe, "=" * 70)
    agregar_linea(
        informe,
        "Fin del informe. Se utilizaron únicamente estadísticas agregadas."
    )
    agregar_linea(informe, "=" * 70)

    # --------------------------------------------------------
    # 8. Guardar y mostrar resultados
    # --------------------------------------------------------

    guardar_informe(informe)

    print("\nAUDITORÍA FINALIZADA")
    print("-" * 70)

    print(f"Registros: {total:,}")
    print(f"Valores numéricos: {valores_numericos.sum():,}")
    print(f"Valores positivos: {valores_positivos.sum():,}")
    print(f"Valores cero: {valores_cero.sum():,}")
    print(f"Valores negativos: {valores_negativos.sum():,}")

    print("\nInconsistencias:")

    for descripcion, cantidad in inconsistencias.items():
        print(f"{descripcion}: {cantidad:,}")

    print("\nInforme generado en:")
    print(INFORME_FILE)


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    try:
        auditar_dataset()

    except Exception as error:
        print("\nERROR DURANTE LA AUDITORÍA")
        print(error)