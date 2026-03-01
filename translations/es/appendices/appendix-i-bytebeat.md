# Apéndice I: Bytebeat y AY-Beat -- Sonido generativo en Z80

> *"Con 256 bytes, bytebeat es tu única opción realista -- no hay espacio para un reproductor de patrones."*
> -- Capítulo 13

---

Este apéndice cubre la generación de sonido basada en fórmulas en el ZX Spectrum -- desde el concepto original de bytebeat PCM hasta la técnica adaptada al AY que produce música estructurada y evolutiva a partir de un puñado de instrucciones Z80. El Capítulo 13 presenta AY-beat como herramienta de sizecoding. Este apéndice es la referencia completa: la teoría, las fórmulas, los mapeos de registros y un motor funcional completo que puedes integrar en una intro de 256 bytes.

Requisito previo: familiaridad con la arquitectura del AY-3-8910 (Capítulo 11) y las restricciones de sizecoding (Capítulo 13). El Apéndice G es la referencia de registros del AY.

---

## 1. Bytebeat: Los orígenes

Bytebeat fue descubierto (o inventado, dependiendo de tu filosofía) por Viznut (Ville-Matias Heikkila) en 2011. La idea: una sola expresión C que, evaluada para valores incrementales de `t`, produce una forma de onda audible cuando se envía directamente a una salida PCM de 8 bits.

La fórmula canónica:

```c
for (t = 0; ; t++)
    putchar( f(t) );    // pipe to /dev/dsp at 8000 Hz
```

Esto genera un patrón audible -- no ruido aleatorio, sino una estructura repetitiva emergente de las relaciones bit a bit entre operaciones enteras. El resultado suena a algo entre música chiptune y interferencia de radio. Es completamente determinista: la misma fórmula siempre produce el mismo sonido.

### Famous Formulas

El desplazamiento de bits crea relaciones de frecuencia. `t>>8` cambia 256 veces más lento que `t`, creando un tono 256 veces más bajo. `t>>11` cambia 2048 veces más lento. La operación OR combina estas sub-frecuencias en una forma de onda compuesta. La multiplicación por `t` crea un pitch sweep ascendente. El truncamiento a 8 bits (conversión implícita en C `char`) crea el patrón de envolvente en diente de sierra que da carácter al sonido.

**`t*(t>>5|t>>8)>>(t>>16)`** -- Evolving rhythmic patterns. The right-shift by `t>>16` means the entire character of the sound changes every ~8 seconds (65536 samples at 8 kHz). Each 8-second section has a different dynamic range and feel.

Bytebeat fue diseñado para hardware de PC con salida de sonido de 8 bits a 8 kHz. El ZX Spectrum no tiene DAC. Su chip de sonido -- el AY-3-8910 -- es un generador de tono/ruido/envolvente, no un dispositivo PCM. Puedes aproximar un DAC a través del puerto del altavoz del beeper ($FE), pero esto consume ~100% de la CPU, sin dejar nada para efectos visuales. En un contexto de sizecoding (256 bytes), eso no es viable.

AY-beat es la solución: adaptar la filosofía del bytebeat -- sonido generado por fórmulas a partir de un contador de tiempo incrementado -- a los registros del AY.

Bitwise operations on an incrementing counter create periodic structures at multiple time scales simultaneously. Consider the bit pattern of `t` as it counts:

## 2. AY-Beat: La adaptación

En lugar de generar muestras PCM, AY-beat genera **valores de registros del AY** a partir de fórmulas. Cada fotograma (a 50 Hz), el contador `t` se incrementa y las fórmulas derivan los periodos de tono, niveles de volumen y parámetros de envolvente que se escriben en los registros del AY-3-8910.

El concepto clave: **los registros del AY son los parámetros de sonido, no la forma de onda.** En bytebeat, la fórmula produce la forma de onda directamente. En AY-beat, la fórmula produce valores de control que le dicen al AY qué tono generar. El AY hace la síntesis real.

### On the Spectrum: The Beeper Dead End

| Registro AY | Qué controla | Rango | Efecto de la fórmula |
|-------------|-------------|-------|---------------------|
| R0-R1 (Tono A) | Periodo del canal A | 0-4095 (12 bits) | Pitch sweep, melodía |
| R2-R3 (Tono B) | Periodo del canal B | 0-4095 | Segunda voz, armonía |
| R4-R5 (Tono C) | Periodo del canal C | 0-4095 | Tercera voz, bajo |
| R6 (Ruido) | Periodo del ruido | 0-31 (5 bits) | Textura de percusión |
| R7 (Mezclador) | Habilitación de tono/ruido | Mapa de bits | Selección de canal |
| R8-R10 (Volumen) | Volumen por canal | 0-15 (4 bits) | Dinámicas, fade |
| R11-R12 (Env periodo) | Periodo de envolvente | 0-65535 (16 bits) | Drone, efecto de bajo |
| R13 (Env forma) | Forma de envolvente | 0-15 | Tipo de decay/sustain |

```z80
; Beeper bytebeat -- uses all CPU, no visuals possible
; DE = t (16-bit counter)
    ld   de, 0
.loop:
    ; Compute f(t) -- simplified: A = t AND (t >> 8)
    ld   a, e          ; 4T   A = low byte of t
    and  d             ; 4T   A = t_lo AND t_hi
    ; Output bit 4 to speaker
    and  $10           ; 7T   isolate bit 4
    out  ($FE), a      ; 11T  toggle speaker
    inc  de            ; 6T   t++
    jr   .loop         ; 12T
                       ; --- 44T per sample = ~79.5 kHz
```

El motor AY-beat más simple: incrementar `t`, calcular el periodo de tono a partir de `t`, escribir en el AY.

For a demo, this is a dead end. The beeper is a 1-bit output that demands constant CPU attention. The real adaptation of bytebeat to the Spectrum requires a different approach entirely.

---

## 2. AY-Beat: Bytebeat Reimagined for a Tone Generator

## 3. El período de envolvente como drone

La característica más potente del AY para AY-beat es el generador de envolvente. Cuando el modo de volumen de un canal se establece a `$10` (bit 4 activado), el AY ignora el volumen manual y lo sustituye por la envolvente hardware -- un patrón de volumen que se repite continuamente, controlado por los registros R11-R13.

Classic bytebeat computes one amplitude sample at ~8000 Hz. AY-beat computes tone periods, volumes, and noise parameters at 50 Hz -- once per video frame, triggered by the HALT instruction. The AY's oscillators handle the actual sound generation between frames.

Establece un canal en modo envolvente (`ld d, $10 : ld a, 10 : call ay_write_d`). Ahora el AY modula el volumen de este canal automáticamente con el periodo de envolvente. Si el periodo de envolvente está cerca del periodo de tono, la interacción produce una forma de onda compleja -- como modulación de frecuencia en un sintetizador FM.

Esto es **buzz-bass** (Capítulo 11). El "drone" del AY-beat: establece un canal en modo E+T y deja que el periodo de envolvente haga un sweep controlado por tu fórmula. El canal produce un tono en constante evolución sin coste adicional de CPU más allá de actualizar R11/R12 cada fotograma.

```z80
; AY-beat frame update -- called once per HALT
; Assumes frame_counter is a byte in memory
ay_beat_update:
    ld   a, (frame_counter)
    ld   e, a             ; E = t (keep a copy)

    ; === Channel A: tone period from formula ===
    ; tone_lo = (t * 3) AND $3F -- pentatonic-ish cycling
    add  a, a             ; 4T   A = t * 2
    add  a, e             ; 4T   A = t * 3
    and  $3F              ; 7T   mask to 6 bits (periods 0-63)
    ld   d, a             ; 4T   save tone period
    ; Write R0 (tone A low) = D
    xor  a                ; 4T   A = 0 (register number)
    call ay_write_d       ; writes D to AY register A

    ; Write R1 (tone A high) = 0
    ld   a, 1             ; 7T
    ld   d, 0             ; 7T
    call ay_write_d

    ; === Channel A: volume from formula ===
    ; volume = bits 6-3 of t, giving 0-15 cycling
    ld   a, e             ; 4T   reload t
    rrca                  ; 4T
    rrca                  ; 4T
    rrca                  ; 4T
    and  $0F              ; 7T   volume 0-15
    ld   d, a             ; 4T
    ld   a, 8             ; 7T   R8 = Volume A
    call ay_write_d

    ; Advance frame counter
    ld   hl, frame_counter
    inc  (hl)             ; 11T
    ret
```

Esto produce un drone que evoluciona -- el periodo de envolvente realiza un sweep a través de rangos, creando batidos de interferencia con el periodo de tono fijo. El tono parece "respirar" a medida que la envolvente acelera y desacelera.

### What Changes from PCM Bytebeat

El registro R13 controla el patrón de la envolvente:

| Forma | Valor | Patrón | Mejor uso |
|-------|-------|--------|-----------|
| Decay simple | `$00` | `\___` | Hit de un disparo, percusión |
| Ataque simple | `$04` | `/___` | Swell, fade in |
| Diente de sierra descendente | `$08` | `\\\\\` | Bass pulsante (repetido) |
| Diente de sierra ascendente | `$0C` | `/////` | Pitch ascendente (repetido) |
| Triángulo | `$0E` | `/\/\/` | Vibrato suave, drone (repetido) |
| Triángulo invertido | `$0A` | `\/\/\` | Vibrato suave, fase invertida |

---

## 3. Drone: Envelope + Tone (E+T Mode)

La envolvente del AY se reinicia cada vez que escribes en R13. Para un drone continuo, escribe R13 una vez (en el fotograma 0) y nunca lo toques de nuevo. La envolvente se repite indefinidamente con la forma elegida. Luego actualiza solo R11/R12 (periodo de envolvente) cada fotograma para controlar el tono del drone.

The result is a drone: a continuously evolving timbre produced by the interaction of the tone oscillator and the envelope oscillator. The CPU cost for maintaining this drone is almost zero -- you only need to update the tone period and envelope period once per frame, and the hardware does the rest.

Esto ahorra bytes: no necesitas escribir R13 en tu bucle por fotograma.

1. Set a tone period from a formula -- this defines the base pitch.
2. Set an envelope period from a different formula -- this defines the modulation rate.
3. Set the envelope shape to a repeating waveform (shapes $08, $0A, $0C, or $0E).
4. Set the channel volume to envelope mode ($10).
5. The hardware produces a continuously evolving drone with zero per-sample CPU cost.

```z80
; Drone setup -- E+T mode
; Tone period evolves per frame, envelope period evolves slower
drone_update:
    ld   a, (frame_counter)
    ld   e, a             ; E = t

    ; --- Tone period: slowly sweeping ---
    and  $7F              ; 128-frame cycle (2.56 seconds)
    ld   d, a
    xor  a                ; R0 = Tone A low
    call ay_write_d
    ld   a, 1             ; R1 = Tone A high
    ld   d, 0
    call ay_write_d

    ; --- Envelope period: evolves on different time scale ---
    ld   a, e             ; reload t
    rrca
    rrca                  ; divide by 4 -- envelope evolves 4x slower
    and  $3F
    add  a, $10           ; offset to avoid very fast envelopes
    ld   d, a
    ld   a, 11            ; R11 = Envelope period low
    call ay_write_d
    ld   a, 12            ; R12 = Envelope period high
    ld   d, 0
    call ay_write_d

    ; --- Envelope shape: repeating triangle ---
    ; CAUTION: writing R13 restarts the envelope cycle.
    ; Only write on the first frame, or when you want a restart.
    ld   a, e
    or   a
    jr   nz, .skip_shape
    ld   a, 13            ; R13 = Envelope shape
    ld   d, $0A           ; shape $0A = repeating triangle \/\/
    call ay_write_d
.skip_shape:

    ; --- Volume A: envelope mode ---
    ld   a, 8             ; R8 = Volume A
    ld   d, $10           ; bit 4 set = use envelope
    call ay_write_d

    ret
```

El generador de ruido del AY (R6) produce ruido blanco a un periodo controlable. Combinado con un decay rápido de volumen, esto crea sonidos de percusión. El truco de AY-beat: activar el ruido solo en ciertos fotogramas derivados de `t`.

Sweeping the envelope period while the tone period also moves produces continuously evolving textures. The two formulas create a two-dimensional parameter space that the sound explores over time. With the right formula pair, the drone never quite repeats -- it wanders through timbral variations, creating an ambient soundscape from fewer than 30 bytes of code.

### Byte Cost

El `and $07` crea una máscara periódica: el hit ocurre cada 8 fotogramas (8 fotogramas / 50 fps = 160 ms entre hits, ~375 BPM). El hit de ruido se desvanece durante 3 fotogramas a través de la secuencia de volumen 15→10→5→0.

---

Diferentes máscaras crean diferentes ritmos:

| Máscara | Periodo | BPM (aprox.) | Sensación |
|---------|---------|--------------|-----------|
| `and $03` | Cada 4 fotogramas | 750 | Frenético |
| `and $07` | Cada 8 fotogramas | 375 | Rápido |
| `and $0F` | Cada 16 fotogramas | 187 | Medio |
| `and $1F` | Cada 32 fotogramas | 94 | Lento |
| `and $3F` | Cada 64 fotogramas | 47 | Ambiental |

Combina dos máscaras para patrones más complejos:

```z80
; Noise percussion on channel C
; Frame counter in A (already loaded)
    ld   e, a             ; E = t
    and  $07              ; every 8th frame = 6.25 Hz pulse
    jr   nz, .decay

    ; --- Hit: enable noise on C, max volume ---
    ld   a, 7             ; R7 = Mixer
    ld   d, %00100100     ; tone C off, noise C on, others unchanged
    call ay_write_d
    ld   a, 6             ; R6 = Noise period
    ld   d, 2             ; low period = harsh, punchy
    call ay_write_d
    ld   a, 10            ; R10 = Volume C
    ld   d, $0F           ; maximum volume
    call ay_write_d
    jr   .done

.decay:
    ; --- Decay: reduce volume each frame ---
    ; Simple approach: volume = 15 - (t AND 7)
    ld   a, e
    and  $07              ; frames since last hit
    ld   d, a
    ld   a, $0F
    sub  d                ; volume = 15 - elapsed
    jr   nc, .vol_ok
    xor  a                ; clamp to 0
.vol_ok:
    ld   d, a
    ld   a, 10            ; R10 = Volume C
    call ay_write_d

.done:
```

Esto produce un patrón combinado donde hay un acento cada 16 fotogramas y un hit débil cada 8.

| R6 Value | Character | Use |
|----------|-----------|-----|
| 0-3 | Harsh click, punchy | Kick drum, rimshot |
| 4-8 | Crisp hiss | Snare body |
| 10-15 | Broad noise | Open hi-hat |
| 20-31 | Low rumble | Distant thunder, ambient |

En lugar de un decay manual de volumen (que cuesta bytes para la secuencia de decremento), usa el generador de envolvente del AY:

Different AND masks on the frame counter produce different rhythmic densities:

Las fórmulas en esta tabla muestran las implementaciones Z80 -- no necesitas almacenar tablas, solo operar sobre el contenido del registro.

Combine two masks for polyrhythm: test `t AND $07` for the kick, `t AND $03` for the hi-hat. This costs about 10 extra bytes but adds significant rhythmic complexity.

En lugar de gestionar el decay del volumen manualmente, re-activa la envolvente en el hit:

Instead of manually decaying the volume each frame, use the AY envelope generator in single-shot mode. Set R13 to shape $00 (decay to zero, hold), and the hardware handles the volume fade automatically:

```z80
; Envelope-based drum hit -- zero CPU cost for decay
    ld   a, e
    and  $07              ; every 8th frame
    jr   nz, .no_hit
    ; Set envelope period (controls decay speed)
    ld   a, 11
    ld   d, $80           ; period = $0080 -- medium decay
    call ay_write_d
    ld   a, 12
    ld   d, 0
    call ay_write_d
    ; Trigger: write shape $00 (single decay)
    ld   a, 13
    ld   d, $00
    call ay_write_d
    ; Volume C = envelope mode
    ld   a, 10
    ld   d, $10
    call ay_write_d
.no_hit:
```

Esto ahorra varios bytes al eliminar el código de decay manual. La contrapartida: el generador de envolvente se comparte entre todos los canales en modo envolvente. Si el canal A está usando drone E+T, el canal C no puede usar independientemente la envolvente para el decay de percusión. Planifica tu asignación de canales en consecuencia.

---

## 5. Armonía multicanal

El AY tiene tres canales de tono independientes. AY-beat puede derivar los tres de una sola fórmula usando rotación de bits, creando la impresión de contrapunto con casi nada de código.

### Three Voices from One Formula

```z80
; Three related voices from one frame counter
    ld   a, (frame_counter)
    ld   e, a

    ; === Channel A: base formula ===
    and  $3F              ; period 0-63
    ld   d, a
    xor  a                ; R0
    call ay_write_d

    ; === Channel B: same formula, rotated 2 bits ===
    ld   a, e
    rrca
    rrca                  ; rotate right by 2
    and  $3F
    ld   d, a
    ld   a, 2             ; R2
    call ay_write_d

    ; === Channel C: same formula, rotated 4 bits ===
    ld   a, e
    rrca
    rrca
    rrca
    rrca                  ; rotate right by 4
    and  $3F
    ld   d, a
    ld   a, 4             ; R4
    call ay_write_d
```

Las rotaciones de bits crean versiones con desplazamiento de fase del mismo patrón. Los canales reproducen melodías relacionadas pero desplazadas -- siguen el mismo contorno pero llegan a cada tono en momentos diferentes. Esto crea una impresión de contrapunto: múltiples voces independientes que comparten una lógica subyacente.

### Why Rotation Creates Harmony

RRCA es una *rotación*, no un desplazamiento -- los bits que caen por abajo vuelven por arriba. Esto significa que los tres canales recorren el mismo conjunto de valores de periodo en el mismo orden, pero desplazados en el tiempo. El desplazamiento depende de la cantidad de rotación:

- **RRCA x 2:** El canal va "adelantado" aproximadamente un cuarto del ciclo del patrón. Esto a menudo crea intervalos que suenan como cuartas o quintas -- no afinados con precisión, pero lo suficientemente relacionados armónicamente como para ser agradables.
- **RRCA x 4:** Medio byte de desplazamiento. Esto tiende a producir relaciones tipo octava, ya que rotar el bit 4 al bit 0 efectivamente reduce el periodo a la mitad en ciertas alineaciones de fase.

Estos no son intervalos musicales reales. Son relaciones pseudo-armónicas creadas por la estructura de los números binarios. Pero el oído es indulgente -- si dos tonos comparten la mayor parte de su patrón de bits, suenan "relacionados", y eso es suficiente para una intro de 256 bytes.

### Volume Formulas for Multi-Channel

Dale a cada canal una fórmula de volumen diferente para evitar que las tres voces estén al mismo nivel simultáneamente:

```z80
    ; Volume A: bits 6-3 of t
    ld   a, e
    rrca
    rrca
    rrca
    and  $0F
    ld   d, a
    ld   a, 8
    call ay_write_d

    ; Volume B: bits 4-1 of t (different phase)
    ld   a, e
    rrca
    and  $0F
    ld   d, a
    ld   a, 9
    call ay_write_d

    ; Volume C: inverted bits 5-2 of t
    ld   a, e
    rrca
    rrca
    and  $0F
    xor  $0F              ; invert -- when A is loud, C is quiet
    ld   d, a
    ld   a, 10
    call ay_write_d
```

El volumen invertido en el canal C crea una dinámica de llamada y respuesta: mientras una voz sube, otra baja. Esto cuesta 2 bytes extra (el `XOR $0F`) pero mejora significativamente la textura musical.

---

## 6. Recetario de fórmulas

Las siguientes fórmulas han sido probadas en el AY a una tasa de 50 Hz. "Bytes" se refiere al coste de implementación Z80 para calcular la fórmula a partir de un valor ya en el registro A (el contador de fotogramas). La máscara de periodo determina el rango de tono.

### Tone Period Formulas

| # | Fórmula | Implementación Z80 | Bytes | Sonido | Mejor para |
|---|---------|---------------------|-------|--------|------------|
| 1 | `t AND $3F` | `and $3F` | 2 | Diente de sierra ascendente, ciclo de 1,28 seg | Sweep simple |
| 2 | `t*3 AND $3F` | `ld e,a : add a,a : add a,e : and $3F` | 5 | Sweep más rápido, intervalos más amplios | Bajo enérgico |
| 3 | `t XOR (t>>3)` | `ld e,a : rrca : rrca : rrca : xor e` | 5 | Caótico con estructura periódica | Textura de ruido |
| 4 | `(t AND $0F) XOR $0F` | `and $0F : xor $0F` | 4 | Onda triangular, sweep ping-pong | Lead melódico |
| 5 | `t*5 AND t>>2` | `ld e,a : add a,a : add a,a : add a,e : ld d,a : ld a,e : rrca : rrca : and d` | 10 | Gate rítmico | Tipo percusión |
| 6 | `(t+t>>4) AND $1F` | `ld e,a : rrca : rrca : rrca : rrca : add a,e : and $1F` | 6 | Sweep lentamente modulado | Drone evolutivo |
| 7 | `t AND (t>>3) AND $1F` | `ld e,a : rrca : rrca : rrca : and e : and $1F` | 6 | Auto-similar, ritmo fractal | Patrones complejos |
| 8 | `(t>>1) XOR (t>>3)` | `ld e,a : rrca : ld d,a : rrca : rrca : xor d` | 6 | Interferencia de doble velocidad | Textura metálica |
| 9 | `t*7 AND $7F` | `ld e,a : add a,a : add a,a : add a,a : sub e : and $7F` | 6 | Sweep amplio, velocidad 7x | Sensación de arpegio rápido |
| 10 | `(t XOR t>>1) AND $3F` | `ld e,a : rrca : xor e : and $3F` | 5 | Secuencia de código Gray | Melodía en escalera |
| 11 | `t AND $07 OR t>>4` | `ld e,a : and $07 : ld d,a : ld a,e : rrca : rrca : rrca : rrca : or d` | 8 | Bucles anidados, dos capas rítmicas | Ritmo en capas |
| 12 | `(t+t+t>>2) AND $3F` | `ld e,a : add a,a : ld d,a : ld a,e : rrca : rrca : add a,d : and $3F` | 8 | Sweep acelerado con sub-patrón | Lead con textura |

### Volume Formulas

| # | Fórmula | Z80 | Bytes | Efecto |
|---|---------|-----|-------|--------|
| V1 | `t>>3 AND $0F` | `rrca : rrca : rrca : and $0F` | 5 | Ciclo de fade lento, 5,12 seg |
| V2 | `(t AND $0F) XOR $0F` | `and $0F : xor $0F` | 4 | Volumen triangular, ping-pong |
| V3 | `t*3>>4 AND $0F` | `ld e,a : add a,a : add a,e : rrca : rrca : rrca : rrca : and $0F` | 8 | Patrón de fade irregular |
| V4 | `$0F` (constante) | `ld d,$0F` | 2 | Volumen máximo, usar con modo envolvente |

### How to Read the Table

Elige una fórmula de tono y una fórmula de volumen. Combínalas. El coste total en bytes es la suma de ambas implementaciones más la sobrecarga de escritura de registros AY (~8 bytes por canal para dos llamadas a ay_write: selección de registro + datos para tono bajo y volumen). Un solo canal con la fórmula #1 y volumen V1 cuesta aproximadamente 2 + 5 + 16 = 23 bytes incluyendo escrituras de registros.

La fórmula #10 (código Gray) merece mención especial. La secuencia de código Gray solo cambia un bit por paso, así que el periodo de tono cambia exactamente una unidad por fotograma -- una melodía suave, tipo escalera. Combinada con la máscara AND, recorre un rango de tono limitado con regularidad agradable. Esta es una de las fórmulas individuales con sonido más musical.

---

## 7. Ensamblándolo todo: Un motor AY-Beat completo

Aquí hay un motor AY-beat completo y mínimo que produce sonido generativo de 3 canales con drone de envolvente. Este es el motor que integras en una intro de 256 bytes junto a tu efecto visual.

```z80
; ============================================================
; Complete AY-beat engine -- 47 bytes
; Produces 3-channel generative music with envelope drone
; Call once per frame (after HALT)
; Clobbers: AF, BC, DE, HL
; ============================================================

ay_beat:
    ld   hl, .frame
    ld   a, (hl)          ; A = frame counter
    inc  (hl)             ; advance for next frame
    ld   e, a             ; E = t (preserved copy)

    ; --- Mixer: all three tones on, no noise ---
    ; Only needed on first frame, but costs 5 bytes either way
    push af
    ld   a, 7             ; R7
    ld   d, $38           ; tones A+B+C on, noise off
    call .wr
    pop  af

    ; --- Channel A: tone = t AND $3F ---
    and  $3F
    ld   d, a
    xor  a                ; R0
    call .wr

    ; --- Channel B: tone = t*3 AND $3F ---
    ld   a, e
    add  a, a
    add  a, e             ; A = t * 3
    and  $3F
    ld   d, a
    ld   a, 2             ; R2
    call .wr

    ; --- Channel C: tone = (t XOR t>>1) AND $3F ---
    ld   a, e
    rrca
    xor  e
    and  $3F
    ld   d, a
    ld   a, 4             ; R4
    call .wr

    ; --- Volumes: A and B fixed at 12, C = envelope mode ---
    ld   a, 8             ; R8 = Volume A
    ld   d, 12
    call .wr
    ld   a, 9             ; R9 = Volume B
    ld   d, 10
    call .wr
    ld   a, 10            ; R10 = Volume C
    ld   d, $10           ; envelope mode
    call .wr

    ; --- Envelope: period sweeps with t, triangle shape ---
    ld   a, e
    rrca
    rrca
    and  $3F
    add  a, $20           ; keep envelope period above $20
    ld   d, a
    ld   a, 11            ; R11
    call .wr
    ; R12 = 0 (envelope period high)
    inc  a                ; A = 12
    ld   d, 0
    call .wr

    ; Shape: only write on frame 0 to avoid constant restarts
    ld   a, e
    or   a
    ret  nz               ; skip shape write on all frames except 0
    ld   a, 13            ; R13
    ld   d, $0E           ; shape $0E = repeating triangle /\/\
    ; fall through to .wr, then ret

.wr:
    ; Write D to AY register A
    ld   bc, $FFFD
    out  (c), a           ; select register
    ld   b, $BF
    out  (c), d           ; write value
    ret

.frame:
    DB   0                ; frame counter (self-modifying data)

; ============================================================
; Total: 47 bytes (code) + AY write routine shared
; The .wr routine is 9 bytes. If your intro already has an
; AY write routine, the engine body alone is 38 bytes.
; ============================================================
```

### What This Produces

- **Canal A:** Un sweep ascendente simple, recorriendo periodos 0-63 cada 64 fotogramas (1,28 segundos). El patrón fundamental.
- **Canal B:** El mismo sweep a velocidad 3x, creando intervalos más rápidos. Cuando se alinea con el canal A, escuchas consonancia; cuando diverge, escuchas disonancia. La alternancia crea interés rítmico.
- **Canal C:** Un sweep de código Gray en modo envolvente. La envolvente triangular crea modulación de volumen automática, produciendo un drone que se desfasa contra el periodo de tono. Esta es la cama armónica bajo las otras dos voces.
- **En conjunto:** Una textura evolutiva y auto-similar que recorre relaciones tonales. Suena alienígena y mecánico -- exactamente lo correcto para una intro de 256 bytes.

### Customisation Points

**Cambia las fórmulas de tono.** Intercambia cualquiera de las secuencias AND/RRCA por una fórmula diferente del recetario (sección 6). Cada sustitución cambia el carácter por completo.

**Añade percusión de ruido.** Inserta un bloque `ld a,e : and $07 : jr nz,.no_hit` (sección 4) para añadir golpes rítmicos. Coste: ~12 bytes. Roba un canal (típicamente B) o superpón ruido en el canal C.

**Usa enmascaramiento pentatónico.** En lugar de `AND $3F` como máscara final, indexa en una tabla de consulta pentatónica de 5 bytes. Esto restringe los periodos de tono a valores armónicamente relacionados, haciendo que la salida suene más deliberadamente musical. Coste: ~8 bytes (5 para la tabla, 3 para la consulta). El Capítulo 13 discute esta técnica.

**Varía los volúmenes fijos.** Reemplaza las escrituras de volumen constante con fórmulas de volumen de la sección 6. Incluso `ld a,e : rrca : rrca : rrca : and $0F` (5 bytes por canal) añade un interés dinámico significativo.

---

## 8. Avanzado: Combinando técnicas

Las secciones anteriores cubren bloques de construcción individuales. Un motor AY-beat bien elaborado combina varios:

### Architecture for a 256-Byte Intro

```
Frame 0:   Set mixer, envelope shape (one-time setup)
Frame N:   Update tone A (melody formula)
           Update tone B (harmony formula, rotated)
           Update volume A (fade formula)
           Update volume B (inverted fade)
           Channel C in E+T drone mode (auto-evolving)
           Every 8th frame: noise hit on C (toggle mixer)
```

El coste total de CPU por fotograma es aproximadamente 300-500 T-states -- muy por debajo del 1% de los ~70.000 T-states disponibles por fotograma. El 99% restante queda disponible para tu efecto visual.

### Register Budget

El AY tiene 14 registros escribibles. En un motor AY-beat mínimo, típicamente escribes 8-10 por fotograma:

| Registro | Escrito | Fuente |
|----------|---------|--------|
| R0 (Tono A bajo) | Cada fotograma | Fórmula |
| R2 (Tono B bajo) | Cada fotograma | Fórmula |
| R4 (Tono C bajo) | Cada fotograma o una vez | Fórmula o fijo |
| R1, R3, R5 (Tono alto) | Una vez (puesto a 0) | Constante |
| R7 (Mezclador) | Cada fotograma o una vez | Constante o conmutado para ruido |
| R8, R9 (Volumen A, B) | Cada fotograma | Fórmula o constante |
| R10 (Volumen C) | Una vez | $10 (modo envolvente) |
| R11 (Envolvente bajo) | Cada fotograma | Fórmula |
| R13 (Forma envolvente) | Una vez (fotograma 0) | Constante |

Registros que puedes omitir por completo: R6 (periodo de ruido -- solo necesario si usas ruido), R12 (envolvente alto -- puesto una vez a 0 para periodos cortos), R14-R15 (puertos de E/S -- irrelevantes para sonido).

### Size Breakdown

Para una intro de 256 bytes, cada byte importa. Así es como se ve un presupuesto típico de AY-beat:

| Componente | Bytes |
|------------|-------|
| Rutina de escritura AY | 9 |
| Gestión del contador de fotogramas | 5 |
| 3 fórmulas de tono (simples) | 12-18 |
| 3 ajustes de volumen | 6-15 |
| Configuración del mezclador | 5 |
| Configuración de envolvente | 8-12 |
| Total | **45-64** |

Esto deja 192-211 bytes para el efecto visual, el bucle principal y cualquier otra infraestructura. Con 45 bytes, el motor de la sección 7 está cerca del óptimo para la cantidad de sonido que produce.

---

## 9. AY como DAC: Bytebeat clásico a través del registro de volumen

Hay un camino intermedio entre el callejón sin salida del beeper y la reinterpretación del AY-beat. Los registros de volumen del AY-3-8910 (registros 8, 9, 10) aceptan valores de 4 bits (0-15). Si actualizas un registro de volumen a una tasa alta -- digamos, durante un bucle ajustado -- la salida del AY se convierte en un DAC de 4 bits. Así es como funcionan la voz digitalizada y la reproducción de muestras en demos del Spectrum.

Aplicado a bytebeat: calcula `f(t)`, desplaza a 4 bits, escribe en el registro de volumen:

```z80
; AY-as-DAC bytebeat -- 4-bit PCM through volume register
; Still costly (~80% CPU), but sounds better than beeper
    ld   a, 7               ; mixer: all channels off (tone+noise)
    ld   d, %00111111
    call ay_write
    ld   de, 0               ; t = 0
.loop:
    ; Compute f(t): t AND (t >> 5) -- classic bytebeat formula
    ld   a, e
    ld   b, d
    srl  b
    rr   a
    srl  b
    rr   a
    srl  b
    rr   a
    srl  b
    rr   a
    srl  b
    rr   a                   ; A = t >> 5 (using DE as 16-bit t)
    and  e                   ; A = t AND (t >> 5)
    rrca
    rrca
    rrca
    rrca
    and  $0F                 ; scale to 4-bit (0-15)
    ld   bc, AY_REG
    ld   b, $FF              ; select register
    push af
    ld   a, 8                ; register 8: volume A
    out  (c), a
    ld   b, $BF
    pop  af
    out  (c), a              ; write volume
    inc  de                  ; t++
    jr   .loop
```

Esto produce bytebeat reconocible -- las fórmulas de forma de onda reales de la sección 1, audibles a través del AY. La calidad de sonido es mejor que la del beeper (resolución de 4 bits vs 1 bit), y la etapa de salida del AY proporciona niveles de audio adecuados.

El coste sigue siendo brutal: ~80% de CPU. Te queda una franja mínima de tiempo para visuales -- suficiente para un efecto de atributos de actualización lenta, no suficiente para nada ambicioso. Esta técnica es útil cuando quieres el *sonido específico* de fórmulas bytebeat clásicas y estás dispuesto a pagar el precio de CPU.

### Three Output Paths Compared

| Ruta | Resolución | Coste CPU | Carácter del sonido | ¿Práctico para demos? |
|------|-----------|----------|---------------------|----------------------|
| Beeper (puerto $FE) | 1 bit | ~100% | Áspero, zumbante | No |
| AY volumen DAC | 4 bits | ~80% | Bytebeat clásico | Apenas (solo efectos de atributos) |
| AY-beat (registros) | Tono/ruido | ~0,5% | Chip music, generativo | Sí -- la opción correcta |

Para intros y demos con restricción de tamaño, AY-beat es casi siempre la opción correcta. Reserva AY-como-DAC para proyectos artísticos donde la estética sonora específica del bytebeat es el objetivo.

---

## 10. Teoría musical para algoritmos

Las fórmulas de AY-beat que ignoran la teoría musical producen ruido interesante. Las fórmulas que *codifican* teoría musical producen música real. Las siguientes técnicas añaden musicalidad con un mínimo de bytes.

### Scale Tables: Constraining Output to Pleasant Notes

Una fórmula cruda como `tone = t AND $3F` produce los 64 valores de periodo posibles -- la mayoría de los cuales no son musicalmente útiles. Una **tabla de escala** mapea la salida de la fórmula a periodos de notas reales, asegurando que cada valor suene bien.

| Escala | Notas | Tamaño tabla | Carácter |
|--------|-------|-------------|----------|
| Pentatónica | 5 (C D E G A) | 10 bytes (5 periodos de 2 bytes) | Siempre consonante, sensación folk/world |
| Diatónica mayor | 7 (C D E F G A B) | 14 bytes | Brillante, occidental, familiar |
| Diatónica menor | 7 (C D Eb F G Ab Bb) | 14 bytes | Oscura, melancólica |
| Blues | 6 (C Eb F F# G Bb) | 12 bytes | Áspera, expresiva |
| Cromática | 12 | 24 bytes | Atonal, disonante -- generalmente incorrecta para sizecoding |

La escala pentatónica es la mejor amiga del sizecoder: 5 notas, 10 bytes, y *cualquier* combinación de notas suena aceptable. No puedes tocar una nota equivocada en una escala pentatónica. Por eso tantas intros de 256 bytes suenan vagamente "asiáticas" o "folk" -- la restricción pentatónica hace que las secuencias aleatorias sean musicales.

```z80
; Scale-constrained note lookup
; Input: A = formula output (any value)
; Output: DE = AY tone period
    ; Map to scale index: A mod scale_length
    and  $07               ; keep low 3 bits
    cp   5                 ; pentatonic has 5 notes
    jr   c, .in_range
    sub  5                 ; wrap: 5→0, 6→1, 7→2
.in_range:
    add  a, a              ; ×2 for word entries
    ld   hl, pentatonic
    add  a, l
    ld   l, a
    ld   e, (hl)
    inc  hl
    ld   d, (hl)           ; DE = tone period
```

### Octave Derivation: Free Pitch Range

Almacena una octava de periodos. Deriva todas las demás por desplazamiento de bits:

- `SRL D : RR E` = una octava arriba (periodo a la mitad, tono al doble)
- `SLA E : RL D` = una octava abajo (periodo al doble, tono a la mitad)

Cinco notas pentatónicas x una octava almacenada x desplazamiento de bits = 5 notas x 5+ octavas = 25+ tonos distintos de 10 bytes de datos. La fórmula selecciona la nota, una máscara de bits separada selecciona la octava:

```z80
    ; note_index = formula AND $0F
    ; octave = note_index / 5 (0-2)
    ; note = note_index % 5
    ; Look up base period, then SRL 'octave' times
```

### Arpeggio: Chord Tones in Sequence

Un arpegio recorre los tonos de un acorde. En términos de grados de escala:

| Acorde | Offsets de escala | Sonido |
|--------|------------------|--------|
| Tríada mayor | 0, 2, 4 (fundamental, tercera, quinta) | Brillante, resuelto |
| Tríada menor | 0, 2, 3 (fundamental, tercera menor, quinta) | Oscuro, tenso |
| Power chord | 0, 4 (fundamental, quinta) | Abierto, fuerte |
| Suspendido | 0, 3, 4 (fundamental, cuarta, quinta) | Ambiguo, flotante |

Implementación: `arp_step = (t / velocidad) % tamaño_acorde`, luego sumar el offset a la nota raíz actual:

```z80
; Arpeggio: cycle through major triad
    ld   a, (frame)
    rrca
    rrca                   ; A = frame / 4 (arp speed)
    ; mod 3 for three chord tones
    ld   b, a
.mod3:
    sub  3
    jr   nc, .mod3
    add  a, 3              ; A = 0, 1, or 2
    ld   hl, arp_major
    add  a, l
    ld   l, a
    ld   a, (hl)           ; A = scale offset
    ; add to chord root, look up in scale table
    ; ...

arp_major:  DB  0, 2, 4    ; root, third, fifth (3 bytes)
arp_minor:  DB  0, 2, 3    ; root, min.third, fifth (3 bytes)
```

Tres bytes por forma de acorde. La velocidad del arpegio se deriva del contador de fotogramas -- no se necesita un temporizador separado.

### Step Ornaments: Trills, Mordents, and Slides

Un ornamento es un pequeño patrón cíclico de offsets relativos de tono aplicado a una nota. En música tracker, los ornamentos dan vida a los tonos planos:

| Ornamento | Patrón | Efecto | Bytes |
|-----------|--------|--------|-------|
| Trino | 0, +1, 0, -1 | Alternancia rápida con vecina | 4 |
| Mordente | 0, +1, 0, 0 | Breve vecina superior, luego asentarse | 4 |
| Deslizamiento arriba | 0, 0, +1, +1 | Subida gradual | 4 |
| Vibrato | 0, +1, +1, 0, -1, -1 | Ondulación suave | 6 |

Se aplica sumando el valor del ornamento al índice de nota antes de la consulta en la tabla de escala:

```z80
    ; ornament_pos = (frame) AND (ornament_length - 1)
    ld   a, (frame)
    and  $03               ; mod 4 for 4-step ornament
    ld   hl, trill
    add  a, l
    ld   l, a
    ld   a, (hl)           ; A = pitch offset (-1, 0, or +1)
    add  a, c              ; C = current note index
    ; ... look up modified note in scale table

trill:    DB  0, 1, 0, -1   ; 4 bytes
mordent:  DB  0, 1, 0, 0    ; 4 bytes
```

Cuatro bytes transforman un tono estático en una voz viva. Apila múltiples ornamentos en diferentes canales para una textura rica.

### Chord Progressions: Harmonic Movement

La raíz del acorde puede cambiar con el tiempo, siguiendo una progresión. Armonía clásica en 4 bytes:

```z80
; I - IV - V - I progression (the backbone of Western music)
progression:  DB  0, 3, 4, 0     ; scale degrees

; Select chord: (frame / 64) AND 3
    ld   a, (frame)
    rrca
    rrca
    rrca
    rrca
    rrca
    rrca                   ; A = frame / 64
    and  $03               ; mod 4
    ld   hl, progression
    add  a, l
    ld   l, a
    ld   a, (hl)           ; A = chord root (scale degree)
```

Cuatro bytes de datos de progresión, recorridos por el contador de fotogramas, dan a tu pieza de AY-beat movimiento armónico -- la sensación de que "va a algún lugar" en vez de repetir sobre un acorde. Otras progresiones:

| Progresión | Grados | Bytes | Sensación |
|------------|--------|-------|-----------|
| I-IV-V-I | 0, 3, 4, 0 | 4 | Resolución clásica |
| I-V-vi-IV | 0, 4, 5, 3 | 4 | Estándar pop/rock |
| i-VI-III-VII | 0, 5, 2, 6 | 4 | Menor épico |
| I-I-I-I | 0, 0, 0, 0 | 1 (o saltarlo) | Drone/meditativo |

### Total Data Budget for Rich Music

Combinando todas las técnicas:

| Componente | Bytes |
|------------|-------|
| Tabla pentatónica (5 notas) | 10 |
| Patrón de arpegio (1 acorde) | 3 |
| Ornamento (trino) | 4 |
| Progresión (4 acordes) | 4 |
| **Total** | **21** |

21 bytes de datos musicales -- más ~45 bytes de código de motor -- produce música de tres canales con melodía, armonía, cambios de acorde y ornamentación. El ejemplo `aybeat.a80` en el código complementario de este libro demuestra este enfoque en 320 bytes, con espacio de sobra para visuales.

---

## 11. Gramáticas L-System: Melodías fractales

Los sistemas de Lindenmayer (L-systems) son gramáticas de reescritura inventadas originalmente para modelar el crecimiento de plantas. Aplicados a la música, generan secuencias auto-similares con estructura de largo alcance a partir de conjuntos de reglas minúsculos.

### The Concept

Un L-system tiene un **axioma** (cadena inicial) y **reglas de producción** (reglas de expansión). Cada iteración reemplaza cada símbolo según su regla:

```
Axiom: A
Rules: A → A B,  B → A
```

```
Step 0: A
Step 1: A B
Step 2: A B A
Step 3: A B A A B
Step 4: A B A A B A B A
```

Este es el **L-system de Fibonacci**. La secuencia crece según la proporción de Fibonacci (~1,618x por paso). Mapea los símbolos a eventos musicales:

| Símbolo | Significado musical |
|---------|---------------------|
| A | Tocar nota raíz (grado 0 de la escala) |
| B | Tocar quinta (grado 4 de la escala) |

La melodía resultante: raíz, quinta, raíz, raíz, quinta, raíz, quinta, raíz... -- una secuencia que no es periódica ni aleatoria, sino *cuasi-periódica*. Tiene estructura a cada escala, como un fractal. Suena intencional sin ser repetitiva.

### Why L-Systems Work for Music

1. **Auto-similitud.** La melodía a grandes escalas hace eco de la melodía a pequeñas escalas. Esto es lo que hace que la música compuesta se sienta coherente -- los temas recurren a diferentes niveles.
2. **No repetición.** A diferencia de un patrón en bucle, una secuencia de L-system nunca se repite exactamente (para ratios de crecimiento irracionales). Se mantiene interesante.
3. **Codificación mínima.** Las reglas son unos pocos bytes. La secuencia que generan es arbitrariamente larga.

### Useful L-System Rules

| Nombre | Axioma | Reglas | Crecimiento | Carácter |
|--------|--------|--------|-------------|----------|
| Fibonacci | A | A->AB, B->A | ~1,618x | Cuasi-periódico, orgánico |
| Thue-Morse | A | A->AB, B->BA | 2x | Equilibrado, justo -- sin secuencias largas |
| Duplicación de periodo | A | A->AB, B->AA | 2x | Cada vez más sincopado |
| Cantor | A | A->ABA, B->BBB | 3x | Disperso, con silencios (B=silencio) |

### Z80 Implementation

El truco para Z80 es **no expandir la cadena en memoria** (eso requeriría espacio de búfer ilimitado). En su lugar, calcula el símbolo en la posición `n` recursivamente: rastrea hacia atrás a través de las aplicaciones de reglas para determinar de qué símbolo original proviene la posición `n`.

Para el L-system de Fibonacci, hay un atajo elegante. El símbolo en la posición `n` depende de la representación de Zeckendorf (codificación Fibonacci) de `n`. Pero para sizecoding práctico, un enfoque más simple funciona:

```z80
; L-system melody generator (Fibonacci: A→AB, B→A)
; Returns next note in sequence
; Uses position counter in memory
;
; The sequence of symbols can be generated iteratively:
; keep two "previous" bytes and generate the next

lsys_next:
    ld   hl, lsys_state
    ld   a, (hl)           ; prev1
    inc  hl
    ld   b, (hl)           ; prev2
    inc  hl
    ld   c, (hl)           ; position in current generation

    ; Fibonacci rule: output prev1, then swap
    ; When position reaches length, expand to next generation
    ld   d, a              ; D = current symbol to output

    ; Advance: shift the pair
    inc  c
    ld   (hl), c
    dec  hl
    ld   (hl), a           ; prev2 = prev1
    dec  hl
    ; New prev1 from rule: A→A (first output), then A→B (second)
    ; Simplified: alternate symbols based on parity
    ld   a, c
    and  $01
    jr   z, .sym_a
    ld   a, 1              ; B
    jr   .store
.sym_a:
    xor  a                 ; A (=0)
.store:
    ld   (hl), a

    ; Map symbol to scale degree
    ld   a, d
    or   a
    jr   z, .root
    ; B = fifth
    ld   a, 4              ; scale degree 4 = fifth in pentatonic
    ret
.root:
    xor  a                 ; scale degree 0 = root
    ret

lsys_state:
    DB   0                 ; prev1 (A=0, B=1)
    DB   0                 ; prev2
    DB   0                 ; position
```

Un enfoque más práctico para sizecoding: precalcular varias iteraciones del L-system en un búfer corto en tiempo de inicialización (una iteración de Fibonacci desde un axioma de 5 símbolos produce 8 símbolos, dos iteraciones producen 13, tres producen 21 -- todas cabiendo en un búfer pequeño), y luego recorrer el búfer como secuencia melódica:

```z80
; Precompute L-system into buffer (Fibonacci, 3 iterations)
; Axiom: "AABAB" (5 symbols) → 8 → 13 → 21 symbols
; 21 notes of fractal melody from 5 bytes of axiom + expansion code

lsys_expand:
    ld   hl, lsys_axiom
    ld   de, lsys_buf
    ld   b, 5              ; axiom length
.expand_iter:
    ; One iteration: for each symbol, apply rule
    push bc
    push hl
    ld   hl, lsys_buf
    ld   de, lsys_work     ; expand into work buffer
    ; ...expand according to rules...
    pop  hl
    pop  bc
    ; Copy work back to buf for next iteration
    ; Repeat for desired number of iterations
    ret

lsys_axiom:
    DB   0, 0, 1, 0, 1     ; A A B A B

; During playback:
; melody_index = frame / note_duration
; note = lsys_buf[melody_index % buf_length]
; look up in scale table → AY period
```

### Melody as Motion, Not Absolute Notes

El uso más musical de los L-systems no es mapear símbolos a notas fijas, sino mapearlos a **direcciones de paso en la escala**. Una melodía es fundamentalmente sobre *movimiento* -- arriba, abajo, repetir, saltar -- en una escala. La nota inicial es arbitraria; el contorno es lo que importa.

Define los símbolos como movimientos:

| Símbolo | Significado | Paso de escala |
|---------|-------------|---------------|
| U | Paso arriba | +1 |
| D | Paso abajo | -1 |
| R | Repetir | 0 |
| S | Salto arriba (salto) | +2 |

Ahora un L-system genera *contorno* melódico, no secuencias de tono fijas:

```
Axiom: U
Rules: U → U R D,  D → U,  R → U D
```

```
Step 0: U                          (+1)
Step 1: U R D                      (+1, 0, -1)
Step 2: U R D  U D  U              (+1, 0, -1, +1, -1, +1)
Step 3: U R D  U D  U  U R D  U  U R D  U D   ...
```

La melodía camina arriba y abajo en la escala actual, manteniéndose siempre dentro de la tabla de escala. Naturalmente tiende hacia el tono inicial (los retornos equilibran las partidas), creando el arco de tensión-y-resolución que hace que la música se sienta intencional.

```z80
; Motion-based L-system playback
; current_note = scale index, modified by each symbol
    ld   a, (current_note)
    ld   hl, lsys_buf
    ld   b, (melody_pos)
    add  a, l
    ; ... get motion symbol at current position ...
    ; D = motion offset from symbol table
    add  a, d              ; current_note += motion
    and  $0F               ; wrap to scale range
    ld   (current_note), a
    ; look up in pentatonic table → AY period
```

Esto es más musical que mapear A=raíz, B=quinta. Las mismas reglas de L-system producen diferentes melodías dependiendo de la nota inicial y la escala subyacente -- cambia la escala de pentatónica a blues y el mismo contorno produce un humor completamente diferente.

### Tribonacci: Three Symbols for Richer Patterns

El L-system de Fibonacci usa dos símbolos. **Tribonacci** usa tres: A->ABC, B->A, C->B. La proporción de crecimiento es ~1,839x (la constante tribonacci). Tres símbolos significan más variedad en el contenido melódico:

| Símbolo | Como movimiento | Como nota |
|---------|----------------|-----------|
| A | Paso arriba (+1) | Raíz |
| B | Repetir (0) | Tercera |
| C | Paso abajo (-1) | Quinta |

```
Axiom: A
Step 1: A B C
Step 2: A B C  A  B
Step 3: A B C  A  B  A B C  A B C
```

La secuencia tribonacci tiene secuencias no repetitivas más largas que Fibonacci y una estructura interna más compleja. Musicalmente, el vocabulario de tres símbolos da a las melodías más variedad -- no solo oscilan entre dos estados.

### PRNG Melodies with Curated Seeds

Un registro de desplazamiento con retroalimentación lineal (LFSR) o PRNG similar genera una secuencia pseudo-aleatoria determinista a partir de un valor semilla. La secuencia *suena* aleatoria pero se repite exactamente si reincias la semilla. Esto te da fragmentos melódicos reproducibles.

La técnica: **pre-probar muchas semillas, quedarse con las que suenen bien.** Almacena 2-4 valores de semilla (2 bytes cada uno) para diferentes secciones de tu pieza. En tiempo de ejecución, carga la semilla y deja que el PRNG genere la melodía. El PRNG en sí son ~6-8 bytes; cada semilla son 2 bytes.

```z80
; LFSR-based melody generator
; HL = seed (determines the melody)
prng_note:
    ld   a, h
    xor  l              ; mix bits
    rrca
    rrca
    xor  h
    ld   h, a
    ld   a, l
    add  a, h
    ld   l, a           ; advance LFSR state (~6 bytes)
    and  $07            ; constrain to scale range
    ret                 ; A = note index for scale table

; Different seeds → different melodies
seed_verse:   DW  $A73B    ; tested: produces ascending contour
seed_chorus:  DW  $1F4D    ; tested: produces energetic pattern
seed_bridge:  DW  $8E21    ; tested: produces descending, calm
```

El flujo de trabajo: escribe un arnés de prueba que reproduzca la melodía PRNG para cada valor de semilla 0-65535, escucha (o analiza), marca las buenas. En la práctica, unas pocas horas de prueba producen docenas de semillas utilizables. Almacena 3-4 de ellas y cambia entre secciones de tu pieza.

**Combinando con tablas de escala:** la salida del PRNG pasa por la tabla pentatónica, así que incluso las semillas "malas" producen notas consonantes. Estás seleccionando por *contorno melódico*, no evitando notas equivocadas -- la tabla de escala ya se encarga de eso.

**Combinando con L-systems:** usa el PRNG para *seleccionar qué regla de L-system aplicar* en cada paso, creando L-systems estocásticos. La semilla controla la "personalidad" de la pieza; las reglas gramaticales controlan la estructura. Este híbrido produce la salida más rica con la menor cantidad de bytes.

### Combining L-Systems with Other Techniques

Los L-systems generan *secuencias* de notas. Combínalos con las otras técnicas de este apéndice:

- **Tabla de escala** mapea los símbolos del L-system a periodos reales del AY
- **Ornamentos** añaden expresión a cada nota
- **Arpegio** convierte cada nota del L-system en un acorde
- **Drone de envolvente** proporciona una cama armónica sostenida bajo la melodía fractal
- **Progresión de acordes** cambia la raíz -- la melodía del L-system se transpone a cada acorde

El resultado: un programa diminuto (~60-80 bytes de código musical + 20 bytes de datos) generando minutos de música estructuralmente coherente, no repetitiva y armónicamente fundamentada. Esto es composición algorítmica, no ruido aleatorio -- y cabe en una intro de tamaño restringido.

### Other Grammars for Music

Más allá de los L-systems, otras gramáticas formales producen secuencias musicales interesantes:

**Autómatas celulares.** La Regla 30 o la Regla 110, aplicadas a una fila de bits, producen patrones complejos. Mapea las posiciones de bits a eventos de nota on/off. Coste: ~15 bytes para la regla del AC, ~20 bytes para el motor.

**Ritmos euclidianos.** Distribuye `k` golpes uniformemente a lo largo de `n` pasos. Este algoritmo (relacionado con el MCD euclidiano) genera patrones rítmicos encontrados en música de todo el mundo: 3 en 8 es tresillo, 5 en 8 es cinquillo, 7 en 12 es un patrón de campana común del África Occidental. La implementación son ~20 bytes y produce fundamentos rítmicos perfectos para cualquier motor AY-beat.

---

## Ver también

- **Capítulo 11** -- Arquitectura del AY-3-8910, teoría de tono/ruido/envolvente, técnica buzz-bass
- **Capítulo 12** -- Integración del motor musical, sincronización con efectos, percusión digital híbrida
- **Capítulo 13** -- Técnicas de sizecoding, dónde encaja AY-beat en los niveles de tamaño 256b/512b/1K/4K
- **Apéndice G** -- Referencia completa de registros AY con disposiciones de bits, direcciones de puertos y tablas de notas

---

> **Fuentes:** Viznut (Ville-Matias Heikkila), "Algorithmic symphonies from one line of code -- how and why?" (2011); countercomplex.blogspot.com; Capítulo 13 de este libro; varias intros de 256 bytes para ZX Spectrum de Pouet.net
