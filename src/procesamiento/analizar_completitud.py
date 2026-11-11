
"""Analiza la disponibilidad real de los campos de las declaraciones PDN."""

import json
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "datos" / "originales"
RESULT_DIR = PROJECT_ROOT / "resultados"


def tiene_informacion(valor):
    """Comprueba si un valor contiene información."""

    if valor is None:
        return False

    if isinstance(valor, str):
        return bool(valor.strip())

    if isinstance(valor, (dict, list)):
        return len(valor) > 0

    # False y 0 también son valores informados.
    return True


def recorrer_campos(valor, prefijo="", resultado=None):
    """Recopila las rutas y sus valores dentro de un registro."""

    if resultado is None:
        resultado = {}

    if isinstance(valor, dict):
        for clave, contenido in valor.items():

            ruta = f"{prefijo}.{clave}" if prefijo else clave

            resultado.setdefault(ruta, False)

            if tiene_informacion(contenido):
                resultado[ruta] = True

            recorrer_campos(contenido, ruta, resultado)

    elif isinstance(valor, list):
        for elemento in valor:
            recorrer_campos(elemento, prefijo, resultado)

    return resultado


def main():

    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    archivos = sorted(DATA_DIR.rglob("*.json"))

    total_registros = 0
    campos_informados = Counter()
    campos_detectados = set()

    for archivo in archivos:

        try:
            with archivo.open("r", encoding="utf-8-sig") as f:
                contenido = json.load(f)

            registros = contenido if isinstance(contenido, list) else []

            for registro in registros:

                if not isinstance(registro, dict):
                    continue

                total_registros += 1

                campos = recorrer_campos(registro)

                campos_detectados.update(campos.keys())

                for campo, informado in campos.items():
                    if informado:
                        campos_informados[campo] += 1

        except Exception as exc:
            print(f"Error en {archivo.name}: {exc}")

    informe = []

    informe.append("=" * 75)
    informe.append("ANÁLISIS DE DISPONIBILIDAD REAL DE CAMPOS - PDN")
    informe.append("=" * 75)

    informe.append(f"\nTotal de registros: {total_registros}")
    informe.append(f"Cantidad de campos/rutas detectados: {len(campos_detectados)}")

    informe.append("\nCAMPOS CON MAYOR DISPONIBILIDAD DE INFORMACIÓN")

    for campo in sorted(campos_detectados):

        cantidad = campos_informados[campo]
        porcentaje = (
            cantidad / total_registros * 100
            if total_registros else 0
        )

        informe.append(
            f"{campo}: {cantidad} registros informados "
            f"({porcentaje:.2f}%)"
        )

    informe.append("\n" + "=" * 75)
    informe.append("FIN DEL INFORME")
    informe.append("=" * 75)

    texto = "\n".join(informe)

    print(texto)

    salida = RESULT_DIR / "informe_completitud_pdn.txt"

    with salida.open("w", encoding="utf-8") as f:
        f.write(texto)

    print(f"\nInforme guardado en: {salida}")


if __name__ == "__main__":
    main()
