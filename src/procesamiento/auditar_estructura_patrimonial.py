
import json
import csv
from pathlib import Path
from collections import Counter, defaultdict


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "datos" / "originales"
OUTPUT_DIR = BASE_DIR / "resultados"

ARCHIVO_DETALLE = OUTPUT_DIR / "auditoria_estructura_detalle.csv"
ARCHIVO_RESUMEN = OUTPUT_DIR / "auditoria_estructura_resumen.txt"


# ==========================================================
# CATEGORÍAS A AUDITAR
# ==========================================================

CATEGORIAS = {
    "inmuebles": {
        "grupo": "situacionPatrimonial",
        "seccion": "bienesInmuebles",
        "elementos": "bienInmueble",
    },
    "vehiculos": {
        "grupo": "situacionPatrimonial",
        "seccion": "vehiculos",
        "elementos": "vehiculo",
    },
    "bienes_muebles": {
        "grupo": "situacionPatrimonial",
        "seccion": "bienesMuebles",
        "elementos": "bienMueble",
    },
    "inversiones": {
        "grupo": "situacionPatrimonial",
        "seccion": "inversiones",
        "elementos": "inversion",
    },
    "adeudos": {
        "grupo": "situacionPatrimonial",
        "seccion": "adeudos",
        "elementos": "adeudo",
    },
    "prestamos": {
        "grupo": "situacionPatrimonial",
        "seccion": "prestamoOComodato",
        "elementos": "prestamo",
    },
    "participaciones": {
        "grupo": "interes",
        "seccion": "participacion",
        "elementos": "participacion",
    },
    "apoyos": {
        "grupo": "interes",
        "seccion": "apoyos",
        "elementos": "apoyo",
    },
    "beneficios_privados": {
        "grupo": "interes",
        "seccion": "beneficiosPrivados",
        "elementos": "beneficio",
    },
    "fideicomisos": {
        "grupo": "interes",
        "seccion": "fideicomisos",
        "elementos": "fideicomiso",
    },
}


# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================

def obtener_diccionario(valor):
    if isinstance(valor, dict):
        return valor
    return {}


def normalizar_ninguno(valor):
    """
    Convierte los valores reconocibles del indicador ninguno
    en True o False. Los valores desconocidos quedan como None.
    """

    if isinstance(valor, bool):
        return valor

    if isinstance(valor, (int, float)):
        if valor == 1:
            return True
        if valor == 0:
            return False

    if isinstance(valor, str):
        texto = valor.strip().lower()

        if texto in ("true", "1", "si", "sí", "yes"):
            return True

        if texto in ("false", "0", "no"):
            return False

    return None


def analizar_categoria(declaracion, configuracion):
    grupo = configuracion["grupo"]
    nombre_seccion = configuracion["seccion"]
    clave_elementos = configuracion["elementos"]

    if grupo == "situacionPatrimonial":
        contenedor = obtener_diccionario(
            declaracion.get("situacionPatrimonial")
        )

    elif grupo == "interes":
        contenedor = obtener_diccionario(
            declaracion.get("interes")
        )

    else:
        contenedor = {}

    seccion = contenedor.get(nombre_seccion)

    seccion_presente = isinstance(seccion, dict)

    if not seccion_presente:
        return {
            "seccion_presente": False,
            "clave_elementos_presente": False,
            "tipo_elementos": "SECCION_NO_DISPONIBLE",
            "cantidad_detectada": 0,
            "ninguno_original": None,
            "ninguno_normalizado": None,
            "clasificacion": "SECCION_NO_DISPONIBLE",
            "consistencia": "NO_EVALUABLE",
        }

    elementos_presentes = clave_elementos in seccion
    elementos = seccion.get(clave_elementos)

    ninguno_original = seccion.get("ninguno")
    ninguno = normalizar_ninguno(ninguno_original)

    if not elementos_presentes:
        tipo_elementos = "CLAVE_AUSENTE"
        cantidad = 0
        clasificacion = "CLAVE_ELEMENTOS_AUSENTE"

    elif isinstance(elementos, list):
        tipo_elementos = "LISTA"
        cantidad = len(elementos)

        if cantidad == 0:
            clasificacion = "LISTA_VACIA"
        else:
            clasificacion = "LISTA_CON_ELEMENTOS"

    elif isinstance(elementos, dict):
        tipo_elementos = "DICCIONARIO"
        cantidad = 1 if elementos else 0

        if elementos:
            clasificacion = "DICCIONARIO_NO_VACIO"
        else:
            clasificacion = "DICCIONARIO_VACIO"

    elif elementos is None:
        tipo_elementos = "NULL"
        cantidad = 0
        clasificacion = "VALOR_NULL"

    else:
        tipo_elementos = type(elementos).__name__.upper()
        cantidad = 0
        clasificacion = "TIPO_NO_ESPERADO"

    # Evaluación de coherencia del indicador ninguno

    if ninguno is True and cantidad > 0:
        consistencia = "CONTRADICCION_NINGUNO_CON_ELEMENTOS"

    elif ninguno is True and cantidad == 0:
        consistencia = "NINGUNO_TRUE_SIN_ELEMENTOS"

    elif ninguno is False and cantidad > 0:
        consistencia = "NINGUNO_FALSE_CON_ELEMENTOS"

    elif ninguno is False and cantidad == 0:
        consistencia = "NINGUNO_FALSE_SIN_ELEMENTOS"

    else:
        consistencia = "INDICADOR_AUSENTE_O_NO_RECONOCIDO"

    return {
        "seccion_presente": True,
        "clave_elementos_presente": elementos_presentes,
        "tipo_elementos": tipo_elementos,
        "cantidad_detectada": cantidad,
        "ninguno_original": (
            str(ninguno_original)
            if ninguno_original is not None
            else None
        ),
        "ninguno_normalizado": (
            str(ninguno).upper()
            if ninguno is not None
            else "NO_RECONOCIDO"
        ),
        "clasificacion": clasificacion,
        "consistencia": consistencia,
    }


# ==========================================================
# PROCESAMIENTO PRINCIPAL
# ==========================================================

def ejecutar_auditoria():

    print("=" * 65)
    print("AUDITORÍA DE ESTRUCTURA PATRIMONIAL - PDN")
    print("=" * 65)

    if not DATA_DIR.exists():
        print(f"No existe la carpeta: {DATA_DIR}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    archivos = sorted(DATA_DIR.rglob("*.json"))

    if not archivos:
        print("No se encontraron archivos JSON.")
        return

    print(f"\nArchivos encontrados: {len(archivos)}")

    campos = [
        "archivo",
        "posicion",
        "tipo_declaracion",
        "categoria",
        "seccion",
        "clave_elementos",
        "seccion_presente",
        "clave_elementos_presente",
        "tipo_elementos",
        "cantidad_detectada",
        "ninguno_original",
        "ninguno_normalizado",
        "clasificacion",
        "consistencia",
    ]

    estadisticas = defaultdict(Counter)

    total_declaraciones = 0
    errores_lectura = 0
    registros_invalidos = 0
    total_filas_auditadas = 0

    with open(
        ARCHIVO_DETALLE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as archivo_csv:

        escritor = csv.DictWriter(
            archivo_csv,
            fieldnames=campos
        )

        escritor.writeheader()

        for indice_archivo, archivo in enumerate(archivos, start=1):

            print(
                f"\rProcesando archivo "
                f"{indice_archivo}/{len(archivos)}",
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

            except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                errores_lectura += 1
                continue

            if isinstance(contenido, list):
                declaraciones = contenido

            elif isinstance(contenido, dict):
                declaraciones = [contenido]

            else:
                registros_invalidos += 1
                continue

            for posicion, datos in enumerate(declaraciones):

                if not isinstance(datos, dict):
                    registros_invalidos += 1
                    continue

                total_declaraciones += 1

                metadata = obtener_diccionario(
                    datos.get("metadata")
                )

                tipo_declaracion = metadata.get("tipo")

                declaracion = obtener_diccionario(
                    datos.get("declaracion")
                )

                for categoria, configuracion in CATEGORIAS.items():

                    resultado = analizar_categoria(
                        declaracion,
                        configuracion
                    )

                    fila = {
                        "archivo": str(
                            archivo.relative_to(DATA_DIR)
                        ),
                        "posicion": posicion,
                        "tipo_declaracion": tipo_declaracion,
                        "categoria": categoria,
                        "seccion": configuracion["seccion"],
                        "clave_elementos": configuracion["elementos"],
                        **resultado,
                    }

                    escritor.writerow(fila)

                    total_filas_auditadas += 1

                    estadisticas[categoria][
                        "declaraciones"
                    ] += 1

                    estadisticas[categoria][
                        resultado["clasificacion"]
                    ] += 1

                    estadisticas[categoria][
                        resultado["consistencia"]
                    ] += 1

                    estadisticas[categoria][
                        "elementos_detectados"
                    ] += resultado["cantidad_detectada"]

    # ======================================================
    # GENERAR INFORME
    # ======================================================

    lineas = []

    lineas.append("=" * 65)
    lineas.append("INFORME DE AUDITORÍA DE ESTRUCTURA PATRIMONIAL")
    lineas.append("=" * 65)

    lineas.append(f"\nArchivos JSON encontrados: {len(archivos)}")
    lineas.append(f"Declaraciones procesadas: {total_declaraciones}")
    lineas.append(f"Filas de auditoría: {total_filas_auditadas}")
    lineas.append(f"Errores de lectura: {errores_lectura}")
    lineas.append(f"Registros inválidos: {registros_invalidos}")

    for categoria in CATEGORIAS:

        datos = estadisticas[categoria]

        lineas.append("\n" + "-" * 65)
        lineas.append(f"CATEGORÍA: {categoria.upper()}")
        lineas.append("-" * 65)

        lineas.append(
            f"Declaraciones auditadas: {datos['declaraciones']}"
        )

        lineas.append(
            f"Elementos detectados: {datos['elementos_detectados']}"
        )

        lineas.append("\nClasificación de estructuras:")

        clasificaciones = [
            "SECCION_NO_DISPONIBLE",
            "CLAVE_ELEMENTOS_AUSENTE",
            "LISTA_VACIA",
            "LISTA_CON_ELEMENTOS",
            "DICCIONARIO_VACIO",
            "DICCIONARIO_NO_VACIO",
            "VALOR_NULL",
            "TIPO_NO_ESPERADO",
        ]

        for nombre in clasificaciones:
            lineas.append(
                f"  {nombre}: {datos[nombre]}"
            )

        lineas.append("\nCoherencia del indicador ninguno:")

        consistencias = [
            "NINGUNO_TRUE_SIN_ELEMENTOS",
            "NINGUNO_FALSE_CON_ELEMENTOS",
            "NINGUNO_FALSE_SIN_ELEMENTOS",
            "CONTRADICCION_NINGUNO_CON_ELEMENTOS",
            "INDICADOR_AUSENTE_O_NO_RECONOCIDO",
            "NO_EVALUABLE",
        ]

        for nombre in consistencias:
            lineas.append(
                f"  {nombre}: {datos[nombre]}"
            )

    lineas.append("\n" + "=" * 65)
    lineas.append("FIN DEL INFORME")
    lineas.append("=" * 65)

    with open(
        ARCHIVO_RESUMEN,
        "w",
        encoding="utf-8"
    ) as f:
        f.write("\n".join(lineas))

    print("\n\nAuditoría finalizada.")
    print(f"\nDetalle CSV: {ARCHIVO_DETALLE}")
    print(f"Informe: {ARCHIVO_RESUMEN}")

    print(f"\nDeclaraciones procesadas: {total_declaraciones}")
    print(f"Filas auditadas: {total_filas_auditadas}")
    print(f"Errores de lectura: {errores_lectura}")
    print(f"Registros inválidos: {registros_invalidos}")


if __name__ == "__main__":
    ejecutar_auditoria()
