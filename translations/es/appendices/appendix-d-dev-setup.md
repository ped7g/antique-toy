# Apéndice D: Configuración del entorno de desarrollo

> *"Necesitas cinco cosas: un editor, un ensamblador, un emulador, un depurador y un Makefile. Todo lo demás es opcional."*
> -- Capítulo 1

Este apéndice te guía paso a paso para configurar un entorno completo de desarrollo Z80 desde cero. Al terminar, podrás compilar todos los ejemplos en ensamblador de este libro, ejecutarlos en un emulador y depurarlos con puntos de interrupción e inspección de registros. Las instrucciones cubren macOS, Linux y Windows.

Si ya seguiste la configuración del Capítulo 1, ya tienes la mayor parte lista. Este apéndice añade más detalle, cubre configuraciones alternativas y sirve como referencia única a la que puedes volver cuando configures una máquina nueva.

---

## 1. El ensamblador: sjasmplus

Todos los ejemplos de código en este libro están escritos para **sjasmplus**, un ensamblador de macros Z80/Z80N de código abierto creado por z00m128. Soporta el juego completo de instrucciones Z80 incluyendo todos los modos indexados IX/IY, macros, scripting en Lua, múltiples formatos de salida y expresiones que hacen práctico escribir código de demoscene.

### Installing from Source

La forma más fiable de obtener sjasmplus es compilarlo desde el código fuente. Esto garantiza que tengas una versión conocida y evita problemas de empaquetado específicos de cada plataforma.

```bash
git clone https://github.com/z00m128/sjasmplus.git
cd sjasmplus
make
```

En macOS, necesitas las herramientas de línea de comandos de Xcode (`xcode-select --install`). En Linux, necesitas `g++` y `make` (instálalos con tu gestor de paquetes). En Windows, usa MinGW o WSL.

Después de compilar, copia el binario `sjasmplus` a algún lugar en tu PATH:

```bash
# macOS / Linux
sudo cp sjasmplus /usr/local/bin/

# Verify
sjasmplus --version
```

Deberías ver la versión 1.20.x o posterior. Este libro fue desarrollado y probado con la v1.21.1.

### Version Pinning

El repositorio del libro fija sjasmplus como un submódulo de git en `tools/sjasmplus/`. Si clonas el repositorio con `--recursive`, obtienes la versión exacta usada para compilar cada ejemplo:

```bash
git clone --recursive https://github.com/[repo]/antique-toy.git
cd antique-toy/tools/sjasmplus
make
```

Este es el enfoque más seguro. El comportamiento del ensamblador puede cambiar entre versiones -- una expresión que funciona en 1.21 podría interpretarse de forma diferente en 1.22.

### Key Flags

| Opción | Propósito | Ejemplo |
|--------|-----------|---------|
| `--nologo` | Suprime el banner de inicio | `sjasmplus --nologo main.a80` |
| `--raw=FILE` | Genera un binario sin cabecera | `sjasmplus --raw=output.bin main.a80` |
| `--sym=FILE` | Escribe un archivo de símbolos (para depuradores) | `sjasmplus --sym=output.sym main.a80` |
| `--fullpath` | Muestra rutas completas de archivos en los mensajes de error | Útil con el matcher de problemas de VS Code |
| `--msg=war` | Suprime mensajes informativos, muestra solo advertencias y errores | Salida de compilación más limpia |
| `--syntax=abf` | Habilita todas las características de sintaxis (A como alias del acumulador, corchetes para indirección, instrucciones falsas completas) | Recomendado para principiantes; permite `add a, b` junto a `add b` |

Un comando de compilación típico para un ejemplo de capítulo:

```bash
sjasmplus --nologo --raw=build/example.bin chapters/ch01-thinking-in-cycles/examples/timing.a80
```

### File Extension

Todos los archivos fuente de ensamblador Z80 en este libro usan la extensión `.a80`. Es una convención, no un requisito -- a sjasmplus no le importa la extensión. Usamos `.a80` porque es reconocida por la extensión Z80 Macro Assembler de VS Code y distingue nuestro código fuente de otros dialectos de ensamblador.

### Hex Notation

El libro usa `$FF` para valores hexadecimales. sjasmplus también acepta `#FF` y `0FFh`, pero `$FF` es la convención a lo largo de todo el libro. El símbolo `$` por sí solo representa la dirección actual del contador de programa, usado en construcciones como `jr $` (bucle infinito) o `dw $ + 4`.

---

## 2. El editor: VS Code

Cualquier editor de texto sirve. Recomendamos **Visual Studio Code** por sus extensiones específicas para Z80 y su terminal integrado. Todo el flujo de trabajo -- editar, compilar, depurar -- ocurre en una sola ventana.

### Essential Extensions

Instálalas desde el marketplace de extensiones de VS Code (Ctrl+Shift+X):

| Extensión | Autor | Qué hace |
|-----------|-------|----------|
| **Z80 Macro Assembler** | mborik (`mborik.z80-macroasm`) | Resaltado de sintaxis, completado de código, resolución de símbolos para ensamblador Z80. Entiende la sintaxis de sjasmplus incluyendo macros y etiquetas locales. |
| **Z80 Assembly Meter** | Nestor Sancho | Muestra el conteo de bytes y el coste en T-states de las instrucciones seleccionadas en la barra de estado. Selecciona un bloque y ve su coste total al instante. Indispensable para contar ciclos. |
| **DeZog** | Maziac | Depurador Z80. Se conecta a emuladores o a su simulador interno. Puntos de interrupción, inspección de registros, inspección de memoria. Ver Sección 4. |

### Build Task

Configura una tarea de compilación para que Ctrl+Shift+B compile tu archivo actual. Crea `.vscode/tasks.json` en la raíz de tu proyecto:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Assemble Z80",
      "type": "shell",
      "command": "sjasmplus",
      "args": [
        "--fullpath",
        "--nologo",
        "--msg=war",
        "${file}"
      ],
      "group": {
        "kind": "build",
        "isDefault": true
      },
      "problemMatcher": {
        "owner": "z80",
        "fileLocation": "absolute",
        "pattern": {
          "regexp": "^(.*)\\((\\d+)\\):\\s+(error|warning)[^:]*:\\s+(.*)$",
          "file": 1,
          "line": 2,
          "severity": 3,
          "message": 4
        }
      }
    }
  ]
}
```

El `problemMatcher` analiza la salida de errores de sjasmplus para que al hacer clic en un error en el terminal se salte a la línea infractora. La opción `--fullpath` asegura que las rutas de archivos sean absolutas, lo que VS Code necesita para resolverlas correctamente.

### Recommended Settings

Añade esto a tu `.vscode/settings.json` del espacio de trabajo para una experiencia limpia de edición Z80:

```json
{
  "editor.tabSize": 8,
  "editor.insertSpaces": false,
  "editor.rulers": [80],
  "files.associations": {
    "*.a80": "z80-macroasm"
  }
}
```

Un tamaño de tabulación de 8 con tabulaciones reales coincide con la convención tradicional del ensamblador donde los mnemónicos y operandos se alinean en columnas fijas.

---

## 3. Emuladores

Necesitas un emulador para ejecutar tu código ensamblado. Diferentes emuladores sirven para diferentes propósitos.

### ZEsarUX -- Feature-Rich Debugging

**ZEsarUX** de cerebellio es el emulador de ZX Spectrum de código abierto con más funciones. Soporta toda la gama de modelos Spectrum (48K, 128K, +2, +3, Pentagon, Scorpion, ZX-Uno, ZX Spectrum Next), tiene un depurador incorporado y se integra con DeZog para depuración desde VS Code.

**Instalar:**

- macOS: `brew install zesarux`
- Linux: Compilar desde código fuente o usar el AppImage de https://github.com/chernandezba/zesarux
- Windows: Descargar el instalador desde el sitio web de ZEsarUX

**Por qué ZEsarUX para este libro:** La mayoría de los ejemplos de los capítulos tienen como objetivo el ZX Spectrum 128K. ZEsarUX emula la paginación de memoria 128K, sonido AY, TurboSound (dos chips AY) y los patrones de contención de los diferentes modelos. Su depurador incorporado muestra registros, memoria y desensamblado sin necesidad de VS Code. Y su integración con DeZog proporciona la experiencia completa de depuración en VS Code cuando la necesitas.

**Inicio rápido:**

```bash
# Run a .sna snapshot
zesarux --machine 128k --nosplash output.sna

# Run a .tap file
zesarux --machine 128k --nosplash output.tap
```

### Fuse -- Lightweight and Accurate

**Fuse** (the Free Unix Spectrum Emulator) de Philip Kendall es ligero, con precisión de ciclo, y está disponible en todas las plataformas. Es la mejor opción para pruebas rápidas cuando no necesitas el depurador completo.

**Instalar:**

- macOS: `brew install fuse-emulator`
- Linux: `apt install fuse-emulator-sdl` (Debian/Ubuntu) o `dnf install fuse-emulator` (Fedora)
- Windows: Descargar desde el sitio web de Fuse

**Inicio rápido:**

```bash
# Run with Pentagon timing (matches the book's T-state counts)
fuse --machine pentagon output.sna

# Run as 128K Spectrum
fuse --machine 128 output.tap
```

Fuse es particularmente bueno para probar código sensible a la temporización porque su precisión de ciclo está bien verificada. Si tu arnés de temporización de franjas de borde (Capítulo 1) muestra resultados diferentes en Fuse frente a otro emulador, confía en Fuse.

### Unreal Speccy -- Windows, Pentagon-Focused

Si desarrollas principalmente en Windows y apuntas a la temporización Pentagon, **Unreal Speccy** es una opción sólida. Tiene un depurador incorporado con mapa de memoria, puntos de interrupción y monitorización de registros AY. Emula el hardware Pentagon y Scorpion con precisión.

Descárgalo de http://dlcorp.nedopc.com/viewforum.php?f=27 o busca "Unreal Speccy Portable."

### For Agon Light 2

El Agon Light 2 usa un CPU eZ80 y una arquitectura de hardware diferente. El Capítulo 22 cubre el desarrollo en Agon en detalle. Para emulación, **Fab Agon Emulator** proporciona una simulación por software del hardware Agon (eZ80 + ESP32 VDP). Está disponible en https://github.com/tomm/fab-agon-emulator y funciona en macOS, Linux y Windows.

### Which Emulator Should I Use?

| Situación | Emulador recomendado |
|-----------|---------------------|
| Desarrollo diario, ejecución de ejemplos | Fuse (inicio rápido, preciso) |
| Depuración con puntos de interrupción e inspección de registros | ZEsarUX + DeZog |
| Desarrollo de música AY/TurboSound | ZEsarUX (mejor emulación AY) |
| Verificación de temporización Pentagon | Fuse o Unreal Speccy |
| Desarrollo para Agon Light 2 | Fab Agon Emulator |
| Comprobación rápida en Windows | Unreal Speccy |

---

## 4. El depurador: DeZog

**DeZog** de Maziac es una extensión de VS Code que convierte tu editor en un depurador Z80. Se conecta a ZEsarUX, CSpect o a su propio simulador Z80 interno y proporciona la experiencia de depuración que los desarrolladores modernos esperan: puntos de interrupción, ejecución paso a paso, inspección de registros, inspección de memoria, vista de desensamblado y pila de llamadas.

El Capítulo 23 discute DeZog en el contexto del desarrollo asistido por IA. Esta sección cubre la configuración práctica.

### Installation

1. Abre VS Code.
2. Ve a Extensiones (Ctrl+Shift+X).
3. Busca "DeZog" de Maziac.
4. Haz clic en Instalar.

### Connecting to ZEsarUX

DeZog se comunica con ZEsarUX a través de una conexión de socket. Primero, lanza ZEsarUX con su servidor ZRCP (ZEsarUX Remote Control Protocol) habilitado:

```bash
zesarux --machine 128k --enable-remoteprotocol --remoteprotocol-port 10000
```

Luego crea un `.vscode/launch.json` en tu proyecto:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "type": "dezog",
      "request": "launch",
      "name": "DeZog + ZEsarUX",
      "remoteType": "zesarux",
      "zesarux": {
        "port": 10000
      },
      "sjasmplus": [
        {
          "path": "build/output.sld"
        }
      ],
      "topOfStack": "$FF00",
      "commandsAfterLaunch": [
        "-sprites disable",
        "-patterns disable"
      ]
    }
  ]
}
```

La sección `sjasmplus` apunta al archivo `.sld` (Source Level Debug) que sjasmplus genera con la opción `--sld=FILE`. Esto le da a DeZog depuración a nivel de código fuente -- puntos de interrupción en líneas de código, no solo en direcciones.

Para generar el archivo `.sld`, añade la opción a tu comando de compilación:

```bash
sjasmplus --nologo --raw=build/output.bin --sld=build/output.sld --sym=build/output.sym main.a80
```

### Using the Internal Simulator

Para una depuración rápida sin lanzar un emulador externo, DeZog incluye un simulador Z80 incorporado. Cambia tu `launch.json` a:

```json
{
  "type": "dezog",
  "request": "launch",
  "name": "DeZog Internal Simulator",
  "remoteType": "zsim",
  "zsim": {
    "machine": "spectrum",
    "memoryModel": "ZX128K"
  },
  "sjasmplus": [
    {
      "path": "build/output.sld"
    }
  ],
  "topOfStack": "$FF00"
}
```

El simulador interno es más rápido de iniciar y no requiere que ZEsarUX esté instalado. Carece de emulación precisa de contención, así que no lo uses para depuración crítica de temporización -- pero para depuración lógica (¿mi rutina de multiplicación produce el resultado correcto?), es perfecto.

### Key DeZog Features

**Puntos de interrupción.** Haz clic en el margen junto a una línea de código para establecer un punto de interrupción. La ejecución se detiene cuando el contador de programa del Z80 alcanza esa dirección. También puedes establecer puntos de interrupción condicionales (p. ej., detener cuando `A == $FF`).

**Inspección de registros.** El panel de Variables muestra todos los registros Z80: AF, BC, DE, HL, IX, IY, SP, PC y el conjunto alternativo (AF', BC', DE', HL'). Las banderas individuales (C, Z, S, P/V, H, N) se muestran por separado para facilitar la lectura.

**Inspección de memoria.** El panel de Memoria muestra un volcado hexadecimal de cualquier rango de direcciones. Puedes escribir una dirección y ver qué hay allí. Esencial para verificar tablas de consulta, contenido de la memoria de pantalla y estado de la pila.

**Vista de desensamblado.** Incluso sin depuración a nivel de código fuente, DeZog desensambla el código alrededor del PC actual. Útil para entender cómo se ve realmente el código auto-modificable en tiempo de ejecución.

**Pila de llamadas.** DeZog rastrea los pares CALL/RET y muestra una pila de llamadas. Esto funciona para código convencional. El código auto-modificable y el encadenamiento RET (Capítulo 3) confundirán al rastreador de pila -- esto es esperable.

---

## 5. Compilar los ejemplos del libro

### Clone the Repository

```bash
git clone --recursive https://github.com/[repo]/antique-toy.git
cd antique-toy
```

La opción `--recursive` descarga el submódulo sjasmplus en `tools/sjasmplus/`. Si ya clonaste sin ella:

```bash
git submodule update --init --recursive
```

### Prerequisites

Necesitas `make` y un compilador de C++ (para compilar sjasmplus desde el submódulo). En la mayoría de los sistemas ya están presentes:

- macOS: `xcode-select --install`
- Debian/Ubuntu: `sudo apt install build-essential`
- Fedora: `sudo dnf install make gcc-c++`
- Windows: Usa WSL, o instala MinGW y GNU Make

### Build Commands

El Makefile del proyecto se encarga de todo. Toda la salida compilada va a `build/`, que está en el gitignore.

| Comando | Qué hace |
|---------|----------|
| `make` | Compilar todos los ejemplos de capítulos con sjasmplus |
| `make test` | Ensamblar todos los ejemplos, informar aprobado/fallido para cada uno |
| `make ch01` | Compilar solo los ejemplos del Capítulo 1 |
| `make ch04` | Compilar solo los ejemplos del Capítulo 4 |
| `make demo` | Compilar la demo complementaria "Antique Toy" |
| `make clean` | Eliminar todos los artefactos de compilación |

Una ejecución exitosa de `make test` se ve así:

```
  OK  chapters/ch01-thinking-in-cycles/examples/timing.a80
  OK  chapters/ch04-maths/examples/multiply.a80
  OK  chapters/ch05-wireframe-3d/examples/cube.a80
  ...
---
12 passed, 0 failed
```

Si algún ejemplo falla, la salida muestra `FAIL` con el nombre del archivo. Ejecuta el archivo que falla manualmente con sjasmplus para ver el error detallado:

```bash
sjasmplus --nologo chapters/ch04-maths/examples/multiply.a80
```

### Running an Example

Después de compilar, carga el binario de salida en tu emulador. El método exacto depende del formato de salida:

```bash
# If the example produces a .sna snapshot
fuse --machine pentagon build/ch01-thinking-in-cycles/examples/timing.sna

# If you built a raw binary, you need to create a .tap or .sna first,
# or load it at the correct address in the emulator's debugger
```

La mayoría de los ejemplos de capítulos usan ORG `$8000` y producen binarios sin cabecera. Para ejecutarlos, puedes:

1. Usar un envoltorio `.tap` (el Makefile los genera cuando el código fuente incluye las directivas apropiadas), o
2. Cargar el binario en la dirección `$8000` en el depurador de tu emulador y establecer PC a `$8000`.

---

## 6. Estructura de proyecto para tu propio código

Cuando empieces a escribir tu propio código Z80 más allá de los ejemplos del libro, aquí tienes una estructura de directorios recomendada:

```
my-demo/
  src/
    main.a80          -- entry point, includes other files
    effects/
      plasma.a80      -- individual effect routines
      scroller.a80
    data/
      font.a80        -- DB/DW data tables
      sintable.a80
    lib/
      multiply.a80    -- reusable utility routines
      draw_line.a80
  assets/
    title.scr         -- raw screen files
    music.pt3         -- tracker music
  build/              -- compiled output (gitignored)
  Makefile
  .vscode/
    tasks.json        -- build task
    launch.json       -- DeZog configuration
```

### Minimal Makefile

```makefile
SJASMPLUS ?= sjasmplus
BUILD_DIR := build
SJASM_FLAGS := --nologo

.PHONY: all clean run

all: $(BUILD_DIR)/demo.bin

$(BUILD_DIR)/demo.bin: src/main.a80 src/effects/*.a80 src/data/*.a80 src/lib/*.a80
	@mkdir -p $(BUILD_DIR)
	$(SJASMPLUS) $(SJASM_FLAGS) --raw=$@ --sym=$(BUILD_DIR)/demo.sym --sld=$(BUILD_DIR)/demo.sld $<

run: $(BUILD_DIR)/demo.bin
	fuse --machine 128 $(BUILD_DIR)/demo.sna

clean:
	rm -rf $(BUILD_DIR)
```

Puntos clave:

- El archivo fuente principal usa directivas `INCLUDE` para incorporar otros archivos. sjasmplus resuelve las inclusiones relativas al directorio del archivo fuente.
- La opción `--sym` genera un archivo de símbolos como referencia. La opción `--sld` genera datos de depuración a nivel de código fuente para DeZog.
- Lista todos los archivos fuente incluidos como dependencias para que `make` recompile cuando cualquier archivo cambie.

### Include Convention

En tu `main.a80`:

```z80
    ORG $8000

    ; --- Entry point ---
start:
    di
    ; set up stack, interrupts, etc.
    ld   sp, $FF00
    ; ...

    include "lib/multiply.a80"
    include "effects/plasma.a80"
    include "data/sintable.a80"
```

sjasmplus procesa los archivos `INCLUDE` en línea, como si el texto se pegara en ese punto. Mantén tus inclusiones organizadas: rutinas de biblioteca primero, luego efectos, luego datos (ya que los datos típicamente se colocan al final del binario).

---

## 7. Herramientas alternativas

Este libro usa sjasmplus porque es el ensamblador Z80 más capaz para trabajo de demoscene y desarrollo de juegos. Pero puedes encontrar otras herramientas en la comunidad.

### Other Assemblers

| Ensamblador | Notas |
|-------------|-------|
| **z80asm** | Parte de la suite de compilador cruzado C z88dk. Bueno si mezclas C y ensamblador. Convenciones de sintaxis diferentes. |
| **RASM** | Por Roudoudou. Rápido, soporta CPC y Spectrum. Popular en la escena del Amstrad CPC. |
| **pasmo** | Simple, portable, funciones limitadas. Adecuado para programas pequeños independientes pero carece de macros y funciones avanzadas necesarias para proyectos más grandes. |

Los ejemplos del libro usan características específicas de sjasmplus (etiquetas locales con `.`, valores negativos en DB, prefijo hexadecimal `$`) que pueden no funcionar sin modificaciones en otros ensambladores. Si quieres portar un ejemplo a un ensamblador diferente, los cambios suelen ser menores: sintaxis de etiquetas, notación hexadecimal y nombres de directivas.

### Other VS Code Extensions

| Extensión | Notas |
|-----------|-------|
| **SjASMPlus Syntax** | Resaltado de sintaxis alternativo ajustado específicamente para sjasmplus. Pruébalo si `z80-macroasm` no resalta correctamente alguna característica específica de sjasmplus. |
| **Z80 Debugger** (Spectron) | Un depurador Z80 más antiguo para VS Code. DeZog lo ha superado en gran medida. |

### CSpect -- Next-Focused Emulator

Si tienes un ZX Spectrum Next o estás apuntando a características específicas de Next (copper, layer 2, DMA, modo turbo 28MHz), **CSpect** de Mike Dailly es el emulador de referencia. DeZog se conecta a CSpect de la misma forma que se conecta a ZEsarUX. CSpect es solo para Windows pero funciona bajo Wine en macOS y Linux.

### SpectrumAnalyzer

Una herramienta basada en navegador que visualiza el diseño de la memoria de pantalla del ZX Spectrum, los conflictos de atributos y la temporización. Útil para entender la discusión del Capítulo 2 sobre el entrelazado de pantalla. Disponible en https://shiru.untergrund.net/spectrumanalyzer.html (o busca "ZX Spectrum screen analyzer").

---

## 8. Resolución de problemas

### "sjasmplus: command not found"

El binario no está en tu PATH. Cópialo a `/usr/local/bin/` (macOS/Linux), añade su directorio a tu PATH, o establece la variable `SJASMPLUS` al ejecutar make:

```bash
make SJASMPLUS=/path/to/sjasmplus
```

### Compilation errors in the book's examples

Primero, asegúrate de que estás usando la versión de sjasmplus del submódulo (`tools/sjasmplus/`). Versiones más nuevas o más antiguas pueden tener comportamiento diferente. Segundo, verifica que estás ensamblando el archivo desde el directorio correcto -- sjasmplus resuelve las rutas de `INCLUDE` relativas al archivo fuente, no al directorio de trabajo.

### DeZog cannot connect to ZEsarUX

1. Asegúrate de que ZEsarUX está ejecutándose con `--enable-remoteprotocol`.
2. Verifica que el número de puerto en `launch.json` coincida con el argumento `--remoteprotocol-port`.
3. En macOS, puede que necesites permitir ZEsarUX a través del firewall (Ajustes del Sistema > Privacidad y Seguridad).
4. Intenta reiniciar ZEsarUX antes de lanzar la sesión de DeZog.

### Emulator shows garbled screen

Si cargas un binario sin cabecera y ves basura, la causa más probable es una dirección de carga incorrecta. Los ejemplos del libro usan ORG `$8000`. Asegúrate de que tu emulador carga el binario en esa dirección, no en `$0000` ni en algún otro valor por defecto. Usar salida `.sna` o `.tap` (que incluye información de dirección) evita este problema.

### Build output is empty or zero bytes

Verifica que tu archivo fuente tiene una directiva `ORG` y al menos una instrucción. sjasmplus con `--raw=` produce un binario desde el primer byte emitido hasta el último. Si nada se emite (p. ej., el archivo contiene solo `ORG $8000` sin código), la salida está vacía.

---

## Referencia de herramientas

| Herramienta | Propósito | URL oficial | Referencia en el libro |
|-------------|-----------|-------------|------------------------|
| **sjasmplus** | Ensamblador de macros Z80/Z80N | https://github.com/z00m128/sjasmplus | Capítulo 1, todos los ejemplos |
| **VS Code** | Editor e IDE | https://code.visualstudio.com | Capítulo 1 |
| **Z80 Macro Assembler** | Extensión de sintaxis para VS Code | Marketplace: `mborik.z80-macroasm` | Capítulo 1 |
| **Z80 Assembly Meter** | Visualización de conteo de ciclos | Marketplace: Nestor Sancho | Capítulo 1 |
| **DeZog** | Depurador Z80 para VS Code | Marketplace: Maziac / https://github.com/maziac/DeZog | Capítulo 23 |
| **ZEsarUX** | Emulador Spectrum rico en funciones | https://github.com/chernandezba/zesarux | Capítulo 1, Capítulo 23 |
| **Fuse** | Emulador Spectrum ligero | https://fuse-emulator.sourceforge.net | Capítulo 1 |
| **Unreal Speccy** | Emulador enfocado en Pentagon | http://dlcorp.nedopc.com | Capítulo 1 |
| **CSpect** | Emulador ZX Spectrum Next | https://dailly.blogspot.com | Capítulo 22 (funciones Next) |
| **Fab Agon Emulator** | Emulador Agon Light 2 | https://github.com/tomm/fab-agon-emulator | Capítulo 22 |
| **ZX0** | Compresor LZ óptimo | https://github.com/einar-saukas/ZX0 | Capítulo 14, Apéndice C |
| **Exomizer** | Compresor con mejor ratio | https://github.com/bitmanipulators/exomizer | Capítulo 14, Apéndice C |
| **Vortex Tracker II** | Tracker de música AY | https://github.com/ivanpirog/vortextracker | Capítulo 11 |

---

## Ver también

- **Capítulo 1:** Primera práctica -- configuración de VS Code, sjasmplus y el arnés de temporización.
- **Capítulo 22:** Configuración de la plataforma Agon Light 2, cadena de herramientas eZ80, Fab Agon Emulator.
- **Capítulo 23:** Integración de DeZog con flujos de trabajo asistidos por IA.
- **Apéndice A:** Referencia de instrucciones Z80 -- las instrucciones que estarás depurando.
- **Apéndice G:** Referencia de registros AY -- útil al depurar código de sonido en ZEsarUX.
