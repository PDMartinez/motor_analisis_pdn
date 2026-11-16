# -*- coding: utf-8 -*-

"""

ANALIZADOR INTEGRAL DE EVOLUCIÓN PATRIMONIAL - PDN

Integra búsqueda de declaraciones, extracción patrimonial, ingresos,

modelos Isolation Forest y comparación de adeudos.

Ejecutar desde la raíz:

    python src/analisis/analizador_integral_patrimonial.py

No exporta nombres, apellidos, RFC, CURP ni datos de titulares.

La metadata de actualización NO se interpreta como fecha de presentación.

"""

import csv
import os

import hashlib

import html

import json

import math

import re

import unicodedata

from pathlib import Path

from datetime import datetime

import numpy as np

import joblib

RAIZ = Path(__file__).resolve().parents[2]

DIR_RESULTADOS = Path(os.environ.get("PDN_RESULTADOS_DIR", str(RAIZ / "resultados"))).resolve()
ARCHIVO_COINCIDENCIAS = DIR_RESULTADOS / "coincidencias_persona.json"
DIR_MODELOS = Path(os.environ.get("PDN_MODELOS_DIR", str(RAIZ / "src" / "modelos" / "entrenados"))).resolve()

ARCHIVO_JSON = DIR_RESULTADOS / "informe_integral_patrimonial.json"

ARCHIVO_CSV = DIR_RESULTADOS / "informe_integral_declaraciones.csv"

ARCHIVO_HTML = DIR_RESULTADOS / "informe_integral_patrimonial.html"

ARCHIVO_COMPARACIONES = DIR_RESULTADOS / "informe_integral_comparaciones.csv"

# Las seis primeras categorías pertenecen a situacionPatrimonial.
# Las cuatro últimas pertenecen a declaracion.interes.
CATEGORIAS = {
    "inmuebles": ("situacionPatrimonial", "bienesInmuebles", "bienInmueble"),
    "vehiculos": ("situacionPatrimonial", "vehiculos", "vehiculo"),
    "bienes_muebles": ("situacionPatrimonial", "bienesMuebles", "bienMueble"),
    "inversiones": ("situacionPatrimonial", "inversiones", "inversion"),
    "adeudos": ("situacionPatrimonial", "adeudos", "adeudo"),
    "prestamos": ("situacionPatrimonial", "prestamoOComodato", "prestamo"),
    "participaciones": ("interes", "participacion", "participacion"),
    "apoyos": ("interes", "apoyos", "apoyo"),
    "beneficios_privados": ("interes", "beneficiosPrivados", "beneficio"),
    "fideicomisos": ("interes", "fideicomisos", "fideicomiso"),
}

FEATURES = [

    "log1p_cantidad_inmuebles",

    "log1p_cantidad_vehiculos",

    "log1p_cantidad_bienes_muebles",

    "log1p_cantidad_inversiones",

    "log1p_cantidad_adeudos",

    "log1p_cantidad_prestamos",

    "log1p_cantidad_participaciones",

    "log1p_cantidad_apoyos",

    "log1p_cantidad_beneficios",

    "log1p_cantidad_fideicomisos",

    "log1p_ingreso_neto_anual_equivalente",

]

def sha256_json(obj):

    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def lista_declaraciones(data):

    if isinstance(data, list):

        return data

    if isinstance(data, dict):

        for key in ("data", "datos", "declaraciones", "results", "resultados"):

            if isinstance(data.get(key), list):

                return data[key]

    raise ValueError("No se encontró una lista de declaraciones en el JSON original.")

def obtener(obj, ruta, default=None):

    actual = obj

    for key in ruta:

        if not isinstance(actual, dict) or key not in actual:

            return default

        actual = actual[key]

    return actual

def fecha_texto(valor):

    return str(valor or "")

def obtener_tipo_ingreso(declaracion, tipo):

    base = ["declaracion", "situacionPatrimonial", "ingresos"]

    nodo = obtener(declaracion, base)

    if not isinstance(nodo, dict):

        return None, "", "SIN_NODO_INGRESOS", ""

    if tipo == "INICIAL":

        campo = "totalIngresosMensualesNetos"

        metodo = "MENSUAL_X_12"

        factor = 12

    elif tipo == "MODIFICACIÓN":

        campo = "totalIngresosAnualesNetos"

        metodo = "ANUAL"

        factor = 1

    elif tipo == "CONCLUSIÓN":

        campo = "totalIngresosConclusionNetos"

        metodo = "ANUAL"

        factor = 1

    else:

        return None, "", "TIPO_NO_RECONOCIDO", ""

    dato = nodo.get(campo)

    if not isinstance(dato, dict):

        return None, "", "SIN_CAMPO_INGRESO", metodo

    moneda = str(dato.get("moneda") or "").upper()

    valor = dato.get("valor")

    try:

        valor = float(valor)

    except (TypeError, ValueError):

        return None, moneda, "VALOR_NO_NUMERICO", metodo

    if not math.isfinite(valor) or valor < 0:

        return None, moneda, "VALOR_INVALIDO", metodo

    if moneda != "MXN":

        return None, moneda, "MONEDA_NO_MXN", metodo

    return valor * factor, moneda, "VALIDADO_MXN", metodo

def extraer_cantidades(declaracion):
    """
    Extrae los diez conteos sin mezclar las dos ramas del esquema PDN:
    situacionPatrimonial e interes.

    Una sección ausente se conserva como None (no se inventa un cero).
    Una sección existente sin lista se registra como cero, de acuerdo con
    la estructura opcional de la declaración.
    """
    raiz_declaracion = declaracion.get("declaracion", {})
    if not isinstance(raiz_declaracion, dict):
        raiz_declaracion = {}

    cantidades = {}
    estados = {}

    for nombre, (rama_nombre, nodo_nombre, lista_nombre) in CATEGORIAS.items():
        rama = raiz_declaracion.get(rama_nombre)
        if not isinstance(rama, dict):
            cantidades[nombre] = None
            estados[nombre] = "SIN_RAMA_" + rama_nombre.upper()
            continue

        nodo = rama.get(nodo_nombre)
        if not isinstance(nodo, dict):
            cantidades[nombre] = None
            estados[nombre] = "SIN_NODO"
            continue

        lista = nodo.get(lista_nombre)
        if isinstance(lista, list):
            cantidades[nombre] = len(lista)
            estados[nombre] = "OK"
        elif lista is None:
            cantidades[nombre] = 0
            estados[nombre] = "SIN_LISTA"
        else:
            cantidades[nombre] = None
            estados[nombre] = "TIPO_INESPERADO"

    return cantidades, estados


def extraer_adeudos_detalle(declaracion):

    lista = obtener(

        declaracion,

        ["declaracion", "situacionPatrimonial", "adeudos", "adeudo"],

        []

    )

    if not isinstance(lista, list):

        return []

    resultado = []

    for item in lista:

        if not isinstance(item, dict):

            continue

        tipo_obj = item.get("tipoAdeudo")

        tipo_adeudo = tipo_obj.get("valor") if isinstance(tipo_obj, dict) else ""

        monto_obj = item.get("montoOriginal")

        if not isinstance(monto_obj, dict):

            monto_obj = {}

        otorgante = item.get("otorganteCredito")

        if not isinstance(otorgante, dict):

            otorgante = {}

        localizacion = item.get("localizacionAdeudo")

        if not isinstance(localizacion, dict):

            localizacion = {}

        # Se excluyen titulares, RFC y cualquier dato identificador.

        resultado.append({

            "tipo_operacion": item.get("tipoOperacion") or "",

            "tipo_adeudo": tipo_adeudo or "",

            "fecha_adquisicion_declarada": item.get("fechaAdquision") or "",

            "monto_original": monto_obj.get("valor"),

            "moneda": monto_obj.get("moneda") or "",

            "institucion_otorgante": otorgante.get("nombreInstitucion") or "",

            "pais": localizacion.get("pais") or "",

        })

    return resultado

def cargar_modelo(tipo):

    nombres = {

        "INICIAL": "isolation_forest_inicial.joblib",

        "MODIFICACIÓN": "isolation_forest_modificacion.joblib",

        "CONCLUSIÓN": "isolation_forest_conclusion.joblib",

    }

    ruta = DIR_MODELOS / nombres[tipo]

    if not ruta.exists():

        return None, f"NO_ENCONTRADO: {ruta.name}"

    try:

        return joblib.load(ruta), "CARGADO"

    except Exception as exc:

        return None, f"ERROR_CARGA: {exc}"

def evaluar_modelo(tipo, cantidades, ingreso):

    modelo, estado_modelo = cargar_modelo(tipo)

    if modelo is None:

        return {

            "estado": "NO_EVALUADO",

            "estado_modelo": estado_modelo,

            "score_anomalia": None,

            "interpretacion_score": "No se pudo cargar el modelo."

        }

    if ingreso is None or any(cantidades.get(k) is None for k in CATEGORIAS):

        return {

            "estado": "NO_EVALUADO",

            "estado_modelo": estado_modelo,

            "score_anomalia": None,

            "interpretacion_score": "Faltan datos requeridos para el modelo."

        }

    valores = [

        cantidades["inmuebles"],

        cantidades["vehiculos"],

        cantidades["bienes_muebles"],

        cantidades["inversiones"],

        cantidades["adeudos"],

        cantidades["prestamos"],

        cantidades["participaciones"],

        cantidades["apoyos"],

        cantidades["beneficios_privados"],

        cantidades["fideicomisos"],

        ingreso,

    ]

    matriz = np.log1p(np.asarray(valores, dtype=float)).reshape(1, -1)

    # Verifica que el orden de columnas coincida con el usado al entrenar.
    nombres_modelo = getattr(modelo, "feature_names_in_", None)
    if nombres_modelo is not None and list(nombres_modelo) != FEATURES:
        return {
            "estado": "NO_EVALUADO",
            "estado_modelo": estado_modelo,
            "score_anomalia": None,
            "interpretacion_score": (
                "Las variables u orden del modelo no coinciden con las "
                "11 características esperadas. No se ejecutó la predicción."
            )
        }

    try:

        pred = int(modelo.predict(matriz)[0])

        score = float(modelo.decision_function(matriz)[0])

        return {

            "estado": "ATIPICO" if pred == -1 else "NORMAL",

            "estado_modelo": estado_modelo,

            "score_anomalia": score,

            "interpretacion_score": (

                "Un score menor indica mayor atipicidad relativa dentro del modelo; "

                "no es una probabilidad ni prueba de irregularidad."

            )

        }

    except Exception as exc:

        return {

            "estado": "NO_EVALUADO",

            "estado_modelo": estado_modelo,

            "score_anomalia": None,

            "interpretacion_score": f"Error de predicción: {exc}"

        }

def texto_porcentaje(anterior, actual):

    if anterior is None or actual is None:

        return None

    if anterior == 0:

        return None

    return round(((actual - anterior) / abs(anterior)) * 100, 2)

def escribir_csv(ruta, filas):

    if not filas:

        return

    with ruta.open("w", newline="", encoding="utf-8-sig") as archivo:

        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0].keys()))

        escritor.writeheader()

        escritor.writerows(filas)

def generar_html(informe):

    resumen = informe["resumen"]

    declaraciones = informe["declaraciones"]

    comparaciones = informe["comparaciones"]

    def celda(v):

        return html.escape("" if v is None else str(v))

    filas_decl = ""

    for d in declaraciones:

        filas_decl += (

            "<tr>"

            f"<td>{celda(d['id_registro'])}</td>"

            f"<td>{celda(d['tipo_declaracion'])}</td>"

            f"<td>{celda(d['metadata_actualizacion'])}</td>"

            f"<td>{celda(d['ingreso_neto_anual_equivalente_mxn'])}</td>"

            f"<td>{celda(d['cantidad_inmuebles'])}</td>"

            f"<td>{celda(d['cantidad_vehiculos'])}</td>"

            f"<td>{celda(d['cantidad_inversiones'])}</td>"

            f"<td>{celda(d['cantidad_adeudos'])}</td>"

            f"<td>{celda(d['resultado_modelo'])}</td>"

            f"<td>{celda(d['score_anomalia'])}</td>"

            "</tr>"

        )

    filas_comp = ""

    for c in comparaciones:

        filas_comp += (

            "<tr>"

            f"<td>{celda(c['registro_anterior'])}</td>"

            f"<td>{celda(c['registro_posterior'])}</td>"

            f"<td>{celda(c['tipo_comparacion'])}</td>"

            f"<td>{celda(c['variaciones_categorias'])}</td>"

            f"<td>{celda(c['variacion_ingreso_mxn'])}</td>"

            f"<td>{celda(c['interpretacion'])}</td>"

            "</tr>"

        )

    return f"""<!doctype html>

<html lang="es"><head><meta charset="utf-8">

<meta name="viewport" content="width=device-width, initial-scale=1">

<title>Informe integral de análisis patrimonial</title>

<style>

body{{font-family:Arial,sans-serif;margin:32px;color:#202124;line-height:1.45}}

h1,h2{{color:#17324d}} .cards{{display:flex;flex-wrap:wrap;gap:12px}}

.card{{border:1px solid #ddd;border-radius:8px;padding:14px;min-width:150px}}

table{{border-collapse:collapse;width:100%;font-size:13px;margin:14px 0 26px}}

th,td{{border:1px solid #ddd;padding:8px;text-align:left;vertical-align:top}}

th{{background:#f1f4f7}} .note{{background:#fff8e1;padding:12px;border-left:4px solid #d6a300}}

.small{{color:#555;font-size:12px}} .tag{{font-weight:bold}}

</style></head><body>

<h1>Informe integral de análisis patrimonial</h1>

<p class="small">Generado automáticamente por el motor de análisis PDN.</p>

<div class="cards">

<div class="card"><b>Coincidencias originales</b><br>{resumen['coincidencias_originales']}</div>

<div class="card"><b>Declaraciones únicas</b><br>{resumen['declaraciones_unicas']}</div>

<div class="card"><b>Duplicados omitidos</b><br>{resumen['duplicados_exactos_omitidos']}</div>

<div class="card"><b>Registros atípicos</b><br>{resumen['registros_atipicos']}</div>

<div class="card"><b>No evaluados</b><br>{resumen['registros_no_evaluados']}</div>

</div>

<h2>1. Declaraciones analizadas</h2>

<table><thead><tr>

<th>ID</th><th>Tipo</th><th>Metadata actualización</th><th>Ingreso anual equivalente (MXN)</th>

<th>Inmuebles</th><th>Vehículos</th><th>Inversiones</th><th>Adeudos</th><th>Modelo</th><th>Score</th>

</tr></thead><tbody>{filas_decl}</tbody></table>

<h2>2. Comparación entre declaraciones</h2>

<table><thead><tr>

<th>Registro anterior (orden metadata)</th><th>Registro siguiente</th><th>Tipo</th>

<th>Variaciones de cantidades</th><th>Variación ingreso (MXN)</th><th>Interpretación</th>

</tr></thead><tbody>{filas_comp}</tbody></table>

<h2>3. Adeudos declarados</h2>

{''.join('<p><b>'+celda(a.get('tipo_adeudo'))+'</b> — '+celda(a.get('monto_original'))+' '+celda(a.get('moneda'))+

' — '+celda(a.get('institucion_otorgante'))+' — Fecha declarada: '+celda(a.get('fecha_adquisicion_declarada'))+

' — Operación: '+celda(a.get('tipo_operacion'))+'</p>' for d in declaraciones for a in d['detalle_adeudos']) or '<p>No se encontraron adeudos detallados.</p>'}

<h2>4. Limitaciones metodológicas</h2>

<div class="note">

<ul>

<li>Las coincidencias por nombre no confirman la identidad de una persona.</li>

<li>El ID identifica un registro declarativo, no necesariamente a una persona.</li>

<li>La metadata de actualización no es fecha de presentación ni fecha de adquisición.</li>

<li>El ingreso de INICIAL se anualiza multiplicando el dato mensual por 12; es una equivalencia aritmética.</li>

<li>Los conteos de bienes no representan su valor económico ni permiten calcular patrimonio neto.</li>

<li>El monto original de un adeudo no equivale necesariamente al saldo pendiente.</li>

<li>Un resultado atípico no demuestra corrupción, fraude o enriquecimiento ilícito.</li>

<li>Los resultados requieren revisión humana y corroboración con fuentes adicionales.</li>

</ul></div>

<p class="small">Este informe es un instrumento de apoyo a la revisión, no una determinación legal ni una acusación.</p>

</body></html>"""

def main():

    DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)

    if not ARCHIVO_COINCIDENCIAS.exists():

        raise FileNotFoundError(

            "No existe resultados/coincidencias_persona.json. "

            "Ejecuta primero buscar_declaraciones_persona.py."

        )

    with ARCHIVO_COINCIDENCIAS.open("r", encoding="utf-8") as f:

        datos_coincidencias = json.load(f)

    coincidencias = datos_coincidencias.get("coincidencias", [])

    if not isinstance(coincidencias, list):

        raise ValueError("La lista 'coincidencias' no tiene el formato esperado.")

    vistos = set()

    declaraciones = []

    errores = []

    for coincidencia in coincidencias:

        archivo_relativo = coincidencia.get("archivo")

        indice = coincidencia.get("indice_registro_archivo")

        if not archivo_relativo or indice is None:

            errores.append("Coincidencia sin archivo o índice.")

            continue

        ruta = Path(archivo_relativo)

        if not ruta.is_absolute():

            ruta = RAIZ / ruta

        try:

            with ruta.open("r", encoding="utf-8") as f:

                registros = lista_declaraciones(json.load(f))

            declaracion = registros[int(indice)]

            huella = sha256_json(declaracion)

            if huella in vistos:

                continue

            vistos.add(huella)

            tipo = coincidencia.get("tipo_declaracion") or ""

            if not tipo:

                tipo = obtener(declaracion, ["declaracion", "tipo"], "") or ""

            cantidades, estados = extraer_cantidades(declaracion)

            ingreso, moneda, estado_ingreso, metodo = obtener_tipo_ingreso(declaracion, tipo)

            modelo = evaluar_modelo(tipo, cantidades, ingreso)

            fila = {

                "huella": huella,

                "id_registro": coincidencia.get("id_registro") or coincidencia.get("id") or "",

                "tipo_declaracion": tipo,

                "estado_carpeta": coincidencia.get("estado_carpeta") or "",

                "metadata_actualizacion": coincidencia.get("metadata_actualizacion") or "",

                "ingreso_neto_anual_equivalente_mxn": ingreso,

                "moneda_ingreso": moneda,

                "metodo_normalizacion_ingreso": metodo,

                "estado_ingreso": estado_ingreso,

                "resultado_modelo": modelo["estado"],

                "score_anomalia": modelo["score_anomalia"],

                "estado_modelo": modelo["estado_modelo"],

                "interpretacion_score": modelo["interpretacion_score"],

                "estados_extraccion": estados,

                "detalle_adeudos": extraer_adeudos_detalle(declaracion),

            }

            for nombre, cantidad in cantidades.items():

                fila["cantidad_" + nombre] = cantidad

            declaraciones.append(fila)

        except Exception as exc:

            errores.append(f"{archivo_relativo} índice {indice}: {exc}")

    # Orden técnico por metadata de actualización, no por fecha de presentación.

    declaraciones.sort(key=lambda x: (x.get("metadata_actualizacion") or "", str(x.get("id_registro"))))

    comparaciones = []

    for anterior, posterior in zip(declaraciones, declaraciones[1:]):

        variaciones = []

        for categoria in CATEGORIAS:

            a = anterior.get("cantidad_" + categoria)

            b = posterior.get("cantidad_" + categoria)

            if a is not None and b is not None and a != b:

                variaciones.append(f"{categoria}: {a} -> {b} ({b-a:+})")

        ing_a = anterior["ingreso_neto_anual_equivalente_mxn"]

        ing_b = posterior["ingreso_neto_anual_equivalente_mxn"]

        variacion_ingreso = None

        if ing_a is not None and ing_b is not None:

            variacion_ingreso = round(ing_b - ing_a, 2)

        mismo_tipo = anterior["tipo_declaracion"] == posterior["tipo_declaracion"]

        if mismo_tipo and anterior["tipo_declaracion"] in ("MODIFICACIÓN", "CONCLUSIÓN"):

            tipo_comparacion = "MISMO_TIPO_DECLARACION"

            interpretacion = "Comparación descriptiva dentro del mismo tipo; verificar contexto y fechas."

        elif anterior["tipo_declaracion"] == "INICIAL" or posterior["tipo_declaracion"] == "INICIAL":

            tipo_comparacion = "TIPOS_DISTINTOS_CON_INICIAL"

            interpretacion = (

                "Comparabilidad limitada: INICIAL usa ingreso mensual multiplicado por 12; "

                "la metadata solo ordena los registros."

            )

        else:

            tipo_comparacion = "TIPOS_DISTINTOS"

            interpretacion = (

                "Comparación descriptiva entre tipos distintos; no asumir equivalencia "

                "temporal ni económica."

            )

        comparaciones.append({

            "registro_anterior": anterior["id_registro"],

            "tipo_anterior": anterior["tipo_declaracion"],

            "metadata_anterior": anterior["metadata_actualizacion"],

            "registro_posterior": posterior["id_registro"],

            "tipo_posterior": posterior["tipo_declaracion"],

            "metadata_posterior": posterior["metadata_actualizacion"],

            "tipo_comparacion": tipo_comparacion,

            "variaciones_categorias": "; ".join(variaciones) if variaciones else "Sin variación en cantidades extraídas",

            "variacion_ingreso_mxn": variacion_ingreso,

            "interpretacion": interpretacion,

        })

    atipicos = sum(d["resultado_modelo"] == "ATIPICO" for d in declaraciones)

    no_evaluados = sum(d["resultado_modelo"] == "NO_EVALUADO" for d in declaraciones)

    resumen = {

        "coincidencias_originales": len(coincidencias),

        "declaraciones_unicas": len(declaraciones),

        "duplicados_exactos_omitidos": len(coincidencias) - len(declaraciones),

        "registros_atipicos": atipicos,

        "registros_normales": sum(d["resultado_modelo"] == "NORMAL" for d in declaraciones),

        "registros_no_evaluados": no_evaluados,

        "comparaciones_generadas": len(comparaciones),

        "errores": len(errores),

    }

    informe = {

        "resumen": resumen,

        "declaraciones": declaraciones,

        "comparaciones": comparaciones,

        "errores": errores,

        "advertencias": [

            "La coincidencia nominal no confirma identidad.",

            "metadata_actualizacion no es fecha de presentación.",

            "El ingreso de INICIAL se multiplica por 12 como equivalencia aritmética.",

            "Los conteos de bienes no son valores patrimoniales.",

            "montoOriginal no es necesariamente saldo pendiente.",

            "ATIPICO es una señal estadística, no una prueba de irregularidad."

        ],

        "nota_privacidad": "No se exportaron nombres, apellidos, RFC, CURP ni titulares."

    }

    with ARCHIVO_JSON.open("w", encoding="utf-8") as f:

        json.dump(informe, f, ensure_ascii=False, indent=2)

    filas_csv = []

    for d in declaraciones:

        fila = {k: v for k, v in d.items() if k not in ("huella", "estados_extraccion", "detalle_adeudos", "interpretacion_score", "estado_modelo")}

        filas_csv.append(fila)

    escribir_csv(ARCHIVO_CSV, filas_csv)

    escribir_csv(ARCHIVO_COMPARACIONES, comparaciones)

    ARCHIVO_HTML.write_text(generar_html(informe), encoding="utf-8")

    print("\n" + "=" * 60)

    print("INFORME INTEGRAL DE ANÁLISIS PATRIMONIAL")

    print("=" * 60)

    for k, v in resumen.items():

        print(f"{k.replace('_', ' ').capitalize()}: {v}")

    print("\nRESULTADO POR DECLARACIÓN")

    for d in declaraciones:

        print(

            f"- ID {d['id_registro']} | {d['tipo_declaracion']} | "

            f"modelo: {d['resultado_modelo']} | "

            f"score: {d['score_anomalia']} | "

            f"ingreso anual equivalente: {d['ingreso_neto_anual_equivalente_mxn']}"

        )

    print("\nARCHIVOS GENERADOS")

    print(f"- {ARCHIVO_JSON.relative_to(RAIZ)}")

    print(f"- {ARCHIVO_CSV.relative_to(RAIZ)}")

    print(f"- {ARCHIVO_COMPARACIONES.relative_to(RAIZ)}")

    print(f"- {ARCHIVO_HTML.relative_to(RAIZ)}")

    if errores:

        print("\nERRORES:")

        for e in errores:

            print("-", e)

if __name__ == "__main__":

    main()
