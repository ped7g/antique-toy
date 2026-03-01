# Capítulo 2: La Pantalla como un Rompecabezas

> "¿Por qué las filas van en ese orden?"
> -- Todo programador de ZX Spectrum, en algún momento

Abre cualquier emulador, escribe `PEEK 16384` y estarás leyendo el primer byte de la pantalla del Spectrum. Pero ¿qué byte es? No es el de la esquina superior izquierda de la pantalla en ningún sentido simple. El píxel en la coordenada (0,0) está ahí, sí -- pero el píxel en (0,1), la siguiente fila hacia abajo, vive a 256 bytes de distancia. El píxel en (0,8), la fila superior de la segunda celda de caracteres, vive a solo 32 bytes del inicio. Y el píxel en (0,64) -- la primera fila del tercio medio de la pantalla -- vive exactamente a 2.048 bytes del inicio, en `$4800`.

Este es el rompecabezas más famoso del Spectrum. El diseño de la memoria de pantalla no es secuencial, no es intuitivo, y no es un accidente. Es una consecuencia de las decisiones de diseño de hardware tomadas en 1982, y da forma a cada pieza de código que toca la pantalla. Comprender este diseño -- y aprender los trucos que hacen rápida la navegación por él -- es fundamental para todo lo que sigue en este libro.

---

## El Mapa de Memoria: 6.912 Bytes de Pantalla

La pantalla del Spectrum ocupa una región fija de memoria:

```text
$4000 - $57FF    Pixel data      6,144 bytes   (256 x 192 pixels, 1 bit per pixel)
$5800 - $5AFF    Attributes        768 bytes   (32 x 24 colour cells)
```

El área de píxeles contiene el mapa de bits: 256 píxeles de ancho, empaquetados 8 por byte, dando 32 bytes por fila. Con 192 filas, eso son 32 x 192 = 6.144 bytes. Cada byte representa 8 píxeles horizontales, con el bit 7 como el píxel más a la izquierda y el bit 0 como el más a la derecha.

El área de atributos contiene la información de color: un byte por cada celda de caracteres de 8x8. Hay 32 columnas y 24 filas, dando 32 x 24 = 768 bytes.

En total: 6.144 + 768 = 6.912 bytes. Esa es la pantalla completa.

<!-- figure: ch02_screen_layout -->
![ZX Spectrum screen memory layout with thirds, character cells, and attribute area](illustrations/output/ch02_screen_layout.png)

Los datos de píxeles y los datos de atributos sirven para propósitos diferentes pero están estrechamente acoplados. Cada byte de píxeles controla 8 puntos en pantalla; el byte de atributo para la celda 8x8 correspondiente controla en qué color aparecen esos puntos. Cambia el píxel y cambiarás la forma. Cambia el atributo y cambiarás el color. Pero solo puedes cambiar el color para un bloque entero de 8x8 -- no por píxel. Este es el "conflicto de atributos" que define el carácter visual del Spectrum, y volveremos a él en breve.

Primero, el rompecabezas: ¿por qué están desordenadas las filas de píxeles?

---

## El Entrelazado: Dónde Viven las Filas

Si el Spectrum almacenara sus filas de píxeles secuencialmente, la fila 0 estaría en `$4000`, la fila 1 en `$4020`, la fila 2 en `$4040`, y así sucesivamente. Cada fila es de 32 bytes, así que la fila N estaría simplemente en `$4000 + N * 32`. Simple, rápido, sensato.

Eso no es lo que pasa.

La pantalla se divide en tres **tercios**, cada uno de 64 filas de píxeles de alto. Dentro de cada tercio, las filas están entrelazadas por fila de celda de caracteres. Aquí es donde realmente viven las primeras 16 filas:

```text
Row  0:  $4000     Third 0, char row 0, scan line 0
Row  1:  $4100     Third 0, char row 0, scan line 1
Row  2:  $4200     Third 0, char row 0, scan line 2
Row  3:  $4300     Third 0, char row 0, scan line 3
Row  4:  $4400     Third 0, char row 0, scan line 4
Row  5:  $4500     Third 0, char row 0, scan line 5
Row  6:  $4600     Third 0, char row 0, scan line 6
Row  7:  $4700     Third 0, char row 0, scan line 7
Row  8:  $4020     Third 0, char row 1, scan line 0
Row  9:  $4120     Third 0, char row 1, scan line 1
Row 10:  $4220     Third 0, char row 1, scan line 2
Row 11:  $4320     Third 0, char row 1, scan line 3
Row 12:  $4420     Third 0, char row 1, scan line 4
Row 13:  $4520     Third 0, char row 1, scan line 5
Row 14:  $4620     Third 0, char row 1, scan line 6
Row 15:  $4720     Third 0, char row 1, scan line 7
```

Observa el patrón. Las primeras 8 filas son las 8 líneas de escaneo de la fila de caracteres 0 -- pero están a 256 bytes de distancia, no a 32. Dentro de esas 8 filas, el byte alto de la dirección se incrementa en 1 cada vez: `$40`, `$41`, `$42`, ... `$47`. Luego la fila 8 salta a `$4020` -- vuelve a un byte alto de `$40`, pero con el byte bajo avanzado en 32.

Aquí está el panorama completo para el tercio superior de la pantalla:

```text
Char row 0:   scan lines at $4000, $4100, $4200, $4300, $4400, $4500, $4600, $4700
Char row 1:   scan lines at $4020, $4120, $4220, $4320, $4420, $4520, $4620, $4720
Char row 2:   scan lines at $4040, $4140, $4240, $4340, $4440, $4540, $4640, $4740
Char row 3:   scan lines at $4060, $4160, $4260, $4360, $4460, $4560, $4660, $4760
Char row 4:   scan lines at $4080, $4180, $4280, $4380, $4480, $4580, $4680, $4780
Char row 5:   scan lines at $40A0, $41A0, $42A0, $43A0, $44A0, $45A0, $46A0, $47A0
Char row 6:   scan lines at $40C0, $41C0, $42C0, $43C0, $44C0, $45C0, $46C0, $47C0
Char row 7:   scan lines at $40E0, $41E0, $42E0, $43E0, $44E0, $45E0, $46E0, $47E0
```

El tercio medio comienza en `$4800` y sigue el mismo patrón. El tercio inferior comienza en `$5000`.

### ¿Por qué?

La razón es la ULA -- el Array de Lógica No Comprometida que genera la señal de vídeo. La ULA lee un byte de datos de píxeles y un byte de datos de atributos por cada celda de caracteres de 8 píxeles que dibuja. Necesita ambos bytes en momentos específicos mientras rastrea la pantalla.

El diseño entrelazado significó que la lógica del contador de direcciones de la ULA podía construirse con menos puertas. Mientras la ULA escanea de izquierda a derecha a través de una fila de caracteres, incrementa los 5 bits bajos de la dirección (la columna). Cuando llega al borde derecho, incrementa el byte alto para moverse a la siguiente línea de escaneo dentro de la misma fila de caracteres. Cuando termina las 8 líneas de escaneo, envuelve el byte alto y avanza los bits de fila del byte bajo.

Esto es elegante desde la perspectiva del hardware. La generación de direcciones de la ULA es una simple combinación de contadores -- sin multiplicación, sin aritmética de direcciones compleja. El enrutamiento del PCB era más simple, el conteo de puertas era menor, y el chip era más barato de fabricar.

El programador paga el precio.

---

## El Diseño de Bits: Decodificando (x, y) en una Dirección

> **Fuentes:** Introspec "Eshchyo raz pro DOWN_HL" (Hype, 2020); Introspec "GO WEST Part 1" (Hype, 2015) para efectos de memoria contendida en direcciones de pantalla; Introspec "Making of Eager" (Hype, 2015) para diseño de efectos basados en atributos; la documentación de la ULA del Spectrum para la justificación del diseño de memoria; Art-top (comunicación personal, 2026) para el UP_HL optimizado y la conversión rápida de píxel a atributo.

Para entender el entrelazado con precisión, observa cómo la coordenada Y se mapea en la dirección de pantalla de 16 bits. Considera un píxel en la columna `x` (0--255) y fila `y` (0--191). El byte que contiene ese píxel está en:

```text
High byte:  0 1 0 T T S S S
Low byte:   L L L C C C C C
```

Donde:
- `TT` = en qué tercio de la pantalla (0, 1 o 2). Bits 7--6 de y.
- `SSS` = línea de escaneo dentro de la celda de caracteres (0--7). Bits 2--0 de y.
- `LLL` = fila de caracteres dentro del tercio (0--7). Bits 5--3 de y.
- `CCCCC` = columna en bytes (0--31). Esto es x / 8, o equivalentemente bits 7--3 de x.

Lo crucial: los bits de y no están en orden. Los bits 7-6 van a un lugar, los bits 5-3 van a otro, y los bits 2-0 van a otro más. La coordenada y se corta en trozos y se distribuye por toda la dirección.

Visualicemos esto con un ejemplo concreto. Píxel (80, 100):

```text
x = 80:     column byte = 80 / 8 = 10      CCCCC = 01010
y = 100:    binary = 01100100
            TT  = 01       (third 1, the middle third)
            LLL = 100      (char row 4 within the third)
            SSS = 100      (scan line 4 within the char cell)

High byte:  0  1  0  0  1  1  0  0  = $4C
Low byte:   1  0  0  0  1  0  1  0  = $8A

Address: $4C8A
```

El bit dentro de ese byte se determina por los 3 bits bajos de x. El bit 7 es el píxel más a la izquierda, así que la posición del píxel (x AND 7) se mapea al bit 7 - (x AND 7).

### El cálculo de dirección en Z80

Convertir (x, y) a una dirección de pantalla es algo que necesitas hacer rápido y a menudo. Aquí tienes una rutina estándar:

```z80 id:ch02_the_address_calculation_in
; Input:  B = y (0-191), C = x (0-255)
; Output: HL = screen address, A = bit mask
;
pixel_addr:
    ld   a, b          ; 4T   A = y
    and  $07           ; 7T   A = SSS (scan line within char)
    or   $40           ; 7T   A = 010 00 SSS (add screen base)
    ld   h, a          ; 4T   H = high byte (partial)

    ld   a, b          ; 4T   A = y again
    rra                ; 4T   \
    rra                ; 4T    | shift bits 5-3 of y
    rra                ; 4T   /  down to bits 2-0
    and  $E0           ; 7T   mask to get LLL 00000
    ld   l, a          ; 4T   L = LLL 00000 (partial)

    ld   a, b          ; 4T   A = y again
    and  $C0           ; 7T   A = TT 000000
    rra                ; 4T   \
    rra                ; 4T    | shift bits 7-6 of y
    rra                ; 4T   /  to bits 4-3
    or   h             ; 4T   combine with SSS
    ld   h, a          ; 4T   H = 010 TT SSS (complete)

    ld   a, c          ; 4T   A = x
    rra                ; 4T   \
    rra                ; 4T    | x / 8
    rra                ; 4T   /
    and  $1F           ; 7T   mask to CCCCC
    or   l             ; 4T   combine with LLL 00000
    ld   l, a          ; 4T   L = LLL CCCCC (complete)
                       ; --- Total: ~91 T-states
```

91 T-states no es barato. En un bucle interno apretado procesando miles de píxeles, no llamarías a esta rutina por cada píxel. En cambio, calculas la dirección de inicio una vez y luego navegas la pantalla usando manipulación rápida de punteros -- lo que nos lleva a la rutina más importante en la programación de gráficos del Spectrum.

![Pixel plotting demo — individual pixels placed on screen using the address calculation routine](../../build/screenshots/ch02_pixel_demo.png)

---

## DOWN_HL: Mover una Fila de Píxeles Hacia Abajo

Tienes un puntero en HL apuntando a algún byte en la pantalla. Quieres moverlo una fila de píxeles hacia abajo -- al byte en la misma columna, una línea de escaneo más abajo. ¿Qué tan difícil puede ser?

En un framebuffer lineal, sumas 32 (el número de bytes por fila). Un `ADD HL, DE` con DE = 32: 11 T-states, listo.

En el Spectrum, es un rompecabezas dentro del rompecabezas. Moverse una fila de píxeles hacia abajo significa:

1. **Dentro de una celda de caracteres** (líneas de escaneo 0--6 a 1--7): incrementar H. Los bits de línea de escaneo están en los 3 bits bajos de H, así que `INC H` te mueve una línea de escaneo hacia abajo.

2. **Cruzando un límite de celda de caracteres** (línea de escaneo 7 a línea de escaneo 0 de la siguiente fila): restablecer los bits de línea de escaneo de H a 0, y sumar 32 a L para moverse a la siguiente fila de caracteres.

3. **Cruzando un límite de tercio** (parte inferior de la fila de car. 7 en un tercio a la parte superior de la fila de car. 0 en el siguiente): restablecer L, y sumar 8 a H para moverse al siguiente tercio. Equivalentemente, sumar `$0800` a la dirección.

La rutina clásica maneja los tres casos:

```z80 id:ch02_downhl_moving_one_pixel_row
; DOWN_HL: move HL one pixel row down on the Spectrum screen
; Input:  HL = current screen address
; Output: HL = screen address one row below
;
down_hl:
    inc  h             ; 4T   try moving one scan line down
    ld   a, h          ; 4T
    and  7             ; 7T   did we cross a character boundary?
    ret  nz            ; 11/5T  no: done

    ; Crossed a character cell boundary.
    ; Reset scan line to 0, advance character row.
    ld   a, l          ; 4T
    add  a, 32         ; 7T   next character row (L += 32)
    ld   l, a          ; 4T
    ret  c             ; 11/5T  if carry, we crossed into next third

    ; No carry from L, but we need to undo the H increment
    ; that moved us into the wrong third.
    ld   a, h          ; 4T
    sub  8             ; 7T   back up one third in H
    ld   h, a          ; 4T
    ret                ; 10T
```

Esta rutina toma diferentes cantidades de tiempo dependiendo del caso:

| Case | Frequency | T-states |
|------|-----------|----------|
| Within a character cell | 7 out of 8 rows | 4 + 4 + 7 + 11 = **26** |
| Character boundary, same third | 7 out of 64 rows | 4 + 4 + 7 + 5 + 4 + 7 + 4 + 5 + 4 + 7 + 4 + 10 = **65** |
| Third boundary | 2 out of 192 rows | 4 + 4 + 7 + 5 + 4 + 7 + 4 + 11 = **46** |

The common case -- staying within a character cell -- is fast: 26 T-states (a conditional RET that fires costs 11T, not 5T). The uncommon case (crossing a character row boundary within the same third) is 65 T-states. Averaged over all 192 rows, the cost works out to about **30.5 T-states per call**.

That average hides a problem. If you are iterating down the full screen and calling DOWN_HL on every row, those occasional 65-T-state calls spike your per-line timing unpredictably. For a demo effect that needs consistent timing per scanline, this jitter is unacceptable.

### La Optimización de Introspec

En diciembre de 2020, Introspec (spke) publicó un análisis detallado en Hype titulado "Una vez más sobre DOWN_HL" (Eshchyo raz pro DOWN_HL). El artículo examinó el problema de iterar eficientemente hacia abajo por toda la pantalla -- no solo el coste de una llamada, sino el coste total de mover HL a través de las 192 filas.

The naive approach -- calling the classic DOWN_HL routine 191 times -- costs **5,825 T-states** for a full screen traversal. Introspec's goal was to find the fastest way to iterate through all 192 rows, visiting every screen address in top-to-bottom order.

Su perspicacia clave fue usar **contadores divididos**. En lugar de probar los bits de la dirección después de cada incremento para detectar cruces de límites, estructuró el bucle para que coincidiera directamente con la jerarquía de tres niveles de la pantalla:

```text id:ch02_introspec_s_optimisation
For each third (3 iterations):
    For each character row within the third (8 iterations):
        For each scan line within the character cell (8 iterations):
            process this row
            INC H                  ; next scan line
        undo 8 INC H's, ADD 32 to L   ; next character row
    undo 8 ADD 32's, advance to next third
```

La operación más interna es solo `INC H` -- 4 T-states. Sin pruebas, sin ramificaciones. Las transiciones de fila de caracteres y de tercio ocurren en puntos fijos y predecibles del bucle, así que no hay lógica condicional en el bucle interno en absoluto.

El resultado: **2.343 T-states** para un recorrido completo de la pantalla. Eso es una mejora del 60% respecto al enfoque clásico, y el coste por línea es absolutamente predecible -- sin jitter.

También había una variación elegante atribuida a RST7, usando un enfoque de doble contador donde el bucle externo mantiene un par de contadores que naturalmente rastrean los límites de fila de caracteres y de tercio. El cuerpo del bucle interno se reduce a un solo `INC H`, y el manejo de límites se integra en la manipulación de contadores a nivel del bucle externo.

La lección práctica: cuando necesites iterar a través de la pantalla del Spectrum en orden, no llames a una rutina DOWN_HL de propósito general 191 veces. Reestructura tu bucle para que coincida con la jerarquía natural de la pantalla, y las ramificaciones desaparecen.

Aquí tienes una versión simplificada del enfoque de contadores divididos:

```z80 id:ch02_introspec_s_optimisation_2
; Iterate all 192 screen rows using split counters
; HL = $4000 at entry (top-left of screen)
;
iterate_screen:
    ld   hl, $4000          ; 10T  start of screen
    ld   c, 3               ; 7T   3 thirds

.third_loop:
    ld   b, 8               ; 7T   8 character rows per third

.row_loop:
    push hl                 ; 11T  save start of this char row

    ; --- Process 8 scan lines within this character cell ---
    REPT 7
        ; ... your per-row code here, using HL ...
        inc  h              ; 4T   next scan line
    ENDR
    ; ... process the 8th (last) scan line ...

    pop  hl                 ; 10T  restore char row start
    ld   a, l               ; 4T
    add  a, 32              ; 7T   next character row
    ld   l, a               ; 4T

    djnz .row_loop          ; 13T/8T

    ; Advance to next third
    ld   a, h               ; 4T
    add  a, 8               ; 7T   next third ($0800 higher)
    ld   h, a               ; 4T

    dec  c                  ; 4T
    jr   nz, .third_loop    ; 12T/7T
```

La directiva `REPT 7` (soportada por sjasmplus) repite el bloque 7 veces en tiempo de ensamblado -- un desenrollado parcial. Dentro de ese bloque, moverse una línea de escaneo hacia abajo es un solo `INC H`. Sin pruebas, sin ramificaciones. El avance de fila de caracteres y el avance de tercio ocurren en los límites fijos del bucle externo.

---

## Memoria de Atributos: 768 Bytes Que lo Cambiaron Todo

Debajo de los datos de píxeles, en `$5800`--`$5AFF`, se encuentra la memoria de atributos. Son 768 bytes -- uno por cada celda de caracteres de 8x8 en la pantalla, dispuestos secuencialmente de izquierda a derecha, de arriba a abajo. A diferencia del área de píxeles, el diseño de atributos es completamente lineal: la celda (col, fila) está en `$5800 + fila * 32 + col`.

Cada byte de atributo tiene este diseño:

```text
  Bit:   7     6     5  4  3     2  1  0
       +-----+-----+--------+--------+
       |  F  |  B  | PAPER  |  INK   |
       +-----+-----+--------+--------+

  F       = Flash (0 = off, 1 = flashing at ~1.6 Hz)
  B       = Bright (0 = normal, 1 = bright)
  PAPER   = Background colour (0-7)
  INK     = Foreground colour (0-7)
```

Los códigos de color de 3 bits se mapean a:

```text
  0 = Black       4 = Green
  1 = Blue        5 = Cyan
  2 = Red         6 = Yellow
  3 = Magenta     7 = White
```

Con el bit BRIGHT, cada color tiene una variante normal y brillante. El negro permanece negro sea brillante o no, así que la paleta total es de 15 colores distintos:

```text
Normal:  Black  Blue  Red  Magenta  Green  Cyan  Yellow  White
Bright:  Black  Blue  Red  Magenta  Green  Cyan  Yellow  White
                (brighter versions of each)
```

<!-- figure: ch02_attr_byte -->
![Attribute byte bit layout showing flash, bright, paper, and ink fields](illustrations/output/ch02_attr_byte.png)

An attribute byte of `$47` = `01000111`: flash off (bit 7 = 0), bright **on** (bit 6 = 1), paper = 000 (black), ink = 111 (white). Bright white text on a black background. The non-bright version is `$07` = `00000111` -- the Spectrum's default after `BORDER 0: PAPER 0: INK 7`.

Este tipo de detalle a nivel de bits importa cuando estás construyendo valores de atributos a velocidad. Un patrón común:

```z80 id:ch02_attribute_memory_768_bytes_4
; Build an attribute byte: bright white ink on blue paper
; Bright = 1, Paper = 001 (blue), Ink = 111 (white)
; = 01 001 111 = $4F
    ld   a, $4F
```

### El Conflicto de Atributos

Aquí está la restricción que define al ZX Spectrum: dentro de cada celda de píxeles de 8x8, solo puedes tener **dos colores** -- ink y paper. Cada píxel activado (1) se muestra en el color ink. Cada píxel desactivado (0) se muestra en el color paper. No puedes tener tres colores, ni gradientes, ni coloración por píxel, dentro de una sola celda.

Esto significa que si un sprite rojo se superpone con un fondo verde, la celda de 8x8 que contiene la superposición debe elegir: todos los píxeles activados en esta celda son o rojos o verdes. No puedes tener algunos píxeles activados rojos y algunos verdes en la misma celda. El resultado visual es un bloque discordante de color que "choca" con su entorno -- el infame conflicto de atributos.

```text
Without clash (hypothetical per-pixel colour):

  +---------+---------+
  |  Red    | Red on  |
  |  sprite | green   |
  |  pixels | back-   |
  |         | ground  |
  +---------+---------+

With attribute clash (Spectrum reality):

  +---------+---------+
  |  Red    | Either  |
  |  sprite | ALL red |
  |  pixels | or ALL  |
  |         | green   |
  +---------+---------+

  The overlapping cell cannot have both colours.
```

Muchos juegos tempranos del Spectrum simplemente evitaron el problema: gráficos monocromáticos, o personajes cuidadosamente diseñados para alinearse con la cuadrícula de 8x8. Juegos como Knight Lore y Head Over Heels usaban un solo par ink/paper para toda el área de juego, eliminando el conflicto por completo a costa del color.

Pero la demoscene lo vio de manera diferente. El conflicto de atributos no es solo una limitación -- es una **restricción creativa**. La cuadrícula de 8x8 impone una estética particular: bloques audaces de color, patrones geométricos nítidos, uso deliberado del contraste. Los efectos de demo que trabajan enteramente en el espacio de atributos -- túneles, plasmas, scrollers -- pueden actualizar 768 bytes por fotograma en vez de 6.144, liberando enormes cantidades de presupuesto de ciclos para computación. Cuando toda tu pantalla está basada en atributos, el conflicto se vuelve irrelevante porque no estás mezclando sprites con fondos -- los atributos *son* los gráficos.

La demo Eager de Introspec (2015) construyó su lenguaje visual enteramente alrededor de esta perspicacia. El efecto de túnel, el chaos zoomer y la animación de ciclo de colores todos operan sobre atributos, no píxeles. El resultado es un efecto que corre a velocidad completa de fotograma con espacio de sobra para tambores digitales y un motor de scripting sofisticado. El conflicto no es un problema porque la restricción fue abrazada desde el inicio.

---

## El Borde: Más que Decoración

El área de pantalla de 256x192 píxeles se encuentra en el centro de la pantalla, rodeada por un borde ancho. El color del borde se establece escribiendo en el puerto `$FE`:

```z80 id:ch02_the_border_more_than
    ld   a, 1          ; 7T   blue = colour 1
    out  ($FE), a       ; 11T  set border colour
```

Solo los bits 0--2 del byte escrito en `$FE` afectan el color del borde. Hay 8 colores (0--7), sin variantes brillantes -- la paleta del borde es el conjunto no brillante. Los bits 3 y 4 del puerto `$FE` controlan las salidas MIC y EAR (interfaz de cinta y sonido del beeper), así que debes enmascarar o establecer esos bits apropiadamente si no pretendes hacer ruido.

El cambio de color del borde tiene efecto inmediatamente -- en la siguiente línea de escaneo que se está dibujando. Esto es lo que hace al borde tan útil como herramienta de depuración. Como vimos en el Capítulo 1, cambiar el color del borde antes y después de una sección de código crea una franja visible cuya altura revela el coste en T-states del código. El borde es tu osciloscopio.

### Efectos de Borde

Debido a que los cambios de color del borde son visibles en la siguiente línea de escaneo, instrucciones `OUT` precisamente temporizadas pueden crear franjas multicolor, barras raster e incluso gráficos primitivos en el área del borde.

El principio básico: la ULA dibuja una línea de escaneo cada 224 T-states (en Pentagon). Si ejecutas una instrucción `OUT ($FE), A` en el momento correcto, cambias el color del borde en una posición horizontal específica de la línea de escaneo actual. Ejecutando una secuencia rápida de instrucciones `OUT` con diferentes valores de color, puedes pintar franjas horizontales de color en el borde.

```z80 id:ch02_border_effects
; Simple border stripes
; Assumes we are synced to the start of a border scanline

    ld   a, 2          ; 7T   red
    out  ($FE), a       ; 11T
    ; ... delay to fill this scanline ...
    ld   a, 5          ; 7T   cyan
    out  ($FE), a       ; 11T
    ; ... delay to fill next scanline ...
    ld   a, 6          ; 7T   yellow
    out  ($FE), a       ; 11T
```

Los efectos de borde más avanzados pueden crear barras de gradiente, texto desplazable, o incluso imágenes de baja resolución. El desafío es extremo: tienes 224 T-states por línea de escaneo, y cada cambio de color cuesta como mínimo 18 T-states (7 para `LD A,n` + 11 para `OUT`). Eso te da aproximadamente 12 cambios de color por línea de escaneo, lo que significa como máximo 12 bandas de color horizontales por línea.

Los programadores de demos han llevado esto a extremos notables. Pre-cargando múltiples registros con valores de color y usando secuencias más rápidas como `OUT (C), A` seguido de intercambios de registros, exprimen más cambios de color por línea. El borde se convierte en una pantalla en sí misma -- un lienzo fuera del lienzo.

Para nuestros propósitos, el papel más importante del borde es el del Capítulo 1: un visualizador de temporización gratuito y siempre disponible. Cuando estés optimizando la rutina de llenado de pantalla más adelante en este capítulo, el borde es cómo verás tu progreso.

---

## Práctica: El Llenado de Tablero de Ajedrez

El ejemplo en `chapters/ch02-screen-as-puzzle/examples/fill_screen.a80` llena el área de píxeles con un patrón de tablero de ajedrez y los atributos con blanco brillante sobre azul. Recorrámoslo sección por sección.

```z80 id:ch02_practical_the_checkerboard
    ORG $8000

SCREEN  EQU $4000       ; pixel area start
ATTRS   EQU $5800       ; attribute area start
SCRLEN  EQU 6144        ; pixel bytes (256*192/8)
ATTLEN  EQU 768         ; attribute bytes (32*24)
```

El código se coloca en `$8000` -- de forma segura en memoria no contendida en todos los modelos de Spectrum. Las constantes nombran las direcciones y tamaños clave.

```z80 id:ch02_practical_the_checkerboard_2
start:
    ; --- Fill pixels with checkerboard pattern ---
    ld   hl, SCREEN
    ld   de, SCREEN + 1
    ld   bc, SCRLEN - 1
    ld   (hl), $55       ; checkerboard: 01010101
    ldir
```

Esto usa el truco clásico de auto-copia LDIR. Escribe `$55` (binario `01010101`) en el primer byte en `$4000`, luego copia de cada byte al siguiente durante 6.143 bytes. El resultado: cada byte del área de píxeles es `$55`, lo que produce píxeles alternados activados/desactivados -- un tablero de ajedrez. Como el patrón es el mismo en cada byte, el orden entrelazado de las filas no importa -- cada fila obtiene el mismo patrón independientemente.

Cost: `LDIR` copies 6,143 bytes. The last iteration costs 16T, all others 21T: (6,143 - 1) x 21 + 16 = 128,998 T-states. Nearly two full frames on a Pentagon. This is fine for a one-time setup, but you would never do this in a per-frame rendering loop.

```z80 id:ch02_practical_the_checkerboard_3
    ; --- Fill attributes: white ink on blue paper ---
    ; Attribute byte: flash=0, bright=1, paper=001 (blue), ink=111 (white)
    ; = 01 001 111 = $4F
    ld   hl, ATTRS
    ld   de, ATTRS + 1
    ld   bc, ATTLEN - 1
    ld   (hl), $4F
    ldir
```

La misma técnica para los atributos. El valor `$4F` se decodifica como: flash apagado (0), bright encendido (1), paper azul (001), ink blanco (111). Cada celda de 8x8 obtiene ink blanco brillante sobre paper azul. Los píxeles del tablero de ajedrez están activados/desactivados, así que ves puntos alternados blancos y azules -- un patrón visual clásico del ZX Spectrum.

Cost: `LDIR` copies 767 bytes -- (767 - 1) x 21 + 16 = 16,102 T-states.

```z80 id:ch02_practical_the_checkerboard_4
    ; --- Border: blue ---
    ld   a, 1
    out  ($FE), a

    ; Infinite loop
.wait:
    halt
    jr   .wait
```

Establece el borde en azul (color 1) para que coincida con el color paper, creando un marco visualmente limpio. Luego entra en bucle infinito, deteniendo entre fotogramas. El `HALT` espera la siguiente interrupción enmascarable, que se dispara una vez por fotograma -- este es el latido inactivo de todo programa de Spectrum.

![Screen fill with alternating bytes — checkerboard pattern in bright white on blue](../../build/screenshots/ch02_fill_screen.png)

### Qué probar

Carga `fill_screen.a80` en tu ensamblador y emulador. Luego experimenta:

- Cambia `$55` a `$AA` para el tablero de ajedrez inverso, o a `$FF` para relleno sólido, o `$81` para barras verticales.
- Cambia `$4F` a `$07` para ver el mismo patrón sin BRIGHT, o a `$38` para paper blanco con ink negro (el inverso del predeterminado).
- Prueba `$C7` -- eso establece el bit de flash. Observa los caracteres alternando entre colores ink y paper a aproximadamente 1,6 Hz.
- Reemplaza el llenado de píxeles LDIR con un bucle DOWN_HL que escriba diferentes patrones en diferentes filas. Ahora verás el entrelazado en acción: si escribes `$FF` en las filas 0-7 (las líneas de escaneo de la primera celda de caracteres), el área llenada aparecerá como 8 franjas horizontales separadas por espacios -- porque esas filas están a 256 bytes de distancia, no a 32.

---

## Navegando la Pantalla: Un Resumen Práctico

Aquí están las operaciones esenciales de punteros para la pantalla del Spectrum, recopiladas en un solo lugar. Estos son los bloques de construcción de toda rutina gráfica.

### Moverse a la derecha un byte (8 píxeles)

```z80 id:ch02_moving_right_one_byte_8
    inc  l             ; 4T
```

Esto funciona dentro de una fila de caracteres porque la columna está en los 5 bits bajos de L. Si necesitas cruzar límites de bytes en el borde derecho (columna 31 a columna 0 de la siguiente fila), necesitas el DOWN_HL completo más reinicio de L -- pero típicamente no lo necesitas, porque tus bucles son de 32 bytes de ancho.

### Moverse una fila de píxeles hacia abajo

```z80 id:ch02_moving_down_one_pixel_row
    inc  h             ; 4T    (within a character cell)
```

Esto funciona para 7 de cada 8 filas. En la octava fila, necesitas la lógica completa de cruce de límites de la rutina DOWN_HL anterior.

### Moverse una fila de caracteres hacia abajo (8 píxeles)

```z80 id:ch02_moving_down_one_character_row
    ld   a, l          ; 4T
    add  a, 32         ; 7T
    ld   l, a          ; 4T    total: 15T (if no third crossing)
```

Esto avanza una fila de caracteres dentro de un tercio. Si L desborda (carry activado), has cruzado al siguiente tercio y necesitas sumar 8 a H.

### Moverse una fila de píxeles hacia arriba

```z80 id:ch02_moving_up_one_pixel_row
    dec  h             ; 4T    (within a character cell)
```

El inverso de `INC H`. Los mismos problemas de límites en los límites de celda de caracteres y de tercio. Aquí está la rutina completa UP_HL, el espejo de DOWN_HL:

```z80 id:ch02_moving_up_one_pixel_row_2
; UP_HL: move HL one pixel row up on the Spectrum screen
; Input:  HL = current screen address
; Output: HL = screen address one row above
;
; Classic version:
up_hl:
    dec  h             ; 4T   try moving one scan line up
    ld   a, h          ; 4T
    and  7             ; 7T   did we cross a character boundary?
    cp   7             ; 7T
    ret  nz            ; 11/5T  no: done

    ; Crossed a character cell boundary upward.
    ld   a, l          ; 4T
    sub  32            ; 7T   previous character row (L -= 32)
    ld   l, a          ; 4T
    ret  c             ; 11/5T  if carry, crossed into prev third

    ld   a, h          ; 4T
    add  a, 8          ; 7T   compensate H
    ld   h, a          ; 4T
    ret                ; 10T
```

There is a subtle optimisation here, contributed by Art-top (Artem Topchiy): replacing `and 7 / cp 7` with `cpl / and 7`. After `DEC H`, if the low 3 bits of H wrapped from `000` to `111`, we crossed a character boundary. The classic test checks `AND 7` then compares with 7. The optimised version complements first: if the bits are `111`, CPL makes them `000`, and `AND 7` gives zero. This saves 1 byte and 3 T-states in the boundary-crossing path:

```z80 id:ch02_moving_up_one_pixel_row_3
; UP_HL optimised (Art-top)
; Saves 1 byte, 3 T-states on boundary crossing
;
up_hl_opt:
    dec  h             ; 4T
    ld   a, h          ; 4T
    cpl                ; 4T   complement: 111 -> 000
    and  7             ; 7T   zero if we crossed boundary
    ret  nz            ; 11/5T

    ld   a, l          ; 4T
    sub  32            ; 7T
    ld   l, a          ; 4T
    ret  c             ; 11/5T

    ld   a, h          ; 4T
    add  a, 8          ; 7T
    ld   h, a          ; 4T
    ret                ; 10T
```

El mismo truco `CPL / AND 7` funciona en DOWN_HL también, aunque la condición de límite allí prueba `000` (que CPL convierte en `111`, también distinto de cero después de AND), así que no ayuda yendo hacia abajo. Es específicamente la dirección *hacia arriba* donde el código clásico necesita el `CP 7` extra que la optimización elimina.

### Calcular la dirección de atributo desde una dirección de píxel

If HL points to a byte in the pixel area, the corresponding attribute address can be calculated. Recall the pixel address structure: H = `010TTSSS`, L = `LLLCCCCC`. The attribute address for the same character cell is `$5800 + TT * 256 + LLL * 32 + CCCCC`. Since L already encodes `LLL * 32 + CCCCC` (which ranges 0--255), the attribute address is simply `($58 + TT) : L`. All we need to do is extract the two TT bits from H, combine them with `$58`, and leave L unchanged:

```z80 id:ch02_computing_the_attribute
; Convert pixel address in HL to attribute address in HL
; Input:  HL = pixel address ($4000-$57FF)
; Output: HL = corresponding attribute address ($5800-$5AFF)
;
    ld   a, h          ; 4T
    rrca               ; 4T
    rrca               ; 4T
    rrca               ; 4T
    and  3             ; 7T
    or   $58           ; 7T
    ld   h, a          ; 4T
    ; L unchanged       --- Total: 34T
```

Esto funciona porque L ya contiene `LLL CCCCC` -- la fila de caracteres dentro del tercio (0--7) combinada con la columna (0--31) -- y eso es exactamente el byte bajo de la dirección de atributo. El byte alto solo necesita el número de tercio sumado a `$58`. Elegante.

**Special case: when H has scanline bits = 111.** If you are iterating through a character cell top-to-bottom and have just processed the last scanline (scanline 7), the low 3 bits of H are `111`. In this case there is a faster 4-instruction conversion, contributed by Art-top:

```z80 id:ch02_computing_the_attribute_2
; Pixel-to-attribute when H low bits are %111
; (e.g., after processing the last scanline of a character cell)
; Input:  HL where H = 010TT111
; Output: HL = attribute address
;
    srl  h             ; 8T   010TT111 -> 0010TT11
    rrc  h             ; 8T   0010TT11 -> 10010TT1
    srl  h             ; 8T   10010TT1 -> 010010TT
    set  4, h          ; 8T   010010TT -> 010110TT = $58+TT
    ; L unchanged.     --- Total: 32T, 4 instructions
```

Esto es 2 T-states más rápido que el método general y evita la secuencia `AND / OR`. La compensación es que solo funciona cuando los bits de línea de escaneo son `111` -- pero esa es exactamente la situación después de un bucle de renderizado de celda de caracteres de arriba a abajo, que es uno de los casos de uso más comunes.

---

> **Agon Light 2 Sidebar**
>
> The Agon Light 2's display is managed by a VDP (Video Display Processor) -- an ESP32 microcontroller running the FabGL library. The eZ80 CPU communicates with the VDP over a serial link, sending commands to set graphics modes, draw pixels, define sprites, and manage palettes.
>
> There is no interleaved memory layout. There is no attribute clash. The VDP supports multiple bitmap modes at various resolutions (from 640x480 down to 320x240 and below), with 64 colours or full RGBA palettes depending on the mode. Hardware sprites (up to 256) and tile maps are supported natively.
>
> What changes for the programmer:
>
> - **No address puzzle.** Pixel coordinates map linearly to buffer positions. You do not need DOWN_HL or split-counter screen traversal.
> - **No attribute clash.** Each pixel can be any colour. The 8x8 grid constraint does not exist.
> - **No direct memory access to the framebuffer.** The CPU cannot write directly to video memory the way a Spectrum CPU writes to `$4000`. Instead, you send VDP commands over the serial link. Drawing a pixel means sending a command sequence, not storing a byte. This introduces latency -- the serial link runs at 1,152,000 baud -- but it also means the CPU is free during rendering.
> - **No cycle-level border tricks.** The VDP handles display timing independently. You cannot create raster effects by timing `OUT` instructions, because the display pipeline is decoupled from the CPU clock.
>
> For a Spectrum programmer, the Agon feels freeing and frustrating in equal measure. The constraints that forced creative solutions on the Spectrum simply do not exist -- but neither do the direct-hardware tricks that those constraints enabled. You trade the puzzle for an API.

---

## Poniéndolo Todo Junto: Lo Que el Diseño de Pantalla Significa para el Código

Cada técnica en el resto de este libro está moldeada por el diseño de pantalla descrito en este capítulo. Aquí está por qué cada pieza importa:

**El dibujo de sprites** requiere calcular una dirección de pantalla para la posición del sprite, luego iterar hacia abajo a través de las filas del sprite. Cada fila significa `INC H` (7 de cada 8 veces) o el cruce completo de límite de caracteres. Un sprite de 16 píxeles de alto abarca exactamente 2 celdas de caracteres -- cruzarás un límite. Un sprite de 24 píxeles abarca 3 celdas, cruzando 2 límites. El coste del cruce de límites es un impuesto fijo sobre cada sprite.

**El borrado de pantalla** (Capítulo 3) usa el truco PUSH -- estableciendo SP en `$5800` y empujando datos hacia abajo a través del área de píxeles. El entrelazado no importa para el borrado porque cada byte obtiene el mismo valor. Pero para borrados *con patrón* (fondos rayados, rellenos de gradiente), el entrelazado significa que debes pensar cuidadosamente sobre qué filas obtienen qué datos.

**El desplazamiento** (Capítulo 17) es donde el diseño más duele. Desplazar la pantalla hacia arriba un píxel significa mover los 32 bytes de cada fila a la dirección de la fila de arriba. En un framebuffer lineal, esto es una gran copia de bloque. En el Spectrum, las direcciones de origen y destino para cada fila están relacionadas por la lógica DOWN_HL -- no por un desplazamiento fijo. Una rutina de desplazamiento debe navegar el entrelazado para cada fila que copia.

**Los efectos de atributos** (Capítulos 8--9) son donde el diseño ayuda. Como el área de atributos es lineal y pequeña (768 bytes), actualizar colores es rápido. Una actualización de atributos de pantalla completa con LDIR cuesta aproximadamente 16.000 T-states -- menos de un cuarto de fotograma. Por eso los efectos basados en atributos (túneles, plasmas, ciclo de colores) son un pilar del trabajo de demoscene del Spectrum.

---

## Resumen

- The Spectrum's 6,912-byte display consists of **6,144 bytes of pixel data** at `$4000`--`$57FF` and **768 bytes of attributes** at `$5800`--`$5AFF`.
- Pixel rows are **interleaved** by character cell: the address encodes y as `010 TT SSS` (high byte) and `LLL CCCCC` (low byte), where the bits of y are shuffled across the address.
- Moving **one pixel row down** within a character cell is just `INC H` (4 T-states). Crossing character and third boundaries requires additional logic.
- The classic **DOWN_HL** routine handles all cases but costs up to 65 T-states at boundaries. For full-screen iteration, **split-counter loops** (Introspec's approach) reduce total cost by 60% and eliminate timing jitter.
- Each attribute byte encodes **Flash, Bright, Paper, and Ink** in the format `FBPPPIII`. Only **two colours per 8x8 cell** -- this is the attribute clash.
- Attribute clash is not just a limitation but a **creative constraint** that defined the Spectrum's visual aesthetic and led to efficient attribute-only demo effects.
- The **border** colour is set by `OUT ($FE), A` (bits 0--2) and changes are visible on the next scanline, making it a **timing debug tool** and a canvas for demoscene raster effects.
- The **Agon Light 2** has no interleaved layout, no attribute clash, and no direct framebuffer access -- it replaces the puzzle with a VDP command API.

---

## Inténtalo Tú Mismo

1. **Mapea las direcciones.** Elige 10 coordenadas (x, y) aleatorias y calcula la dirección de pantalla a mano usando el diseño de bits `010TTSSS LLLCCCCC`. Luego escribe una pequeña rutina Z80 que dibuje un solo píxel en cada coordenada y verifica que tus cálculos coincidan.

2. **Visualiza el entrelazado.** Modifica `fill_screen.a80` para escribir diferentes valores en las primeras 8 filas. Escribe `$FF` (sólido) en la fila 0 y `$00` (vacío) en las filas 1--7. Como las filas 0--7 están en `$4000`, `$4100`, ..., `$4700`, necesitarás cambiar H para alcanzar cada fila. El resultado debería ser una sola línea brillante en la parte superior, con un espacio de 7 líneas vacías antes de la siguiente línea sólida en la fila 8.

3. **Mide DOWN_HL.** Usa la arnés de temporización de color de borde del Capítulo 1. Llama a la rutina clásica DOWN_HL 191 veces (para un recorrido completo de pantalla) y mide la franja. Luego implementa la versión con contadores divididos y compara. La versión con contadores divididos debería producir una franja visiblemente más corta.

4. **Pintor de atributos.** Escribe una rutina que llene el área de atributos con un gradiente: la columna 0 obtiene el color 0, la columna 1 obtiene el color 1, y así sucesivamente (ciclando del 0 al 7). Cada fila debería tener el mismo patrón. Luego modifícalo para que cada fila desplace el patrón una posición -- un arcoíris diagonal. Esta es la semilla de un efecto de demo basado en atributos.

5. **Franjas de borde.** Después de un `HALT`, ejecuta un bucle cerrado que cambie el color del borde en cada línea de escaneo durante 64 líneas. Usa los 8 colores de borde en secuencia (0, 1, 2, 3, 4, 5, 6, 7, repetir). Deberías ver franjas de arcoíris horizontales en el borde superior. Ajusta el retardo de temporización entre instrucciones `OUT` hasta que las franjas estén limpias y estables.

---

> **Sources:** Introspec "Eshchyo raz pro DOWN_HL" (Hype, 2020); Introspec "GO WEST Part 1" (Hype, 2015) for contended memory effects at screen addresses; Introspec "Making of Eager" (Hype, 2015) for attribute-based effect design; the Spectrum's ULA documentation for memory layout rationale; Art-top (personal communication, 2026) for the optimised UP_HL and fast pixel-to-attribute conversion.

*Siguiente: Capítulo 3 -- La Caja de Herramientas del Demoscener. Bucles desenrollados, código auto-modificable, la pila como tubería de datos, y las técnicas que te permiten hacer lo imposible dentro del presupuesto.*
