# Apéndice F: Variantes del Z80 --- Juegos de instrucciones extendidos

> *"El mismo juego de instrucciones, una máquina completamente diferente."*
> -- Capítulo 22

El Zilog Z80 no se quedó congelado en 1976. A lo largo de cinco décadas, el diseño original ha sido clonado, extendido, reimaginado y --- en el caso del ZX Spectrum Next --- reconstruido por la misma comunidad que pasó treinta años maldiciendo sus limitaciones. Este apéndice examina las principales variantes del Z80 y sus extensiones de juego de instrucciones, con enfoque en lo que importa para programadores de la demoscene y de juegos. El juego de instrucciones estándar del Z80 se cubre en el Apéndice A; el eZ80 recibe un análisis en profundidad en el Apéndice E. Este apéndice es la visión general --- cómo se relacionan las variantes, qué añade cada una y por qué.

---

## 1. El árbol genealógico del Z80

El Z80 fue diseñado por Federico Faggin y Masatoshi Shima en Zilog en 1976 como sucesor compatible en software del Intel 8080. Se convirtió en el CPU de 8 bits más utilizado de la historia, impulsando desde máquinas de negocios con CP/M hasta gabinetes de arcade y toda una generación de ordenadores domésticos. El juego de instrucciones quedó congelado en su lanzamiento y nunca fue extendido oficialmente por Zilog --- hasta el eZ80, dos décadas después.

Pero otros sí lo extendieron. Aquí está la familia de un vistazo:

| Variante | Año | Máquina notable | Adición clave |
|----------|-----|-----------------|---------------|
| Z80 (Zilog) | 1976 | ZX Spectrum, MSX, Amstrad CPC | El original. 158 instrucciones documentadas. |
| KR1858VM1 (Soviético) | ~1986 | Pentagon, Scorpion | Clon exacto. Sin cambios en instrucciones. |
| NSC800 (National Semi) | 1980 | Varios embebidos | Z80 CMOS con bus estilo 8085. Sin instrucciones nuevas. |
| R800 (ASCII Corp) | 1990 | MSX turboR | Compatible con Z80, pipeline radicalmente diferente. MULUB, MULUW. |
| eZ80 (Zilog) | 2001 | Agon Light 2 | Direccionamiento de 24 bits, MLT, LEA, PEA, modo ADL. |
| Z80N (equipo Next) | 2017 | ZX Spectrum Next | Lista de deseos de la demoscene: MUL, MIRROR, LDIRX, PIXELDN, desplazamientos barrel. |

El Z80 y sus clones comparten un juego de instrucciones idéntico. El R800, eZ80 y Z80N añadieron cada uno instrucciones para resolver problemas específicos --- pero problemas muy diferentes, reflejando objetivos de diseño muy diferentes.

---

## 2. Z80N --- La lista de deseos del demoscener

El Z80N es el CPU del ZX Spectrum Next. Fue diseñado por Victor Trucco, Fabio Belavenuto y el equipo Next --- personas que habían pasado décadas escribiendo código Z80 y sabían exactamente dónde dolía. Cada nueva instrucción aborda un punto de dolor específico y documentado de treinta años de programación en Spectrum. El Z80N funciona a 28 MHz (8x el reloj del Spectrum original) y añade aproximadamente 40 instrucciones nuevas, todas codificadas en el espacio de opcodes `$ED xx` previamente sin usar.

La mejor manera de entender las extensiones del Z80N es por el problema que resuelve cada instrucción.

### Screen Navigation (the DOWN_HL problem)

En un Spectrum estándar, calcular una dirección de pantalla a partir de coordenadas de píxel toma 50-60 T-states y una página de código (ver `pixel_addr` en el Apéndice A). Moverse un píxel hacia abajo requiere la infame rutina `DOWN_HL` --- un laberinto condicional de INC, AND, ADD y SUB que maneja los límites de carácter y los límites de tercio. El Z80N reemplaza todo esto con instrucciones individuales.

| Instrucción | Bytes | T | Qué reemplaza |
|-------------|-------|---|---------------|
| `PIXELDN` | 2 | 8 | La secuencia `DOWN_HL` de 10+ instrucciones (verificar límite de tercio, manejar el desbordamiento, ajustar H y L). Mueve HL una fila de píxeles hacia abajo en la memoria de pantalla. |
| `PIXELAD` | 2 | 8 | Cálculo completo de dirección de pantalla a partir de coordenadas (D,E). Reemplaza la rutina `pixel_addr` (~55T, 15+ instrucciones). |
| `SETAE` | 2 | 8 | Establece el bit de píxel apropiado en A basándose en los 3 bits bajos de E (la coordenada x). Reemplaza una tabla de consulta o secuencia de desplazamiento. |

Con estas tres instrucciones, la secuencia completa de trazado de píxeles que consumía más de 70 T-states y más de 20 bytes en el Z80 original se convierte en:

```z80
; Z80N: plot pixel at (D=y, E=x) — 23T total
    pixelad             ; 8T  HL = screen address from (D,E)
    setae               ; 8T  A = pixel bit mask from E
    or   (hl)           ; 7T  set pixel (non-destructive)
    ; ... ld (hl), a to write
```

### Sprite Rendering (the masked blit problem)

La operación más intensiva en CPU en cualquier juego o demo de Spectrum es el blit de sprite con máscara: copiar un bloque rectangular de datos de sprite a la memoria de pantalla mientras se omiten los píxeles transparentes. En el Z80 estándar, esto requiere un bucle interno de LD/AND/OR/LD por byte, típicamente 30-40 T-states por byte de píxel. El Z80N añade instrucciones de copia en bloque con transparencia incorporada.

| Instrucción | Bytes | T | Qué reemplaza |
|-------------|-------|---|---------------|
| `LDIX` | 2 | 16 | `LDI` pero omite la copia si `(HL) == A`. Copia transparente en una instrucción: carga A con el color transparente, apunta HL a la fuente, DE al destino, y cada byte se copia solo si no es el valor transparente. |
| `LDDX` | 2 | 16 | Igual que LDIX pero decrementando (como `LDD`). |
| `LDIRX` | 2 | 21/16 | LDIX con repetición. Blit de sprite con máscara por hardware en una sola instrucción. Copia BC bytes de (HL) a (DE), omitiendo cualquier byte igual a A. 21T por byte mientras BC>0, 16T en la iteración final. |
| `LDDRX` | 2 | 21/16 | LDDX con repetición. |
| `LDPIRX` | 2 | 21/16 | Relleno de patrón con transparencia desde una fuente alineada a 8 bytes. Lee de `(HL & $FFF8) + (E & 7)`, copia a (DE) si no es igual a A, incrementa DE, decrementa BC. Renderizador de fondo de baldosas por hardware. 21T por byte mientras BC>0, 16T en la iteración final. |

Solo `LDIRX` reemplaza el bucle interno más intensamente optimizado en décadas de código de juegos para Spectrum. `LDPIRX` es aún más exótico --- trata la fuente como un patrón repetitivo de 8 bytes, dándote efectivamente un renderizador de baldosas por hardware con transparencia. Combinadas con el hardware de Layer 2 y tilemap del Next, estas instrucciones hacen del Spectrum Next una plataforma cualitativamente diferente para juegos con muchos sprites.

### Arithmetic (the multiply problem)

El Z80 no tiene instrucción de multiplicación. Cada multiplicación en código de Spectrum es un bucle de desplazamiento y suma que cuesta 150-250 T-states (ver `mulu112` en el Apéndice A). El Z80N soluciona esto con una sola instrucción.

| Instrucción | Bytes | T | Qué reemplaza |
|-------------|-------|---|---------------|
| `MUL D,E` | 2 | 8 | Multiplicación 8x8 sin signo, resultado en DE. Reemplaza el bucle de desplazamiento y suma de ~200T. |

Ocho T-states. A 28 MHz, eso son 286 nanosegundos. La misma operación en un Spectrum estándar a 3.5 MHz toma aproximadamente 57 microsegundos --- una mejora de 200:1 cuando consideras tanto el reloj más rápido como la instrucción más rápida. Matrices de rotación, transformaciones de coordenadas, mapeado de texturas, proyección en perspectiva --- todo lo que necesita multiplicación es fundamentalmente más barato en el Z80N.

### Bit Manipulation

| Instrucción | Bytes | T | Qué reemplaza |
|-------------|-------|---|---------------|
| `MIRROR` | 2 | 8 | Invierte los 8 bits de A. Volteo horizontal de sprite sin tabla de consulta de 256 bytes. En el Z80 estándar, invertir los bits de A requiere una secuencia desenrollada de 18 instrucciones (`LD B,A : XOR A` luego 8× `RR B : RLA`, ~104T) o una tabla de consulta de 256 bytes (11T pero cuesta 256 bytes de RAM). |
| `SWAPNIB` | 2 | 8 | Intercambia los nibbles alto y bajo de A. Reemplaza `RLCA : RLCA : RLCA : RLCA` (16T, 4 bytes). |
| `TEST nn` | 3 | 11 | `AND A, nn` sin almacenar el resultado --- establece banderas pero preserva A. Como un CP para AND bit a bit. Similar a la instrucción TST del eZ80. |

`MIRROR` es particularmente valioso para juegos. Sin él, cada sprite volteado horizontalmente necesita una copia pre-volteada en memoria (duplicando los datos del sprite) o una tabla de consulta de inversión de bits de 256 bytes más consultas por byte en la tabla. Con él, puedes voltear sprites al vuelo a 8T por byte.

### Barrel Shifts (the multi-bit shift problem)

En el Z80 estándar, desplazar un valor de 16 bits más de un bit requiere un bucle: `SLA E : RL D` por bit, costando 16T por posición de bit. Desplazar DE a la izquierda 5 bits cuesta 80T. El Z80N añade instrucciones de desplazamiento barrel que desplazan DE un número arbitrario de posiciones (especificado en B) en tiempo constante.

| Instrucción | Bytes | T | Qué reemplaza |
|-------------|-------|---|---------------|
| `BSLA DE,B` | 2 | 8 | Desplazar DE a la izquierda B bits. Reemplaza `B * (SLA E : RL D)`. |
| `BSRA DE,B` | 2 | 8 | Desplazamiento aritmético de DE a la derecha B bits (con extensión de signo). |
| `BSRL DE,B` | 2 | 8 | Desplazamiento lógico de DE a la derecha B bits (rellenando con ceros). |
| `BSRF DE,B` | 2 | 8 | Desplazar DE a la derecha B bits, rellenando con bit 15. |
| `BRLC DE,B` | 2 | 8 | Rotar DE a la izquierda B bits (circular). |

Estas son enormemente útiles en aritmética de punto fijo, sub-posicionamiento de píxeles y cualquier código que convierta entre escalas enteras. Una operación común como "multiplicar por 5 y desplazar a la derecha 3" que tomaría ~50T en un Z80 estándar se vuelve trivial.

### Convenience Instructions

| Instrucción | Bytes | T | Qué reemplaza |
|-------------|-------|---|---------------|
| `PUSH nn` | 4 | 23 | Empujar un valor inmediato de 16 bits a la pila. Sin necesidad de registro. Ahorra el patrón `LD rr, nn : PUSH rr` (21T, 4 bytes en el Z80 original --- mismo tamaño en bytes, 2T *más lento*, pero no destruye un par de registros). Cuando el par de registros ya está en uso, PUSH nn ahorra un par PUSH/POP alrededor del LD+PUSH, lo que más que compensa. |
| `ADD HL,A` | 2 | 8 | Sumar A a HL. Reemplaza la secuencia de 5 instrucciones y 23T: `ADD A,L : LD L,A : ADC A,H : SUB L : LD H,A` (o el equivalente usando un registro libre). |
| `ADD DE,A` | 2 | 8 | Igual que ADD HL,A pero para DE. |
| `ADD BC,A` | 2 | 8 | Igual para BC. |
| `NEXTREG reg,val` | 4 | 20 | Escritura directa a un registro de hardware del Next. Sin necesidad de configurar puertos de E/S. Reemplaza `LD BC,$243B : OUT (C),reg : LD BC,$253B : OUT (C),val` --- cuatro instrucciones, 8 bytes, ~48T. |
| `NEXTREG reg,A` | 3 | 17 | Escribir A en un registro de hardware del Next. |
| `OUTINB` | 2 | 16 | `OUT (C),(HL) : INC HL` combinados. Útil para transmitir datos a puertos de E/S. |

### The Big Picture

El Z80N es, en un sentido real, treinta años de frustración de la demoscene fundidos en silicio. Cada instrucción es una cicatriz de un dolor específico y bien documentado:

- `PIXELDN` existe porque cada programador de Spectrum ha escrito `DOWN_HL` al menos una vez, ha depurado el caso del límite de tercio al menos dos veces, y ha deseado no tener que hacerlo nunca más.
- `MIRROR` existe porque cada programador de juegos ha desperdiciado 256 bytes en una tabla de inversión de bits para volteos horizontales de sprites.
- `LDIRX` existe porque el bucle interno del blit con máscara es donde la mayoría de los juegos de Spectrum gastan la mayor parte de su tiempo de CPU.
- `MUL D,E` existe porque el bucle de multiplicación por desplazamiento y suma es la subrutina más reimplementada en la historia del Z80.

A diferencia del eZ80 (diseñado por Zilog para mercados embebidos) o el R800 (diseñado por ASCII Corporation para la plataforma MSX), el Z80N fue diseñado por la comunidad, para la comunidad. El juego de instrucciones se lee como una lista de deseos de la demoscene porque *es* una lista de deseos de la demoscene --- el equipo del Next solicitó aportes de codificadores activos de Spectrum y priorizó las instrucciones que eliminarían más dolor de las operaciones más comunes.

---

## 3. eZ80 --- La extensión empresarial

El eZ80 es el sucesor oficial de Zilog al Z80, diseñado para sistemas embebidos que necesitan más de 64 KB de espacio de direcciones. Es un superconjunto estricto del Z80 --- cada opcode del Z80 es válido y se comporta de forma idéntica. Las extensiones son arquitectónicas más que computacionales:

- **Direccionamiento de 24 bits y modo ADL.** Los registros pueden ser de 16 o 24 bits dependiendo del modo de operación. El modo ADL (Address Data Long) te da registros de 24 bits y un espacio de direcciones plano de 16 MB. El modo compatible Z80 se comporta exactamente como un Z80 estándar con MBASE proporcionando los 8 bits superiores de dirección faltantes.

- **MLT rr --- multiplicación 8x8 sin signo.** `MLT BC` multiplica B por C y almacena el resultado de 16 bits en BC. Similarmente para `MLT DE` (D * E -> DE) y `MLT HL` (H * L -> HL). Esto es más flexible que el `MUL D,E` del Z80N, que solo opera sobre DE. El eZ80 te da tres unidades de multiplicación independientes. A 6 T-states en el eZ80 (funcionando a 18.432 MHz en el Agon), esto es extremadamente rápido.

- **LEA y PEA.** Load Effective Address y Push Effective Address --- instrucciones de cálculo de direcciones indexadas. `LEA rr, IX+d` carga la dirección calculada en un par de registros sin acceder a memoria. `PEA IX+d` empuja la dirección calculada a la pila. Útiles para paso de parámetros y aritmética de punteros.

- **TST (test) y TSTIO.** Test AND no destructivo, similar al `TEST nn` del Z80N. `TSTIO` testea un valor de puerto de E/S contra una máscara.

- **IN0/OUT0.** Acceso de E/S al espacio de periféricos interno (direcciones $00--$FF).

El eZ80 fue diseñado para control industrial, equipamiento de redes e impresoras --- no para retrocomputación. Pero aterrizó en el Agon Light 2, y de repente un CPU diseñado para mercados embebidos se convirtió en una plataforma retro de juegos. La referencia completa del eZ80 está en el Apéndice E; la historia del portado está en el Capítulo 22.

---

## 4. R800 --- El velocista del MSX turboR

El R800 es el miembro más peculiar de la familia. Desarrollado por ASCII Corporation para el MSX turboR (1990, Panasonic FS-A1GT/FS-A1ST), es compatible con el Z80 en el sentido de que ejecuta el juego completo de instrucciones Z80 --- pero su arquitectura interna es radicalmente diferente.

**Pipeline, no microcódigo.** El Z80 original usa microcódigo: cada instrucción se divide en ciclos de máquina (M-cycles) de 3-6 tics de reloj cada uno, y las instrucciones complejas requieren muchos M-cycles. El R800 usa un diseño con pipeline donde la mayoría de las instrucciones se completan en 1-2 ciclos de reloj. A 7.16 MHz, esto le da un rendimiento efectivo aproximadamente 5-8x más rápido que un Z80 a 3.5 MHz para código típico.

**Multiplicación por hardware.** El R800 añade dos instrucciones de multiplicación:

| Instrucción | Operandos | Resultado | Ciclos | Notas |
|-------------|-----------|-----------|--------|-------|
| `MULUB A,r` | A * r (8 bits sin signo) | HL = producto de 16 bits | 14 | r = B, C, D, E |
| `MULUW HL,rr` | HL * rr (16 bits sin signo) | DE:HL = producto de 32 bits | 36 | rr = BC, SP |

Una multiplicación 16x16 con resultado de 32 bits en 36 ciclos es notable para un CPU de la era de 8 bits. En un Z80 estándar, una multiplicación 16x16 toma 600-1000 T-states dependiendo de la implementación. El R800 hace que las transformaciones 3D, el filtrado estilo DSP y otros algoritmos intensivos en multiplicaciones sean genuinamente prácticos.

**La trampa del pipeline.** El código optimizado para la temporización del Z80 puede comportarse inesperadamente en el R800. El truco de optimización Z80 de desenrollar `LDIR` en instrucciones `LDI` individuales (ahorrando 5T por byte) en realidad se ejecuta *más lento* en el R800, porque el pipeline del R800 maneja el prefijo de repetición de `LDIR` eficientemente. De manera similar, el código auto-modificable --- un pilar de la técnica de la demoscene Z80 --- puede provocar paradas en el pipeline del R800 cuando una escritura impacta una instrucción pre-cargada. El código que es rápido en el Z80 no es necesariamente rápido en el R800, y viceversa.

**Presencia en la demoscene.** El MSX turboR tiene una demoscene pequeña pero dedicada. La multiplicación por hardware hace viable el 3D en tiempo real, y la velocidad bruta permite efectos que serían imposibles a las velocidades de reloj del Z80. Pero la rareza de la plataforma (vendida solo en Japón, tirada de producción pequeña) significa que el R800 sigue siendo una nota al pie en la historia más amplia del Z80.

---

## 5. Clones soviéticos --- Detrás del Telón de Acero

La Unión Soviética produjo varios clones del Z80 para eludir las restricciones de exportación occidentales. Estos chips hicieron posible un ecosistema completo de ordenadores compatibles con el ZX Spectrum que floreció desde finales de los años 80 hasta los 90 --- y cuya comunidad de demoscene sigue activa hoy.

**KR1858VM1** (КР1858ВМ1). El clon soviético principal del Z80. Compatible en pines, compatible en instrucciones, compatible en bugs. Fabricado en la fábrica Angstrem de Zelenogrado usando máscaras obtenidas por ingeniería inversa. El KR1858VM1 impulsó el Pentagon 128 y el Scorpion ZS-256 --- los dos clones soviéticos más importantes del Spectrum, y las plataformas donde gran parte de la moderna demoscene rusa/CEI del ZX sigue dirigiendo su trabajo.

**T34VM1** (Т34ВМ1). Una versión CMOS posterior del mismo diseño, con menor consumo de energía y características eléctricas ligeramente diferentes. Funcionalmente idéntico al KR1858VM1.

Ninguno de los chips añade nuevas instrucciones. Son réplicas funcionales exactas del Zilog Z80. Las diferencias son eléctricas: diferentes procesos de fabricación, diferentes márgenes de temporización en setup y hold, comportamiento ligeramente diferente en opcodes no documentados y bits de banderas. Para propósitos de software, el código que se ejecuta en un Zilog Z80 se ejecuta idénticamente en un KR1858VM1.

La importancia histórica es inmensa. Sin estos clones, el ecosistema del ZX Spectrum no se habría extendido por la Unión Soviética y sus estados sucesores. El Pentagon 128, construido alrededor del KR1858VM1, se convirtió en la plataforma Spectrum *de facto* estándar en Rusia, y su temporización sin contención (sin retardos de contención de la ULA) es la temporización de referencia usada a lo largo de este libro.

---

## 6. Tabla comparativa

| Característica | Z80 | Z80N | eZ80 | R800 |
|----------------|-----|------|------|------|
| Reloj (típico) | 3.5 MHz | 28 MHz | 18.4 MHz | 7.16 MHz |
| Espacio de direcciones | 64 KB | 64 KB + regs Next | 16 MB | 64 KB |
| Multiplicación por hardware | No | `MUL D,E` (8T) | `MLT rr` (6T) | `MULUB` (14T), `MULUW` (36T) |
| Multiplicación 16x16 | No | No | No | `MULUW` (36T, resultado de 32 bits) |
| Desplazamiento barrel | No | `BSLA/BSRA/BSRL/BSRF/BRLC DE,B` (8T) | No | No |
| Copia en bloque con máscara | No | `LDIRX`, `LDPIRX` | No | No |
| Ayudas de dirección de pantalla | No | `PIXELDN`, `PIXELAD`, `SETAE` | No | No |
| Inversión de bits | No | `MIRROR` (8T) | No | No |
| Intercambio de nibble | No | `SWAPNIB` (8T) | No | No |
| Modo de 24 bits | No | No | Modo ADL | No |
| Push inmediato | No | `PUSH nn` (23T) | No | No |
| Sumar 8 bits a 16 bits | No | `ADD HL/DE/BC, A` (8T) | No | No |
| Test (AND no destructivo) | No | `TEST nn` (11T) | `TST` (7T) | No |
| E/S de registros de hardware | No | `NEXTREG` (17-20T) | `IN0`/`OUT0` | No |
| Diseñado para | Computación general | ZX Spectrum Next | Sistemas embebidos | MSX turboR |

### Effective Multiply Performance

Como las cuatro variantes funcionan a diferentes velocidades de reloj, los conteos brutos de T-states no cuentan toda la historia. Aquí está el tiempo real de reloj para una multiplicación 8x8 sin signo en cada plataforma:

| Variante | Reloj | Instrucción | Ciclos | Tiempo real |
|----------|-------|-------------|--------|-------------|
| Z80 | 3.5 MHz | Bucle de desplazamiento y suma | ~200 | ~57 us |
| Z80N | 28 MHz | `MUL D,E` | 8 | ~0.29 us |
| eZ80 | 18.4 MHz | `MLT DE` | 6 | ~0.33 us |
| R800 | 7.16 MHz | `MULUB A,r` | 14 | ~1.96 us |

El Z80N y el eZ80 están efectivamente empatados en rendimiento de multiplicación. El R800 es 30x más rápido que un Z80 estándar pero 6-7x más lento que el Z80N/eZ80. Los tres son suficientemente rápidos para hacer práctico el 3D en tiempo real.

---

## 7. Lo que esto significa para el libro

Todo el código ensamblador de este libro apunta al **juego de instrucciones estándar del Z80**. Cada ejemplo en cada capítulo se ensamblará y ejecutará en un ZX Spectrum 48K de serie, un Pentagon 128, un Scorpion, un MSX, o cualquier otra máquina con un Zilog Z80 o clon compatible. No se requieren extensiones.

Esta es una decisión deliberada. Los principios de optimización --- presupuestos de T-states, asignación de registros, estructura de bucles, código auto-modificable, bucles desenrollados, trucos con la pila --- son universales. El código que es rápido en un Z80 a 3.5 MHz es rápido en un Z80N a 28 MHz. El código que cabe en 48 KB cabe en 16 MB. Las restricciones del Z80 original te enseñan a pensar de una manera que se transfiere a cada variante de la familia.

Dicho esto, si tienes un ZX Spectrum Next, las extensiones del Z80N son demasiado buenas para ignorarlas. El Capítulo 22 cubre estrategias de portado incluyendo optimizaciones específicas del Z80N. Si tienes un Agon Light 2, el Apéndice E es tu referencia del eZ80 y el Capítulo 22 te guía a través de un portado completo de Spectrum a Agon. Los desplazamientos barrel, la multiplicación por hardware y las instrucciones de blit con máscara no cambian *cómo* piensas sobre la optimización --- cambian *dónde se mueve el cuello de botella* una vez que los puntos de dolor clásicos se eliminan.

Los fundamentos no cambian. Las instrucciones mejoran.

---

## Ver también

- **Apéndice A: Referencia rápida de instrucciones Z80** --- tabla completa de instrucciones Z80 estándar con T-states, conteo de bytes y efectos en las banderas. La base que comparten todas las variantes.
- **Apéndice E: Referencia rápida del eZ80** --- referencia completa del eZ80 incluyendo el sistema de modos, MLT, LEA/PEA y especificaciones del Agon Light 2.
- **Capítulo 22: Portar --- Agon Light 2** --- guía práctica de portado que cubre tanto las extensiones del eZ80 como del Z80N en contexto.

---

> **Nota de auditoría de T-states:** Los valores de T-states del Z80N en este apéndice fueron corregidos usando la documentación oficial en wiki.specnext.dev. Los valores iniciales (aproximadamente reducidos a la mitad en general) fueron identificados como incorrectos por Ped7g (Peter Helcmanovsky).

> **Fuentes:** Zilog Z80 CPU User Manual (UM0080); Zilog eZ80 CPU User Manual (UM0077); ZX Spectrum Next User Manual, Issue 2; ZX Spectrum Next Extended Instruction Set Documentation (wiki.specnext.dev); Victor Trucco, Fabio Belavenuto et al., notas de diseño del juego de instrucciones Z80N; ASCII Corporation R800 Technical Reference (1990); Sean Young, "The Undocumented Z80 Documented" (2005); Introspec, "Once more about DOWN_HL" (Hype, 2020); Dark / X-Trade, "Programming Algorithms" (Spectrum Expert #01, 1997)
