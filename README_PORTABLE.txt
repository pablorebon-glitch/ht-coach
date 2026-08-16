HT Coach Alpha 0.6.9 Portable

Como iniciar
------------

Abri la carpeta "HT Coach Portable" y hace doble click en:

HT Coach.exe

No hace falta instalar Python, crear un entorno virtual ni abrir PowerShell.

Mantene la carpeta completa
---------------------------

No muevas solamente el .exe. La carpeta completa debe viajar junta porque incluye:

- recursos de idioma;
- datos;
- logs;
- backups;
- archivos de soporte.

Donde se guardan tus datos
--------------------------

En modo portable, HT Coach guarda todo junto a la aplicacion:

HT Coach Portable\data

Los logs se guardan en:

HT Coach Portable\logs

Los backups se guardan en:

HT Coach Portable\backups

Copiar a otra PC o pendrive
---------------------------

1. Cierra HT Coach.
2. Copia la carpeta completa "HT Coach Portable".
3. Pegala en otra PC, carpeta local o pendrive.
4. Abri "HT Coach.exe" desde la nueva ubicacion.

Antes de quitar un pendrive
---------------------------

1. Cierra HT Coach.
2. Espera unos segundos si acabas de guardar datos.
3. Usa "Quitar hardware de forma segura" en Windows.

Backups
-------

HT Coach crea backups antes de operaciones de alto impacto, como importar datos.
Tambien podes copiar manualmente la carpeta "data" como respaldo.

Importar datos de otra instalacion
----------------------------------

En Configuracion usa:

Importar datos de otra instalacion

Selecciona una carpeta de datos de HT Coach. La app mostrara que archivos se van a
copiar y creara un backup antes de reemplazar datos portables.

Diagnostico
-----------

Si la app no abre o necesitas ver mensajes tecnicos, usa:

HT Coach Debug.cmd

Este lanzador muestra una consola para diagnostico.

Windows SmartScreen y seguridad
-------------------------------

Windows SmartScreen puede advertir que el ejecutable no esta firmado.
Algunos antivirus o politicas corporativas pueden bloquear ejecutables portables.

No intentes evitar politicas de seguridad de una empresa. Si una PC corporativa no
permite ejecutar la app, usa una PC personal aprobada como alternativa.
