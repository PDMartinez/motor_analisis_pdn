"""
BUSCADOR DE DECLARACIONES PDN POR NOMBRE
Busca coincidencias nominales en los JSON originales sin modificar los archivos.

Uso desde la raíz del proyecto:
python src/analisis/buscar_declaraciones_persona.py --nombre "JUAN" --primer-apellido "PEREZ" --segundo-apellido "LOPEZ"

El segundo apellido es opcional.
Los resultados NO confirman identidad: son coincidencias nominales que requieren revisión.
"""

from pathlib import Path
import argparse
import json
import re
import unicodedata
import csv
import os
from collections import Counter


BASE_DIR = Path(__file__).resolve().parents[2]
DIR_ORIGINALES = Path(os.environ.get("PDN_DATOS_ORIGINALES", str(BASE_DIR / "datos" / "originales"))).resolve()
DIR_RESULTADOS = Path(os.environ.get("PDN_RESULTADOS_DIR", str(BASE_DIR / "resultados"))).resolve()


def normalizar_texto(valor):
    if valor is None:
        return ""
    texto = str(valor).strip().upper()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^A-Z0-9 ]", " ", texto)
    return " ".join(texto.split())


def obtener_texto(datos, clave):
    valor = datos.get(clave, "")
    if isinstance(valor, dict):
        # Compatibilidad por si el dato viene encapsulado como {valor: "..."}.
        valor = valor.get("valor", "")
    if valor is None:
        return ""
    return str(valor).strip()


def obtener_tipo(metadata):
    if not isinstance(metadata, dict):
        return ""
    return (
        metadata.get("tipo")
        or metadata.get("tipoDeclaracion")
        or metadata.get("tipo_declaracion")
        or ""
    )


def iterar_registros(objeto):
    """
    Encuentra registros que contienen metadata + declaracion.
    También admite una estructura donde la declaración esté directamente
    dentro de un objeto con situacionPatrimonial.
    """
    if isinstance(objeto, dict):
        if isinstance(objeto.get("declaracion"), dict):
            yield objeto
            return

        if "situacionPatrimonial" in objeto:
            yield {"declaracion": objeto, "metadata": {}}
            return

        for valor in objeto.values():
            yield from iterar_registros(valor)

    elif isinstance(objeto, list):
        for elemento in objeto:
            yield from iterar_registros(elemento)


def obtener_datos_generales(registro):
    declaracion = registro.get("declaracion", {})
    if not isinstance(declaracion, dict):
        return {}
    situacion = declaracion.get("situacionPatrimonial", {})
    if not isinstance(situacion, dict):
        return {}
    datos = situacion.get("datosGenerales", {})
    return datos if isinstance(datos, dict) else {}


def buscar(nombre, primer_apellido, segundo_apellido=""):
    objetivo_nombre = normalizar_texto(nombre)
    objetivo_primer = normalizar_texto(primer_apellido)
    objetivo_segundo = normalizar_texto(segundo_apellido)

    if not objetivo_nombre or not objetivo_primer:
        raise ValueError("Nombre y primer apellido son obligatorios.")

    if not DIR_ORIGINALES.exists():
        raise FileNotFoundError(
            "No existe la carpeta de datos originales: " + str(DIR_ORIGINALES)
        )

    archivos = sorted(DIR_ORIGINALES.rglob("*.json"))
    resultados = []
    archivos_con_error = 0
    total_registros = 0

    for ruta in archivos:
        try:
            with open(ruta, "r", encoding="utf-8") as archivo:
                contenido = json.load(archivo)
        except Exception:
            archivos_con_error += 1
            continue

        estado = ruta.relative_to(DIR_ORIGINALES).parts[0] if ruta.relative_to(DIR_ORIGINALES).parts else "NO_IDENTIFICADO"

        for indice, registro in enumerate(iterar_registros(contenido)):
            total_registros += 1
            datos = obtener_datos_generales(registro)

            nombre_reg = normalizar_texto(obtener_texto(datos, "nombre"))
            primer_reg = normalizar_texto(obtener_texto(datos, "primerApellido"))
            segundo_reg = normalizar_texto(obtener_texto(datos, "segundoApellido"))

            coincide = (
                nombre_reg == objetivo_nombre
                and primer_reg == objetivo_primer
            )
            if objetivo_segundo:
                coincide = coincide and segundo_reg == objetivo_segundo

            if not coincide:
                continue

            metadata = registro.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}

            resultados.append({
                "archivo": str(ruta.relative_to(BASE_DIR)),
                "indice_registro_archivo": indice,
                "id_registro": registro.get("id", ""),
                "estado_carpeta": estado,
                "tipo_declaracion": obtener_tipo(metadata),
                # Es fecha de actualización del archivo/dato, no fecha de presentación.
                "metadata_actualizacion": metadata.get("actualizacion", ""),
                "coincidencia": (
                    "NOMBRE_PRIMER_Y_SEGUNDO_APELLIDO"
                    if objetivo_segundo
                    else "NOMBRE_Y_PRIMER_APELLIDO_SEGUNDO_NO_ESPECIFICADO"
                ),
            })

    return {
        "criterio_busqueda": {
            "nombre": nombre.strip(),
            "primer_apellido": primer_apellido.strip(),
            "segundo_apellido": segundo_apellido.strip(),
            "normalizacion": "Mayúsculas, sin acentos, puntuación normalizada y espacios compactados",
            "tipo_busqueda": "Coincidencia exacta de los campos proporcionados",
        },
        "resumen": {
            "archivos_json": len(archivos),
            "registros_revisados": total_registros,
            "coincidencias": len(resultados),
            "archivos_con_error_lectura": archivos_con_error,
            "por_tipo_declaracion": dict(Counter(
                r["tipo_declaracion"] or "NO_INFORMADO" for r in resultados
            )),
            "por_estado_carpeta": dict(Counter(
                r["estado_carpeta"] for r in resultados
            )),
        },
        "advertencias": [
            "Una coincidencia de nombre no demuestra que los registros pertenezcan a la misma persona.",
            "Puede haber homónimos o variaciones de captura no detectadas por esta búsqueda exacta.",
            "El ID encontrado identifica un registro de declaración, no una persona.",
            "metadata.actualizacion no debe interpretarse como fecha de presentación de la declaración.",
            "Antes de atribuir declaraciones a una persona se requiere revisión y corroboración adicional.",
        ],
        "coincidencias": resultados,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Busca declaraciones PDN por nombre y apellidos."
    )
    parser.add_argument("--nombre", required=True)
    parser.add_argument("--primer-apellido", required=True)
    parser.add_argument("--segundo-apellido", default="")
    args = parser.parse_args()

    resultado = buscar(
        args.nombre,
        args.primer_apellido,
        args.segundo_apellido
    )

    DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)
    ruta_json = DIR_RESULTADOS / "coincidencias_persona.json"
    ruta_csv = DIR_RESULTADOS / "coincidencias_persona.csv"

    with open(ruta_json, "w", encoding="utf-8") as archivo:
        json.dump(resultado, archivo, ensure_ascii=False, indent=4)

    campos = [
        "archivo",
        "indice_registro_archivo",
        "id_registro",
        "estado_carpeta",
        "tipo_declaracion",
        "metadata_actualizacion",
        "coincidencia",
    ]
    with open(ruta_csv, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(resultado["coincidencias"])

    print("=" * 60)
    print("BUSQUEDA PDN FINALIZADA")
    print("=" * 60)
    print("Archivos JSON:", resultado["resumen"]["archivos_json"])
    print("Registros revisados:", resultado["resumen"]["registros_revisados"])
    print("Coincidencias:", resultado["resumen"]["coincidencias"])
    print("Por tipo:", resultado["resumen"]["por_tipo_declaracion"])
    print("JSON:", ruta_json)
    print("CSV:", ruta_csv)
    print("\nIMPORTANTE: las coincidencias nominales no confirman identidad.")


if __name__ == "__main__":
    main()
