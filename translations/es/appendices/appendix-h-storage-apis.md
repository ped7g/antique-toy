# Apéndice H: APIs de almacenamiento --- TR-DOS y esxDOS

> *"Una demo técnicamente impresionante que se envíe como .tzx cuando las reglas exigen .trd será descalificada."*
> -- Capítulo 20

Dos APIs de almacenamiento dominan el mundo del ZX Spectrum: **TR-DOS** (el sistema operativo de disco de la interfaz soviética Beta Disk 128, estándar en clones Pentagon y Scorpion) y **esxDOS** (el sistema operativo moderno de tarjeta SD que se ejecuta en hardware DivMMC y DivIDE). La mayoría de los lanzamientos de la demoscene rusa y ucraniana se distribuyen como imágenes de disco `.trd`. La mayoría de los lanzamientos occidentales modernos usan imágenes de cinta `.tap` o distribuciones de archivos compatibles con esxDOS. Si estás lanzando una demo o un juego hoy, la opción práctica es proporcionar una imagen `.trd` para compatibilidad con la enorme base de usuarios rusa/ucraniana, y un archivo `.tap` para todos los demás. Si tu cargador soporta detección de esxDOS (como se describe en el Capítulo 21), los usuarios con hardware DivMMC obtienen carga rápida desde tarjeta SD gratuitamente.

Este apéndice es la referencia de API que mantienes abierta mientras escribes tu cargador. El Capítulo 21 cubre la integración en un proyecto de juego completo. El Capítulo 15 cubre los detalles de hardware de la conmutación de bancos de memoria y el mapeado de puertos que sustentan ambas APIs.

---

## 1. TR-DOS (Beta Disk 128)

### Hardware

La interfaz Beta Disk 128 es el controlador de disquetes estándar para Pentagon, Scorpion y la mayoría de clones soviéticos del ZX Spectrum. Está basada en el chip controlador de disquetes Western Digital WD1793, que se comunica con el Z80 a través de cinco puertos de E/S.

La ROM de TR-DOS (8 KB) ocupa `$0000`--`$3FFF` cuando la interfaz Beta Disk está activa. Se pagina automáticamente cuando el Z80 ejecuta código en la dirección `$3D13` (el punto de entrada mágico), y se despagina cuando la ejecución retorna al área de la ROM principal.

### Disk Format

| Propiedad | Valor |
|-----------|-------|
| Pistas | 80 |
| Caras | 2 |
| Sectores por pista | 16 |
| Bytes por sector | 256 |
| Capacidad total | 640 KB (655.360 bytes) |
| Formato de imagen | `.trd` (imagen de disco sin cabecera, 640 KB) |
| Pista del sistema | Pista 0, cara 0 |

La pista 0 contiene el directorio del disco (sectores 1--8) y el sector de información del disco (sector 9). El directorio admite hasta 128 entradas de archivo. Cada entrada tiene 16 bytes:

```
Bytes 0-7:   Filename (8 characters, space-padded)
Byte  8:     File type: 'C' = code, 'B' = BASIC, 'D' = data, '#' = sequential
Bytes 9-10:  Start address (or BASIC line number)
Bytes 11-12: Length in bytes
Byte  13:    Length in sectors
Byte  14:    Starting sector
Byte  15:    Starting track
```

### WD1793 Port Map

| Puerto | Lectura | Escritura |
|--------|---------|-----------|
| `$1F` | Registro de estado | Registro de comando |
| `$3F` | Registro de pista | Registro de pista |
| `$5F` | Registro de sector | Registro de sector |
| `$7F` | Registro de datos | Registro de datos |
| `$FF` | Registro de sistema TR-DOS | Registro de sistema TR-DOS |

El puerto `$FF` es el puerto de sistema del Beta Disk. Controla la selección de unidad, selección de cara, carga de cabezal y densidad. Los bits superiores también reflejan las señales DRQ (Data Request) e INTRQ (Interrupt Request) del WD1793.

### WD1793 Commands

| Comando | Código | Descripción |
|---------|--------|-------------|
| Restore | `$08` | Mover el cabezal a la pista 0. Verificar pista. |
| Seek | `$18` | Mover el cabezal a la pista del registro de datos. |
| Step In | `$48` | Avanzar el cabezal una pista hacia el centro. |
| Step Out | `$68` | Retroceder el cabezal una pista hacia el borde. |
| Read Sector | `$88` | Leer un sector de 256 bytes. |
| Write Sector | `$A8` | Escribir un sector de 256 bytes. |
| Read Address | `$C0` | Leer el siguiente campo de ID de sector. |
| Force Interrupt | `$D0` | Abortar el comando actual. |

El nibble bajo de cada byte de comando contiene banderas modificadoras (velocidad de paso, verificación, selección de cara, retardo). Los valores anteriores usan valores por defecto comunes. Consulta la hoja de datos del WD1793 para la disposición completa de bits.

### ROM API: Loading a File

El enfoque estándar para E/S de archivos bajo TR-DOS es llamar a las rutinas de la ROM en `$3D13`. La ROM de TR-DOS proporciona operaciones de archivo de alto nivel a través de un sistema de comandos: colocas los parámetros en registros y en el área de sistema en `$5D00`--`$5FFF`, y luego llamas a la ROM.

```z80
; TR-DOS: Load a file by name
; Loads a code file ('C' type) to its stored start address
;
; The filename must be placed at $5D02 (8 bytes, space-padded).
; The file type goes to $5D0A.
;
; Call $3D13 with C = $08 (load file command)

load_trdos_file:
    ; Set up filename at TR-DOS system area
    ld   hl, my_filename
    ld   de, $5D02
    ld   bc, 8
    ldir                    ; copy 8-char filename

    ld   a, 'C'             ; file type: code
    ld   ($5D0A), a

    ld   c, $08             ; TR-DOS command: load file
    call $3D13              ; enter TR-DOS ROM
    ret

my_filename:
    db   "SCREEN  "         ; 8 characters, space-padded
```

Para cargar en una dirección específica (anulando la dirección de inicio almacenada):

```z80
; TR-DOS: Load file to explicit address
; HL = destination address
; DE = length to load
; Filename already at $5D02, type at $5D0A

load_trdos_to_addr:
    ld   hl, $4000          ; load to screen memory
    ld   de, 6912           ; 6912 bytes (one screen)
    ld   ($5D03), hl        ; override start address
    ld   ($5D05), de        ; override length
    ld   c, $08             ; load file
    call $3D13
    ret
```

### Direct Sector Access

Para demos que transmiten datos desde disco --- animaciones a pantalla completa, datos musicales que exceden la RAM disponible, o demos multiparte que cargan efectos al vuelo --- el acceso directo a sectores evita el sistema de archivos por completo. Tú controlas la posición del cabezal, lees sectores uno a la vez y procesas los datos a medida que llegan.

```z80
; Read a single sector directly via WD1793 ports
; B = track number (0-159, with side encoded in bit 0 of $FF)
; C = sector number (1-16)
; HL = destination buffer (256 bytes)

read_sector:
    ld   a, b
    out  ($3F), a           ; set track register
    ld   a, c
    out  ($5F), a           ; set sector register

    ld   a, $88             ; Read Sector command
    out  ($1F), a           ; issue command

    ; Wait for DRQ and read 256 bytes
    ld   b, 0               ; 256 bytes to read
.wait_drq:
    in   a, ($FF)           ; read system register
    bit  6, a               ; test DRQ bit
    jr   z, .wait_drq       ; wait until data ready
    in   a, ($7F)           ; read data byte
    ld   (hl), a
    inc  hl
    djnz .wait_drq

    ; Wait for command completion
.wait_done:
    in   a, ($1F)           ; read status register
    bit  0, a               ; test BUSY bit
    jr   nz, .wait_done
    ret
```

**Advertencia:** El acceso directo a sectores es sensible a la temporización. Las interrupciones deben deshabilitarse durante el bucle de transferencia de datos, o se perderán bytes. El WD1793 activa DRQ durante una ventana de tiempo limitada; si el Z80 no lee el registro de datos antes de que llegue el siguiente byte, los datos se sobrescriben. A 250 kbit/s (doble densidad), dispones de aproximadamente 32 microsegundos por byte --- unos 112 T-states en un Pentagon. El bucle ajustado anterior se ejecuta en aproximadamente 50--60 T-states por byte, dejando un margen adecuado.

### Disk Detection

Para detectar si hay una interfaz Beta Disk presente:

```z80
; Detect Beta Disk 128
; Returns: carry clear if present, carry set if absent
detect_beta_disk:
    ; The TR-DOS ROM signature is at $0069 when paged in.
    ; We can check port $FF for a sane response:
    ; If no Beta Disk is present, port $FF reads as floating bus.
    in   a, ($1F)           ; read WD1793 status
    cp   $FF                ; floating bus returns $FF
    scf
    ret  z                  ; probably no controller
    or   a                  ; clear carry = present
    ret
```

Un método más robusto es intentar llamar a `$3D13` y verificar si los bytes de firma de la ROM de TR-DOS están presentes. El código de producción típicamente comprueba una secuencia de bytes conocida en los puntos de entrada de la ROM de TR-DOS.

---

## 2. esxDOS (DivMMC / DivIDE)

### Hardware

DivMMC (y su hermano mayor DivIDE) es una interfaz de almacenamiento masivo que conecta una tarjeta SD al ZX Spectrum. El firmware esxDOS proporciona una API de archivos tipo POSIX accesible desde código Z80 a través de `RST $08`. esxDOS soporta sistemas de archivos FAT16 y FAT32, nombres de archivo largos, subdirectorios y múltiples handles de archivo abiertos.

DivMMC usa auto-mapeado: cuando el Z80 busca una instrucción en ciertas direcciones "trampa" (notablemente `$0000`, `$0008`, `$0038`, `$0066`, `$04C6`, `$0562`), el hardware DivMMC pagina automáticamente su propia ROM en `$0000`--`$1FFF`. La trampa `RST $08` es el punto de entrada principal de la API.

### API Pattern

Cada llamada a esxDOS sigue el mismo patrón:

```z80
    rst  $08              ; trigger DivMMC auto-map
    db   function_id      ; function number (byte after RST)
    ; Returns:
    ;   Carry clear = success
    ;   Carry set   = error, A = error code
```

El número de función es el byte inmediatamente después de la instrucción `RST $08` en memoria. El Z80 ejecuta `RST $08`, que salta a la dirección `$0008`. DivMMC auto-mapea su ROM en esa dirección, lee el siguiente byte (el número de función), despacha la llamada, luego des-mapea su ROM y retorna a la instrucción después del `DB`.

### Function Reference

| Función | ID | Descripción | Entrada | Salida |
|---------|-----|------------|---------|--------|
| `M_GETSETDRV` | `$89` | Obtener/establecer unidad por defecto | A = `'*'` para la predeterminada | A = letra de unidad |
| `F_OPEN` | `$9A` | Abrir archivo | IX = nombre de archivo (terminado en cero), B = modo, A = unidad | A = handle de archivo |
| `F_CLOSE` | `$9B` | Cerrar archivo | A = handle de archivo | -- |
| `F_READ` | `$9D` | Leer bytes | A = handle, IX = búfer, BC = cantidad | BC = bytes leídos |
| `F_WRITE` | `$9E` | Escribir bytes | A = handle, IX = búfer, BC = cantidad | BC = bytes escritos |
| `F_SEEK` | `$9F` | Posicionar en archivo | A = handle, L = whence, BCDE = desplazamiento | BCDE = nueva posición |
| `F_FSTAT` | `$A1` | Estado del archivo (por handle) | A = handle, IX = búfer | Bloque stat de 11 bytes |
| `F_OPENDIR` | `$A3` | Abrir directorio | IX = ruta (terminada en cero) | A = handle de directorio |
| `F_READDIR` | `$A4` | Leer entrada de directorio | A = handle de directorio, IX = búfer | Entrada en (IX) |
| `F_CLOSEDIR` | `$A5` | Cerrar directorio | A = handle de directorio | -- |
| `F_GETCWD` | `$A8` | Obtener directorio actual | IX = búfer | Ruta en (IX) |
| `F_CHDIR` | `$A9` | Cambiar directorio | IX = ruta | -- |
| `F_STAT` | `$AC` | Estado del archivo (por nombre) | IX = nombre de archivo | Bloque stat de 11 bytes |

### File Open Modes

| Modo | Valor | Descripción |
|------|-------|-------------|
| Solo lectura | `$01` | Abrir archivo existente para lectura |
| Crear/truncar | `$06` | Crear nuevo o truncar existente para escritura |
| Solo crear nuevo | `$04` | Crear archivo nuevo; fallar si existe |
| Añadir | `$0E` | Abrir para escritura al final del archivo |

### Seek Whence Values

| Referencia | Valor | Descripción |
|------------|-------|-------------|
| `SEEK_SET` | `$00` | Desplazamiento desde el inicio del archivo |
| `SEEK_CUR` | `$01` | Desplazamiento desde la posición actual |
| `SEEK_END` | `$02` | Desplazamiento desde el final del archivo |

### Code Example: Load a File

```z80
; esxDOS: Load a binary file into memory
;
; Uses register conventions from esxDOS API documentation.
; Note: F_READ uses IX for the destination buffer, not HL.

    ld   a, '*'             ; use default drive
    ld   ix, filename       ; pointer to zero-terminated filename
    ld   b, $01             ; FA_READ: open for reading
    rst  $08
    db   $9A                ; F_OPEN
    jr   c, .error          ; carry set = error

    ld   (.file_handle), a  ; save file handle

    ld   ix, $4000          ; destination buffer (screen memory)
    ld   bc, 6912           ; bytes to read (one full screen)
    ld   a, (.file_handle)
    rst  $08
    db   $9D                ; F_READ
    jr   c, .error

    ld   a, (.file_handle)
    rst  $08
    db   $9B                ; F_CLOSE
    ret

.error:
    ; A contains the esxDOS error code
    ; Common errors:
    ;   5 = file not found
    ;   7 = file already exists (on create)
    ;   9 = invalid file handle
    ret

filename:
    db   "screen.scr", 0

.file_handle:
    db   0
```

### Code Example: Streaming Data from File

Para demos que cargan datos incrementalmente --- descomprimiendo fragmentos de nivel entre fotogramas, transmitiendo una animación pre-renderizada, o cargando patrones musicales bajo demanda --- el patrón es: abrir el archivo una vez, leer un fragmento por fotograma, cerrar cuando termine.

```z80
; Streaming: read N bytes per frame from an open file
; Call stream_init once, then stream_chunk from your main loop.

CHUNK_SIZE  equ  256        ; bytes per frame (tune to budget)

stream_handle:  db 0
stream_done:    db 0

; Initialise: open the file
stream_init:
    ld   a, '*'
    ld   ix, stream_file
    ld   b, $01             ; FA_READ
    rst  $08
    db   $9A                ; F_OPEN
    ret  c                  ; error
    ld   (stream_handle), a
    xor  a
    ld   (stream_done), a   ; not done yet
    ret

; Per-frame: read one chunk into buffer
; Returns: BC = bytes actually read (may be < CHUNK_SIZE at EOF)
stream_chunk:
    ld   a, (stream_done)
    or   a
    ret  nz                 ; already finished

    ld   a, (stream_handle)
    ld   ix, stream_buffer
    ld   bc, CHUNK_SIZE
    rst  $08
    db   $9D                ; F_READ
    jr   c, .eof

    ; BC = bytes actually read
    ld   a, b
    or   c
    jr   z, .eof            ; zero bytes read = end of file
    ret

.eof:
    ld   a, (stream_handle)
    rst  $08
    db   $9B                ; F_CLOSE
    ld   a, 1
    ld   (stream_done), a
    ret

stream_file:
    db   "anim.bin", 0

stream_buffer:
    ds   CHUNK_SIZE
```

### Detecting esxDOS

```z80
; Detect esxDOS presence
; Returns: carry clear = esxDOS available, carry set = not available
;
; Strategy: attempt M_GETSETDRV. If esxDOS is present, it returns
; the current drive letter. If not present, RST $08 goes to the
; Spectrum ROM's error handler at $0008 (a benign instruction on
; the 128K ROM) and does not crash.

detect_esxdos:
    ld   a, '*'             ; request default drive
    rst  $08
    db   $89                ; M_GETSETDRV
    ret                     ; carry flag set by esxDOS on error
```

Un enfoque más conservador verifica la firma de la trampa de DivMMC antes de llamar a cualquier función de la API. En la práctica, el método anterior funciona en todos los modelos 128K porque el manejador de `$0008` de la ROM 128K no cuelga --- ejecuta una secuencia benigna y retorna. En una máquina 48K sin esxDOS, `RST $08` va al restart de error, que puede necesitar un manejo especial. El Capítulo 21 discute esto en el contexto de un cargador de juego de producción.

---

## 3. +3DOS (Amstrad +3)

El Amstrad Spectrum +3, con su unidad de disquetes de 3 pulgadas incorporada, tiene su propio DOS: +3DOS. La API usa un mecanismo diferente --- llamadas a puntos de entrada en la ROM de +3DOS en la página `$01`, accedida a través de `RST $08` con un conjunto diferente de códigos de función.

+3DOS se usa raramente en la demoscene por dos razones. Primero, el +3 se vendió principalmente en Europa Occidental y nunca fue el modelo de Spectrum dominante en ninguna comunidad de la escena. Segundo, la disposición de memoria no estándar del +3 y su esquema de paginación de ROM lo hacen incompatible con la mayoría del código de demoscene escrito para la arquitectura 128K/Pentagon. Si necesitas compatibilidad con +3, la API de +3DOS está documentada en el manual técnico del Spectrum +3 (Amstrad, 1987). Para la mayoría de proyectos de demos y juegos, proporcionar un archivo `.tap` es suficiente --- el +3 carga archivos `.tap` nativamente a través de su modo de compatibilidad con cinta.

---

## 4. Patrones prácticos

### Loading Screen from Disk (TR-DOS)

La pantalla de carga es la primera impresión del usuario. En TR-DOS, el archivo de pantalla (`SCREEN  C`, 6912 bytes) se carga directamente en `$4000` y aparece inmediatamente:

```z80
; TR-DOS: Load a .scr file directly to screen memory
; The screen appears as it loads, line by line.
load_screen_trdos:
    ld   hl, scr_filename
    ld   de, $5D02
    ld   bc, 8
    ldir
    ld   a, 'C'
    ld   ($5D0A), a
    ld   hl, $4000          ; destination: screen memory
    ld   ($5D03), hl
    ld   de, 6912           ; length: full screen
    ld   ($5D05), de
    ld   c, $08             ; load file
    call $3D13
    ret

scr_filename:
    db   "SCREEN  "         ; 8 chars, padded
```

### Loading Screen from SD (esxDOS)

Mismo resultado visual, diferente API:

```z80
; esxDOS: Load a .scr file to screen memory
load_screen_esxdos:
    ld   a, '*'
    ld   ix, scr_filename_esx
    ld   b, $01             ; FA_READ
    rst  $08
    db   $9A                ; F_OPEN
    ret  c

    push af                 ; save handle
    ld   ix, $4000          ; destination: screen memory
    ld   bc, 6912
    pop  af
    push af
    rst  $08
    db   $9D                ; F_READ
    pop  af
    rst  $08
    db   $9B                ; F_CLOSE
    ret

scr_filename_esx:
    db   "screen.scr", 0
```

### Dual-Mode Loader

Un cargador de producción debería detectar el almacenamiento disponible y usarlo:

```z80
; Unified loader: try esxDOS first, fall back to TR-DOS, then tape
load_data:
    call detect_esxdos
    jr   nc, .use_esxdos    ; carry clear = esxDOS present

    call detect_beta_disk
    jr   nc, .use_trdos     ; carry clear = Beta Disk present

    ; Fall back to tape loading
    jp   load_from_tape

.use_esxdos:
    jp   load_from_esxdos

.use_trdos:
    jp   load_from_trdos
```

### Streaming Compressed Data

El patrón más potente combina la API de almacenamiento con compresión (Apéndice C). Abre un archivo que contenga datos comprimidos, lee fragmentos en un búfer cada fotograma, descomprime en el destino y avanza:

```
Frame 1:  F_READ 256 bytes -> buffer   |  decompress buffer -> screen
Frame 2:  F_READ 256 bytes -> buffer   |  decompress buffer -> screen
Frame 3:  F_READ 256 bytes -> buffer   |  decompress buffer -> screen
...
Frame N:  F_READ < 256 bytes (EOF)     |  decompress, close file
```

A 256 bytes por fotograma y 50 fps, transmites 12,5 KB/seg desde la tarjeta SD --- suficiente para una animación comprimida a pantalla completa. Con TR-DOS, las lecturas directas de sector a un sector por fotograma dan 12,8 KB/seg (256 bytes * 50 fps). El cuello de botella es la velocidad de descompresión, no la E/S.

---

## 5. Referencia de formatos de archivo

| Formato | Extensión | Uso | Notas |
|---------|-----------|-----|-------|
| Imagen de disco TR-DOS | `.trd` | Estándar para lanzamientos en Pentagon/Scorpion | Imagen bruta de 640 KB. Todos los emuladores la soportan. |
| Contenedor de archivos TR-DOS | `.scl` | Más simple que .trd | Contiene archivos sin la estructura completa de disco. Bueno para distribución. |
| Imagen de cinta | `.tap` | Formato de cinta universal | Funciona en todos los modelos de Spectrum y emuladores. Sin sistema de archivos. |
| Imagen de cinta extendida | `.tzx` | Cinta con protección anticopia / cargadores turbo | Preserva la temporización exacta de la cinta. Raramente necesario para lanzamientos nuevos. |
| Snapshot (48K/128K) | `.sna` | Carga rápida, sin sistema de archivos | Captura el estado completo de la máquina. No necesita código de carga. |
| Snapshot (comprimido) | `.z80` | Como .sna pero comprimido | Múltiples versiones; .z80 v3 soporta 128K. |
| Distribución Next | `.nex` | Ejecutable de ZX Spectrum Next | Binario auto-contenido con cabecera que especifica la disposición de bancos. |

**Elegir un formato de lanzamiento:** Para un lanzamiento de demoscene, proporciona al menos dos formatos:

1. **`.trd`** para usuarios de TR-DOS (la comunidad rusa/ucraniana, propietarios de Pentagon/Scorpion, y usuarios de emuladores que prefieren imágenes de disco). Este es el formato por defecto para parties como Chaos Constructions y DiHalt.
2. **`.tap`** para todos los demás (hardware 128K real con entrada de cinta, usuarios de DivMMC vía cargador `.tap`, y todos los emuladores). sjasmplus puede generar salida `.tap` directamente con su directiva `SAVETAP`.

Si tu demo es lo bastante pequeña (menos de 48 KB), un snapshot `.sna` también funciona bien --- se carga instantáneamente sin necesidad de código de carga.

---

## 6. Ver también

- **Capítulo 15** --- Anatomía del hardware: conmutación de bancos de memoria, puerto `$7FFD`, el mapa completo de puertos donde conviven TR-DOS y esxDOS.
- **Capítulo 20** --- Flujo de trabajo de demos: formatos de lanzamiento, reglas de envío a parties, requisitos de `.trd` vs `.tap`.
- **Capítulo 21** --- Juego completo: código de carga de cinta y esxDOS de calidad de producción, detección de modo dual, carga banco por banco.
- **Apéndice C** --- Compresión: qué compresores emparejar con E/S por transmisión.
- **Apéndice E** --- eZ80 / Agon Light 2: la API de archivos MOS en Agon, que proporciona operaciones de archivo similares (`mos_fopen`, `mos_fread`, `mos_fclose`) a través de un mecanismo diferente (RST $08 con códigos de función MOS en modo ADL).

---

> **Fuentes:** Hoja de datos del WD1793 (Western Digital, 1983); desensamblado de TR-DOS v5.03 (varios, dominio público); documentación de la API de esxDOS (Wikipedia, zxe.io); especificación de hardware DivMMC (Mario Prato / ByteDelight); Manual técnico del Spectrum +3 (Amstrad, 1987); Introspec, "Loading and saving on the Spectrum" (Hype, 2016)
