# Capítulo 7: Rotozoomer y Píxeles Chunky

> *"El truco es que no rotas la pantalla. Rotas tu recorrido a través de la textura."*
> -- parafraseando la idea central detrás de todo rotozoomer jamás escrito

---

Hay un momento en Illusion donde la pantalla se llena con un patrón -- una textura, monocromática, que se repite -- y entonces comienza a girar. La rotación es suave y continua, el zoom respira hacia adentro y hacia afuera, y todo funciona a un ritmo que te hace olvidar que estás viendo un Z80 empujando píxeles a 3,5 MHz. No es el efecto técnicamente más exigente de la demo. La esfera (Capítulo 6) es más difícil matemáticamente. El dotfield scroller (Capítulo 10) es más ajustado en su presupuesto de ciclos. Pero el rotozoomer es el que parece sin esfuerzo, y en el Spectrum, hacer que algo parezca sin esfuerzo es el truco más difícil de todos.

Este capítulo traza dos hilos. El primero es el análisis de Introspec de 2017 del rotozoomer de Illusion por X-Trade. El segundo es el artículo de sq de 2022 en Hype sobre la optimización de píxeles chunky, que lleva el enfoque a 4x4 píxeles y cataloga una familia de estrategias de renderizado con conteos de ciclos precisos. Juntos, mapean el espacio de diseño: cómo funcionan los píxeles chunky, cómo los usan los rotozoomers, y las compensaciones de rendimiento que determinan si tu efecto corre a 4 fotogramas por pantalla o 12.

---

## Qué Hace Realmente un Rotozoomer

Un rotozoomer muestra una textura 2D rotada por cierto ángulo y escalada por cierto factor. El enfoque ingenuo: para cada píxel de pantalla, calcular su coordenada de textura correspondiente mediante una rotación trigonométrica:

```text
    tx = sx * cos(theta) * scale  +  sy * sin(theta) * scale  +  offset_x
    ty = -sx * sin(theta) * scale  +  sy * cos(theta) * scale  +  offset_y
```

A 256x192, eso son 49.152 píxeles, cada uno necesitando dos multiplicaciones. Incluso con una multiplicación de tabla de cuadrados de 54 T-states (Capítulo 4), excedes cinco millones de T-states -- aproximadamente 70 fotogramas de tiempo de CPU. El efecto es matemáticamente trivial y computacionalmente imposible.

La idea clave es que la transformación es *lineal*. Moverse un píxel a la derecha en la pantalla siempre suma el mismo (dx, dy) a las coordenadas de textura. Moverse un píxel hacia abajo siempre suma el mismo (dx', dy'). El costo por píxel colapsa de dos multiplicaciones a dos sumas:

```text
Step right:   dx = cos(theta) * scale,   dy = -sin(theta) * scale
Step down:    dx' = sin(theta) * scale,  dy' = cos(theta) * scale
```

Comienza cada fila en la coordenada de textura correcta y avanza por (dx, dy) para cada píxel. El bucle interno se convierte en: leer el téxel, avanzar por (dx, dy), repetir. Dos sumas por píxel, ninguna multiplicación. La configuración por fotograma son cuatro multiplicaciones para calcular los vectores de paso a partir del ángulo y escala actuales. Todo lo demás se deduce de la linealidad.

Esta es la optimización fundamental detrás de todo rotozoomer en toda plataforma. En el Amiga, en el PC, en el Spectrum.

### Paso en Punto Fijo en el Z80

En una plataforma de 16 o 32 bits, dx y dy serían valores de punto fijo: la parte entera selecciona el téxel, y la parte fraccional acumula precisión sub-píxel. En el Z80, nos faltan los registros y el ancho de banda para bucles internos de punto fijo verdaderos. La solución clásica del Spectrum es colapsar el paso a incrementos enteros -- siempre exactamente +1, -1, o 0 por eje -- y controlar la *proporción* de pasos entre ejes para aproximar el ángulo.

Considera una rotación de 30 grados. El vector de paso exacto sería (cos 30, -sin 30) = (0,866, -0,5). En una máquina con aritmética de punto fijo, sumarías 0,866 a la coordenada de columna y restarías 0,5 de la coordenada de fila por píxel. En el Z80, el bucle interno en cambio alterna entre dos pasos enteros: algunos píxeles avanzan (+1 columna, 0 filas) y otros avanzan (+1 columna, -1 fila). Si distribuyes estos en una proporción aproximada de 2:1 -- dos pasos solo de columna por cada paso diagonal -- la dirección promedio aproxima la proporción 0,866:0,5 de un recorrido de 30 grados. Esto es el algoritmo de línea de Bresenham aplicado al recorrido de textura.

El factor de zoom determina cuántos téxeles saltas por píxel de pantalla. A escala 1,0, cada téxel se mapea a un píxel de pantalla. A escala 2,0, saltas cada otro téxel, haciendo zoom efectivamente. En el Spectrum, esto se controla duplicando las instrucciones de recorrido: en lugar de un `INC L` por píxel, ejecutas dos, avanzando 2 téxeles y produciendo un zoom 2x. Los niveles de zoom intermedios de nuevo usan distribución tipo Bresenham: algunos píxeles avanzan 1, otros 2, con la proporción controlada por un acumulador de error.

El coste por fotograma de computar estos parámetros es despreciable: cuatro consultas a una tabla de seno, unas pocas multiplicaciones (o consultas de tabla, ver Capítulo 4), y una pasada de configuración Bresenham. Todo el trabajo pesado está en el bucle interno, que se ha reducido a nada más que incrementos de registros y lecturas de memoria.

---

## Píxeles Chunky: Intercambiando Resolución por Velocidad

Incluso a dos sumas por píxel, escribir 6.144 bytes en la memoria de video entrelazada del Spectrum por fotograma es impráctico -- no si también quieres actualizar el ángulo y dejar tiempo para la música. Los píxeles chunky resuelven esto reduciendo la resolución efectiva. En lugar de un téxel por píxel de pantalla, mapeas un téxel a un bloque de 2x2, 4x4 u 8x8.

Illusion usa píxeles chunky de 2x2: resolución efectiva 128x96, una reducción de 4x en el trabajo. El efecto se ve pixelado de cerca, pero a la velocidad con que la textura barre la pantalla, el movimiento oculta la tosquedad. El ojo perdona la baja resolución cuando todo está en movimiento.

### Por Qué 2x2 Es el Punto Óptimo

La elección del tamaño de bloque implica un compromiso de tres vías: calidad visual, velocidad de renderizado y memoria. A 2x2, obtienes 128x96 píxeles efectivos -- suficiente para leer texto y reconocer patrones en la textura. A 4x4, la cuadrícula de 64x48 es notablemente más gruesa; los detalles finos en la textura se vuelven ilegibles, pero el efecto todavía "se lee" como una superficie rotante coherente. A 8x8, estás en 32x24 bloques, que es la resolución de la cuadrícula de atributos -- cualquier detalle de textura se pierde, y el efecto parece rectángulos coloreados. El último caso puede ser útil para efectos solo de color (túneles de atributos, Capítulo 9), pero para un rotozoomer renderizado por píxeles, 2x2 o 4x4 es el rango práctico.

El coste de memoria también importa. Cada píxel chunky almacena un byte, así que un rotozoomer 2x2 a 128x96 necesita 12.288 téxeles por fotograma. Con una fila de textura de 256 bytes (el ancho natural para envolvimiento de 8 bits), la textura en sí ocupa 256 bytes por fila multiplicado por cuantas filas necesites. Una versión 4x4 solo procesa 3.072 téxeles, lo que significa que el bucle interno se ejecuta una cuarta parte de las iteraciones -- pero el coste visual es significativo.

En la práctica, las demos del Spectrum usan 2x2 para efectos de rotozoomer destacados y reservan 4x4 para situaciones donde el rotozoomer comparte la pantalla con otros efectos (overlays de bumpmapping, composiciones de pantalla dividida).

### El Truco de Codificación $03

La codificación está diseñada para el bucle interno. Cada píxel chunky se almacena como `$03` (encendido) o `$00` (apagado). Este valor no es arbitrario -- codifica exactamente los dos bits bajos activados: `%00000011`. Observa qué sucede cuando cuatro píxeles se acumulan en el registro A:

```text
After pixel 1:  A = %00000011                  ($03)
After 2x shift: A = %00001100                  ($0C)
After pixel 2:  A = %00001100 + %00000011      ($0F)
After 2x shift: A = %00111100                  ($3C)
After pixel 3:  A = %00111100 + %00000011      ($3F)
After 2x shift: A = %11111100                  ($FC)
After pixel 4:  A = %11111100 + %00000011      ($FF)
```

Si los cuatro píxeles están "encendidos", el resultado es `$FF` -- todos los bits activados. Si los cuatro están "apagados" (`$00`), los desplazamientos y sumas producen `$00`. Los patrones mixtos producen la franja correcta de 2 bits por píxel: por ejemplo, encendido-apagado-encendido-apagado da `%11001100` = `$CC`. Cada par de bits en el byte de salida corresponde a un píxel chunky. Como cada píxel chunky tiene 2 píxeles de pantalla de ancho (2x2), el byte de salida de 8 bits cubre exactamente 8 píxeles de pantalla: cuatro columnas chunky por dos píxeles cada una.

La propiedad crítica: como solo sumamos `$03` o `$00`, no hay acarreo entre campos de píxeles. Los grupos de dos bits nunca desbordan uno en otro. Esto es lo que hace la codificación sin ramificaciones -- no se necesita enmascaramiento, sin operaciones OR, solo `ADD A,A` y `ADD A,(HL)`.

---

## El Bucle Interno de Illusion

El desensamblado de Introspec revela la secuencia central de renderizado. HL recorre la textura; H rastrea un eje y L el otro:

```z80 id:ch07_the_inner_loop_from_illusion
; Inner loop: combine 4 chunky pixels into one output byte
    ld   a,(hl)        ;  7T  -- read first chunky pixel ($03 or $00)
    inc  l             ;  4T  -- step right in texture
    dec  h             ;  4T  -- step up in texture
    add  a,a           ;  4T  -- shift left
    add  a,a           ;  4T  -- shift left (now shifted by 2)
    add  a,(hl)        ;  7T  -- add second chunky pixel
```

La secuencia se repite para el tercer y cuarto píxel. Los `inc l` y `dec h` juntos trazan un camino diagonal a través de la textura -- y diagonal significa rotado. La combinación específica de instrucciones de incremento y decremento determina el ángulo de rotación.

| Paso | Instrucciones | T-states |
|------|-------------|----------|
| Leer píxel 1 | `ld a,(hl)` | 7 |
| Caminar | `inc l : dec h` | 8 |
| Desplazar + Leer píxel 2 | `add a,a : add a,a : add a,(hl)` | 15 |
| Caminar | `inc l : dec h` | 8 |
| Desplazar + Leer píxel 3 | `add a,a : add a,a : add a,(hl)` | 15 |
| Caminar | `inc l : dec h` | 8 |
| Desplazar + Leer píxel 4 | `add a,a : add a,a : add a,(hl)` | 15 |
| Caminar | `inc l : dec h` | 8 |
| Salida + avance | `ld (de),a : inc e` | ~11 |
| **Total por byte** | | **~95** |

Introspec midió aproximadamente 95 T-states por 4 chunks.

La observación crítica: la dirección de caminata está codificada directamente en el flujo de instrucciones. Un ángulo de rotación diferente requiere instrucciones diferentes. Ocho direcciones primarias son posibles usando combinaciones de `inc l`, `dec l`, `inc h`, `dec h` y `nop`. Esto significa que el código de renderizado cambia cada fotograma.

### Código Auto-Modificable a Nivel de Byte

"Generación de código por fotograma" suena exótico, pero el mecanismo es mundano. Cada instrucción de recorrido es un solo byte en memoria. `INC L` es el código de operación `$2C`. `DEC L` es `$2D`. `INC H` es `$24`. `DEC H` es `$25`. `NOP` es `$00`. Para cambiar la dirección de recorrido de "derecha y arriba" (`INC L` + `DEC H`) a "pura derecha" (`INC L` + `NOP`), escribes `$00` al byte donde `$25` reside actualmente. Ese es todo el paso de generación de código: `LD A,$00 : LD (walk_target),A`. Unas pocas escrituras en el flujo de instrucciones, y el bucle interno ahora recorre en una dirección diferente.

Los objetivos se conocen en tiempo de ensamblado. Cada sitio SMC tiene etiqueta (ej., `.smc_walk_h_0:`) y el código de parcheado usa esas etiquetas como direcciones literales. No hay asignación dinámica de memoria, ni análisis de instrucciones, ni desensamblado en tiempo de ejecución. Estás escribiendo códigos de operación conocidos en direcciones conocidas. El Z80 no tiene caché de instrucciones que invalidar, ni tubería que vaciar. La escritura toma efecto inmediatamente en la siguiente búsqueda desde esa dirección.

En un bucle interno completamente desenrollado (que Illusion usa para sus filas de 16 bytes), habría 64 sitios de instrucción de recorrido a parchear: 4 pares de recorrido por byte de salida multiplicado por 16 bytes por fila. Parchear 64 bytes cuesta aproximadamente 64 x 13 = 832 T-states (cada `LD (nn),A` son 13 T-states), lo cual es despreciable comparado con los más de 100.000 T-states que toma la pasada de renderizado. El generador de código es barato. El código generado es lo que importa.

---

## Generación de Código por Fotograma

El código de renderizado se genera fresco en cada fotograma, con instrucciones de dirección parcheadas para el ángulo actual:

| Rango de ángulo | Paso H | Paso L | Dirección |
|-------------|--------|--------|-----------|
| ~0 grados | `nop` | `inc l` | Pura derecha |
| ~45 grados | `dec h` | `inc l` | Derecha y arriba |
| ~90 grados | `dec h` | `nop` | Pura arriba |
| ~135 grados | `dec h` | `dec l` | Izquierda y arriba |
| ~180 grados | `nop` | `dec l` | Pura izquierda |
| ~225 grados | `inc h` | `dec l` | Izquierda y abajo |
| ~270 grados | `inc h` | `nop` | Pura abajo |
| ~315 grados | `inc h` | `inc l` | Derecha y abajo |

Para ángulos intermedios, el generador distribuye los pasos de manera desigual usando una acumulación de error tipo Bresenham. Una rotación de 30 grados alterna entre `inc l : nop` e `inc l : dec h` a una proporción aproximada de 2:1, aproximando la tangente de 1,73:1 de 30 grados. El código resultante es un bucle desenrollado donde cada iteración tiene su propio par de caminata específico, ajustado al ángulo actual.

El coste de renderizado para 128x96 a 2x2 chunky. El área de 128x96 tiene 96 filas de píxeles, pero cada téxel 2x2 cubre dos filas de píxeles, dando 48 filas de téxeles. Cada fila de téxeles produce 16 bytes de salida (128 píxeles / 8 bits por byte, con 4 píxeles chunky empaquetados por byte):

```text
16 output bytes/row x 95 T-states = 1,520 T-states/row
1,520 x 48 texel rows = 72,960 T-states total
```

Aproximadamente 1 fotograma en un Pentagon (71.680 T-states por fotograma). Pero esto es solo el bucle interno puro. Una contabilidad completa añade:

```text
Code generation:        ~  1,000 T  (patching walk instructions)
Row setup (per row):    ~    800 T  (48 rows x ~17 T each)
Buffer-to-screen copy:  ~ 20,000 T  (stack trick, 1,536 bytes)
Sine table lookups:     ~    200 T
Frame overhead:         ~    500 T  (HALT, border, angle update)
                        ----------
Inner loop:               72,960 T
Total per frame:        ~ 95,460 T  (= 1.33 Pentagon frames)
```

En un Spectrum estándar 48K/128K a 69.888 T-states por fotograma, el renderizado toma aproximadamente 1,4 fotogramas. La estimación de Introspec de 4-6 fotogramas por pantalla tiene en cuenta la ruta de código más compleja en Illusion (que maneja la pantalla completa de 256x192, no solo una franja de 128x96) y el coste del motor de música ejecutándose en la interrupción. En un Pentagon con su fotograma ligeramente más largo (71.680 T-states) y sin contención, el bucle interno se ejecuta aproximadamente un 3% más rápido.

La contención de memoria en el Spectrum 48K/128K añade otro coste oculto. Durante las 192 líneas de escaneo superiores, la ULA roba ciclos a la CPU al acceder a los 16KB inferiores de RAM ($4000-$7FFF). El bucle interno lee de la textura (que debería estar por encima de $8000, fuera de la memoria contendida) y escribe a un búfer (también por encima de $8000), así que evita la contención completamente. La transferencia del búfer a pantalla, sin embargo, escribe directamente a la RAM de vídeo y será ralentizada por la contención si se solapa con el período de visualización. Por eso las demos sincronizan la transferencia de pantalla al período de borde o a la parte inferior de la visualización.

---

## Transferencia de Búfer a Pantalla

El rotozoomer renderiza en un búfer fuera de pantalla, luego lo transfiere a la memoria de video. La disposición de pantalla entrelazada hace que el renderizado directo sea doloroso, y el búfer evita el tearing.

La transferencia usa la pila:

```z80 id:ch07_buffer_to_screen_transfer
    pop  hl                   ; 10T -- read 2 bytes from buffer
    ld   (screen_addr),hl     ; 16T -- write 2 bytes to screen
```

Las direcciones de pantalla están incrustadas como operandos literales, precalculadas para el entrelazado del Spectrum -- otra instancia de generación de código. A 26 T-states por dos bytes, una transferencia completa de 1.536 bytes cuesta menos de 20.000 T-states. El paso de renderizado es el cuello de botella, no la transferencia.

---

## Inmersión Profunda: Píxeles Chunky 4x4 (sq, Hype 2022)

El artículo de sq lleva los píxeles chunky a 4x4 -- resolución efectiva 64x48. El resultado visual es más tosco, pero la ganancia de rendimiento abre efectos como bumpmapping y renderizado entrelazado. El artículo es un estudio en metodología de optimización: empieza directo, mejora iterativamente, mide en cada paso.

**Enfoque 1: LD/INC básico (101 T-states por par).** Carga valor chunky, escribe al búfer, avanza punteros. El cuello de botella es la gestión de punteros: `INC HL` a 6 T-states se acumula a lo largo de miles de iteraciones.

**Enfoque 2: Variante LDI (104 T-states -- ¡más lento!).** `LDI` copia un byte e incrementa automáticamente ambos punteros en una instrucción. Pero también decrementa BC, consumiendo un par de registros. La sobrecarga de guardar/restaurar lo hace *más lento* que el enfoque ingenuo. Una historia con moraleja: en el Z80, la instrucción "inteligente" no siempre es la rápida.

**Enfoque 3: LDD doble byte (80 T-states por par).** Organizando origen y destino en orden inverso, el auto-decremento de `LDD` trabaja a tu favor. Una secuencia combinada de dos bytes explota esto para una mejora del 21% sobre la línea base.

**Enfoque 4: Código auto-modificable (76-78 T-states por par).** Pre-generar 256 procedimientos de renderizado, uno por cada posible valor de byte, cada uno con el valor del píxel incorporado como operando inmediato:

```z80 id:ch07_deep_dive_4x4_chunky_pixels
; One of 256 pre-generated procedures
proc_A5:
    ld   (hl),$A5        ; 10T  -- value baked into instruction
    inc  l               ;  4T
    ld   (hl),$A5        ; 10T  -- 4x4 block spans 2 bytes horizontally
    ; ... handle vertical repetition ...
    ret                  ; 10T
```

Los 256 procedimientos ocupan aproximadamente 3KB. El renderizado por píxel cae a 76-78 T-states -- 23% más rápido que la línea base, 27% más rápido que LDI.

### Comparación de Rendimiento

| Enfoque | Ciclos/par | Relativo | Memoria |
|----------|------------|----------|--------|
| LD/INC básico | 101 | 1,00x | Mínima |
| Variante LDI | 104 | 0,97x | Mínima |
| LDD doble byte | 80 | 1,26x | Mínima |
| Auto-modificable (256 procs) | 76-78 | 1,30x | ~3KB |

El enfoque auto-modificable gana, pero el margen sobre LDD es estrecho. En una demo de 128K, 3KB están fácilmente disponibles. En una producción de 48K, el enfoque LDD podría ser la mejor decisión de ingeniería.

### Raíces Históricas: Born Dead #05 y el Linaje de la Escena

sq señala que estas técnicas se construyen sobre trabajo publicado en Born Dead #05, un periódico de demoscene ruso de aproximadamente 2001. Born Dead era una de varias revistas de disco en ruso que servían como publicaciones técnicas para la demoscene del ZX Spectrum. A diferencia de las publicaciones de la demoscene de PC occidental que podían asumir hardware de clase 486, las revistas del Spectrum operaban bajo las restricciones de una comunidad que aún desarrollaba activamente nuevas técnicas para una máquina de 1982. El artículo fundacional describía el renderizado chunky básico -- la idea de que podías tratar la pantalla bitmap del Spectrum como un búfer de píxeles chunky de menor resolución y ganar velocidad a expensas de la resolución.

La contribución de sq, veintiún años después, fue la optimización sistemática y la variante de procedimientos pre-generados. Pero entre Born Dead #05 y el artículo de sq de 2022, el rotozoomer chunky apareció en numerosas demos del Spectrum. *Illusion* de X-Trade (ENLiGHT'96) fue una de las primeras implementaciones completas. Otros ejemplos notables incluyen GOA4K y Refresh de Exploder^XTM, las producciones de 4D, y trabajos posteriores de las escenas rusa y polaca. La técnica se difundió parcialmente a través del desensamblado -- el análisis de Introspec de Illusion en 2017 es en sí mismo un ejemplo de la tradición de la escena de aprender mediante ingeniería inversa -- y parcialmente a través de la red informal de conocimiento de revistas de disco, publicaciones en BBS, y comunicación directa entre programadores.

Así es como evoluciona el conocimiento de la escena: una técnica aparece en una revista de disco oscura, circula dentro de la comunidad, y veintiún años después alguien la revisita con mediciones frescas y trucos nuevos. La cadena desde Born Dead hasta sq hasta este capítulo es ininterrumpida.

---

## Práctico: Construyendo un Rotozoomer Simple

Aquí está la estructura para un rotozoomer funcional con píxeles chunky 2x2 y una textura de tablero de ajedrez.

**Textura.** Una tabla de 256 bytes alineada a página donde cada byte es `$03` o `$00`, generando franjas de 8 píxeles de ancho. El registro H proporciona la segunda dimensión; hacer XOR de H en la consulta crea un tablero de ajedrez completo:

```lua id:ch07_practical_building_a_simple
    ALIGN 256
texture:
    LUA ALLPASS
    for i = 0, 255 do
        if math.floor(i / 8) % 2 == 0 then
            sj.add_byte(0x03)
        else
            sj.add_byte(0x00)
        end
    end
    ENDLUA
```

**Tabla de senos y configuración por fotograma.** Una tabla de senos de 256 entradas alineada a página controla la rotación. Cada fotograma lee `sin(frame_counter)` y `cos(frame_counter)` (coseno mediante un desplazamiento de índice de 64) para calcular los vectores de paso, luego parchea las instrucciones de caminata del bucle interno con los opcodes correctos.

**El bucle de renderizado.** El bucle externo establece la coordenada de textura inicial para cada fila (avanzando perpendicular a la dirección de caminata). El bucle interno recorre la textura:

```z80 id:ch07_practical_building_a_simple_2
.byte_loop:
    ld   a,(hl)              ; read texel 1
    inc  l                   ; walk (patched per-frame)
    add  a,a : add  a,a     ; shift
    add  a,(hl)              ; read texel 2
    inc  l                   ; walk
    add  a,a : add  a,a     ; shift
    add  a,(hl)              ; read texel 3
    inc  l                   ; walk
    add  a,a : add  a,a     ; shift
    add  a,(hl)              ; read texel 4
    inc  l                   ; walk
    ld   (de),a              ; write output byte
    inc  de
    djnz .byte_loop
```

Las instrucciones `inc l` son los objetivos del generador de código. Antes de cada fotograma, se parchan a la combinación apropiada de `inc l`/`dec l`/`inc h`/`dec h`/`nop` basada en el ángulo actual. Para ángulos no cardinales, un acumulador de error de Bresenham distribuye los pasos del eje menor a lo largo de la fila, así que cada instrucción de caminata en el bucle desenrollado puede ser diferente de sus vecinas.

![Salida del rotozoomer — la textura rota y escala en tiempo real, renderizada con píxeles chunky de 2x2](../../build/screenshots/ch07_rotozoomer.png)

**Bucle principal.** `HALT` para vsync, calcular vectores de paso, generar código de caminata, renderizar al búfer, copiar búfer a pantalla via pila, incrementar contador de fotograma, repetir.

---

## Diseño de Textura y Manejo de Límites

La textura es la estructura de datos más restringida del rotozoomer. Cada decisión de diseño en el bucle interno -- la alineación a página, el comportamiento de envolvimiento, el dimensionado en potencias de dos -- se remonta a cómo la textura está dispuesta en memoria.

### Por Qué Alineada a Página, Por Qué 256 Columnas

La textura está alineada a página de modo que H selecciona la fila y L selecciona la columna. Esto no es meramente conveniente; hace posible el bucle interno. `INC L` y `DEC L` envuelven automáticamente en el límite de página de 256 bytes -- cuando L desborda de `$FF` a `$00`, H no cambia. La textura envuelve horizontalmente gratis, con cero sobrecarga de ramificación. Si la textura no estuviera alineada a página, los incrementos de L acarrearían a H, corrompiendo la dirección de fila. Necesitarías enmascaramiento explícito (`AND $3F` después de cada paso), lo que añadiría 4-8 T-states por píxel y destruiría el bucle interno ajustado.

El eje vertical (H) también envuelve, pero sobre el rango completo de filas asignadas a la textura. Si asignas 64 filas (páginas), H va desde la página base de la textura hasta base+63. `INC H` y `DEC H` recorrerán felizmente más allá del final de la textura hacia cualquier memoria que siga. Illusion maneja esto enmascarando H a la altura de la textura al inicio de cada fila (no por píxel -- el enmascaramiento por píxel sería demasiado caro). Esto funciona porque dentro de una sola fila de 16 bytes, la coordenada H cambia como máximo 16 pasos, y si la textura es suficientemente alta en relación al ancho de la fila, un desbordamiento dentro de una fila no puede alcanzar memoria que produzca basura visual. Una textura de 64 filas con 16 pasos de H por fila tiene un margen cómodo.

### Eligiendo el Tamaño de Textura

La textura debe ser potencia de dos en ancho (siempre 256, ya que L es de 8 bits) e idealmente potencia de dos en altura para enmascaramiento fácil. Opciones comunes:

- **256x256** (64KB): llena toda la RAM superior en un Spectrum de 128K. Máxima resolución, pero no deja espacio para código ni búferes.
- **256x64** (16KB): la opción práctica. Cabe en un banco de 16KB en hardware de 128K. La máscara de altura de 6 bits (`AND $3F`) es rápida y tesela sin costuras.
- **256x32** (8KB): cabe en un Spectrum de 48K con espacio para todo lo demás. La textura se repite más visiblemente, pero para un patrón de tablero de ajedrez o franjas, la repetición *es* el diseño.
- **256x16** (4KB): mínimo. Funciona para patrones muy simples como franjas de un solo eje.

Para texturas no repetitivas (imágenes, logos), la altura debería ser al menos tan grande como la altura de pantalla efectiva dividida por el factor de escala. Un rotozoomer 2x2 con 96 filas efectivas necesita al menos 96 filas de textura para evitar teselado visible cuando el zoom está en 1:1. En niveles de zoom más altos, se necesitan menos filas porque la cámara está "más cerca" de la superficie de la textura.

### ¿Y los Límites de Pantalla?

La pantalla del Spectrum de 256x192 tiene 32 bytes de ancho por 192 líneas. Si tu rotozoomer llena una franja de 128x96 en el centro, nunca te acercas al borde de la memoria de vídeo. Pero un rotozoomer de pantalla completa a 256x192 (o incluso 128x192 con chunky 2x2) debe manejar el caso donde la dirección de salida alcanza el área de atributos en `$5800`. El enfoque más simple: renderizar en un búfer y solo copiar la porción que cabe. Un enfoque más agresivo: recortar el conteo de filas al área visible durante la generación de código, lo que evita computación desperdiciada pero añade complejidad al bucle de filas.

En la práctica, la mayoría de los rotozoomers del Spectrum renderizan una franja más pequeña que la pantalla completa. El enmarcado visual -- un borde, una barra de título, un crédito de música -- oculta el recorte y recupera T-states para otros efectos.

---

## El Espacio de Diseño

El tamaño de píxel chunky es la decisión de diseño más trascendental en un rotozoomer:

| Parámetro | 2x2 (Illusion) | 4x4 (sq) | 8x8 (atributos) |
|-----------|----------------|----------|-------------------|
| Resolución | 128x96 | 64x48 | 32x24 |
| Téxeles/fotograma | 12.288 | 3.072 | 768 |
| Coste del bucle interno | ~73.000 T | ~29.000 T | ~7.300 T |
| Fotogramas/pantalla | ~1,3 | ~0,5 | ~0,1 |
| Calidad visual | Buen movimiento | Chunky pero rápido | Muy pixelado |
| Caso de uso | Efectos destacados | Bumpmapping, overlays | FX solo atributos |

La versión 4x4 cabe dentro de un solo fotograma con espacio para un motor de música y otros efectos. La versión 2x2 toma aproximadamente 1,3-1,5 fotogramas (incluyendo sobrecarga) pero se ve sustancialmente mejor. El caso 8x8 es el túnel de atributos del Capítulo 9.

Una vez que tienes un renderizador chunky rápido, el rotozoomer es solo una aplicación. El mismo motor impulsa **bumpmapping** (leer diferencias de altura en lugar de téxeles crudos, derivar sombreado), **efectos entrelazados** (renderizar filas pares/impares en fotogramas alternos, duplicando la tasa de fotogramas efectiva a costa de parpadeo), y **distorsión de texturas** (variar la dirección de caminata por fila para efectos ondulados o de ondulación). Un rotozoomer 4x4 puede compartir un fotograma con un scrolltext, un motor de música y una transferencia de pantalla. El trabajo de sq fue motivado exactamente por esta versatilidad.

---

## Tres Enfoques para la Rotación de Textura

Todo lo anterior trata al rotozoomer como una técnica con un tamaño de bloque ajustable. Pero "rotozoomer" en el Spectrum es realmente una familia de tres enfoques distintos, cada uno con diferentes bucles internos, diferente carácter visual y diferentes perfiles de rendimiento. Comparten la misma base matemática -- los vectores de paso lineales, la distribución de ángulos estilo Bresenham -- pero divergen completamente a nivel de renderizado.

### Variante 1: Bitmap Monocromo (Resolución de Píxel Completa)

La forma más pura: cada píxel de pantalla se mapea a un téxel. La textura es monocroma -- un bit por píxel -- así que leer un téxel significa probar un solo bit, y escribir a la pantalla significa activar o desactivar un solo bit. Sin codificación chunky, sin agrupación de bloques. El resultado es una textura rotada a la resolución completa de 256x192 de la pantalla del Spectrum.

El esqueleto del bucle interno se ve algo así:

```z80 id:ch07_variant_1_monochrome_bitmap
; For each screen pixel:
; DE = texture pointer, HL = screen pointer
    ld   a,(de)           ;  7T  -- read texture byte
    and  n                ;  7T  -- test texture bit at current coords
    jr   z,.pixel_off     ; 12/7T
    set  m,(hl)           ; 15T  -- set screen bit
    jr   .pixel_done      ; 12T
.pixel_off:
    res  m,(hl)           ; 15T  -- clear screen bit
.pixel_done:
    ; advance texture coords (inc e / dec d / etc.)
    ; advance screen bit position
    ; ... next pixel
```

Nota que SET y RES solo funcionan con (HL), (IX+d), o (IY+d) -- no (DE) o (BC). Esto obliga a HL a servir como puntero de pantalla, mientras DE maneja las coordenadas de textura.

El coste por píxel es brutal: 35-45 T-states mínimo, con ramificación en cada píxel. A través de 49.152 píxeles, eso es 1,5 a 2 millones de T-states solo para la pasada de renderizado -- aproximadamente 21-28 fotogramas en un Spectrum estándar. Un rotozoomer monocromo de pantalla completa a 50fps no va a suceder.

Pero nadie dijo que necesitas llenar toda la pantalla. La técnica brilla cuando se aplica a una región más pequeña -- una franja de 128x64, un viewport circular, un área enmascarada -- o cuando aceptas una tasa de fotogramas más baja a cambio del impacto visual de la rotación a resolución completa. También funciona maravillosamente para efectos de distorsión donde la "rotación" no es uniforme: variar los vectores de paso por línea de escaneo produce distorsiones de onda, efectos de barril, y el aspecto de "onda sónica" visto en partes de Illusion por Dark/X-Trade. El mapeo de coordenadas ya no es una simple rotación sino una deformación por línea a través de la textura. Las matemáticas son las mismas -- paso en punto fijo a lo largo de una dirección -- pero la dirección en sí cambia cada fila.

La recompensa visual es impactante. Donde un rotozoomer chunky 2x2 parece un mosaico rotante, la versión de bitmap monocromo parece una *imagen* rotante. En una máquina donde cada efecto lucha contra el mismo presupuesto de 69.888 T-states, dedicar múltiples fotogramas al renderizado a resolución completa es una elección estética deliberada.

### Variante 2: Rotozoomer Chunky (Bloques 2x2 o 4x4)

Esta es la técnica cubierta en la mayor parte de este capítulo. Cada bloque de pantalla (2x2 o 4x4 píxeles) se mapea a un téxel. La codificación `$03`/`$00`, la acumulación `add a,a : add a,(hl)`, el parcheado de instrucciones de recorrido -- todo apunta a este enfoque.

A 2x2 (128x96 de resolución efectiva), el bucle interno se ejecuta a aproximadamente 95 T-states por byte de salida, produciendo el rotozoomer suave y reconocible visto en Illusion. A 4x4 (64x48), la variante de procedimientos pre-generados de sq elimina la sobrecarga del bucle completamente, reduciendo el coste a 76-78 T-states por par de salida y dejando espacio para composiciones multi-efecto dentro de un solo fotograma.

El rotozoomer chunky ocupa el terreno medio: lo suficientemente rápido para tiempo real, lo suficientemente detallado para llevar un efecto destacado. Es el caballo de batalla del repertorio de rotozoomers del Spectrum.

### Variante 3: Rotozoomer de Atributos ("Píxeles" de Bloques 8x8)

El área de atributos del Spectrum en `$5800`-`$5AFF` almacena información de color para cada celda de caracteres de 8x8 píxeles: 32 columnas por 24 filas, 768 bytes en total. Cada byte codifica tinta, papel, brillo y parpadeo para un solo bloque de 8x8. El rotozoomer de atributos ignora el bitmap completamente y trata estas 768 celdas de atributos como la superficie de visualización. Cada celda se convierte en un "píxel" en una imagen de 32x24.

El bucle interno es estructuralmente idéntico a la versión chunky -- recorrer coordenadas de textura, leer un valor, escribirlo a la salida -- pero la salida es el área de atributos, y el valor de "téxel" es un byte de atributo de color en lugar de un patrón de bits. La resolución efectiva es solo 32x24, lo que significa que la pasada de renderizado completa tiene 768 iteraciones del bucle de paso.

Las matemáticas:

```text
32 columns x 24 rows = 768 attribute cells
~10 T-states per cell (read texel + write attribute + step)
768 x 10 = ~7,680 T-states total
```

Eso es aproximadamente el 11% de un solo fotograma. Podrías ejecutar el rotozoomer de atributos nueve veces y aún tener espacio para un motor de música. El coste es tan bajo que el efecto es esencialmente gratis.

Pero la recompensa visual es diferente de las variantes de bitmap. No estás rotando píxeles -- estás rotando bloques de color. A 32x24, los detalles finos son invisibles. Lo que obtienes en cambio es un campo amplio de color, un mosaico vívido que gira y respira. El rotozoomer de atributos en Illusion usa exactamente esto: una textura de colores llamativos (no un bitmap monocromo) mapeada a través de la cuadrícula de atributos, produciendo el aspecto característico de "vitral" de campos de color rotantes por el que Illusion es conocida. Los campos de papel y tinta en cada byte de atributo te dan dos colores por celda, así que una textura cuidadosamente diseñada puede empaquetar más información visual de lo que la resolución bruta sugiere.

El rotozoomer de atributos es perfecto para fondos, transiciones, o como capa base con efectos a nivel de píxel compuestos encima. Como solo escribe al área de atributos, el bitmap puede usarse simultáneamente para un efecto diferente -- un scroller, un logo, un campo de partículas -- ejecutándose a su propio ritmo. Este enfoque por capas es una marca distintiva de las pantallas multi-efecto de demos del Spectrum.

### Comparación

| Variante | Resolución efectiva | Bytes escritos/fotograma | ~T-states (renderizado) | Color | Uso típico |
|---------|---------------------|--------------------|--------------------|--------|-------------|
| Bitmap monocromo | 256x192 (o subregión) | 6.144 (pantalla completa) | 1.500.000-2.000.000 | 1 bit | Efecto estrella, distorsión, deformación |
| Chunky 2x2 | 128x96 | 1.536 | ~73.000 | 1 bit | Rotozoomer destacado |
| Chunky 4x4 | 64x48 | 384 | ~29.000 | 1 bit | Multi-efecto, overlay |
| Atributos | 32x24 | 768 | ~7.700 | Tinta+Papel (2 colores/celda) | Fondo, lavado de color, transición |

La progresión de arriba a abajo es un intercambio suave: resolución por velocidad, detalle por margen de maniobra. El bitmap monocromo te da todo lo que la pantalla del Spectrum puede mostrar, a un coste que demanda dedicación. La versión de atributos te da casi nada en resolución, pero se ejecuta tan rápido que el rotozoomer se convierte en solo otro instrumento en una composición multi-efecto en lugar del evento principal.

Las cuatro filas de esta tabla comparten el mismo algoritmo central. Los vectores de paso se computan de la misma manera. La distribución de Bresenham funciona de la misma manera. La diferencia es solo dónde escribes y cuántas iteraciones ejecutas. Una vez que has construido un rotozoomer, los has construido todos.

---

## El Rotozoomer en Contexto

El rotozoomer no es un algoritmo de rotación. Es un *patrón de recorrido de memoria*. Caminas a través de un búfer en línea recta, y la dirección de caminata determina lo que ves. La rotación es una elección de dirección. El zoom es una elección de tamaño de paso. El Z80 no sabe trigonometría. Sabe `INC L` y `DEC H`. Todo lo demás es la interpretación del programador.

En Illusion, el rotozoomer se encuentra junto a la esfera y el dotfield scroller. Los tres comparten la misma arquitectura: parámetros precalculados, bucles internos generados, acceso secuencial a memoria. La esfera usa tablas de salto y conteos variables de `INC L`. El rotozoomer usa instrucciones de caminata parcheadas por dirección. El dotfield usa tablas de direcciones basadas en pila. Tres efectos, una filosofía de motor.

Dark construyó todos ellos. Introspec trazó todos ellos. El patrón que los conecta es la lección de la Parte II: calcula lo que necesitas antes de que comience el bucle interno, genera código que no haga nada más que leer-desplazar-escribir, y mantén el acceso a memoria secuencial.

---

## Resumen

- Un rotozoomer muestra una textura rotada y con zoom recorriéndola en ángulo. La linealidad reduce el costo por píxel de dos multiplicaciones a dos sumas.
- Los píxeles chunky (2x2, 4x4) reducen la resolución efectiva y el costo de renderizado proporcionalmente. Illusion usa 2x2 a 128x96; el sistema de sq usa 4x4 a 64x48.
- El bucle interno de Illusion: `ld a,(hl) : add a,a : add a,a : add a,(hl)` con instrucciones de caminata entre lecturas. Costo: ~95 T-states por byte para 4 píxeles chunky.
- La dirección de caminata cambia por fotograma, requiriendo generación de código -- el bucle de renderizado se parchea antes de cada fotograma.
- El recorrido de optimización 4x4 de sq: LD/INC básico (101 T-states) a LDI (104 T-states, más lento) a LDD (80 T-states) a código auto-modificable con 256 procedimientos pre-generados (76-78 T-states, ~3KB). Basado en trabajo anterior en Born Dead #05 (~2001).
- Transferencia de búfer a pantalla via `pop hl : ld (nn),hl` a ~26 T-states por dos bytes.
- El rotozoomer comparte su arquitectura con la esfera (Capítulo 6) y el dotfield (Capítulo 10): parámetros precalculados, bucles internos generados, acceso secuencial a memoria.

---

> **Fuentes:** Introspec, "Technical Analysis of Illusion by X-Trade" (Hype, 2017); sq, "Chunky Effects on ZX Spectrum" (Hype, 2022); Born Dead #05 (~2001, técnicas originales de píxeles chunky).
