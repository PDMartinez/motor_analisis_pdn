# -*- coding: utf-8 -*-
"""
interpretar_resultados.py
Interpreta el informe integral generado por el motor PDN para DenunciaFácil 360.

No entrena modelos ni modifica el informe original.
Genera:
- resultados/interpretacion_patrimonial.json
- resultados/interpretacion_declaraciones.csv
- resultados/interpretacion_comparaciones.csv
- resultados/interpretacion_patrimonial.html

Ejecutar desde la raíz del proyecto:
    python src/analisis/interpretar_resultados.py
"""

import csv
import html
import json
import math
import os
from collections import Counter
from datetime import datetime
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[2]
CARPETA_RESULTADOS = Path(os.environ.get("PDN_RESULTADOS_DIR", str(RAIZ / "resultados"))).resolve()
ARCHIVO_ENTRADA = CARPETA_RESULTADOS / "informe_integral_patrimonial.json"

ARCHIVO_JSON = CARPETA_RESULTADOS / "interpretacion_patrimonial.json"
ARCHIVO_CSV_DECLARACIONES = CARPETA_RESULTADOS / "interpretacion_declaraciones.csv"
ARCHIVO_CSV_COMPARACIONES = CARPETA_RESULTADOS / "interpretacion_comparaciones.csv"
ARCHIVO_HTML = CARPETA_RESULTADOS / "interpretacion_patrimonial.html"

CATEGORIAS = {
    "cantidad_inmuebles": "Inmuebles",
    "cantidad_vehiculos": "Vehículos",
    "cantidad_bienes_muebles": "Bienes muebles",
    "cantidad_inversiones": "Inversiones",
    "cantidad_adeudos": "Adeudos",
    "cantidad_prestamos": "Préstamos o comodatos",
    "cantidad_participaciones": "Participaciones",
    "cantidad_apoyos": "Apoyos",
    "cantidad_beneficios_privados": "Beneficios privados",
    "cantidad_fideicomisos": "Fideicomisos",
}


def numero(valor):
    """Convierte un valor a número finito o devuelve None."""
    try:
        if valor is None or isinstance(valor, bool):
            return None
        resultado = float(valor)
        if not math.isfinite(resultado):
            return None
        return resultado
    except (TypeError, ValueError):
        return None


def formato_moneda(valor):
    valor = numero(valor)
    if valor is None:
        return "No disponible"
    return "$" + format(valor, ",.2f") + " MXN"


def fecha_legible(valor):
    if not valor:
        return "No disponible"
    try:
        fecha = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        return fecha.strftime("%d/%m/%Y")
    except ValueError:
        return str(valor)


def interpretar_declaracion(registro):
    observaciones = []
    recomendaciones = []

    tipo = registro.get("tipo_declaracion", "No especificado")
    resultado = registro.get("resultado_modelo", "NO_EVALUADO")
    estado_modelo = registro.get("estado_modelo", "NO_ESPECIFICADO")
    score = numero(registro.get("score_anomalia"))
    ingreso = numero(registro.get("ingreso_neto_anual_equivalente_mxn"))
    estado_ingreso = registro.get("estado_ingreso", "NO_ESPECIFICADO")
    metodo_ingreso = registro.get("metodo_normalizacion_ingreso", "NO_ESPECIFICADO")

    # Resultado del modelo estadístico.
    if estado_modelo != "CARGADO" or resultado == "NO_EVALUADO":
        observaciones.append(
            "La declaración no cuenta con una evaluación válida del modelo estadístico."
        )
        recomendaciones.append(
            "Verificar la disponibilidad del modelo y la calidad de los datos antes de interpretar esta declaración."
        )
    elif resultado == "ATIPICO":
        observaciones.append(
            "El modelo estadístico clasificó esta declaración como ATÍPICA respecto de los patrones aprendidos."
        )
        recomendaciones.append(
            "Revisar manualmente las variables de esta declaración y corroborar la información con fuentes independientes."
        )
    elif resultado == "NORMAL":
        observaciones.append(
            "El modelo no identificó un patrón estadísticamente atípico en esta declaración."
        )
    else:
        observaciones.append(
            "El resultado del modelo no corresponde a una categoría reconocida por este intérprete."
        )
        recomendaciones.append("Verificar el valor de resultado_modelo en el informe de origen.")

    if score is not None:
        observaciones.append(
            "Score estadístico: {:.6f}. Un valor menor representa mayor atipicidad relativa dentro del modelo; no es una probabilidad.".format(score)
        )

    # Calidad de extracción.
    estados = registro.get("estados_extraccion") or {}
    estados_no_ok = [
        nombre for nombre, estado in estados.items()
        if str(estado).upper() != "OK"
    ]
    if estados_no_ok:
        observaciones.append(
            "Hay categorías cuya extracción no figura como OK: " + ", ".join(estados_no_ok) + "."
        )
        recomendaciones.append(
            "Revisar las categorías con extracción incompleta antes de sacar conclusiones."
        )
    elif estados:
        observaciones.append(
            "Las categorías patrimoniales incluidas en el informe presentan estado de extracción OK."
        )

    # Conteos patrimoniales: un cero es un conteo extraído, no una prueba de inexistencia.
    categorias_con_elementos = []
    categorias_cero = []
    categorias_sin_dato = []

    for clave, etiqueta in CATEGORIAS.items():
        valor = numero(registro.get(clave))
        if valor is None:
            categorias_sin_dato.append(etiqueta)
        elif valor > 0:
            categorias_con_elementos.append("{}: {}".format(etiqueta, int(valor)))
        else:
            categorias_cero.append(etiqueta)

    if categorias_con_elementos:
        observaciones.append(
            "Categorías con elementos registrados: " + "; ".join(categorias_con_elementos) + "."
        )
    if categorias_cero:
        observaciones.append(
            "El informe registra cero elementos en: " + ", ".join(categorias_cero) + "."
        )
        recomendaciones.append(
            "Interpretar los conteos cero como ausencia de elementos en los datos extraídos, no como prueba de que la persona carezca de esos bienes o intereses."
        )
    if categorias_sin_dato:
        observaciones.append(
            "No hay conteo disponible para: " + ", ".join(categorias_sin_dato) + "."
        )
        recomendaciones.append(
            "Verificar los campos faltantes; un dato no disponible no equivale a cero."
        )

    # Ingresos y normalización.
    if estado_ingreso == "VALIDADO_MXN" and ingreso is not None:
        if tipo == "INICIAL" or metodo_ingreso == "MENSUAL_X_12":
            observaciones.append(
                "Ingreso mensual convertido a equivalente anual mediante multiplicación por 12: {}. Es una equivalencia aritmética, no un ingreso anual declarado directamente.".format(
                    formato_moneda(ingreso)
                )
            )
        else:
            observaciones.append(
                "Ingreso neto anual reportado en MXN: {}.".format(formato_moneda(ingreso))
            )
        if ingreso == 0:
            recomendaciones.append(
                "Verificar el contexto del ingreso declarado en cero; no debe interpretarse automáticamente como ausencia de actividad económica."
            )
    else:
        observaciones.append(
            "El ingreso no está disponible como dato validado en MXN para esta declaración."
        )
        recomendaciones.append(
            "No utilizar esta declaración para comparaciones monetarias hasta validar el ingreso y su moneda."
        )

    # Adeudos: solo describir lo que efectivamente contiene el informe.
    adeudos = registro.get("detalle_adeudos")
    if isinstance(adeudos, list):
        if adeudos:
            observaciones.append(
                "El informe contiene {} elemento(s) de detalle de adeudos.".format(len(adeudos))
            )
            recomendaciones.append(
                "Revisar cada adeudo y sus datos de origen; el monto original no necesariamente representa el saldo pendiente."
            )
        else:
            observaciones.append(
                "El informe no contiene elementos en el detalle de adeudos de esta declaración."
            )

    observaciones.append(
        "La fecha mostrada corresponde a metadata_actualizacion y no debe tratarse como fecha confirmada de presentación."
    )

    # Quitar posibles repeticiones conservando el orden.
    observaciones = list(dict.fromkeys(observaciones))
    recomendaciones = list(dict.fromkeys(recomendaciones))

    return {
        "id_registro": str(registro.get("id_registro", "")),
        "tipo_declaracion": tipo,
        "estado_carpeta": registro.get("estado_carpeta"),
        "metadata_actualizacion": registro.get("metadata_actualizacion"),
        "fecha_metadata_legible": fecha_legible(registro.get("metadata_actualizacion")),
        "resultado_modelo": resultado,
        "score_anomalia": score,
        "ingreso_neto_anual_equivalente_mxn": ingreso,
        "estado_ingreso": estado_ingreso,
        "metodo_normalizacion_ingreso": metodo_ingreso,
        "cantidades": {
            clave.replace("cantidad_", ""): registro.get(clave)
            for clave in CATEGORIAS
        },
        "observaciones": observaciones,
        "recomendaciones_revision": recomendaciones,
        "advertencia_identidad": "La coincidencia nominal no confirma que todas las declaraciones correspondan a la misma persona."
    }


def interpretar_comparacion(comparacion):
    tipo = comparacion.get("tipo_comparacion", "NO_ESPECIFICADO")
    variacion = numero(comparacion.get("variacion_ingreso_mxn"))
    texto = comparacion.get("interpretacion", "")
    categorias = comparacion.get("variaciones_categorias", "")

    observaciones = [
        "Comparación entre los registros {} ({}) y {} ({}).".format(
            comparacion.get("registro_anterior", ""),
            comparacion.get("tipo_anterior", ""),
            comparacion.get("registro_posterior", ""),
            comparacion.get("tipo_posterior", "")
        )
    ]

    if categorias:
        observaciones.append("Variaciones de cantidades informadas por el análisis: {}.".format(categorias))

    if variacion is not None:
        if tipo == "MISMO_TIPO_DECLARACION":
            if variacion > 0:
                sentido = "aumento"
            elif variacion < 0:
                sentido = "disminución"
            else:
                sentido = "sin variación"
            observaciones.append(
                "La diferencia aritmética de ingreso entre los registros es {} de {}.".format(
                    sentido, formato_moneda(abs(variacion))
                )
            )
        else:
            observaciones.append(
                "Se informa una diferencia aritmética de ingreso de {}; la comparación tiene comparabilidad limitada por tratarse de tipos de declaración distintos.".format(
                    formato_moneda(variacion)
                )
            )

    if texto:
        observaciones.append("Nota metodológica del análisis original: {}.".format(texto))

    observaciones.append(
        "La metadata de actualización solo permite ordenar los registros; no confirma fechas de presentación ni demuestra evolución patrimonial."
    )

    return {
        "registro_anterior": str(comparacion.get("registro_anterior", "")),
        "tipo_anterior": comparacion.get("tipo_anterior"),
        "metadata_anterior": comparacion.get("metadata_anterior"),
        "registro_posterior": str(comparacion.get("registro_posterior", "")),
        "tipo_posterior": comparacion.get("tipo_posterior"),
        "metadata_posterior": comparacion.get("metadata_posterior"),
        "tipo_comparacion": tipo,
        "variacion_ingreso_mxn": variacion,
        "variaciones_categorias": categorias,
        "observaciones": observaciones,
        "requiere_revision_humana": True
    }


def crear_resumen(informe, declaraciones):
    resumen_origen = informe.get("resumen") or {}
    tipos = Counter(d.get("tipo_declaracion", "NO_ESPECIFICADO") for d in declaraciones)
    resultados = Counter(d.get("resultado_modelo", "NO_EVALUADO") for d in declaraciones)

    scores = [
        d["score_anomalia"] for d in declaraciones
        if d.get("score_anomalia") is not None
    ]
    scores_ordenados = sorted(scores)

    ingresos_validos = [
        d["ingreso_neto_anual_equivalente_mxn"]
        for d in declaraciones
        if d.get("estado_ingreso") == "VALIDADO_MXN"
        and d.get("ingreso_neto_anual_equivalente_mxn") is not None
    ]

    conteo_categorias = {}
    for clave, etiqueta in CATEGORIAS.items():
        valores = [numero(d.get(clave)) for d in informe.get("declaraciones", [])]
        validos = [v for v in valores if v is not None]
        conteo_categorias[etiqueta] = {
            "declaraciones_con_elementos": sum(1 for v in validos if v > 0),
            "elementos_registrados_total": int(sum(validos)),
            "declaraciones_con_cero": sum(1 for v in validos if v == 0),
            "declaraciones_sin_dato": len(valores) - len(validos)
        }

    score_menor = None
    if declaraciones:
        con_score = [d for d in declaraciones if d.get("score_anomalia") is not None]
        if con_score:
            score_menor = min(con_score, key=lambda d: d["score_anomalia"])

    return {
        "resumen_origen": resumen_origen,
        "declaraciones_por_tipo": dict(tipos),
        "resultados_modelo": dict(resultados),
        "cantidad_scores_disponibles": len(scores),
        "score_minimo": min(scores) if scores else None,
        "score_maximo": max(scores) if scores else None,
        "registro_con_score_menor": (
            {
                "id_registro": score_menor["id_registro"],
                "tipo_declaracion": score_menor["tipo_declaracion"],
                "score_anomalia": score_menor["score_anomalia"],
                "resultado_modelo": score_menor["resultado_modelo"]
            } if score_menor else None
        ),
        "ingresos_validos_mxn": {
            "cantidad": len(ingresos_validos),
            "minimo": min(ingresos_validos) if ingresos_validos else None,
            "maximo": max(ingresos_validos) if ingresos_validos else None,
            "promedio": (
                sum(ingresos_validos) / len(ingresos_validos)
                if ingresos_validos else None
            )
        },
        "categorias_patrimoniales": conteo_categorias
    }


def escribir_csv(ruta, filas, campos):
    with ruta.open("w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos, extrasaction="ignore")
        escritor.writeheader()
        for fila in filas:
            fila_csv = dict(fila)
            for clave, valor in fila_csv.items():
                if isinstance(valor, (dict, list)):
                    fila_csv[clave] = json.dumps(valor, ensure_ascii=False)
            escritor.writerow(fila_csv)


def construir_html(resultado):
    resumen = resultado["resumen"]
    declaraciones = resultado["declaraciones"]
    comparaciones = resultado["comparaciones"]

    tarjetas = [
        ("Declaraciones", resumen["resumen_origen"].get("declaraciones_unicas", len(declaraciones))),
        ("Normales", resumen["resultados_modelo"].get("NORMAL", 0)),
        ("Atípicas", resumen["resultados_modelo"].get("ATIPICO", 0)),
        ("No evaluadas", resumen["resultados_modelo"].get("NO_EVALUADO", 0)),
    ]

    html_tarjetas = "".join(
        '<div class="card"><div class="numero">{}</div><div class="etiqueta">{}</div></div>'.format(
            html.escape(str(valor)), html.escape(str(etiqueta))
        )
        for etiqueta, valor in tarjetas
    )

    filas = []
    for d in declaraciones:
        filas.append(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                html.escape(d["id_registro"]),
                html.escape(str(d["tipo_declaracion"])),
                html.escape(str(d["fecha_metadata_legible"])),
                html.escape(str(d["resultado_modelo"])),
                html.escape(str(d["score_anomalia"])),
                html.escape("; ".join(d["observaciones"]))
            )
        )

    filas_comparaciones = []
    for c in comparaciones:
        filas_comparaciones.append(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                html.escape(c["registro_anterior"]),
                html.escape(c["registro_posterior"]),
                html.escape(str(c["tipo_comparacion"])),
                html.escape(" ".join(c["observaciones"]))
            )
        )

    advertencias = [
        "Las coincidencias por nombre no confirman identidad.",
        "La fecha metadata_actualizacion no es necesariamente la fecha de presentación.",
        "Los conteos de bienes no representan valores monetarios ni patrimonio neto.",
        "El ingreso mensual de una declaración INICIAL multiplicado por 12 es una equivalencia aritmética.",
        "El score del modelo no es una probabilidad ni prueba de irregularidad.",
        "Toda señal o diferencia requiere revisión humana y corroboración independiente."
    ]

    return """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Interpretación patrimonial - DenunciaFácil 360</title>
<style>
body{{font-family:Arial,sans-serif;background:#f4f6f9;color:#202938;margin:0;padding:24px}}
main{{max-width:1400px;margin:auto}}
h1,h2{{color:#26364a}}
.sub{{color:#64748b}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:22px 0}}
.card{{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:18px}}
.numero{{font-size:28px;font-weight:bold}} .etiqueta{{color:#64748b;margin-top:5px}}
section{{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:20px;margin:18px 0;overflow-x:auto}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border-bottom:1px solid #e5e7eb;padding:10px;text-align:left;vertical-align:top}}
th{{background:#f8fafc}}
li{{margin:8px 0}}
.note{{background:#fff8e7;border-left:4px solid #d69e2e;padding:14px;margin:14px 0}}
</style>
</head>
<body><main>
<h1>Interpretación del análisis patrimonial</h1>
<p class="sub">DenunciaFácil 360 · Informe generado automáticamente a partir del informe integral PDN.</p>
<div class="cards">{cards}</div>
<section><h2>Alcance y resumen</h2>
<p>Se procesaron {n_decl} declaraciones y {n_comp} comparaciones. La interpretación se genera mediante reglas descriptivas; no constituye una determinación de responsabilidad ni una conclusión jurídica.</p>
<div class="note"><strong>Advertencia:</strong> las coincidencias nominales no confirman que todos los registros pertenezcan a la misma persona. La metadata de actualización no confirma fechas de presentación.</div>
</section>
<section><h2>Declaraciones e interpretaciones</h2>
<table><thead><tr><th>ID</th><th>Tipo</th><th>Fecha metadata</th><th>Modelo</th><th>Score</th><th>Observaciones</th></tr></thead>
<tbody>{filas}</tbody></table>
</section>
<section><h2>Comparaciones entre declaraciones</h2>
<table><thead><tr><th>Registro anterior</th><th>Registro posterior</th><th>Tipo comparación</th><th>Interpretación</th></tr></thead>
<tbody>{filas_comp}</tbody></table>
</section>
<section><h2>Advertencias metodológicas</h2><ul>{advertencias}</ul></section>
<p class="sub">Este documento es una herramienta de apoyo para revisión humana. No acredita identidad, enriquecimiento ilícito, corrupción ni ausencia de irregularidades.</p>
</main></body></html>""".format(
        cards=html_tarjetas,
        n_decl=len(declaraciones),
        n_comp=len(comparaciones),
        filas="".join(filas),
        filas_comp="".join(filas_comparaciones),
        advertencias="".join("<li>{}</li>".format(html.escape(x)) for x in advertencias)
    )


def main():
    print("=" * 62)
    print("INTERPRETACIÓN AUTOMÁTICA - DENUNCIAFÁCIL 360")
    print("=" * 62)

    if not ARCHIVO_ENTRADA.exists():
        print("\nERROR: No se encontró el informe de entrada:")
        print(ARCHIVO_ENTRADA)
        print("\nPrimero ejecutá el motor integral de análisis patrimonial.")
        return 1

    try:
        with ARCHIVO_ENTRADA.open("r", encoding="utf-8") as archivo:
            informe = json.load(archivo)
    except Exception as exc:
        print("\nERROR al leer el informe: {}".format(exc))
        return 1

    registros = informe.get("declaraciones")
    if not isinstance(registros, list):
        print("\nERROR: El informe no contiene una lista 'declaraciones'.")
        return 1

    comparaciones_origen = informe.get("comparaciones") or []
    declaraciones = [interpretar_declaracion(r) for r in registros]
    comparaciones = [interpretar_comparacion(c) for c in comparaciones_origen]

    resultado = {
        "titulo": "Interpretación automática del análisis patrimonial",
        "version": "1.0",
        "metodo": "Reglas descriptivas sobre resultados del motor PDN; no es un nuevo modelo predictivo.",
        "resumen": crear_resumen(informe, declaraciones),
        "declaraciones": declaraciones,
        "comparaciones": comparaciones,
        "advertencias": [
            "La coincidencia nominal no confirma identidad.",
            "metadata_actualizacion no es fecha confirmada de presentación.",
            "Los conteos de bienes no son valores patrimoniales ni permiten calcular patrimonio neto.",
            "El ingreso mensual de INICIAL multiplicado por 12 es una equivalencia aritmética.",
            "montoOriginal no representa necesariamente el saldo pendiente de una deuda.",
            "NORMAL no demuestra ausencia de irregularidades; ATIPICO no demuestra una conducta ilícita.",
            "Las observaciones requieren revisión humana y corroboración independiente."
        ]
    }

    CARPETA_RESULTADOS.mkdir(parents=True, exist_ok=True)

    with ARCHIVO_JSON.open("w", encoding="utf-8") as archivo:
        json.dump(resultado, archivo, ensure_ascii=False, indent=2)

    campos_decl = [
        "id_registro", "tipo_declaracion", "estado_carpeta",
        "metadata_actualizacion", "resultado_modelo", "score_anomalia",
        "ingreso_neto_anual_equivalente_mxn", "estado_ingreso",
        "metodo_normalizacion_ingreso", "cantidades",
        "observaciones", "recomendaciones_revision"
    ]
    escribir_csv(ARCHIVO_CSV_DECLARACIONES, declaraciones, campos_decl)

    campos_comp = [
        "registro_anterior", "tipo_anterior", "metadata_anterior",
        "registro_posterior", "tipo_posterior", "metadata_posterior",
        "tipo_comparacion", "variacion_ingreso_mxn",
        "variaciones_categorias", "observaciones", "requiere_revision_humana"
    ]
    escribir_csv(ARCHIVO_CSV_COMPARACIONES, comparaciones, campos_comp)

    ARCHIVO_HTML.write_text(construir_html(resultado), encoding="utf-8")

    resumen = resultado["resumen"]
    print("\nDeclaraciones interpretadas: {}".format(len(declaraciones)))
    print("Comparaciones interpretadas: {}".format(len(comparaciones)))
    print("Resultados del modelo: {}".format(resumen["resultados_modelo"]))
    print("\nArchivos generados:")
    print("JSON :", ARCHIVO_JSON.relative_to(RAIZ))
    print("CSV declaraciones:", ARCHIVO_CSV_DECLARACIONES.relative_to(RAIZ))
    print("CSV comparaciones:", ARCHIVO_CSV_COMPARACIONES.relative_to(RAIZ))
    print("HTML :", ARCHIVO_HTML.relative_to(RAIZ))
    print("\nIMPORTANTE:")
    print("Las observaciones son descriptivas y requieren revisión humana.")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
