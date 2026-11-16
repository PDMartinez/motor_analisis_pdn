# Motor de análisis PDN - paquete preparado para DenunciaFácil 360

## Estructura

- `src/analisis/`: buscador, analizador integral, intérprete y orquestador.
- `src/modelos/entrenados/`: los tres modelos Isolation Forest ya entrenados.
- `datos/originales/`: aquí se copian los JSON originales de la PDN, manteniendo su estructura de carpetas.
- `resultados/denuncias/<id>/`: salida aislada por denuncia.

## 1. Instalar en Windows

Abrir CMD en la carpeta raíz del proyecto:

```bat
py -3.9 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-produccion.txt
```

Usar inicialmente la misma versión de Python con la que se entrenaron los modelos (el proyecto original fue trabajado con Python 3.9). Si los modelos se guardaron con versiones específicas de scikit-learn, instalar esa misma versión para evitar incompatibilidades de serialización.

## 2. Colocar los datos PDN

Copiar los JSON originales dentro de `datos/originales/`, sin alterar los subdirectorios ni los archivos. No se incluyen en este paquete por su tamaño.

## 3. Probar el motor desde consola

```bat
.venv\Scripts\python.exe src\analisis\ejecutar_analisis.py --denuncia-id 125 --nombre "JUAN CARLOS" --primer-apellido "PEREZ" --segundo-apellido "LOPEZ"
```

El segundo apellido es opcional. No ejecutar con datos reales hasta confirmar que la carpeta de originales y las dependencias estén correctamente instaladas.

## 4. Resultado por denuncia

Cada ejecución genera su propia carpeta:

`resultados/denuncias/<id>/`

Archivos principales:

- `estado_ejecucion.json`: estado `EN_PROCESO`, `FINALIZADO`, `SIN_COINCIDENCIAS` o `ERROR`.
- `coincidencias_persona.json`: resultado de búsqueda.
- `informe_integral_patrimonial.json`: salida del análisis integral.
- `interpretacion_patrimonial.json`: informe interpretado para el dashboard.
- `interpretacion_patrimonial.html`: informe HTML alternativo.
- `ejecucion.log`: salida y errores técnicos de los pasos.

## 5. Integración PHP

PHP debe ejecutar el orquestador con `proc_open` o una cola de trabajos, usando la ruta absoluta a `.venv\Scripts\python.exe` y pasando los argumentos como arreglo/escapados correctamente. No concatenar datos del usuario directamente a un comando de shell. El proceso debe ejecutarse fuera del directorio público de Apache.

El dashboard de DenunciaFácil 360 debe leer únicamente `interpretacion_patrimonial.json` de la carpeta asociada a la denuncia, validando que el usuario tenga permiso para consultar esa denuncia.

## Seguridad y metodología

- Mantener `datos/originales/`, `resultados/` y los modelos fuera de `htdocs` o bloquear completamente su acceso HTTP.
- No exponer los JSON originales ni logs al navegador.
- El resultado nominal no confirma identidad. `NORMAL` no demuestra ausencia de irregularidades y `ATIPICO` no demuestra conducta ilícita.
- `metadata.actualizacion` no es fecha confirmada de presentación.
- Los informes requieren revisión humana y corroboración independiente.
