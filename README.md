# Motor de Análisis PDN

## Paquete preparado para DenunciaFácil 360

## 1. Descripción general

El Motor de Análisis PDN es una aplicación desarrollada en Python para realizar búsquedas nominales y análisis patrimoniales a partir de los datos abiertos de la Plataforma Digital Nacional (PDN).

El motor permite identificar posibles coincidencias de personas, recuperar información patrimonial disponible, realizar comparaciones y aplicar modelos de aprendizaje automático basados en Isolation Forest.

Está diseñado para funcionar de manera independiente y comunicarse con DenunciaFácil 360 mediante la ejecución de procesos Python desde PHP.

## 2. Estructura del proyecto

La estructura general del motor es la siguiente:

```text
motor_analisis_pdn/
│
├── src/
│   ├── analisis/
│   │   ├── buscador
│   │   ├── analizador_integral
│   │   ├── interprete
│   │   └── ejecutar_analisis.py
│   │
│   └── modelos/
│       └── entrenados/
│           └── Modelos Isolation Forest
│
├── datos/
│   └── originales/
│       └── Archivos JSON originales de la PDN
│
├── resultados/
│   └── denuncias/
│       └── <id>/
│
├── requirements-produccion.txt
│
└── .venv/
```

### Descripción de los directorios

**`src/analisis/`**

Contiene los componentes encargados de realizar la búsqueda de personas, el análisis patrimonial integral, la interpretación de los resultados y la ejecución del proceso completo.

**`src/modelos/entrenados/`**

Contiene los tres modelos Isolation Forest previamente entrenados y preparados para su utilización durante el análisis.

**`datos/originales/`**

Directorio destinado a almacenar los archivos JSON originales de la PDN, manteniendo su estructura de carpetas.

**`resultados/denuncias/<id>/`**

Contiene los resultados generados para cada denuncia. Cada ejecución mantiene sus archivos separados mediante el identificador correspondiente.

**`.venv/`**

Entorno virtual de Python donde se instalan las dependencias necesarias para ejecutar el motor.

## 3. Requisitos

- Windows 10 o superior.
- Python 3.9.
- Dependencias definidas en `requirements-produccion.txt`.
- Archivos JSON originales de la PDN.
- Modelos Isolation Forest entrenados.
- Espacio suficiente en disco para almacenar los datos y resultados.

Se recomienda utilizar inicialmente la misma versión de Python con la que se desarrolló y entrenó el proyecto.

Si los modelos fueron guardados con versiones específicas de Scikit-learn, instalar esas mismas versiones para evitar incompatibilidades de serialización.

## 4. Instalación en Windows

### Paso 1. Ubicar el proyecto

Copiar o extraer el motor en una carpeta de trabajo.

Ejemplo:

```text
C:\xampp\htdocs\motor_analisis_pdn
```

Para una instalación de producción, se recomienda utilizar una ubicación fuera de `htdocs`.

### Paso 2. Abrir CMD

Abrir una ventana de CMD dentro de la carpeta raíz del proyecto.

Ejemplo:

```bat
cd C:\xampp\htdocs\motor_analisis_pdn
```

### Paso 3. Crear el entorno virtual

Ejecutar:

```bat
py -3.9 -m venv .venv
```

### Paso 4. Activar el entorno virtual

```bat
.venv\Scripts\activate
```

### Paso 5. Actualizar pip

```bat
python -m pip install --upgrade pip
```

### Paso 6. Instalar dependencias

```bat
pip install -r requirements-produccion.txt
```

Una vez finalizada la instalación, el entorno virtual estará preparado para ejecutar el motor.

## 5. Incorporación de los datos originales de la PDN

Copiar los archivos JSON originales dentro del directorio:

```text
datos/originales/
```

Es importante mantener la estructura original de carpetas y archivos.

Ejemplo:

```text
datos/
└── originales/
    ├── s1/
    ├── s2/
    ├── s3/
    └── ...
```

La estructura concreta debe corresponder a los archivos disponibles en el conjunto de datos utilizado por el proyecto.

**Importante:**

- Los archivos originales de la PDN no se incluyen en el paquete debido a su tamaño.
- No modificar los nombres ni la estructura de los archivos sin verificar previamente cómo los consume el motor.
- Confirmar que los datos estén correctamente ubicados antes de ejecutar análisis.
- Mantener los archivos originales protegidos y fuera del acceso público del servidor web.

## 6. Ejecutar una prueba desde consola

Para comprobar el funcionamiento del motor, abrir CMD en la carpeta raíz del proyecto.

Ejecutar el siguiente comando:

```bat
.venv\Scripts\python.exe src\analisis\ejecutar_analisis.py --denuncia-id 125 --nombre "JUAN CARLOS" --primer-apellido "PEREZ" --segundo-apellido "LOPEZ"
```

Los parámetros utilizados son:

| Parámetro | Descripción |
|---|---|
| `--denuncia-id` | Identificador de la denuncia asociada al análisis. |
| `--nombre` | Nombre de la persona denunciada. |
| `--primer-apellido` | Primer apellido de la persona. |
| `--segundo-apellido` | Segundo apellido, opcional. |

El segundo apellido puede omitirse cuando no se dispone de ese dato.

**Importante:** El identificador utilizado en esta prueba es ilustrativo. Para realizar pruebas con datos reales, verificar previamente que los datos de la PDN y las dependencias estén correctamente instalados.

## 7. Resultados por denuncia

Cada ejecución genera una carpeta independiente:

```text
resultados/denuncias/<id>/
```

Por ejemplo:

```text
resultados/
└── denuncias/
    └── 125/
        ├── estado_ejecucion.json
        ├── coincidencias_persona.json
        ├── informe_integral_patrimonial.json
        ├── interpretacion_patrimonial.json
        ├── interpretacion_patrimonial.html
        └── ejecucion.log
```

### Descripción de los archivos

**`estado_ejecucion.json`**

Contiene el estado del proceso de análisis.

Los estados contemplados son:

- `EN_PROCESO`
- `FINALIZADO`
- `SIN_COINCIDENCIAS`
- `ERROR`

**`coincidencias_persona.json`**

Contiene los resultados de la búsqueda nominal realizada sobre los datos disponibles.

**`informe_integral_patrimonial.json`**

Contiene la información generada durante el análisis patrimonial integral.

**`interpretacion_patrimonial.json`**

Contiene la interpretación de los resultados preparada para ser consumida por el dashboard de DenunciaFácil 360.

**`interpretacion_patrimonial.html`**

Contiene una versión HTML del informe, que permite consultar los resultados de manera independiente.

**`ejecucion.log`**

Registra información técnica del proceso, incluyendo mensajes y posibles errores durante la ejecución.

## 8. Integración con DenunciaFácil 360

El motor se comunica con DenunciaFácil 360 mediante la ejecución de un proceso Python desde el backend PHP.

La aplicación web utiliza la ruta absoluta del ejecutable Python:

```text
.venv\Scripts\python.exe
```

Y ejecuta el archivo:

```text
src\analisis\ejecutar_analisis.py
```

La integración debe utilizar `proc_open` o un mecanismo de cola de trabajos para iniciar el proceso y gestionar su ejecución.

Los datos enviados al motor corresponden al identificador de la denuncia y a la información nominal de la persona denunciada.

### Configuración en DenunciaFácil 360

El archivo de configuración se encuentra en:

```text
DENUNCIAFACIL360/config/motor_pdn.php
```

Ejemplo de configuración:

```php
<?php

return [
    'motor_root' => 'C:/xampp/htdocs/motor_analisis_pdn',

    'python_exe' => 'C:/xampp/htdocs/motor_analisis_pdn/.venv/Scripts/python.exe',
];
```

Si el motor se instala en otra ubicación, actualizar los valores de configuración.

### Lectura de resultados

El dashboard de DenunciaFácil 360 debe consultar únicamente el archivo:

```text
resultados/denuncias/<id>/interpretacion_patrimonial.json
```

La aplicación debe verificar que el usuario tenga permisos para consultar la denuncia correspondiente antes de mostrar sus resultados.

No se deben exponer directamente al navegador los archivos originales, los registros técnicos ni las rutas internas del motor.

## 9. Seguridad

- Mantener `datos/originales/` fuera del directorio público de Apache.
- Mantener `resultados/` fuera de `htdocs` o bloquear completamente su acceso HTTP.
- Proteger los modelos entrenados y los archivos de configuración.
- No exponer los archivos JSON originales al navegador.
- No permitir que los usuarios accedan directamente a los registros técnicos.
- Validar los parámetros recibidos desde PHP.
- No concatenar datos proporcionados por el usuario directamente en comandos de shell.
- Utilizar rutas absolutas y argumentos correctamente escapados.
- Limitar el acceso a los resultados según los permisos del sistema.

## 10. Consideraciones metodológicas

Los resultados generados por el motor deben interpretarse con precaución.

**Coincidencias nominales**

Una coincidencia de nombres y apellidos no confirma por sí sola la identidad de una persona. Pueden existir homónimos o coincidencias parciales.

**Clasificación NORMAL**

Un resultado `NORMAL` no demuestra que no existan irregularidades patrimoniales. Únicamente representa la clasificación generada por el modelo según los datos y características analizadas.

**Clasificación ATIPICO**

Un resultado `ATIPICO` no demuestra la existencia de una conducta ilícita. Indica un comportamiento que el modelo identifica como diferente del patrón aprendido.

**Fechas de actualización**

El campo `metadata.actualizacion` no debe interpretarse automáticamente como la fecha confirmada de presentación de una declaración patrimonial.

**Revisión humana**

Los informes requieren revisión por parte de personal autorizado y corroboración mediante fuentes independientes antes de extraer conclusiones.

## 11. Solución de problemas

### No se encuentra Python

Verificar que Python 3.9 esté instalado y que el entorno virtual exista:

```text
.venv\Scripts\python.exe
```

### Error al importar bibliotecas

Activar el entorno virtual e instalar nuevamente las dependencias:

```bat
.venv\Scripts\activate
pip install -r requirements-produccion.txt
```

### No se encuentran coincidencias

Verificar:

- Que los archivos JSON estén ubicados en `datos/originales/`.
- Que se mantenga la estructura original de los datos.
- Que los nombres y apellidos estén correctamente ingresados.
- Que los datos consultados estén disponibles en el conjunto de datos.

### Error durante el análisis

Consultar los archivos:

```text
resultados/denuncias/<id>/ejecucion.log
```

y:

```text
resultados/denuncias/<id>/estado_ejecucion.json
```

Estos archivos permiten identificar el estado de ejecución y los posibles errores técnicos.

### DenunciaFácil 360 no puede iniciar el motor

Verificar:

- La ruta configurada en `config/motor_pdn.php`.
- La existencia del ejecutable Python.
- Los permisos del usuario con el que se ejecuta Apache.
- La ubicación del script `ejecutar_analisis.py`.
- La correcta instalación de las dependencias.

## 12. Recomendaciones para despliegue

Antes de utilizar el motor en un entorno de producción:

1. Instalar el motor fuera del directorio público de Apache.
2. Verificar las versiones de Python y Scikit-learn.
3. Confirmar que los modelos entrenados puedan cargarse correctamente.
4. Comprobar la integridad y disponibilidad de los datos originales.
5. Verificar los permisos de lectura y escritura.
6. Probar la ejecución desde consola.
7. Probar la integración desde DenunciaFácil 360.
8. Configurar respaldos de los datos y resultados.
9. Restringir el acceso a los informes y registros técnicos.

---

**Motor de Análisis PDN — Componente de análisis de datos abiertos integrado con DenunciaFácil 360.**