# Apéndice E: Referencia rápida del eZ80

> *"El mismo juego de instrucciones, una máquina completamente diferente."*
> -- Capítulo 22

Este apéndice es una tarjeta de referencia para programadores de Z80 que se acercan al eZ80 por primera vez. Cubre las diferencias arquitectónicas, el sistema de modos, las instrucciones nuevas y los detalles específicos del Agon Light 2 que necesitas para portar código. No es un manual exhaustivo del eZ80 --- es el subconjunto que importa para el trabajo del Capítulo 22.

Si ya conoces el Z80 (y si has llegado hasta aquí, lo conoces), el eZ80 te resultará familiar. Los registros tienen los mismos nombres, las instrucciones tienen los mismos mnemónicos, las banderas funcionan de la misma manera. Pero tres cosas son diferentes: las direcciones tienen 24 bits de ancho, los registros pueden tener 24 bits de ancho, y hay un sistema de modos que controla qué ancho está activo. Todo lo demás se deriva de eso.

---

## 1. Visión general de la arquitectura

El eZ80 es el Z80 extendido de Zilog, diseñado para sistemas embebidos que necesitan más de 64 KB de espacio de direcciones. Es un superconjunto estricto del Z80 --- cada código de operación del Z80 es válido en el eZ80, con comportamiento idéntico. Las extensiones añaden direccionamiento de 24 bits, ancho de registro de 24 bits y un puñado de instrucciones nuevas.

| Característica | Z80 | eZ80 |
|----------------|-----|------|
| Ancho de dirección | 16 bits (64 KB) | 24 bits (16 MB) |
| Ancho de registro | 16 bits (HL, BC, DE, SP, IX, IY) | 16 bits o 24 bits (dependiente del modo) |
| Marco de pila por PUSH/CALL | 2 bytes | 2 bytes (modo Z80) o 3 bytes (modo ADL) |
| Multiplicación por hardware | Ninguna | MLT rr (8x8 sin signo) |
| Prefijos de instrucción | CB, DD, ED, FD | Los mismos, más prefijos de sufijo de modo |
| Registro MBASE | N/A | Proporciona los 8 bits superiores de las direcciones en modo Z80 |
| Instrucciones nuevas | N/A | LEA, PEA, MLT, TST, TSTIO, SLP, IN0/OUT0, STMIX/RSMIX |

El modelo mental clave: en **modo ADL** (Address Data Long), el eZ80 se comporta como un Z80 con registros de 24 bits y direcciones de 24 bits. En **modo compatible Z80**, se comporta como un Z80 estándar, con registros de 16 bits y el registro MBASE proporcionando los 8 bits superiores de dirección que faltan.

---

## 2. Sistema de modos

El eZ80 tiene dos modos de operación que controlan el ancho de los registros y la generación de direcciones. Entender estos modos es el concepto más importante para cualquier programador de Z80 que se acerque al eZ80.

### The Two Modes

**Modo compatible Z80.** Los registros tienen 16 bits de ancho. Las direcciones son de 16 bits, con MBASE proporcionando los 8 bits superiores. `LD HL,$4000` carga un valor de 16 bits. `PUSH HL` empuja 2 bytes. El código se comporta exactamente como un Z80 estándar.

**Modo ADL (Address Data Long).** Los registros tienen 24 bits de ancho. Las direcciones son de 24 bits. `LD HL,$040000` carga un valor de 24 bits. `PUSH HL` empuja 3 bytes. Este es el modo nativo del eZ80 y el predeterminado en el Agon Light 2.

### Mode Suffixes

Las instrucciones individuales pueden anular el modo actual usando prefijos de sufijo:

| Sufijo | Significado | Ancho de registro | Ancho de dirección |
|--------|-------------|-------------------|-------------------|
| `.SIS` | Short Immediate, Short | 16 bits | 16 bits |
| `.LIS` | Long Immediate, Short | 24 bits | 16 bits |
| `.SIL` | Short Immediate, Long | 16 bits | 24 bits |
| `.LIL` | Long Immediate, Long | 24 bits | 24 bits |

La primera letra (S/L) controla el ancho de registro para esa instrucción. La tercera letra (S/L) controla el ancho de dirección. En modo ADL, `.SIS` fuerza a una instrucción a comportarse como Z80 estándar. En modo Z80, `.LIL` fuerza a una instrucción a comportarse como 24 bits completo.

### Mode-Switching Calls and Jumps

Las llamadas y saltos pueden cambiar el modo del procesador en el destino:

| Instrucción | Modo actual | Modo destino | Tamaño de dirección de retorno |
|-------------|------------|-------------|-------------------------------|
| `CALL.IS nn` | ADL | Z80 | 3 bytes (convención ADL) |
| `CALL.IL nn` | Z80 | ADL | 3 bytes (largo) |
| `JP.SIS nn` | cualquiera | Z80 | N/A (sin dirección de retorno) |
| `JP.LIL nn` | cualquiera | ADL | N/A (sin dirección de retorno) |
| `RST.LIL $08` | Z80 | ADL | 3 bytes (largo) |

El sufijo `.IS` significa "Instruction Short" --- el destino se ejecuta en modo Z80. `.IL` significa "Instruction Long" --- el destino se ejecuta en modo ADL.

### The Practical Rule

**Quédate en modo ADL.** MOS arranca el Agon en modo ADL. Las llamadas a la API de MOS esperan modo ADL. Los comandos VDP se envían a través de rutinas de MOS que asumen marcos de pila de 24 bits. Si cambias a modo Z80 y llamas a MOS, la discrepancia en el ancho del marco de pila corromperá la pila y se producirá un cuelgue.

Si necesitas bucles internos ajustados de 16 bits (p. ej., portar un bucle interno Z80 sin reescribirlo), usa el sufijo `.SIS` en instrucciones individuales en lugar de cambiar todo el modo del procesador.

### The MBASE Trap

En modo compatible Z80, el registro MBASE proporciona los 8 bits superiores de cada dirección de memoria --- incluyendo las lecturas de instrucciones. Si cambias MBASE mientras ejecutas en modo Z80, la siguiente lectura de instrucción usa el nuevo valor de MBASE. A menos que tu código exista en la dirección física correspondiente, la ejecución saltará a basura.

Regla: si debes usar el modo Z80, establece MBASE una vez al inicio y déjalo en paz. Mejor aún, quédate en modo ADL.

---

## 3. Instrucciones nuevas

Estas instrucciones existen en el eZ80 pero no en el Z80 estándar. Son la razón por la que el eZ80 es más que un Z80 con registros más anchos.

### Arithmetic and Test

| Instrucción | Bytes | Ciclos | Descripción |
|-------------|-------|--------|-------------|
| `MLT BC` | 2 | 6 | Multiplicación 8x8 sin signo: B * C -> BC |
| `MLT DE` | 2 | 6 | Multiplicación 8x8 sin signo: D * E -> DE |
| `MLT HL` | 2 | 6 | Multiplicación 8x8 sin signo: H * L -> HL |
| `MLT SP` | 2 | 6 | Multiplicación 8x8 sin signo: SPH * SPL -> SP (raramente útil) |
| `TST A, n` | 3 | 7 | Test: A AND n, establece banderas, A sin cambios |
| `TST A, r` | 2 | 4 | Test: A AND r, establece banderas, A sin cambios |
| `TSTIO n` | 3 | 12 | Test I/O: (C) AND n, establece banderas |

### Address Computation

| Instrucción | Bytes | Ciclos | Descripción |
|-------------|-------|--------|-------------|
| `LEA BC, IX+d` | 3 | 4 | BC = IX + desplazamiento con signo d |
| `LEA DE, IX+d` | 3 | 4 | DE = IX + d |
| `LEA HL, IX+d` | 3 | 4 | HL = IX + d |
| `LEA IX, IX+d` | 3 | 4 | IX = IX + d (sumar desplazamiento a IX) |
| `LEA BC, IY+d` | 3 | 4 | BC = IY + d |
| `LEA DE, IY+d` | 3 | 4 | DE = IY + d |
| `LEA HL, IY+d` | 3 | 4 | HL = IY + d |
| `LEA IY, IY+d` | 3 | 4 | IY = IY + d (sumar desplazamiento a IY) |
| `PEA IX+d` | 3 | 7 | Empujar (IX + d) a la pila |
| `PEA IY+d` | 3 | 7 | Empujar (IY + d) a la pila |

LEA calcula una dirección efectiva sin realizar un acceso a memoria --- es aritmética pura de registros. En el Z80 estándar, calcular `HL = IX + 5` requiere una secuencia de múltiples instrucciones (`PUSH IX / POP HL / LD DE,5 / ADD HL,DE`). LEA lo hace en una sola instrucción en 4 ciclos.

### I/O and System

| Instrucción | Bytes | Ciclos | Descripción |
|-------------|-------|--------|-------------|
| `IN0 r, (n)` | 3 | 7 | Lectura de puerto de E/S interno (dirección de 8 bits) |
| `OUT0 (n), r` | 3 | 7 | Escritura en puerto de E/S interno (dirección de 8 bits) |
| `SLP` | 2 | -- | Dormir: detener CPU hasta interrupción (menor consumo que HALT) |
| `STMIX` | 2 | 4 | Establecer bandera de modo mixto (habilitar intercalado ADL/Z80) |
| `RSMIX` | 2 | 4 | Resetear bandera de modo mixto |

IN0/OUT0 usan una dirección de puerto de 8 bits (a diferencia del IN/OUT estándar que puede usar direcciones de puerto de 16 bits a través de BC). Están diseñados para los periféricos internos del eZ80 y rara vez se usan en código de juegos del Agon.

---

## 4. MLT --- El cambio de juego

De todas las instrucciones nuevas del eZ80, MLT es la de mayor impacto para código de juegos y demos. Realiza una multiplicación 8x8 sin signo en una sola instrucción.

En el Z80 estándar, la multiplicación 8x8 requiere un bucle de desplazamiento y suma:

```z80
; Z80: 8x8 unsigned multiply (B * C -> A:C)
; Cost: 196-204 T-states, 14 bytes
mulu_z80:
    ld   a, 0           ; 7T   clear accumulator
    ld   d, 8           ; 7T   8 bits

.loop:
    rr   c              ; 8T   shift multiplier bit into carry
    jr   nc, .noadd     ; 7/12T
    add  a, b           ; 4T   add multiplicand
.noadd:
    rra                 ; 4T   shift result right
    dec  d              ; 4T
    jr   nz, .loop      ; 12T
    ret                 ; 10T  ~200 T-states total
```

En el eZ80:

```z80
; eZ80: 8x8 unsigned multiply (B * C -> BC)
; Cost: 6 cycles, 2 bytes
    mlt  bc             ; BC = B * C. Done.
```

Seis ciclos. Dos bytes. Sin bucle, sin gestión de acarreo, sin registros temporales. El resultado queda en el par de registros completo de 16 bits: el byte alto del producto está en B, el byte bajo en C.

### What MLT Enables

**Indexación de tablas de seno.** Calcular `base + ángulo * paso` para consultas de seno con paso variable se reduce de una llamada a subrutina a dos instrucciones (`MLT` + `ADD`).

**Cálculo de desplazamiento de sprites.** Encontrar la dirección del fotograma N de un sprite en una hoja de sprites: `base + fotograma * tamaño_fotograma`. Con MLT, esto es trivial cuando tamaño_fotograma cabe en 8 bits.

**Aritmética de punto fijo.** Multiplicar dos valores de punto fijo de 8 bits (p. ej., velocidad * fricción) se convierte en una sola instrucción en lugar de un bucle de ~200 T-states.

**Direccionamiento de mapas de baldosas.** Calcular `base_baldosa + (fila * ancho + columna)` donde ancho cabe en 8 bits: un MLT para el desplazamiento de fila, un ADD para la columna.

### MLT Limitations

- **Solo sin signo.** Para multiplicación con signo, ajusta el signo manualmente después del MLT.
- **Solo 8x8.** Para multiplicación 16x16, todavía necesitas un algoritmo de múltiples pasos (aunque puedes construirlo a partir de componentes MLT).
- **El resultado sobrescribe ambos operandos.** `MLT BC` destruye tanto B como C, reemplazándolos con el producto de 16 bits. Guarda los valores de entrada primero si los necesitas.

---

## 5. Resumen de diferencias clave

| Característica | Z80 (ZX Spectrum 128K) | eZ80 (Agon Light 2) |
|----------------|----------------------|----------------------|
| Reloj | 3.5 MHz | 18.432 MHz |
| Ancho de dirección | 16 bits (64 KB visibles) | 24 bits (16 MB, 512 KB poblados) |
| Ancho de registro | 16 bits | 16 bits (modo Z80) o 24 bits (modo ADL) |
| Pila por PUSH/CALL | 2 bytes | 2 bytes (modo Z80) o 3 bytes (modo ADL) |
| Instrucción de multiplicación | Ninguna (bucle de desplazamiento y suma, ~200T) | MLT rr (6 ciclos) |
| RAM | 128 KB paginada (8 x 16 KB páginas) | 512 KB plana |
| Modelo de acceso a RAM | Conmutación de bancos vía puerto $7FFD | Direccionamiento plano de 24 bits |
| Vídeo | ULA: mapeado directo en memoria en $4000 | VDP (ESP32): basado en comandos vía UART |
| Sonido | AY-3-8910 vía puertos de E/S | Audio VDP vía comandos serie |
| Interrupciones | IM1 (RST $38) o IM2 (tabla de vectores) | IM2 con vectores gestionados por MOS |
| Presupuesto de fotograma (50 Hz) | ~71.680 T-states (Pentagon) | ~368.640 T-states |
| Memoria contendida | Sí (ULA roba ciclos de $4000-$7FFF) | Sin contención |
| SO | Ninguno (bare metal) | MOS (Machine Operating System) |
| Almacenamiento | Cinta / DivMMC | Tarjeta SD (FAT32, API de archivos MOS) |

---

## 6. Especificaciones del Agon Light 2

### Hardware

- **CPU:** Zilog eZ80F92, 18.432 MHz
- **RAM:** 512 KB SRAM externa, espacio de direcciones plano
- **VDP:** ESP32-PICO-D4 ejecutando FabGL, se comunica con el eZ80 vía UART a 1.152.000 baudios
- **Modos de vídeo:** Múltiples, hasta 640x480x64 colores. La mayoría de los juegos usan 320x240 o 320x200.
- **Sprites por hardware:** Hasta 256, gestionados enteramente por el VDP
- **Mapas de baldosas por hardware:** Capas de baldosas desplazables, gestionadas por el VDP
- **Audio:** Síntesis VDP --- seno, cuadrada, triángulo, diente de sierra, ruido. Envolventes ADSR por canal.
- **Almacenamiento:** Tarjeta MicroSD, FAT32, accedida a través de la API de archivos MOS

### Frame Budget

A 18.432 MHz y refresco de 50 Hz:

```
18,432,000 cycles/sec / 50 frames/sec = 368,640 cycles/frame
```

Compara con Pentagon (3.5 MHz, 50 Hz): 71.680 T-states/fotograma. El Agon tiene aproximadamente **5.1x** el presupuesto por fotograma. Pero como muchas instrucciones del eZ80 también se ejecutan en menos ciclos que sus equivalentes Z80, el rendimiento efectivo para código típico es de 5x--20x mayor.

### MOS API

MOS (Machine Operating System) proporciona la interfaz del sistema. El punto de entrada estándar es `RST $08`:

```z80
; MOS API call pattern (in ADL mode)
    ld   a, mos_function     ; function number in A
    rst  $08                 ; call MOS
    ; return value in A (and sometimes HL)
```

Funciones clave de la API de MOS:

| Función | Número | Descripción |
|---------|--------|-------------|
| `mos_getkey` | $00 | Esperar pulsación de tecla, devolver código ASCII |
| `mos_load` | $01 | Cargar archivo de la tarjeta SD a memoria |
| `mos_save` | $02 | Guardar región de memoria a archivo en la tarjeta SD |
| `mos_cd` | $03 | Cambiar directorio actual |
| `mos_dir` | $04 | Listar contenido del directorio |
| `mos_del` | $05 | Eliminar un archivo |
| `mos_ren` | $06 | Renombrar un archivo |
| `mos_sysvars` | $08 | Obtener puntero a variables del sistema (mapa de teclado, estado VDP, reloj) |
| `mos_fopen` | $0A | Abrir archivo, devolver handle |
| `mos_fclose` | $0B | Cerrar handle de archivo |
| `mos_fread` | $0C | Leer bytes del archivo |
| `mos_fwrite` | $0D | Escribir bytes al archivo |
| `mos_fseek` | $0E | Buscar dentro del archivo |

### VDP Command Protocol

Los comandos VDP se envían como flujos de bytes usando `RST $10` (MOS: enviar byte al VDP). La mayoría de los comandos comienzan con VDU 23, seguido de parámetros específicos del comando:

```z80
; Send one byte to VDP
    ld   a, byte_value
    rst  $10                 ; MOS: send byte to VDP

; Example: set screen mode
    ld   a, 22               ; VDU 22 = set mode
    rst  $10
    ld   a, mode_number      ; 0-3 for standard modes
    rst  $10

; Example: move hardware sprite
; VDU 23, 27, 4, spriteNum          -- select sprite
; VDU 23, 27, 13, x.lo, x.hi, y.lo, y.hi  -- set position
```

El VDP procesa los comandos de forma asíncrona. Hay un retardo de transferencia serie entre enviar un comando y que el VDP actúe sobre él. Para una animación suave, envía todas las actualizaciones temprano en el fotograma.

---

## 7. Lista de verificación para portar

Al portar código Z80 del Spectrum al modo ADL del eZ80 en el Agon, repasa esta lista de verificación:

**Direcciones y punteros:**
- Todas las direcciones pasan a ser de 24 bits (3 bytes en lugar de 2)
- Cambia `DW` (define word) a `DL` (define long) para tablas de direcciones
- La indexación de tablas de punteros cambia de `* 2` a `* 3`
- Asegúrate de que el byte superior de las direcciones de 24 bits sea correcto (típicamente $00 o $04)

**Marcos de pila:**
- Cada PUSH son 3 bytes, cada CALL empuja una dirección de retorno de 3 bytes
- Verifica que los pares PUSH/POP estén equilibrados --- un par desbalanceado corrompe 3 bytes, no 2
- Los desplazamientos relativos a la pila (p. ej., acceder a parámetros empujados por el llamador) cambian

**Operaciones de bloque:**
- `LDIR` / `LDDR` usan BC de 24 bits en modo ADL --- asegúrate de que el byte superior de BC sea cero si tu conteo cabe en 16 bits
- Los trucos de copia de bloques basados en `PUSH`/`POP` empujan 3 bytes por PUSH, no 2

**Multiplicación:**
- Reemplaza los bucles de multiplicación por desplazamiento y suma con `MLT` donde sea aplicable
- `MLT BC` = B * C -> BC, `MLT DE` = D * E -> DE, `MLT HL` = H * L -> HL

**E/S y periféricos:**
- Reemplaza E/S de puertos (`OUT (C), A`, `IN A, ($FE)`) con llamadas a la API MOS/VDP
- Reemplaza escrituras directas al framebuffer ($4000--$5AFF) con comandos VDP
- Reemplaza escrituras de registros AY ($FFFD/$BFFD) con comandos de sonido VDP

**Arquitectura de memoria:**
- Elimina toda la lógica de conmutación de bancos (escrituras al puerto $7FFD) --- espacio de direcciones plano
- Elimina las soluciones para memoria contendida --- sin contención en el Agon
- Elimina los trucos de pantalla sombra --- el VDP maneja el doble búfer

**Patrones de código que se vuelven innecesarios:**
- Código auto-modificable para velocidad (todavía funciona, rara vez vale la complejidad)
- Trucos con el puntero de pila para rellenados rápidos de pantalla (no hay framebuffer que rellenar)
- Copias de sprites pre-desplazados (los sprites por hardware manejan el posicionamiento sub-píxel)
- Cálculos de direcciones de pantalla entrelazada (DOWN_HL, pixel_addr --- elimínalos)

**Patrones de código que se transfieren directamente:**
- Bucles de sistemas de entidades (solo ampliar punteros)
- Detección de colisiones AABB (comparaciones de 8 bits, sin cambios)
- Aritmética de punto fijo 8.8 (a nivel de byte, sin cambios)
- Máquinas de estados y tablas de salto (ampliar entradas de tabla a 24 bits)
- Bucles DJNZ, búsquedas CPIR, ramificación basada en banderas (todo idéntico)

---

## Ver también

- **Apéndice A: Referencia rápida de instrucciones Z80** --- tabla completa de instrucciones Z80 con T-states, conteos de bytes y efectos en las banderas. Todo en el Apéndice A también se aplica al eZ80 en modo compatible Z80.
- **Capítulo 22: Portar --- Agon Light 2** --- el tutorial completo de portado, con ejemplos de código antes/después para renderizado, sonido, entrada y lógica de juego.

---

> **Fuentes:** Zilog eZ80 CPU User Manual (UM0077); Zilog eZ80F92 Product Specification (PS0153); Agon Light 2 Official Documentation, The Byte Attic; Dean Belfield, "Agon Light --- Programming Guide" (breakintoprogram.co.uk); Agon MOS API Documentation (github.com/AgonConsole8/agon-docs); Capítulo 22 de este libro
