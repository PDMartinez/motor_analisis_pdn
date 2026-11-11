# Motor de análisis PDN - DenunciaFácil 360

Proyecto independiente en Python para preparar, buscar y analizar datos abiertos de declaraciones públicas de México.

## Requisitos
- Python instalado.
- Entorno virtual creado y activado.
- Dependencias instaladas desde `requirements.txt`.

## Estructura
- `datos/originales/`: colocar aquí los JSON originales de la PDN. No modificarlos.
- `datos/procesados/`: archivos derivados y normalizados.
- `notebooks/`: experimentos y exploración interactiva.
- `src/procesamiento/`: lectura, validación y limpieza de datos.
- `src/busqueda/`: búsqueda y comparación de personas.
- `src/analisis/`: análisis de variaciones y generación de resultados.
- `src/modelos/`: experimentos y modelos de Machine Learning.
- `database/`: scripts y esquemas de base de datos.
- `resultados/`: reportes y salidas generadas.

## Preparación en Windows (CMD)
Desde la carpeta del proyecto, activar el entorno virtual que se haya creado fuera del proyecto:

```cmd
C:\Users\danil\pdn\Scripts\activate.bat
```

Instalar dependencias:

```cmd
py -m pip install -r requirements.txt
```

Ejecutar el primer explorador JSON:

```cmd
py src\procesamiento\explorar_json.py
```

## Datos y privacidad
Colocar los archivos JSON originales en `datos/originales/`. No subirlos a repositorios públicos si contienen datos personales o información protegida. El proyecto debe utilizar únicamente campos necesarios y fuentes cuyo acceso y tratamiento estén autorizados.

## Alcance inicial
Esta estructura no contiene un modelo entrenado ni determina irregularidades o culpabilidad. La primera etapa consiste en conocer y preparar los datos disponibles. Las coincidencias y anomalías deberán presentarse como indicios para revisión humana, junto con sus fuentes y limitaciones.
