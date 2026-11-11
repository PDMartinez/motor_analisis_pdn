
"""Analiza estadísticamente los archivos JSON de la PDN."""

import json
from pathlib import Path
from collections import Counter, defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "datos" / "originales"
RESULT_DIR = PROJECT_ROOT / "resultados"


def obtener_registros(contenido):
    """Obtiene los registros de un archivo JSON."""

    if isinstance(contenido, list):
        return contenido

    if isinstance(contenido, dict):
        # Algunos archivos pueden contener los registros
        # dentro de una propiedad del objeto principal.
        for valor in contenido.values():
            if isinstance(valor, list):
                return valor

        return [contenido]

    return []


def valor_no_vacio(valor):
    """Determina si un valor contiene información."""

    if valor is None:
        return False

    if isinstance(valor, str):
        return bool(valor.strip())

    if isinstance(valor, (dict, list)):
        return len(valor) > 0

    return True


def analizar_rutas(valor, prefijo="", rutas=None):
    """Identifica los campos presentes en la estructura JSON."""

    if rutas is None:
        rutas = set()

    if isinstance(valor, dict):
        for clave, contenido in valor.items():
            ruta = f"{prefijo}.{clave}" if prefijo else clave
            rutas.add(ruta)
            analizar_rutas(contenido, ruta, rutas)

    elif isinstance(valor, list):
        for elemento in valor:
            analizar_rutas(elemento, prefijo, rutas)

    return rutas


def obtener_por_ruta(registro, ruta):
    """Obtiene un valor utilizando una ruta de campos."""

    valor = registro

    for clave in ruta.split("."):
        if not isinstance(valor, dict) or clave not in valor:
            return None

        valor = valor[clave]

    return valor


def main():

    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    archivos = sorted(DATA_DIR.rglob("*.json"))

    if not archivos:
        print("No se encontraron archivos JSON.")
        return

    total_registros = 0
    archivos_validos = 0
    archivos_invalidos = 0

    tipos_declaracion = Counter()
    instituciones = Counter()
    años = Counter()
    campos_presentes = Counter()

    registros_completos = 0
    registros_incompletos = 0

    campos_metadata = [
        "actualizacion",
        "institucion",
        "declaracionCompleta",
        "actualizacionConflictoInteres",
        "tipo"
    ]

    campos_metadata_vacios = Counter()

    print("=" * 65)
    print("ANÁLISIS DE DATOS - PLATAFORMA DIGITAL NACIONAL")
    print("=" * 65)

    for archivo in archivos:

        try:
            with archivo.open("r", encoding="utf-8-sig") as f:
                contenido = json.load(f)

            registros = obtener_registros(contenido)
            archivos_validos += 1

            print(f"Procesando: {archivo.relative_to(DATA_DIR)}")

            for registro in registros:

                if not isinstance(registro, dict):
                    continue

                total_registros += 1

                metadata = registro.get("metadata", {})

                if not isinstance(metadata, dict):
                    metadata = {}

                # Tipo de declaración
                tipo = metadata.get("tipo")

                if valor_no_vacio(tipo):
                    tipos_declaracion[str(tipo)] += 1
                else:
                    tipos_declaracion["No informado"] += 1

                # Institución
                institucion = metadata.get("institucion")

                if valor_no_vacio(institucion):
                    instituciones[str(institucion)] += 1
                else:
                    instituciones["No informada"] += 1

                # Año de actualización
                fecha = metadata.get("actualizacion")

                if isinstance(fecha, str) and len(fecha) >= 4:
                    año = fecha[:4]

                    if año.isdigit():
                        años[año] += 1
                    else:
                        años["Fecha no válida"] += 1
                else:
                    años["No informado"] += 1

                # Campos de metadata faltantes
                for campo in campos_metadata:
                    if not valor_no_vacio(metadata.get(campo)):
                        campos_metadata_vacios[campo] += 1

                # Campos estructurales presentes
                rutas = analizar_rutas(registro)

                for ruta in rutas:
                    campos_presentes[ruta] += 1

                # Completitud declarativa según metadata
                if metadata.get("declaracionCompleta") is True:
                    registros_completos += 1
                else:
                    registros_incompletos += 1

        except json.JSONDecodeError as exc:
            archivos_invalidos += 1
            print(f"JSON inválido: {archivo.name} - {exc}")

        except Exception as exc:
            archivos_invalidos += 1
            print(f"Error en {archivo.name}: {exc}")

    # Construcción del informe
    informe = []

    informe.append("=" * 65)
    informe.append("INFORME DE ANÁLISIS DE DATOS - PDN")
    informe.append("=" * 65)

    informe.append("\n1. RESUMEN GENERAL")
    informe.append(f"Archivos encontrados: {len(archivos)}")
    informe.append(f"Archivos procesados correctamente: {archivos_validos}")
    informe.append(f"Archivos con errores: {archivos_invalidos}")
    informe.append(f"Total de registros analizados: {total_registros}")

    informe.append("\n2. TIPOS DE DECLARACIÓN")
    for tipo, cantidad in tipos_declaracion.most_common():
        informe.append(f"{tipo}: {cantidad}")

    informe.append("\n3. PRINCIPALES INSTITUCIONES")
    for institucion, cantidad in instituciones.most_common(20):
        informe.append(f"{institucion}: {cantidad}")

    informe.append("\n4. REGISTROS POR AÑO DE ACTUALIZACIÓN")
    for año, cantidad in sorted(años.items()):
        informe.append(f"{año}: {cantidad}")

    informe.append("\n5. INFORMACIÓN DE COMPLETITUD")
    informe.append(f"Declaraciones marcadas como completas: {registros_completos}")
    informe.append(f"Declaraciones no marcadas como completas: {registros_incompletos}")

    informe.append("\n6. CAMPOS DE METADATA SIN INFORMACIÓN")
    for campo, cantidad in campos_metadata_vacios.most_common():
        informe.append(f"{campo}: {cantidad}")

    informe.append("\n7. CAMPOS Y ESTRUCTURAS ENCONTRADAS")

    for campo, cantidad in campos_presentes.most_common(60):
        porcentaje = (
            cantidad / total_registros * 100
            if total_registros else 0
        )

        informe.append(
            f"{campo}: {cantidad} registros ({porcentaje:.2f}%)"
        )

    informe.append("\n" + "=" * 65)
    informe.append("FIN DEL INFORME")
    informe.append("=" * 65)

    texto_informe = "\n".join(informe)

    # Mostrar en terminal
    print("\n" + texto_informe)

    # Guardar informe
    archivo_salida = RESULT_DIR / "informe_analisis_pdn.txt"

    with archivo_salida.open("w", encoding="utf-8") as f:
        f.write(texto_informe)

    print(f"\nInforme guardado en: {archivo_salida}")


if __name__ == "__main__":
    main()
