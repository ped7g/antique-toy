# Capítulo 10: El Dotfield Scroller y Color de 4 Fases

> *"Dos fotogramas normales y dos fotogramas invertidos. El ojo ve el promedio."*
> -- Introspec, Making of Eager (2015)

---

El ZX Spectrum muestra dos colores por celda de 8x8. El texto se desplaza por una pantalla a la velocidad que la CPU pueda manejar. Estas son restricciones fijas -- el hardware hace lo que hace, y ninguna cantidad de ingenio cambiará el silicio.

Pero el ingenio puede cambiar lo que el espectador *percibe*.

Este capítulo reúne dos técnicas de dos demos diferentes, separadas por casi veinte años pero conectadas por un principio compartido. El dotfield scroller de *Illusion* de X-Trade (ENLiGHT'96) renderiza texto como una nube rebotante de puntos individuales, cada uno colocado a un costo de solo 36 T-states. La animación de color de 4 fases de *Eager* de Introspec (3BM Open Air 2015) alterna cuatro fotogramas cuidadosamente construidos a 50Hz para engañar al ojo haciéndole ver colores que el hardware no puede producir. Uno explota la resolución espacial -- colocando puntos donde quieras, sin restricción de celdas de caracteres. El otro explota la resolución temporal -- ciclando fotogramas más rápido de lo que el ojo puede seguir. Juntos demuestran los dos ejes principales de hacer trampa en hardware con restricciones: espacio y tiempo.

---

## Parte 1: El Dotfield Scroller

### Lo Que Ve el Espectador

Imagina un mensaje -- "ILLUSION BY X-TRADE" -- renderizado no en caracteres de bloque sólidos sino como un campo de puntos individuales, cada punto un solo píxel. El texto se desliza horizontalmente por la pantalla en un desplazamiento suave. Pero los puntos no están sentados en líneas de escaneo planas. Rebotan. Todo el campo de puntos ondula en una onda sinusoidal, cada columna desplazada verticalmente de sus vecinas, creando la impresión de texto ondulando sobre la superficie del agua.

### La Fuente como Textura

La fuente se almacena como una textura de bitmap en memoria -- un bit por punto. Si el bit es 1, un punto aparece en pantalla. Si el bit es 0, nada sucede. La palabra crítica es *transparente*. En un renderizador normal, escribes cada posición de píxel. En el dotfield scroller, los píxeles transparentes son casi gratis. Verificas el bit, y si es cero, lo saltas. Solo los píxeles encendidos requieren una escritura a la memoria de video.

Esto significa que el costo de renderizado es proporcional al número de puntos visibles, no al área total. Un carácter típico de 8x8 podría tener 20 píxeles encendidos de 64. Para un mensaje de desplazamiento grande, esta economía importa enormemente. BC apunta a los datos de fuente; RLA desplaza cada bit a la bandera de acarreo para determinar encendido o apagado.

![Prototipo de scroller de campo de puntos — cada carácter renderizado como píxeles individuales rebotando sobre una onda sinusoidal, produciendo el clásico efecto de texto de la demoscene](../../build/screenshots/proto_ch10_dotfield.png)

### Tablas de Direcciones Basadas en Pila

En un scroller convencional, la posición de pantalla de cada píxel se calcula a partir de coordenadas (x, y) usando la fórmula de dirección entrelazada del Spectrum. Ese cálculo involucra desplazamientos, máscaras y consultas. Hacerlo para miles de píxeles por fotograma consumiría todo el presupuesto.

La solución de Dark: precalcular cada dirección de pantalla y almacenarlas como una tabla que el puntero de pila recorre. POP lee 2 bytes y auto-incrementa SP, todo en 10 T-states. Apunta SP a la tabla en lugar de la pila real, y POP se convierte en la recuperación de direcciones más rápida posible -- sin registros de índice, sin aritmética de punteros, sin sobrecarga.

Compara POP con las alternativas. `LD A,(HL) : INC HL` obtiene un byte en 11 T-states -- necesitarías dos de esos pares (22 T) para obtener una dirección, más la contabilidad de `LD L,A / LD H,A`. Una carga indexada como `LD L,(IX+0) : LD H,(IX+1)` cuesta 38 T-states por el par. POP obtiene ambos bytes, incrementa el puntero, y carga un par de registros -- 10 T-states, sin competencia. El precio es que entregas el puntero de pila al renderizador. Nada más puede usar SP mientras el bucle interno se ejecuta.

Esto significa que las interrupciones son fatales. Si una interrupción se dispara mientras SP apunta a la tabla de direcciones, el Z80 empuja la dirección de retorno a la "pila" -- que en realidad es tu tabla de datos. Dos bytes de direcciones de pantalla cuidadosamente computadas se sobrescriben con una dirección de retorno, y la rutina de servicio de interrupción procede a ejecutar cualquier basura que haya en la ubicación corrompida. El resultado es cualquier cosa desde un fotograma distorsionado hasta un cuelgue total. La solución es simple y no negociable: `DI` antes de secuestrar SP, `EI` después de restaurarlo. Toda rutina con truco POP en toda demo del Spectrum sigue este patrón:

```z80 id:ch10_stack_based_address_tables
    di
    ld   (.smc_sp+1), sp  ; save SP via self-modifying code
    ld   sp, table_addr    ; point SP at pre-computed data
    ; ... inner loop using POP ...
.smc_sp:
    ld   sp, $0000          ; self-modified: restores original SP
    ei
```

El guardado/restauración usa código auto-modificable porque es la forma más rápida de guardar y restaurar SP en un solo paso. `EX (SP),HL` requiere una pila válida. `LD (addr),SP` existe (código de operación ED 73, 20 T-states), pero guarda SP en una dirección fija -- luego necesitarías un `LD SP,(addr)` separado para restaurarlo después (también 20 T-states), y la restauración no es más rápida que el enfoque auto-modificable. La técnica SMC escribe el valor de SP directamente en el campo de operando de una instrucción `LD SP,nnnn` posterior: `LD (.smc+1),SP` cuesta 20 T-states para el guardado, y la restauración (`LD SP,nnnn` con el operando parcheado) cuesta solo 10 T-states. El guardado+restauración combinado es 30 T-states frente a 40 T-states del par LD (addr),SP / LD SP,(addr) -- un pequeño ahorro que también evita reservar una ubicación de memoria separada.

Una consecuencia sutil: la ventana DI/EI bloquea la interrupción de fotograma. Si el bucle interno se ejecuta largo, HALT al inicio del bucle principal aún capturará la siguiente interrupción -- pero si el renderizado se excede un fotograma entero, pierdes sincronización. Por eso importa la aritmética de presupuesto. Debes conocer tu peor caso de temporización antes de comprometerte con el truco POP.

El movimiento de rebote está codificado enteramente en la tabla de direcciones. Cada entrada es una dirección de pantalla que ya incluye el desplazamiento vertical sinusoidal. El "rebote" no ocurre en tiempo de renderizado. Ocurrió cuando la tabla fue construida. Las tres dimensiones de la animación -- posición de desplazamiento, onda de rebote, forma del carácter -- colapsan en una sola secuencia lineal de direcciones de 16 bits, consumida a máxima velocidad por POP.

### El Bucle Interno

El análisis de Introspec de 2017 de Illusion revela el bucle interno. Un byte de datos de fuente contiene 8 bits -- 8 píxeles. `LD A,(BC)` lee el byte una vez, luego RLA desplaza un bit a la vez a través de 8 iteraciones desenrolladas:

```z80 id:ch10_the_inner_loop
; Dotfield scroller inner loop (unrolled for one font byte)
; BC = pointer to font/texture data, SP = pre-built address table

    ld   a,(bc)      ;  7 T  read font byte (once per 8 pixels)
    inc  bc          ;  6 T  advance to next font byte

    ; Pixel 7 (MSB)
    pop  hl          ; 10 T  get screen address from stack
    rla              ;  4 T  shift texture bit into carry
    jr   nc,.skip7   ; 12/7 T  skip if transparent
    set  7,(hl)      ; 15 T  plot the dot
.skip7:
    ; Pixel 6
    pop  hl          ; 10 T
    rla              ;  4 T
    jr   nc,.skip6   ; 12/7 T
    set  6,(hl)      ; 15 T
.skip6:
    ; ... pixels 5 through 0 follow the same pattern,
    ; with SET 5 through SET 0 ...
```

El costo por píxel, excluyendo la obtención amortizada del byte:

| Camino | Instrucciones | T-states |
|------|-------------|----------|
| Píxel opaco | `pop hl` + `rla` + `jr nc` (no tomado) + `set ?,(hl)` | **36** |
| Píxel transparente | `pop hl` + `rla` + `jr nc` (tomado) | **26** |

![Scroller de texto de campo de puntos rebotante en acción -- texto renderizado como píxeles individuales ondulando sobre una onda sinusoidal](../../build/screenshots/ch10_dotscroll.png)

Los `LD A,(BC)` e `INC BC` cuestan 13 T-states amortizados sobre 8 píxeles -- alrededor de 1,6 T por píxel. Los "36 T-states por píxel" de Introspec son el costo del peor caso dentro del byte desenrollado, excluyendo esa sobrecarga.

La posición del bit SET cambia para cada píxel (7, 6, 5 ... 0), que es por qué el bucle se desenrolla 8 veces en lugar de repetirse. No puedes parametrizar la posición del bit en SET sin indexación IX/IY (demasiado lenta) o código auto-modificable (sobrecarga). Desenrollar es la solución limpia.

### La Aritmética del Presupuesto

Trabajemos los números correctamente. El fotograma estándar del Spectrum 48K es 69.888 T-states (el clon Pentagon funciona ligeramente más largo a 71.680). De eso, la ULA roba T-states durante la visualización activa por contención de memoria, pero el scroller escribe a la memoria de pantalla durante todo el fotograma, no solo durante el borde, así que la contención es un factor real. En la práctica, asume unos 60.000 T-states utilizables en un 48K y 65.000 en un Pentagon. Resta la reproducción de música (un reproductor AY típico cuesta 3.000-5.000 T por fotograma), el borrado de pantalla, y la construcción de tablas. Eso deja aproximadamente 40.000-50.000 T-states para el renderizado real de puntos.

Considera una visualización de 8 caracteres de fuente 8x8 = 512 bits de fuente por fotograma (8 caracteres x 8 bytes x 8 bits). Con una tasa de relleno de fuente típica de aproximadamente 30%, aproximadamente 154 bits están activados (opacos) y 358 están desactivados (transparentes). El coste del bucle interno:

- 154 píxeles opacos a 36 T cada uno = 5.544 T
- 358 píxeles transparentes a 26 T cada uno = 9.308 T
- 64 búsquedas de byte (`LD A,(BC) : INC BC`) a 13 T cada una = 832 T
- Total: aproximadamente 15.684 T-states

Eso está bien dentro de un solo fotograma. Podrías renderizar más de 20 caracteres antes de alcanzar el techo de presupuesto. El cuello de botella no es el bucle interno -- es la construcción de la tabla. Construir 512 entradas de dirección con consultas de seno y cálculo de direcciones de pantalla cuesta aproximadamente 100-150 T-states por entrada (dependiendo de la implementación), añadiendo 50.000-75.000 T al fotograma. Illusion resuelve esto pre-computando todo el conjunto de tablas en memoria y ciclando a través de desplazamientos, o construyendo incrementalmente: cuando el desplazamiento avanza un píxel, la mayoría de las entradas de tabla se desplazan una posición y solo la nueva columna necesita recálculo completo.

Los números funcionan porque dos optimizaciones se combinan. El direccionamiento basado en pila elimina todo cálculo de coordenadas del bucle interno. La transparencia basada en textura elimina todas las escrituras para píxeles vacíos. La construcción de la tabla es costosa, pero se ejecuta fuera de la ventana crítica DI y puede distribuirse a lo largo del fotograma.

### Cómo Se Codifica el Rebote

La tabla de direcciones es donde vive el arte. Para crear el movimiento de rebote, una tabla de senos desplaza la posición vertical de cada columna:

```text
y_offset = sin_table[(column * phase_freq + scroll_pos * speed_freq) & 255]
```

Los dos parámetros de frecuencia controlan el carácter visual de la onda. `phase_freq` determina la frecuencia espacial -- cuántos ciclos de onda caben a lo largo de las columnas de puntos visibles. Un valor de 4 significa que cada columna de puntos avanza 4 posiciones en la tabla de seno, así que 256/4 = 64 columnas abarcan un ciclo de onda completo. Un valor de 8 duplica la frecuencia, creando una ondulación más apretada. `speed_freq` controla qué tan rápido se propaga la onda en el tiempo: valores más altos hacen que el rebote se desplace más rápido independientemente del desplazamiento del texto.

La tabla de seno en sí es un array de 256 bytes de desplazamientos con signo, alineado a página para consulta rápida. La alineación a página significa que el byte alto de la dirección de la tabla es fijo; solo el byte bajo cambia, así que la consulta se reduce a:

```z80 id:ch10_how_the_bounce_is_encoded_2
    ld   hl, sin_table    ; H = page, L = don't care
    ld   l, a             ; A = (column * freq + phase) & $FF
    ld   a, (hl)          ; 7 T — one memory read, no arithmetic
```

Los valores en la tabla tienen signo: desplazamientos positivos empujan el punto hacia abajo, negativos hacia arriba. La amplitud está incorporada en la tabla en el momento de la generación. Una tabla con rango -24 a +24 da un rebote de 48 líneas de escaneo pico a pico. Generar la tabla es un coste de una sola vez, típicamente hecho offline o durante la inicialización usando una consulta o una aproximación simple. En el Z80, computar valores de seno verdaderos en tiempo de ejecución es caro, así que los programadores de la demoscene o pre-calculan tablas externamente o usan simetría de cuadrante: calculan un cuarto de onda (64 entradas), luego lo espejan y niegan para rellenar los tres cuartos restantes.

Dada la (x, y + y_offset) de cada punto, la dirección de pantalla del Spectrum se calcula y se almacena en la tabla. El código de construcción de tabla se ejecuta una vez por fotograma, fuera del bucle interno. El bucle interno solo ve un flujo de direcciones precalculadas.

### Más Allá del Simple Seno: Lissajous, Hélice y Patrones Multi-Onda

La belleza del enfoque de tabla precalculada es que al bucle interno no le importa qué forma sigue el movimiento. Consume direcciones a un coste fijo independientemente de la trayectoria que las generó. Esto hace trivial experimentar con diferentes patrones de movimiento -- toda la complejidad reside en el código de construcción de tabla.

Un **patrón de Lissajous** añade un desplazamiento horizontal sinusoidal además del vertical. En lugar de que cada columna se mapee a un byte x fijo en pantalla, la posición x también oscila:

```text
x_offset = sin_table[(column * x_freq + phase_x) & 255]
y_offset = sin_table[(column * y_freq + phase_y) & 255]
```

Cuando `x_freq` e `y_freq` son coprimos (digamos 3 y 2), el campo de puntos traza una figura de Lissajous -- el clásico patrón de osciloscopio. El texto se convierte en una cinta tejiéndose a través del espacio. Diferentes ratios de frecuencia producen formas dramáticamente diferentes: 1:1 da un círculo o elipse, 1:2 da un ocho, 2:3 da el patrón de trébol familiar del viejo equipo de pruebas analógico.

Un efecto de **hélice** o espiral usa una sola fase que avanza por columna, pero varía la amplitud:

```text
amplitude = base_amp + sin_table[(column * 2 + time) & 255] * depth_scale
y_offset = sin_table[(column * freq + phase) & 255] * amplitude / max_amp
```

Esto crea la ilusión de puntos retrocediendo en profundidad -- la onda se aplana en el punto "lejano" de la espiral y se expande en el punto "cercano".

La **superposición multi-onda** es la técnica más simple con el resultado más dramático. Suma dos términos sinusoidales con diferentes frecuencias:

```text
y_offset = sin_table[(col * 4 + phase1) & 255] + sin_table[(col * 7 + phase2) & 255]
```

El resultado es una ondulación compleja, de aspecto orgánico, que nunca se repite del todo. Avanzar `phase1` y `phase2` a velocidades diferentes produce movimiento en continua evolución con solo dos consultas de tabla por columna. Tres o más armónicos crean ondas que parecen casi fluido-dinámicas. Esta es la forma más barata posible de generar movimiento complejo -- cada armónico adicional cuesta una consulta de tabla y una suma por columna en el constructor de tabla, y el coste del bucle interno permanece sin cambios.

---

## Parte 2: Animación de Color de 4 Fases

### El Problema del Color

Cada celda de 8x8 tiene un color de tinta (0-7) y un color de papel (0-7). Dentro de un solo fotograma, obtienes exactamente dos colores por celda. Pero el Spectrum funciona a 50 fotogramas por segundo, y el ojo humano no ve fotogramas individuales a esa tasa. Ve el promedio.

### El Truco

La técnica de 4 fases de Introspec cicla a través de cuatro fotogramas:

1. **Normal A:** tinta = C1, papel = C2. Datos de píxeles = patrón A.
2. **Normal B:** tinta = C3, papel = C4. Datos de píxeles = patrón B.
3. **Invertido A:** tinta = C2, papel = C1. Datos de píxeles = patrón A (mismos píxeles, colores intercambiados).
4. **Invertido B:** tinta = C4, papel = C3. Datos de píxeles = patrón B (mismos píxeles, colores intercambiados).

A 50Hz, cada fotograma se muestra durante 20 milisegundos. El ciclo de cuatro fotogramas se completa en 80ms -- 12,5 ciclos por segundo, por encima del umbral de fusión de parpadeo en pantallas CRT.

### Las Matemáticas de la Percepción

Traza un solo píxel que está "encendido" en el patrón A y "apagado" en el patrón B:

| Fotograma | Estado del píxel | Color mostrado |
|-------|-------------|-----------------|
| Normal A | encendido (tinta) | C1 |
| Normal B | apagado (papel) | C4 |
| Invertido A | encendido (tinta) | C2 |
| Invertido B | apagado (papel) | C3 |

El ojo percibe el promedio: (C1 + C2 + C3 + C4) / 4.

Ahora verifica: un píxel "encendido" en ambos patrones ve C1, C3, C2, C4. Un píxel "apagado" en ambos ve C2, C4, C1, C3. Todos los casos producen el mismo promedio. El patrón de píxeles no afecta el tono percibido -- solo la elección de C1 a C4 lo hace.

¿Entonces por qué tener dos patrones? Porque las transiciones *intermedias* importan. Un píxel que alterna entre rojo brillante y verde brillante parpadea notablemente a 12,5Hz. Un píxel alternando entre tonos similares apenas parpadea. Los patrones de dithering -- tableros de ajedrez, rejillas de medio tono, matrices ordenadas -- controlan la *textura* del parpadeo. Introspec eligió patrones de modo que las transiciones entre fotogramas produjeran mínima oscilación visible. Esta es la selección de píxeles anti-conflicto: la disposición cuidadosa de bits "encendidos" y "apagados" para asegurar que ningún píxel alterne entre colores dramáticamente diferentes en fotogramas consecutivos.

### Por Qué la Inversión Es Esencial

Sin el paso de inversión, los píxeles "encendidos" siempre mostrarían tinta y los píxeles "apagados" siempre mostrarían papel. Obtendrías exactamente dos colores visibles por celda, parpadeando entre dos pares diferentes. La inversión asegura que tanto tinta como papel contribuyen a ambos estados de píxel a lo largo del ciclo, mezclando los cuatro colores en la salida percibida.

En el Spectrum, la inversión es barata. La disposición del byte de atributo es `FBPPPIII` -- Flash, Brillo, 3 bits de color de papel, 3 bits de color de tinta. Intercambiar tinta y papel significa rotar los 6 bits inferiores: el papel se mueve a la posición de tinta, la tinta se mueve a la posición de papel, mientras Flash y Brillo permanecen en su lugar. En código:

```z80 id:ch10_why_inversion_is_essential
; Swap ink and paper in attribute byte (A)
; Input:  A = F B P2 P1 P0 I2 I1 I0
; Output: A = F B I2 I1 I0 P2 P1 P0
    ld   b, a
    and  $C0           ; isolate Flash + Bright bits
    ld   c, a          ; save FB------
    ld   a, b
    and  $38           ; isolate paper (--PPP---)
    rrca
    rrca
    rrca               ; paper now in ink position (-----PPP)
    ld   d, a          ; save ink-from-paper
    ld   a, b
    and  $07           ; isolate ink (-----III)
    rlca
    rlca
    rlca               ; ink now in paper position (--III---)
    or   d             ; combine: --IIIPPP
    or   c             ; combine: FBIIIPPP = swapped attribute
```

La alternativa es pre-computar ambos búferes de atributos normal e invertido en la inicialización y simplemente ciclar punteros de búfer en tiempo de ejecución. Esto intercambia 3.072 bytes de memoria por cero computación por fotograma -- un intercambio que vale la pena en máquinas de 128K con memoria de sobra.

### Costo Práctico

Cuatro búferes de atributos pre-construidos, ciclados una vez por fotograma. El coste por fotograma es una copia de bloque de 768 bytes a la RAM de atributos ($5800-$5AFF). Usando LDIR, esto cuesta 21 T-states por byte: 768 x 21 = 16.128 T-states. Usando el truco de la pila (POP del búfer fuente, cambiar SP, PUSH a la RAM de atributos, procesando por lotes a través de pares de registros y registros sombra), un coste realista es de alrededor de 11.000-13.000 T-states dependiendo del tamaño del lote y la sobrecarga del bucle -- una modesta aceleración de 1,2-1,5x sobre LDIR. La ganancia es menor de lo que podrías esperar porque cada lote requiere dos cambios de SP (guardar posición fuente, cargar destino, luego volver a cambiar), y esa sobrecarga compensa en gran medida la ventaja de velocidad bruta de POP+PUSH sobre LDIR. Para un *relleno* (escribir el mismo valor en cada byte), el truco PUSH es mucho más efectivo -- cargas pares de registros una vez, luego haces PUSH repetidamente -- pero una copia desde datos fuente variables no puede evitar el coste de lectura.

La lógica de ciclo en sí es trivial. Una sola variable contiene la fase (0-3). Cada fotograma, la incrementas y haces AND con 3 para envolver. Indexas en una tabla de 4 entradas de direcciones base de búfer:

```z80 id:ch10_practical_cost
    ld   a, (phase)
    inc  a
    and  3
    ld   (phase), a
    add  a, a           ; phase * 2 (pointer table is 16-bit entries)
    ld   hl, buf_ptrs
    ld   e, a
    ld   d, 0
    add  hl, de
    ld   a, (hl)
    inc  hl
    ld   h, (hl)
    ld   l, a           ; HL = source buffer address
    ld   de, $5800      ; DE = attribute RAM
    ld   bc, 768
    ldir                ; copy attributes for this phase
```

Memoria: 4 x 768 = 3.072 bytes para los búferes. En una máquina 48K eso es un trozo significativo; en 128K puedes colocar búferes en bancos paginados. Los patrones de píxeles (A y B) se escriben una vez en la inicialización y nunca se tocan de nuevo -- solo la RAM de atributos cambia cada fotograma.

### Superposición de Texto

En Eager, el texto desplazable se superpone sobre la animación de color. Hay varios enfoques, cada uno con diferentes compromisos.

El más simple es la **exclusión de celdas**: reservar ciertas celdas de caracteres para texto, omitirlas durante el ciclo de color, y escribir atributos fijos de blanco sobre negro con glifos de fuente reales. Esto es fácil de implementar -- solo enmascara esas celdas de la copia LDIR -- pero crea un límite visual duro entre el fondo animado y la región de texto estático. El texto parece pegado encima.

Un enfoque más sofisticado es la **integración de patrones**: las formas de los glifos anulan bits específicos en ambos patrones de píxeles A y B. Donde la fuente tiene un bit activado, ambos patrones reciben ese bit activado (o desactivado, dependiendo del color de texto deseado). Esto asegura que el píxel de texto muestre el mismo color en las cuatro fases -- no parpadea porque nunca transiciona entre diferentes estados de color. Los píxeles circundantes continúan ciclando normalmente. El resultado es texto que parece flotar sobre el fondo animado, con sangrado de color hasta los bordes de cada forma de letra. El coste es que debes regenerar (o parchear) los patrones de píxeles cada vez que el texto se desplaza, lo que añade unos pocos miles de T-states por fotograma dependiendo de cuántas celdas contienen texto.

Una tercera opción para máquinas de 128K es la **composición de capas**: mantener el fondo de 4 fases en un conjunto de páginas de memoria y el scroller de texto en otro, luego combinarlos durante la copia de atributos. Esto mantiene los dos sistemas independientes -- el scroller no necesita saber sobre la animación de color y viceversa -- al coste de un bucle de copia ligeramente más complejo que enmascara las celdas de texto.

---

## Linaje en la Demoscene

El scroller de campo de puntos no apareció de la nada. La técnica se sitúa en un linaje de efectos del ZX Spectrum que se extiende desde mediados de los años 1980 hasta el presente.

Los primeros scrollers del Spectrum eran asuntos simples a nivel de celda de caracteres: desplazamientos horizontales basados en LDIR que movían una línea entera de celdas de caracteres, un byte a la vez. El desplazamiento suave a nivel de píxel era más difícil -- el Spectrum no tiene registro de desplazamiento por hardware, así que cada desplazamiento de píxel requiere reescribir los datos del bitmap. A principios de los años 1990, los programadores de demos habían desarrollado varios enfoques: desplazamiento por píxel basado en RL/RR (desplazando cada byte en una línea de pantalla), scrollers con tabla de consulta (copias pre-desplazadas de cada carácter), y la técnica de doble búfer (dibujar en un búfer trasero, copiar a pantalla). Todos estos estaban limitados por el coste fundamental de mover bytes dentro y fuera de la RAM de vídeo.

El enfoque del campo de puntos rompe completamente con esta tradición. En lugar de desplazar un bloque contiguo de píxeles, descompone el texto en puntos individuales y coloca cada uno independientemente. Esta fue la perspicacia de Dark a mediados de los 1990: si renuncias a la idea de una fuente sólida y aceptas un renderizado puntillista, puedes usar el truco POP para colocar cada punto con sobrecarga mínima. El resultado visual -- texto disolviéndose en una nube de partículas, rebotando sobre una onda sinusoidal -- se convirtió en uno de los efectos emblemáticos de la demoscene rusa.

*Illusion* de X-Trade (ENLiGHT'96) fue la demo que hizo famosa la técnica en el mundo del Spectrum. El scroller de campo de puntos fue su efecto estrella, ejecutándose suavemente junto a la música y otros elementos visuales. Dark publicó los principios algorítmicos en *Spectrum Expert* números #01 y #02 (1997-98), donde describió el enfoque general del renderizado basado en POP y la animación con tabla de seno. Dos décadas después, la ingeniería inversa detallada del binario de Illusion por Introspec (publicada en la revista *Hype*, 2017) confirmó las afirmaciones de Dark y proporcionó los conteos de ciclos exactos sobre los que la comunidad había especulado durante mucho tiempo.

La técnica de color de 4 fases tiene un pedigrí diferente. El ciclado de colores en el Spectrum se ha explorado desde los años 1980 -- la alternancia simple de dos fotogramas (efectos tipo flash) era común en juegos y demos. Pero el enfoque sistemático de cuatro fases, con su cuidadoso paso de inversión para asegurar que los cuatro colores contribuyan igualmente, fue refinado por Introspec para *Eager* (3BM Open Air 2015). El file_id.diz de la versión de fiesta menciona explícitamente la técnica, y el artículo "Making of Eager" de Introspec en *Hype* (2015) describe el proceso de diseño: elegir colores de modo que las fases adyacentes minimicen el parpadeo visible, y usar patrones de tramado que distribuyan las transiciones uniformemente a lo largo de la celda.

El principio más amplio -- la multiplexación temporal del color -- aparece en otras plataformas también. La Atari 2600 famosamente alterna fotogramas para crear pseudo-sprites parpadeantes. La Game Boy usa un truco similar para pseudo-transparencia. En el Spectrum, la técnica es particularmente efectiva porque la persistencia del fósforo del CRT suaviza las transiciones más de lo que lo haría un LCD. Esto vale la pena notar para los espectadores modernos: el color de 4 fases se ve sustancialmente mejor en un CRT real o un buen emulador de CRT (con simulación de fósforo) que en una visualización cruda de píxeles perfectos.

---

## El Principio Compartido: Engaño Temporal

El dotfield scroller usa 50 fotogramas por segundo para flexibilidad *espacial*. Cada fotograma es una instantánea de posiciones de puntos en un instante; el cerebro del espectador interpola entre instantáneas para percibir movimiento suave. El trabajo de la CPU es *colocar* puntos lo más rápido posible, leyendo direcciones precalculadas de la pila.

La animación de color de 4 fases usa 50 fotogramas por segundo para flexibilidad de *color*. Cada fotograma muestra uno de cuatro estados de color; la retina del espectador los promedia. Ningún fotograma individual contiene el resultado percibido -- solo existe en la persistencia de visión.

Ambos explotan la misma realidad física: el CRT se refresca a 50Hz, y el sistema visual humano no puede resolver fotogramas individuales a esa tasa. La resolución *temporal* del Spectrum es mucho más rica que su resolución espacial o de color. Los programadores de la demoscene descubrieron que la resolución temporal es el eje más barato para explotar.

Ambos reducen sus bucles internos al mínimo absoluto. El scroller a 36 T-states por punto. La animación de color a una sola copia de búfer por fotograma. Ambos mueven la complejidad fuera del bucle interno hacia la precalculación. Y ambos producen resultados que parecen, para el espectador casual, como si el hardware no debería ser capaz de ellos.

Esto es lo que hace de la demoscene una forma de arte temporal. Una captura de pantalla de un dotfield scroller muestra una dispersión de píxeles. Una captura de pantalla de una animación de color de 4 fases muestra dos colores por celda, exactamente como el hardware especifica. Tienes que verlos *moverse* para verlos funcionar. La belleza está en la secuencia, no en el fotograma.

---

## Práctico 1: Un Scroller de Texto Dot-Matrix Rebotante

Construye un dotfield scroller simplificado: un mensaje de texto corto renderizado como un campo de puntos-matriz rebotante usando direccionamiento basado en POP.

**Estructuras de datos.** Una fuente de bitmap 8x8 alineada a página (la fuente ROM en `$3D00` funciona). Una tabla de senos de 256 bytes para el desplazamiento de rebote. Un búfer RAM para la tabla de direcciones (hasta 4.096 x 2 bytes).

**Construcción de tabla.** Antes de cada fotograma, iterar a través de los caracteres visibles. Para cada bit en cada byte de fuente, calcular la dirección de pantalla incorporando el desplazamiento de rebote sinusoidal, y almacenarlo en la tabla de direcciones. Esto se ejecuta una vez por fotograma fuera del bucle interno.

**Renderizado.** Deshabilitar interrupciones. Guardar SP via código auto-modificable. Apuntar SP a la tabla de direcciones. Ejecutar el bucle interno desenrollado: `ld a,(bc) : inc bc`, luego 8 repeticiones de `pop hl : rla : jr nc,skip : set N,(hl)` con N de 7 a 0. Restaurar SP. Habilitar interrupciones.

**Bucle principal.** `halt` (sincronizar a 50Hz), limpiar la pantalla (limpieza basada en PUSH del Capítulo 3), construir la tabla de direcciones, renderizar el dotfield, avanzar posición de desplazamiento y fase de rebote.

**Extensiones.** Limpieza parcial de pantalla (rastrear el rectángulo delimitador). Doble búfer via pantalla sombra en 128K. Múltiples armónicos de rebote. Densidad variable de puntos para un aspecto más disperso y etéreo.

---

## Práctico 2: Una Animación de Ciclado de Color de 4 Fases

Construye una animación de color de 4 fases produciendo gradientes suaves.

**Patrones de píxeles.** Llena la memoria de bitmap con dos patrones de dithering complementarios. Lo más simple: líneas de píxeles pares obtienen `$55` (01010101), líneas impares obtienen `$AA` (10101010). Para calidad de producción, usa una matriz Bayer 4x4 ordenada.

**Búferes de atributos.** Precalcula cuatro búferes de 768 bytes. Los búferes 0 y 1 contienen atributos normales con dos esquemas de color diferentes (variando tinta/papel a través de la pantalla para un gradiente diagonal). Los búferes 2 y 3 son las versiones invertidas -- bits de tinta y papel intercambiados. El intercambio es una rotación de bits: tres RRCAs para mover bits de tinta a posición de papel, tres RLCAs en la otra dirección, enmascarar y combinar.

**Bucle principal.** Cada fotograma: `halt`, indexar en una tabla de 4 entradas de punteros de búfer usando un contador de fase (AND 3), LDIR 768 bytes a `$5800`, incrementar el contador de fase. Ese es todo el motor en tiempo de ejecución -- alrededor de 16.000 T-states por fotograma.

**Animación.** Para un gradiente en movimiento, regenerar un búfer por fotograma (el que está a punto de convertirse en el más antiguo del ciclo de 4 fotogramas) con un desplazamiento de color avanzando. Esto mantiene un pipeline: mostrar fotograma N mientras generas fotograma N+4. Alternativamente, precalcular todos los búferes a través de bancos de 128K para cero costo en tiempo de ejecución.

---

## Resumen

- El **dotfield scroller** renderiza texto como puntos individuales. El bucle interno -- `pop hl : rla : jr nc,skip : set ?,(hl)` -- cuesta 36 T-states por píxel opaco, 26 por píxel transparente.
- El **direccionamiento basado en pila** codifica la trayectoria de rebote como direcciones de pantalla preconstruidas. POP las recupera a 10 T-states cada una -- la lectura de acceso aleatorio más rápida en el Z80.
- El **color de 4 fases** cicla 4 fotogramas de atributos (2 normales + 2 invertidos) a 50Hz. La persistencia de visión promedia los colores, creando la ilusión de más de 2 colores por celda.
- El **paso de inversión** asegura que los cuatro colores contribuyan a cada posición de píxel.
- Ambas técnicas explotan la **resolución temporal** para crear efectos imposibles en cualquier fotograma individual.
- El scroller usa la pila para flexibilidad espacial; la animación de color usa alternancia de fotogramas para flexibilidad de color -- los dos ejes principales del engaño en la demoscene.

---

## Inténtalo Tú Mismo

1. Construye el dotfield scroller. Empieza con un solo carácter estático trazado via el bucle interno basado en POP. Verifica la temporización esperada con la arnés de borde del Capítulo 1. Luego agrega la tabla de rebote y observa cómo ondula.

2. Experimenta con los parámetros de rebote. Cambia la amplitud del seno, la frecuencia espacial y la velocidad de fase. Pequeños cambios producen diferencias visuales dramáticas.

3. Construye la animación de color de 4 fases. Empieza con color uniforme (todas las celdas iguales en cada fase). Verifica que ves un color estable que no es ni la tinta ni el papel de ningún fotograma individual. Luego agrega el gradiente diagonal.

4. Prueba diferentes patrones de dithering. Tablero de ajedrez, bloques 2x2, matriz Bayer, ruido aleatorio. ¿Cuáles minimizan el parpadeo visible? ¿Cuáles producen los gradientes percibidos más suaves?

5. Combina ambas técnicas: fondo de color de 4 fases con un dotfield scroller monocromático encima.

---

> **Fuentes:** Introspec, "Technical Analysis of Illusion by X-Trade" (Hype, 2017); Introspec, "Making of Eager" (Hype, 2015); Dark, "Programming Algorithms" (Spectrum Expert #01, 1997). El desensamblado del bucle interno y conteos de ciclos siguen el análisis de Introspec de 2017. La técnica de color de 4 fases se describe en el artículo making-of de Eager y el file_id.diz de la versión de party.
