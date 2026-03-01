# Capítulo 13: El arte del sizecoding

> "Era como jugar juegos de rompecabezas -- un constante reordenamiento de código para encontrar codificaciones más cortas."
> -- UriS, sobre escribir NHBF (2025)

Hay una categoría de competición del demoscene donde la restricción no es el tiempo sino el *espacio*. Tu programa completo -- el código que dibuja la pantalla, produce el sonido, maneja el bucle de fotogramas, contiene los datos que necesite -- debe caber en 256 bytes. O 512. O 1K, o 4K, u 8K. Ni un byte más. El archivo se mide, y si son 257 bytes, queda descalificado.

Estas son competiciones de **sizecoding**, y producen algunos de los trabajos más notables de la escena del ZX Spectrum. Una intro de 256 bytes que llena la pantalla con patrones animados y toca una melodía reconocible es una forma de compresión tan extrema que es difícil de creer hasta que lees el código. La brecha entre lo que ve la audiencia y el tamaño del archivo que lo produce -- esa brecha es el arte.

Este capítulo trata sobre la mentalidad, las técnicas y los trucos específicos que hacen posible el sizecoding.

---

## 13.1 ¿Qué es el sizecoding?

Las competiciones de demos típicamente ofrecen varias categorías con límite de tamaño:

| Categoría | Límite de tamaño | Qué cabe |
|----------|-----------|-----------|
| 256 bytes | 256 | Un efecto ajustado, quizás sonido simple |
| 512 bytes | 512 | Un efecto con música básica o dos efectos simples |
| 1K intro | 1.024 | Múltiples efectos, música apropiada, transiciones |
| 4K intro | 4.096 | Una demo corta con varias partes |
| 8K intro | 8.192 | Una mini-demo pulida |

Los límites son absolutos. El archivo se mide en bytes, y no hay negociación.

Lo que hace fascinante al sizecoding es que invierte la jerarquía normal de optimización. En el mundo de efectos del demoscene con conteo de ciclos, optimizas para *velocidad* -- desenrollando bucles, duplicando datos, generando código, todo intercambiando espacio por tiempo. El sizecoding invierte esto. La velocidad no importa. La legibilidad no importa. La única pregunta es: ¿puedo hacerlo un byte más corto?

UriS, quien escribió la intro de 256 bytes NHBF para Chaos Constructions 2025, describió el proceso como "jugar juegos de rompecabezas." La descripción es exacta. El sizecoding es un rompecabezas donde las piezas son instrucciones Z80, el tablero son 256 bytes de RAM, y las mejores soluciones involucran movimientos que resuelven múltiples problemas simultáneamente.

El cambio de mentalidad:

- **Cada byte es precioso.** Una instrucción de 3 bytes donde una de 2 bytes basta es el 0,4% de tu programa entero. A 256 bytes, un byte ahorrado es como ahorrar 250 bytes en un programa de 64K.

- **Código y datos se superponen.** Los mismos bytes que se ejecutan como instrucciones pueden servir como datos. El Z80 no conoce la diferencia -- solo la ruta del contador de programa a través de la memoria distingue el código de los datos.

- **La elección de instrucción está impulsada por el tamaño, no la velocidad.** `RST $10` cuesta 1 byte. `CALL $0010` hace lo mismo en 3 bytes. En una demo normal nunca lo notarías. En 256 bytes, esos 2 bytes son la diferencia entre tener sonido o no.

- **El estado inicial es datos gratis.** Después del arranque, los registros tienen valores conocidos. La memoria en ciertas direcciones contiene datos conocidos. Un programador de sizecoding explota cada bit de este estado gratuito.

- **El código auto-modificable no es un truco -- es una necesidad.** Cuando no puedes permitirte una variable separada, modificas el operando de una instrucción en su lugar.

### El Kit de Herramientas del Size-Coder Z80

Algunos trucos recurren tan a menudo en intros de sizecoding que forman un vocabulario compartido. Conocer estos de memoria -- sus costes en bytes, sus efectos secundarios -- es el prerrequisito para el sizecoding serio.

**Suposiciones de inicialización de registros.** Cuando un programa del Spectrum se lanza desde BASIC (vía `RANDOMIZE USR`), el estado de la CPU no es aleatorio. Después de `CLEAR` y antes de la llamada USR, A es típicamente 0, BC contiene la dirección USR, DE y HL tienen valores conocidos del intérprete BASIC, el puntero de pila está en la dirección de CLEAR, y las interrupciones están habilitadas. Muchos de estos son lo suficientemente estables como para confiar en ellos. Si tu programa necesita A = 0 al inicio, no escribas `XOR A` -- ya es cero. Si necesitas un contador de 16 bits comenzando en 0, verifica si DE o HL ya contiene 0 o un valor útil. Un byte ahorrado aquí, dos bytes ahorrados allá -- estos se acumulan hasta la diferencia entre 260 bytes y 256.

El área de variables del sistema ($5C00-$5CB5) es otra fuente de datos gratuitos. El intérprete BASIC mantiene más de 100 bytes de estado en direcciones conocidas. Si necesitas el valor 2, podrías encontrarlo en la dirección que contiene el número de flujo actual. Si necesitas $FF, varios campos de variables del sistema lo contienen. Leer desde una dirección fija cuesta 3 bytes (`LD A, (nn)`), pero si reemplaza una carga de 2 bytes *más* alguna computación, sales ganando.

**DJNZ como salto corto hacia atrás.** `DJNZ label` son 2 bytes, igual que `JR label` -- pero también decrementa B. Si B no es cero y necesitas un salto hacia atrás, `DJNZ` hace ambas cosas gratis. Incluso cuando no te importa el decremento de B, `DJNZ` sigue siendo 2 bytes, el mismo coste que `JR`. Pero si B llega a cero en el momento exacto en que quieres continuar sin saltar, has fusionado un contador de bucle y un salto en una sola instrucción. Los size-coders rutinariamente estructuran bucles para que la cuenta regresiva natural de B se alinee con la condición de salida.

**RST como CALL de 1 byte.** El Z80 reserva ocho direcciones de reinicio: $00, $08, $10, $18, $20, $28, $30, $38. `RST n` empuja la dirección de retorno y salta al destino -- igual que `CALL n` -- pero en 1 byte en lugar de 3. En el Spectrum, la ROM coloca rutinas útiles en varias de estas direcciones:

- `RST $10` -- imprimir un carácter (rutina ROM en $0010)
- `RST $20` -- recoger siguiente carácter de BASIC (menos útil para demos)
- `RST $28` -- entrar a la calculadora de punto flotante (útil para matemáticas)
- `RST $38` -- el manejador de interrupciones enmascarable (IM 1 salta aquí)

En una demo normal, estas rutinas ROM son demasiado lentas para llamar en un bucle ajustado. En una intro de 256 bytes, ahorrar 2 bytes por llamada vale la penalización de velocidad. Si tu programa llama `RST $10` seis veces para imprimir caracteres, son 12 bytes ahorrados sobre seis instrucciones `CALL $0010`. Doce bytes es casi el 5% de 256.

**Instrucciones superpuestas.** El Z80 decodifica instrucciones byte por byte, sin requisitos de alineación. Si saltas al medio de una instrucción multibyte, la CPU decodifica fresco desde ese punto. Esto significa que puedes ocultar una instrucción dentro de otra:

```z80 id:ch13_the_z80_size_coder_s_toolkit
    ld   a, $AF              ; opcode $3E, operand $AF
                              ; BUT: $AF is XOR A
```

Si la CPU ejecuta desde el inicio, ve `LD A, $AF` (2 bytes). Si otra ruta de código salta al segundo byte, ve `XOR A` (1 byte). Un byte sirve dos propósitos. La técnica es frágil -- demanda control perfecto de todas las rutas de ejecución -- pero en código de competición, la fragilidad es aceptable.

Un patrón común: el byte `$18` es `JR d` (salto relativo). Si necesitas el valor $18 como dato *y* necesitas un salto en esa ubicación, el mismo byte hace ambas cosas. El operando que sigue es tanto el desplazamiento del salto como (desde otra perspectiva) la siguiente pieza de datos.

**Abuso del estado de banderas.** Toda instrucción aritmética y lógica establece banderas. Los size-coders memorizan qué banderas afecta cada instrucción y explotan los resultados en lugar de computarlos por separado. Después de `DEC B`, la bandera de cero te dice si B llegó a cero -- no se necesita `CP 0`. Después de `ADD A, n`, la bandera de acarreo te dice si el resultado desbordó más allá de 255. Después de `AND mask`, la bandera de cero te dice si algún bit enmascarado estaba activado.

El truco de banderas más profundo es `SBC A, A`: si el acarreo está activado, A se convierte en $FF; si el acarreo está desactivado, A se convierte en $00. Un byte, sin ramificación, una máscara completa desde una bandera. Compara esto con la alternativa de ramificación:

```z80 id:ch13_the_z80_size_coder_s_toolkit_2
    ; With branching: 6 bytes
    jr   nc, .zero            ; 2
    ld   a, $FF               ; 2
    jr   .done                ; 2
.zero:
    xor  a                    ; 1
.done:

    ; With SBC A,A: 1 byte
    sbc  a, a                 ; 1 — carry -> $FF, no carry -> $00
```

Cinco bytes ahorrados. En una intro de 256 bytes, eso es el dos por ciento del programa entero.

---

## 13.2 Anatomía de una intro de 256 bytes: NHBF

**NHBF** (No Heart Beats Forever) fue creada por UriS para Chaos Constructions 2025, inspirada por RED REDUX de Multimatograf 2025. Produce texto con efectos de pantalla y música -- acordes de potencia de onda cuadrada en bucle con notas de melodía pentatónica aleatorias -- todo en 256 bytes.

### La música

A 256 bytes, no puedes incluir un reproductor de tracker ni tablas de notas. NHBF controla el chip AY directamente. Los acordes de potencia están codificados como valores inmediatos en las instrucciones de escritura de registros del AY -- los mismos bytes que forman el operando de `LD A, n` *son* la nota musical. El canal de melodía usa un generador pseudo-aleatorio (típicamente `LD A, R` -- leer el registro de refresco -- seguido de AND para enmascarar el rango) para elegir de una escala pentatónica. Una escala pentatónica suena agradable sin importar qué notas caigan una al lado de otra, así que la melodía suena intencional aunque sea aleatoria. Dos bytes para un número "aleatorio"; cinco notas que nunca chocan.

### Lo visual

Imprimir texto a través de la ROM -- `RST $10` muestra un carácter por 1 byte por llamada -- es la manera más barata de poner píxeles en pantalla. Pero incluso una cadena de 20 caracteres cuesta 40 bytes (códigos de carácter + llamadas RST). Los programadores de sizecoding buscan formas de comprimir más: superponer los datos de la cadena con otro código, o computar caracteres desde una fórmula.

### El rompecabezas: Encontrar superposiciones

UriS describe el proceso central como un reordenamiento constante. Escribes una primera versión a 300 bytes, luego la miras fijamente. Notas que el contador de bucle para el efecto visual termina con el valor que necesitas como número de registro del AY. Eliminas el `LD A, 7` que lo establecería -- el bucle ya dejó A con 7. Dos bytes ahorrados. La rutina de limpieza de pantalla usa LDIR, que decrementa BC a cero. Arregla el código para que la siguiente sección necesite BC = 0, y ahorra el `LD BC, 0` -- otros 3 bytes.

Cada instrucción produce efectos secundarios -- valores de registro, estados de banderas, contenidos de memoria -- y el arte es organizar las instrucciones para que los efectos secundarios de una rutina sean las entradas de otra.

### El descubrimiento de Art-Top

Durante el desarrollo, Art-Top notó algo notable: los valores de registro sobrantes de la rutina de limpieza de pantalla coincidían con la longitud exacta necesaria para la cadena de texto. No fue planeado. UriS había escrito la limpieza de pantalla, luego la salida de texto, y las dos resultaron compartir un estado de registro que eliminaba un contador de longitud separado.

Este tipo de superposición fortuita es el corazón de la programación de 256 bytes. No puedes planificarlo. Solo puedes crear condiciones donde pueda ocurrir, reordenando constantemente el código y observando alineaciones accidentales. Cuando encuentras una, se siente como descubrir que dos piezas de rompecabezas de puzzles diferentes encajan perfectamente.

### El Presupuesto de Bytes

Cuando trabajas a 256 bytes, un presupuesto aproximado te ayuda a planificar antes de escribir una sola instrucción. Aquí hay un desglose realista para una intro típica de 256 bytes del ZX Spectrum con visuales y sonido:

| Componente | Bytes | Notas |
|-----------|-------|-------|
| Relleno de píxeles (dither/borrado) | 18-25 | LD HL, LDIR o un bucle de relleno compacto |
| Inicialización AY | 16-22 | Mezclador, volumen, tono inicial — vía escrituras a puerto |
| Sincronización de fotograma del bucle principal | 1 | HALT |
| Actualización de tono AY por fotograma | 10-14 | Seleccionar registro, escribir período de tono |
| Núcleo del efecto visual | 30-50 | El bucle interno que computa y escribe atributos |
| Control de bucle externo / filas | 8-12 | Contador de filas, contador de columnas, saltos |
| Actualización del contador de fotogramas (SMC) | 6-8 | Leer, incrementar, escribir de vuelta en la instrucción |
| Salto de vuelta al principal | 2 | JR main_loop |
| **Total del marco** | **~91-134** | Antes de cualquier código específico del efecto |

Eso deja 122-165 bytes para el contenido creativo real -- la fórmula visual, tablas de datos, lógica de sonido extra, cadenas de texto, o cualquier otra cosa que haga la intro *tuya*. El marco es caro. Por eso los size-coders luchan tan duro por cada byte en el andamiaje: cada byte ahorrado en el marco es un byte ganado para el arte.

Mira el ejemplo acompañante `intro256.a80`. Su bucle de relleno de píxeles usa 18 bytes. La configuración del AY toma 20 bytes. El marco del bucle principal (HALT, lectura del contador de fotogramas, actualización del borde) son 8 bytes. La actualización de tono del AY son 13 bytes. El efecto visual -- un patrón de interferencia Moiré computado puramente desde aritmética de registros -- consume 36 bytes. La escritura de vuelta del contador de fotogramas y el salto del bucle toman 8 bytes. Total: alrededor de 103 bytes de marco y 36 bytes de efecto. Esa proporción -- aproximadamente 3:1 de marco a efecto -- es típica. Cuanto mejor comprimas el marco, más espacio tienes para la expresión creativa.

![Salida de una intro de 256 bytes -- patrón de interferencia Moiré animado con ciclado de colores, generado completamente desde aritmética de registros](../../build/screenshots/ch13_intro256.png)

### Técnicas clave a 256 bytes

**1. Usar el estado inicial de registros y memoria.** Después de una carga estándar por cinta, los registros tienen valores conocidos: A a menudo contiene el último byte cargado, BC la longitud del bloque, HL apunta cerca del final de los datos cargados. El área de variables del sistema ($5C00-$5CB5) contiene valores conocidos. La memoria de pantalla está limpia después de CLS. Cada valor conocido que explotas en lugar de cargarlo explícitamente ahorra 1-3 bytes.

**2. Superponer código y datos.** El byte $3E es el código de operación (opcode) de `LD A, n` y también el valor 62 -- un carácter ASCII, una coordenada de pantalla, o un valor de registro del AY. Si tu programa ejecuta este byte como una instrucción *y* lo lee como datos desde una ruta de código diferente, has hecho que un byte haga dos trabajos. Patrón común: el operando inmediato de `LD A, n` sirve como datos que otra rutina lee con `LD A, (addr)` apuntando a instruction_address + 1.

**3. Elegir instrucciones por tamaño.**

| Codificación larga | Codificación corta | Ahorro |
|---------------|----------------|---------|
| `CALL $0010` (3 bytes) | `RST $10` (1 byte) | 2 bytes |
| `JP label` (3 bytes) | `JR label` (2 bytes) | 1 byte |
| `LD A, 0` (2 bytes) | `XOR A` (1 byte) | 1 byte |
| `CP 0` (2 bytes) | `OR A` (1 byte) | 1 byte |

Las instrucciones RST son críticas. `RST n` es un CALL de 1 byte a una de ocho direcciones ($00, $08, $10, $18, $20, $28, $30, $38). En el Spectrum, `RST $10` llama a la salida de caracteres de la ROM, `RST $28` entra en la calculadora. En una demo normal estas rutinas ROM son demasiado lentas. A 256 bytes, ahorrar 2 bytes por CALL lo es todo.

**Cada JP en una intro de 256 bytes debería ser un JR** -- todo el programa cabe dentro del rango -128..+127.

**4. Código auto-modificable para reusar secuencias.** ¿Necesitas una subrutina para operar en dos direcciones diferentes? Codifica la primera y parchea el operando para la segunda llamada. Más barato que pasar parámetros.

**5. Relaciones matemáticas entre constantes.** Si tu música necesita un período de tono de 200 y tu efecto necesita un contador de bucle de 200, usa el mismo registro. Si un valor es el doble de otro, usa `ADD A, A` (1 byte) en lugar de cargar una segunda constante (2 bytes).

---

## 13.3 Intros Famosas de 256 Bytes: Qué las Hizo Ingeniosas

La categoría de 256 bytes del ZX Spectrum tiene una rica historia. Estudiar las entradas ganadoras revela qué tipos de efectos caben en 256 bytes y qué estrategias creativas tienen éxito.

**Los efectos basados en atributos dominan.** La razón es aritmética: el área de atributos del Spectrum tiene 768 bytes (32 x 24), y puedes llenarla con un patrón computado usando un bucle anidado ajustado de 15-20 bytes. Los efectos a nivel de píxel requieren direccionar 6.144 bytes de memoria de pantalla entrelazada -- mucho más código solo para el cálculo de direcciones. A 256 bytes, simplemente no puedes permitirte la sobrecarga. Así que la gran mayoría de intros de 256 bytes trabajan en espacio de atributos: plasmas de color, patrones de interferencia, animaciones de gradiente, ciclado de colores. La memoria de píxeles o se queda en blanco, recibe un relleno de dither de una sola vez, o se deja con lo que la ROM ponga ahí.

**El sonido generativo supera al sonido secuenciado.** Una tabla de notas para una melodía cuesta bytes -- incluso una secuencia simple de 8 notas son 8 bytes, más la lógica de indexación. A 256 bytes, la estrategia ganadora es derivar el sonido del estado del efecto. Usa el contador de fotogramas como período de tono (el tono barre continuamente). Usa un byte de la computación visual como parámetro de ruido. O usa `LD A, R` -- lee el registro de refresco del Z80, que se incrementa en cada búsqueda de instrucción -- como fuente pseudo-aleatoria, luego enmascáralo a un rango pentatónico. El sonido no será una composición, pero estará *presente*, y la audiencia recordará "esa intro diminuta que tenía música."

**La ROM es tu biblioteca.** Cada byte de la ROM de 16K del Spectrum está disponible y no cuenta contra tu límite de tamaño. `RST $10` imprime caracteres usando el renderizado de fuente completo de la ROM -- 96 caracteres imprimibles, 8x8 píxeles cada uno, con gestión de cursor. Son miles de bytes de código de renderizado disponibles por 1 byte por llamada. `RST $28` accede a la calculadora de punto flotante, que puede computar seno, coseno y raíces cuadradas -- operaciones que costarían docenas de bytes implementar. El coste es velocidad (las rutinas ROM son lentas), pero en una intro de 256 bytes ejecutándose a 50fps con un efecto simple, a menudo tienes ciclos de sobra.

**Las entradas que ganan son las que parecen imposibles en su tamaño.** Los jueces y la audiencia reaccionan a la brecha entre la complejidad percibida y el tamaño del archivo. Una intro de 256 bytes con un plasma de color suave y una melodía reconocible genera más aplausos que una con un visual ligeramente mejor pero sin sonido. El truco es elegir un efecto que *se vea* complejo pero que *se codifique* barato. Los patrones de interferencia basados en XOR son perfectos: visualmente intrincados, matemáticamente triviales. El ciclado de colores a través de atributos es otro: el ojo percibe movimiento y profundidad, pero el código es solo incrementar valores en un bucle. Patrones de desplazamiento diagonal, animaciones de tablero de ajedrez, anillos en expansión -- todos pueden producirse con menos de 20 bytes de código de bucle interno si la fórmula se elige cuidadosamente.

---

## 13.4 El Truco de LPRINT

En 2015, diver4d publicó "Los secretos de LPRINT" en Hype, documentando una técnica más antigua que el propio demoscene -- una que apareció por primera vez en los cargadores de software pirata en casete en los años 80.

### Cómo funciona

La variable del sistema en la dirección 23681 ($5C81) controla a dónde las rutinas de salida de BASIC dirigen los datos. Normalmente apunta al búfer de impresora. Modifícala para apuntar a la memoria de pantalla, y LPRINT escribe directamente en la pantalla:

```basic
10 POKE 23681,64: LPRINT "HELLO"
```

Ese único POKE redirige el canal de impresora a $4000 -- el inicio de la memoria de pantalla.

### El efecto de transposición

El resultado visual no es solo texto en pantalla -- es texto *transpuesto*. La memoria de pantalla del Spectrum es entrelazada (Capítulo 2), pero el controlador de impresora escribe secuencialmente. Los datos aterrizan en la memoria de pantalla según la lógica lineal del controlador pero se *muestran* según el diseño entrelazado. El resultado cicla a través de 8 estados visuales a medida que progresa por los tercios de la pantalla -- una cascada de datos que se construye en bandas horizontales, desplazándose y recombinándose.

Con diferentes datos de caracteres -- caracteres gráficos, UDGs, o secuencias ASCII cuidadosamente elegidas -- la transposición produce patrones visuales impactantes. La sentencia LPRINT maneja todo el direccionamiento de pantalla, renderizado de caracteres y avance del cursor. Tu programa solo proporciona los datos.

### De cargadores piratas al arte demo

diver4d rastreó el truco hasta los cargadores de casetes piratas. Los piratas que añadían pantallas de carga personalizadas necesitaban efectos visuales en muy pocos bytes de BASIC -- LPRINT era ideal. La técnica cayó en desuso a medida que la escena se movió al código máquina.

Pero en 2011, JtN y 4D lanzaron **BBB**, una demo que deliberadamente volvió a LPRINT como declaración artística. El viejo truco del cargador pirata, enmarcado con intención, se convirtió en arte demo. La restricción -- BASIC, un hack de redirección de impresora, sin código máquina -- se convirtió en el medio.

### Por qué importa para el sizecoding

LPRINT logra una salida de pantalla compleja por casi cero bytes de tu propio código. La ROM hace el trabajo pesado. Tu contribución: un POKE para redirigir la salida, datos para imprimir, y `RST $10` (o LPRINT) para dispararlo. Aprovechas la ROM de 16K del Spectrum como un motor de salida de pantalla "gratuito" -- código que no cuenta contra tu límite de tamaño.

---

## 13.5 Intros de 512 Bytes: Espacio para Respirar

Duplicar de 256 a 512 bytes no es el doble -- es cualitativamente diferente. A 256, luchas por cada instrucción y el sonido es mínimo. A 512, puedes tener un efecto apropiado *y* sonido apropiado, o dos efectos con una transición.

### Lo Que Habilita Cada Nivel de Tamaño

El salto entre categorías de tamaño no es lineal. Cada duplicación abre posibilidades cualitativamente nuevas:

**256 bytes** es un efecto y quizá sonido primitivo. No puedes permitirte una tabla de datos más larga que unos 16 bytes. Cada variable vive en un registro o en el flujo de instrucciones (código auto-modificable). La salida de texto está limitada a unos pocos caracteres. Tienes espacio para un bucle anidado con 2-3 operaciones aritméticas en el cuerpo interno. El visual será basado en atributos, generado puramente desde aritmética. El sonido, si está presente, es un barrido de tono o notas aleatorias.

**512 bytes** te permite añadir una tabla de seno (32-64 bytes), un motor de música AY real (melodía + bajo en dos canales), o un segundo efecto visual con transición. Puedes permitirte una máquina de estados contada por fotogramas apropiada que cambie entre dos partes. El código auto-modificable se vuelve estructural en lugar de desesperado. Incluso podrías tener espacio para una cadena de texto corta (10-20 caracteres) mostrada con `RST $10`.

**1K (1.024 bytes)** es un mundo diferente. Puedes tener un reproductor de música estilo tracker con un patrón comprimido (un canal con un bucle de 32 pasos ocupa unos 80-120 bytes incluyendo el reproductor). Múltiples efectos con transiciones se vuelven estándar. Los efectos a nivel de píxel -- plasma simple en espacio de píxeles, texto desplazándose, barras raster -- se vuelven factibles porque puedes permitirte el cálculo de direcciones de memoria de pantalla. Puedes incluir una tabla de seno de 256 bytes, o generar una al inicio y guardarla en un búfer. A 1K, la restricción todavía moldea cada decisión, pero las decisiones son sobre *qué características incluir*, no sobre *qué instrucciones puedes permitirte*.

**Las intros de 4K y 8K** se acercan al territorio de demos cortas. A 4K, la compresión se vuelve viable y puedes incluir composiciones multi-efecto con música -- un salto cualitativo cubierto en la Sección 13.6. Una intro de 8K es una mini-demo pulida donde la restricción tiene más que ver con la compresión de datos que con trucos de tamaño a nivel de instrucción. Las técnicas de este capítulo siguen aplicándose, pero el enfoque cambia de "¿puedo ahorrar un byte?" a "¿puedo comprimir este flujo de datos?"

El punto dulce para aprender sizecoding es 256 bytes. A ese tamaño, cada técnica de este capítulo es obligatoria. A 512, tienes suficiente espacio para elegir. A 1K, la mentalidad de sizecoding ayuda pero no domina.

### Patrones comunes de 512 bytes

**Plasma vía sumas de tabla de seno.** La tabla de seno es la parte costosa. Una tabla completa de 256 bytes consume la mitad de tu presupuesto. Soluciones: una tabla de cuarto de onda de 64 entradas reflejada en tiempo de ejecución (ahorra 192 bytes), o generar la tabla al inicio usando la aproximación parabólica del Capítulo 4 (~20 bytes de código en lugar de 256 bytes de datos).

**Túnel vía consulta de ángulo/distancia.** A 512 bytes, calculas ángulo y distancia al vuelo usando aproximaciones burdas. Menor calidad visual que el túnel de Eager (Capítulo 9), pero reconociblemente un túnel.

**Fuego vía autómata celular.** Cada celda promedia sus vecinos de abajo, menos decaimiento. Pocas instrucciones por píxel, animación convincente, y a 512 bytes puedes añadir atributos para color *y* un sonido de beeper.

### Trucos de auto-modificación

La auto-modificación se vuelve estructural a 512 bytes. Incrusta el contador de fotograma *dentro* de una instrucción:

```z80 id:ch13_self_modifying_tricks
frame_ld:
    ld   a, 0               ; this 0 is the frame counter
    inc  a
    ld   (frame_ld + 1), a  ; update the counter in place
```

Sin variable separada. El contador vive en el flujo de instrucciones.

Parchea offsets de salto para cambiar entre efectos:

```z80 id:ch13_self_modifying_tricks_2
effect_jump:
    jr   effect_1               ; this offset gets patched
    ; ...
effect_1:
    ; render effect 1, then:
    ld   a, effect_2 - effect_jump - 2
    ld   (effect_jump + 1), a   ; next frame jumps to effect 2
```

### El truco del ORG

Elige la dirección ORG de tu programa para que los bytes de dirección en sí mismos sean datos útiles. Coloca código en $4000 y cada JR/DJNZ que apunte a etiquetas cerca del inicio genera bytes de offset pequeños -- utilizables como contadores de bucle, valores de color, o números de registro del AY. Si tu efecto necesita $40 (el byte alto de la memoria de pantalla) como constante, coloca código en una dirección donde $40 aparezca naturalmente en un operando de dirección. La *codificación del propio código* proporciona datos que necesitas en otra parte.

Este es el nivel más profundo del rompecabezas del sizecoding.

---

## 13.6 Intros de 4K: La Mini-Demo

4096 bytes es donde el sizecoding transiciona de "un truco" a "mini-demo". A 256 bytes, tienes espacio para un solo efecto y quizá sonido primitivo. A 512 o 1K, puedes tener un efecto apropiado con música. A 4K, puedes tener múltiples efectos, transiciones entre ellos, una banda sonora completa, y un arco narrativo coherente. La diferencia entre 1K y 4K es cualitativa, no solo cuantitativa -- es la diferencia entre "truco ingenioso" y "producción diminuta."

### La Compresión se Vuelve Viable

El cambio más grande a 4K es que la compresión de datos se paga sola. Un buen descompresor Z80 -- ZX0, Exomizer, o similar -- cuesta aproximadamente 150-200 bytes de código. A 256 o 512 bytes, esa sobrecarga es catastrófica. A 4K, es menos del 5% de tu presupuesto, y el retorno es enorme: una intro de 4K podría contener 6-8K de código y datos sin comprimir, empaquetados para caber en el límite. Tu espacio de trabajo real casi se duplica.

El flujo de trabajo se convierte en un bucle de retroalimentación: escribir código, ensamblar a binario, comprimir con ZX0, verificar el tamaño del archivo de salida, iterar. El número que importa ya no es el tamaño ensamblado -- es el tamaño *comprimido*. Esto cambia tu estrategia de optimización. Ya no estás contando bytes de instrucciones individuales. Estás pensando en qué se comprime bien.

El código con patrones repetitivos se comprime mejor que el código con alta entropía. Una tabla de valores de seno se comprime bien (suave, predecible). Una tabla de bytes aleatorios no. El código de efecto que reutiliza secuencias de instrucciones similares entre rutinas se comprime mejor que el código donde cada rutina tiene una estructura única. Este es un cambio sutil: optimizas no solo para *código pequeño* sino para *código compresible*.

### La Música Cabe

A 256 bytes, el sonido es un lujo -- un barrido de tono o notas pentatónicas aleatorias. A 4K, puedes tener una banda sonora real. Un motor de reproductor AY diminuto -- algo como la salida de Beepola o un tracker mínimo personalizado -- ocupa 200-400 bytes. Añade 500-1000 bytes de datos de patrón (comprimidos) y tienes una composición completa de tres canales AY con melodía, bajo y tambores. Estos números se comprimen bien porque los datos de patrones musicales son altamente repetitivos.

El impacto en la audiencia es desproporcionado. El sonido transforma una entrada de sizecoding de una curiosidad visual a una *experiencia*. En las proyecciones de compo, las intros con música puntúan dramáticamente más alto que las silenciosas de igual calidad visual. Si tienes 4K para trabajar y no estás incluyendo música, estás dejando puntos sobre la mesa.

### Estructura Multi-Efecto

A diferencia de 256 bytes donde estás limitado a un solo visual, 4K te da espacio para 2-4 efectos distintos con transiciones. El marco estructural es ligero: una tabla de escenas mapeando punteros de efecto a duraciones cuesta quizá 30 bytes:

```z80 id:ch13_multi_effect_structure
scene_table:
    DW effect_plasma    ; pointer to effect routine
    DB 150              ; duration in frames (3 seconds at 50fps)
    DW effect_tunnel
    DB 200
    DW effect_scroller
    DB 250
    DB 0                ; end marker

scene_runner:
    ld   hl, scene_table
.next_scene:
    ld   e, (hl)
    inc  hl
    ld   d, (hl)        ; DE = effect routine address
    inc  hl
    ld   a, (hl)        ; A = duration
    or   a
    ret  z              ; end of table
    inc  hl
    push hl             ; save table pointer
    ld   b, a           ; B = frame counter
.frame_loop:
    push bc
    push de
    call .call_effect
    pop  de
    pop  bc
    halt                ; wait for vsync
    djnz .frame_loop
    pop  hl
    jr   .next_scene

.call_effect:
    push de
    ret                 ; jump to DE via push+ret trick
```

Cada efecto individual podría ejecutar 500-1000 bytes de código. A 4K comprimido, puedes permitirte tres efectos sustanciales, una tabla de escenas, un reproductor de música, y lógica de transición (fundido a negro entre escenas es barato -- simplemente rellena a cero el área de atributos).

### GOA4K, inal y Megademica

**GOA4K** de Exploder^XTM es una intro de 4K para ZX Spectrum 128K que marca un hito y demuestra lo que es alcanzable cuando la compresión se encuentra con la programación ingeniosa. Empaqueta un rotozoomer chunky y otros efectos en 4096 bytes -- visuales que serían respetables en una demo de tamaño completo, comprimidos a un tamaño que cabrías en un solo sector de disco.

La historia no termina ahí. **SerzhSoft** tomó GOA4K y lo rehizo como **inal** -- una versión solo para 48K en solo 2980 bytes. El mismo impacto visual, en una máquina más restringida, en menos bytes. Esta es la comunidad de sizecoding en acción: un programador pone la barra, otro la supera desde una posición de partida más difícil.

SerzhSoft continuó ganando la compo de intro 4K en **Revision 2019** con **Megademica** -- compitiendo no en una categoría específica de ZX, sino contra todas las plataformas en el evento de demoscene más grande del mundo. Una intro de 4K para ZX Spectrum, juzgada junto a entradas de PC y Amiga, obtuvo el primer lugar. Esta es la trayectoria que el sizecoding de 4K permite: del técnico de escena local al reconocimiento global.

Estudiar entradas como estas revela un patrón: las mejores intros de 4K eligen efectos que son visualmente impresionantes *y* se comprimen bien, luego exprimen cada byte a través de un ciclo ajustado de empaquetar-probar-iterar.

### Los Compromisos de 4K

Trabajar a 4K introduce compromisos que no existen en tamaños más pequeños:

**La tasa de compresión dirige la elección de efecto.** No todos los efectos se comprimen igual. Un plasma que depende de una tabla de seno suave se comprime maravillosamente -- los datos de la tabla son predecibles, y el bucle de renderizado reutiliza patrones de instrucciones similares. Un efecto de dithering pseudo-aleatorio donde cada píxel se computa desde una fórmula diferente produce código de alta entropía que apenas se comprime. A 4K, eliges efectos parcialmente por su mérito visual y parcialmente por qué tan bien se empaqueta su implementación.

**El tiempo de arranque es visible.** La descompresión toma tiempo real -- típicamente 1-3 segundos en un Z80 a 3,5MHz para unos pocos kilobytes de datos. La audiencia ve una pausa antes de que la intro comience. La mayoría de intros de 4K enmascaran esto con un efecto de carga simple: llenar el borde con ciclado de colores, dibujar un patrón rápido en atributos, o mostrar una pantalla de título de un solo fotograma. El descompresor en sí se ejecuta desde un stub pequeño sin comprimir al inicio del archivo. Una vez que la descompresión termina, el stub salta al código desempaquetado y el espectáculo real comienza.

**Optimizas para tamaño empaquetado, no velocidad en tiempo de ejecución.** En una intro de 256 bytes, el mismo código que se ejecuta es el código que mides. A 4K, escribes código que se descomprime en RAM y luego se ejecuta desde ahí. Las restricciones de ROM desaparecen -- tu código desempaquetado reside en RAM libre. Pero el objetivo de optimización cambia: te importa cuántos bytes ocupa el binario empaquetado, no el tamaño ensamblado bruto. Un efecto que se ensambla a 900 bytes pero se comprime a 400 es mejor que uno que se ensambla a 600 pero se comprime a 500.

**Contando bytes empaquetados.** El proceso de compilación gana un paso de compresión. Ensamblar a binario, comprimir con ZX0 (o tu compresor de elección), verificar el tamaño del archivo de salida. Con sjasmplus:

```sh
sjasmplus --nologo --raw=build/intro4k.bin intro4k.a80
zx0 build/intro4k.bin build/intro4k.zx0
ls -l build/intro4k.zx0    # this is the number that must be <= 4096
```

El stub del descompresor prepuesto al archivo final también debe caber dentro del límite de 4096 bytes. Archivo total = stub del descompresor + carga comprimida. Un descompresor ZX0 típico es de unos 70 bytes en su forma más pequeña, dejando aproximadamente 4026 bytes para datos comprimidos.

### Categorías de Competición

Las fiestas de la demoscene ofrecen varias categorías con límite de tamaño más allá del clásico 256. Los niveles de competición comunes incluyen 4K, 8K, y a veces 16K, junto con los más pequeños 256 y 512. Las categorías específicas varían por fiesta -- Chaos Constructions, DiHalt, y Forever han alojado todas compos de 4K para el Spectrum. Algunas fiestas combinan plataformas (una compo de "intro 4K" aceptando entradas para cualquier plataforma de 8 bits), mientras que otras son específicas del Spectrum. Revisa las reglas de la fiesta antes de empezar -- el método de medición (tamaño de archivo bruto vs. imagen de memoria cargada) y el límite exacto de bytes importan.

A 8K y 16K, el enfoque es esencialmente el mismo que a 4K pero con más espacio para respirar. Una intro de 8K es una mini-demo pulida donde la tubería de compresión es estándar y el desafío creativo tiene más que ver con la dirección artística que con el conteo de bytes. A 16K, esencialmente estás haciendo una demo corta que resulta caber en 16K -- la restricción de tamaño moldea tu ambición pero no dicta tus elecciones de instrucciones. Las técnicas de sizecoding de este capítulo todavía ayudan en estos presupuestos más grandes, pero su impacto es proporcionalmente menor.

---

## 13.7 Práctica: Escribir una Intro de 256 Bytes Paso a Paso

Comienza con un plasma de atributos funcional (~400 bytes) y optimízalo a 256.

### Paso 1: La versión sin optimizar

Un plasma de atributos simple: llena 768 bytes de memoria de atributos con valores de sumas de seno, desplazados por un contador de fotograma. Sonido: una melodía cíclica en el canal A del AY. Esta versión es limpia, legible, y de aproximadamente 400 bytes -- la tabla de seno (32 bytes), tabla de notas (16 bytes), escrituras AY en línea, y el bucle de plasma con consultas de tabla.

### Paso 2: Reemplazar CALL con RST

Cualquier llamada a una dirección ROM que coincida con un vector RST ahorra 2 bytes por invocación. Para la salida del AY, reemplaza las seis escrituras verbosas de registros en línea (~60 bytes) con una pequeña subrutina:

```z80 id:ch13_step_2_replace_call_with_rst
ay_write:                      ; register in A, value in E
    ld   bc, $FFFD
    out  (c), a
    ld   b, $BF
    out  (c), e
    ret                        ; 8 bytes total
```

Seis llamadas (5 bytes cada una: cargar A + cargar E + CALL) = 30 + 8 = 38 bytes. Ahorro: ~22 bytes.

### Paso 3: Superponer datos con código

La tabla de seno de 32 bytes al punto de entrada se decodifica como instrucciones Z80 mayormente inofensivas ($00=NOP, $06=LD B,n, $0C=INC C...). Colócala al inicio del programa. En la primera ejecución, la CPU tropieza a través de estas "instrucciones," revolviendo algunos registros. El bucle principal luego salta más allá de la tabla y nunca la ejecuta de nuevo -- pero los datos permanecen para las consultas. Los bytes de la tabla cumplen doble función.

### Paso 4: Explotar el estado de los registros

Después de que el bucle de plasma escribe 768 atributos, HL = $5B00 y BC = 0 (de cualquier LDIR usado en la inicialización). Si la siguiente operación necesita estos valores, omite las cargas explícitas. El descubrimiento de Art-Top en NHBF fue exactamente esto: los valores de los registros de la limpieza de pantalla coincidían con la longitud de la cadena de texto. No fue planeado. Fue notado.

Después de cada pase de optimización, anota lo que cada registro contiene en cada punto. El estado de los registros es un recurso compartido -- la moneda fundamental del sizecoding.

### Paso 5: Codificaciones más pequeñas en todas partes

- `LD A, 0` -> `XOR A` (ahorrar 1 byte)
- `LD HL, nn` + `LD A, (HL)` -> `LD A, (nn)` (ahorrar 1 byte si HL no se necesita)
- `JP` -> `JR` en todas partes (ahorrar 1 byte cada vez)
- `CALL sub : ... : RET` -> caer directamente (ahorrar 4 bytes)
- `PUSH AF` para guardados temporales vs `LD (var), A` (ahorrar 2 bytes)

### Paso 6: Contando Bytes con Precisión

La intuición sobre "qué tan grande es esto" no es confiable. Necesitas contar. Hay tres métodos, y los size-coders serios usan los tres.

**Salida del ensamblador.** sjasmplus puede reportar el tamaño ensamblado. La directiva `DISPLAY` imprime a la consola durante el ensamblaje, y `ASSERT` impone el límite:

```z80 id:ch13_step_6_counting_bytes
intro_end:
    ASSERT intro_end - init <= 256, "Intro exceeds 256 bytes!"
    DISPLAY "Intro size: ", /D, intro_end - init, " bytes"
```

Ejecuta el ensamblador después de cada cambio. La línea DISPLAY te dice dónde estás; el ASSERT captura desbordamientos antes de que pierdas tiempo probando un binario roto.

**Análisis del archivo de símbolos.** Ensambla con `--sym=build/intro.sym` para obtener una tabla de símbolos. Compara direcciones de etiquetas para encontrar exactamente cuántos bytes ocupa cada sección. Cuando tu intro tiene 262 bytes y necesitas cortar 6, el archivo de símbolos te dice que la inicialización AY son 22 bytes (¿puedes cortar 2?), el bucle de efecto son 38 bytes (¿puedes fusionar los contadores de fila y columna?), la escritura de vuelta del contador de fotogramas son 8 bytes (¿puedes reestructurar para que sean 5?). Sin este desglose, estás adivinando.

**Inspección del volcado hexadecimal.** Después de ensamblar, examina el binario crudo en un editor hexadecimal (o `xxd build/intro.bin`). El volcado hexadecimal te muestra los bytes reales que la CPU ejecutará. Notarás redundancias invisibles en el código fuente: dos cargas consecutivas que podrían ser una, un código de operación cuyo valor coincide con datos que necesitas en otro lugar, una secuencia de NOPs dejada por una alineación accidental. El volcado hexadecimal es la verdad fundamental. El código fuente es una abstracción sobre ella.

### El empujón final

Los últimos 10-20 bytes son los más difíciles. Reestructuración: reordena el código para que los fall-throughs eliminen instrucciones JR. Fusiona los bucles de sonido y visual. Incrusta bytes de datos en el flujo de instrucciones -- si necesitas $07 como datos y también necesitas un `RLCA` (código de operación (opcode) $07), arregla que uno sirva como ambos.

En esta etapa, mantén un registro. Anota cada cambio que pruebes: "moví la inicialización AY antes del relleno de píxeles: ahorré 2 bytes (reutilización del registro C), perdí 1 byte (necesito LD B extra). Neto: +1 byte." Muchos cambios no ayudan. Algunos empeoran las cosas. Sin un registro, probarás el mismo callejón sin salida dos veces. Con un registro, construyes un mapa del espacio de soluciones.

Prueba reestructuraciones radicales. ¿Puede el bucle del efecto visual también actualizar el AY? Si el bucle interno itera 768 veces (una por celda de atributo), y escribes un nuevo valor de tono cada 32 iteraciones (una por fila), la actualización de sonido sucede dentro del bucle visual al coste de una verificación `BIT 4, E` / `JR NZ` -- 4 bytes para fusionar dos rutinas que previamente necesitaban código de marco separado. A veces fusionar ahorra 10 bytes; a veces cuesta 5. No sabrás hasta que lo intentes.

**La vía de escape: elige un efecto diferente.** Si tu plasma necesita una tabla de seno y estás 30 bytes por encima, ninguna cantidad de micro-optimización te salvará. Cambia a un efecto que genere su visual desde aritmética de registros pura: patrones XOR, aritmética modular, manipulación de bits. Un patrón de interferencia XOR como el de `intro256.a80` necesita cero bytes de datos. El visual es menos suave que un plasma de seno, pero cabe. A 256 bytes, "cabe" es el único criterio que importa.

Miras fijamente el volcado hexadecimal. Pruebas mover la rutina de sonido antes de la rutina visual. Pruebas reemplazar la tabla de seno con un generador en tiempo de ejecución. Cada intento reordena los bytes. A veces todo se alinea.

La satisfacción de encajar una experiencia audiovisual coherente en 256 bytes -- de resolver el rompecabezas -- es real y específica y diferente a cualquier otra sensación en la programación.

---

## 13.8 Música en Sizecoding: Bytebeat en AY

En la demoscene de PC, **bytebeat** es un enfoque de sonido basado en fórmulas: una sola expresión como `t*((t>>12|t>>8)&63&t>>4)` genera muestras PCM, produciendo música sorprendentemente compleja desde unos pocos bytes de código. El concepto fue popularizado por Viznut (Ville-Matias Heikkilä) en 2011, y las intros de 256 bytes de PC rutinariamente usan bytebeat para sus bandas sonoras.

En el ZX Spectrum, la situación es diferente. El AY-3-8910 no es un DAC -- es un generador de tono y ruido con registros de período y volumen por canal. No puedes alimentarlo con muestras PCM en el sentido tradicional (la reproducción de muestras por registro de volumen existe pero cuesta demasiados ciclos para una intro de sizecoding). En cambio, "bytebeat AY" significa computar **períodos de tono y envolventes de volumen desde fórmulas matemáticas** conducidas por un contador de fotogramas.

El principio es el mismo que el bytebeat de PC: reemplazar datos de música almacenados con una fórmula. El destino de salida es diferente.

### El Motor de Fórmulas AY Mínimo

Un enfoque típico en una intro de 256 bytes:

```z80 id:ch13_the_minimal_ay_formula_engine
; Frame-driven AY "bytebeat" — ~20 bytes
; A = frame counter (incremented each HALT)
    ld   e, a
    and  $1F              ; period = low 5 bits of frame
    ld   d, a             ; D = tone period low
    ld   a, e
    rrca
    rrca
    rrca
    and  $0F              ; volume = bits 5-7 of frame, shifted
    ; Write to AY: register 0 = tone period low, register 8 = volume
```

Esto produce un tono cíclico que barre a través de períodos y aparece/desaparece gradualmente -- no es música en ningún sentido tradicional, pero es sonido reconociblemente estructurado. El truco es elegir fórmulas que produzcan **patrones musicalmente interesantes** desde operaciones bitwise simples.

### Técnicas para Fórmulas con Mejor Sonido

**Enmascaramiento pentatónico.** Las fórmulas bitwise crudas producen ruido cromático. Enmascara el valor del período a través de una consulta pentatónica (5 bytes: los intervalos de notas) para restringir la salida a una escala agradable. Cinco bytes de datos compran sonido musicalmente coherente.

**Fórmulas multicanal.** El AY tiene tres canales de tono. Usa diferentes rotaciones de bits del mismo contador de fotogramas para cada canal -- producirán patrones relacionados pero distintos, creando una impresión de armonía:

```z80 id:ch13_techniques_for_better
    ld   a, (frame)
    call .write_ch_a      ; channel A: raw formula
    ld   a, (frame)
    rrca
    rrca                  ; channel B: frame >> 2
    call .write_ch_b
    ld   a, (frame)
    add  a, a             ; channel C: frame << 1
    call .write_ch_c
```

**Percusión de ruido.** Alterna el generador de ruido en intervalos de fotograma específicos (cada 8 o 16 fotogramas) para un pulso rítmico. Coste: un `AND` + un `OUT` — unos 6 bytes para un patrón de bombo básico.

**LD A,R como entropía.** El registro R (contador de refresco de memoria) es efectivamente aleatorio desde una perspectiva musical. Mézclalo con el contador de fotogramas: `ld a,r : xor (frame)` produce texturas en evolución que nunca se repiten del todo. Útil para paisajes sonoros ambientales o experimentales.

### Bytebeat vs. Música Secuenciada

| | Bytebeat (fórmula) | Secuenciada (datos de patrón) |
|---|---|---|
| **Bytes** | 10-30 (solo código) | 200-400 (reproductor) + 500+ (patrones) |
| **Calidad musical** | Abstracta, generativa, alienígena | Melódica, estructurada, humana |
| **Mejor en** | 256b, 512b | 1K, 4K |
| **Sonido** | Ruido rítmico, barridos, zumbidos | Melodías reales |

A 256 bytes, bytebeat es tu única opción realista -- no hay espacio para un reproductor de patrones. A 512, puedes permitirte un secuenciador diminuto con 4-8 notas. A 4K, usa un reproductor real. El enfoque bytebeat no es inferior -- produce un *tipo diferente* de sonido que encaja con la estética de programas diminutos. Algunas de las intros de 256 bytes más memorables son memorables precisamente porque su sonido es alienígena y generativo, no porque imite música convencional.

---

## 13.9 Gráficos Procedurales: La Compo de GFX Renderizado

Algunas fiestas de la demoscene organizan una competición de **gráficos renderizados** (o **gráficos procedurales**): envía un programa que genere una imagen estática. Sin bitmaps pre-dibujados, sin datos cargados -- cada píxel debe ser computado. La salida visual se juzga como obra de arte, pero debe nacer del código.

En el Spectrum, esto significa que tu programa llena el área de pantalla de 6.912 bytes (bitmap + atributos) algorítmicamente, luego se detiene. La imagen permanece en pantalla para el jurado. Los límites de tamaño de archivo varían -- algunas compos permiten cualquier tamaño, otras imponen límites de 256 bytes o 4K, convirtiéndolo en un híbrido de sizecoding y arte digital.

### Por Qué el Spectrum Es Interesante para Esto

Las restricciones de pantalla del Spectrum -- píxeles de 1 bit con color de atributo 8×8 -- hacen de los gráficos procedurales un desafío genuinamente diferente de hacerlo en un VGA de 256 colores o un framebuffer de 24 bits. No puedes simplemente computar valores RGB por píxel. Debes pensar en términos de:

- **Patrones de píxeles** dentro de celdas de caracteres de 8×8 (dithering, medio tono)
- **Color de atributo** por celda (2 colores de una paleta de 15)
- **La interacción** entre patrón de píxeles y atributo -- un gradiente necesita tanto dithering suave COMO transiciones de atributo suaves

Esta restricción crea un estilo visual distintivo. Los gráficos procedurales del Spectrum no se parecen a nada más -- la cuadrícula de colores les da una calidad de mosaico que es parte de la estética, no una limitación a ocultar.

### Enfoques Comunes

**Conjuntos de Mandelbrot y Julia.** La elección clásica. El bucle de iteración es compacto (~30-50 bytes para el núcleo), y el detalle fractal es infinito -- las coordenadas de zoom y el conteo de iteraciones son los únicos parámetros. Mapea el conteo de iteraciones a patrón de dither para datos de píxeles, mapea a índice de paleta para atributos. Un renderizador de Mandelbrot cabe cómodamente en 256 bytes y produce imágenes que parecen hechas a mano.

**Patrones de interferencia.** Múltiples ondas sinusoidales o cosenoidales superpuestas, muestreadas en cada posición de píxel. `pixel = sin(x*freq1 + phase1) + sin(y*freq2 + phase2) > threshold`. Produce formas orgánicas y fluidas. En el Spectrum, aplica un umbral a la suma para obtener el bit de píxel, cuantiza para obtener el color de atributo.

**Campos de distancia.** Computa la distancia desde cada píxel a un conjunto de formas (círculos, líneas, curvas Bézier). Aplica umbral a la distancia para datos de píxeles, mapéala a color para atributos. Unas pocas formas pueden producir imágenes sorprendentemente complejas -- solo círculos superpuestos pueden crear patrones intrincados.

**Sistemas-L y fractales.** Estructuras de ramificación recursiva (árboles, helechos, triángulos de Sierpinski). La recursión se mapea naturalmente a código Z80 basado en pila, y la salida visual tiene complejidad orgánica desde código mínimo. Un renderizador de triángulo de Sierpinski son unos 20 bytes; un árbol ramificado con ángulos aleatorios son quizá 80.

### El Presupuesto de Bytes para Arte

En una compo de GFX renderizado con límite de tamaño, cada byte va hacia la complejidad visual. No hay bucle de fotograma, sin sonido, sin animación -- solo un programa en línea recta que llena la pantalla y se detiene. Esto significa que tu presupuesto completo va a código de renderizado y generación de coordenadas. A 256 bytes, puedes producir un fractal detallado. A 4K (comprimido), puedes generar imágenes con múltiples capas, texturas computadas, y dithering cuidadoso que se acercan a la calidad dibujada a mano.

El criterio de juicio es puramente visual -- la audiencia vota la imagen, no el código. Pero la restricción de código moldea la estética. Los gráficos procedurales del Spectrum tienen un aspecto reconocible: precisión matemática, detalle fractal, y la cuadrícula de colores característica del renderizado basado en atributos. Las mejores entradas abrazan estas restricciones como estilo en lugar de luchar contra ellas.

---

## 13.10 El Sizecoding como Arte

El sizecoding te enseña cosas que mejoran toda tu programación: la disciplina de cuestionar cada byte agudiza la conciencia de codificación de instrucciones, el hábito de buscar superposiciones se transfiere a cualquier trabajo de optimización, y la práctica de explotar el estado inicial y los efectos secundarios te hace un mejor programador de sistemas.

---

## Resumen

- Las competiciones de **sizecoding** requieren programas completos en 256, 512, 1K, 4K u 8K bytes -- límites estrictos que demandan un enfoque fundamentalmente diferente de la programación.
- **El kit de herramientas del size-coder** incluye suposiciones de inicialización de registros, DJNZ como decremento-y-salto combinado, RST como CALL de 1 byte, instrucciones superpuestas, y abuso de banderas vía SBC A,A -- trucos que ahorran 1-5 bytes cada uno pero se acumulan a lo largo de un programa.
- **NHBF** (UriS, CC 2025) demuestra la mentalidad de 256 bytes: cada byte cumple doble función, los estados de registro de una rutina alimentan la siguiente, la elección de instrucción está impulsada puramente por el tamaño de codificación.
- **El presupuesto de bytes** para una intro típica de 256 bytes asigna ~90-130 bytes al marco (relleno de pantalla, inicialización AY, sincronización de fotograma, estructura de bucle), dejando 120-160 bytes para el efecto creativo real.
- **Elegir el efecto correcto** importa más que la micro-optimización: los visuales basados en atributos con fórmulas aritméticas (XOR, matemáticas modulares) se codifican baratos; los efectos a nivel de píxel y las tablas de datos consumen demasiados bytes a 256.
- **El truco de LPRINT** (diver4d, 2015) redirige la salida de impresora de BASIC a la memoria de pantalla vía la dirección 23681, produciendo patrones visuales complejos en un puñado de bytes -- de cargadores de casetes piratas al arte de demo.
- **Cada nivel de tamaño es cualitativamente diferente:** 256 bytes permite un efecto con sonido mínimo; 512 añade tablas de seno y música de dos canales; 1K habilita efectos a nivel de píxel, música tracker, y múltiples partes; 4K cruza el umbral al territorio de mini-demo con compresión, bandas sonoras completas, y composiciones multi-efecto.
- **Las intros de 4K** son donde la compresión se vuelve viable: un descompresor de ~200 bytes desbloquea 6-8K de espacio de trabajo, los reproductores de música con datos de patrón caben cómodamente, y las tablas de escenas habilitan 2-4 efectos distintos con transiciones. El objetivo de optimización cambia del tamaño ensamblado bruto al tamaño empaquetado comprimido.
- **El bytebeat AY** reemplaza datos de música almacenados con fórmulas: computa períodos de tono y volúmenes desde el contador de fotogramas usando aritmética bitwise. A 256 bytes, el sonido basado en fórmulas (10-30 bytes) es la única opción; a 4K, cambia a un reproductor de patrones real. El enmascaramiento pentatónico, la rotación de bits multicanal, y la percusión de ruido añaden musicalidad por bytes mínimos.
- **Los gráficos procedurales** (GFX renderizado) requieren que cada píxel sea computado, no cargado. Los píxeles de 1 bit del Spectrum con color de atributo 8×8 hacen de esto un desafío único -- conjuntos de Mandelbrot, patrones de interferencia, campos de distancia, y sistemas-L todos producen resultados distintivos dentro de la estética de la cuadrícula de atributos.
- **El proceso de optimización** se mueve desde cambios estructurales (eliminar tablas, fusionar bucles) a elecciones de codificación (RST por CALL, JR por JP, XOR A por LD A,0) a descubrimientos fortuitos (estados de registro alineándose con necesidades de datos).
- **Contar bytes con precisión** -- vía DISPLAY/ASSERT del ensamblador, análisis de archivo de símbolos, e inspección de volcado hexadecimal -- es esencial. La intuición sobre el tamaño del código no es confiable.
- **El truco del ORG** -- elegir tu dirección de carga para que los bytes de dirección sirvan como datos útiles -- representa el nivel más profundo del rompecabezas.

---

## Inténtalo tú mismo

1. **Empieza grande, reduce.** Escribe un plasma de atributos con un contador de fotograma. Hazlo funcionar a cualquier tamaño. Luego optimiza a 512 bytes, rastreando cada byte ahorrado y cómo.

2. **Explora LPRINT.** En BASIC, prueba `POKE 23681,64 : FOR i=1 TO 500 : LPRINT CHR$(RND*96+32); : NEXT i`. Observa cómo los datos transpuestos llenan la pantalla. Experimenta con diferentes rangos de caracteres.

3. **Mapea el estado de tus registros.** Escribe un programa pequeño y anota lo que contiene cada registro en cada punto. Busca lugares donde la salida de una rutina coincide con la entrada necesaria de otra.

4. **Estudia los vectores RST.** Desensambla la ROM del Spectrum en $0000, $0008, $0010, $0018, $0020, $0028, $0030, $0038. Estas son tus subrutinas "gratuitas."

5. **El desafío de 256 bytes.** Lleva la práctica de este capítulo a 256 bytes. Tendrás que tomar decisiones difíciles sobre qué conservar y qué eliminar. Esa es la cuestión.

---

*Siguiente: Capítulo 14 -- Compresión: Más datos en menos espacio. Pasamos de programas que caben en 256 bytes al problema de meter kilobytes de datos en kilobytes de almacenamiento, con el benchmark comprehensivo de Introspec de 10 compresores como nuestra guía.*

> **Fuentes:** UriS "NHBF Making-of" (Hype, 2025); diver4d "LPRINT Secrets" (Hype, 2015)
