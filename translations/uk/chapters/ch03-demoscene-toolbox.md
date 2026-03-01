# Розділ 3: Інструментарій демосценера

У кожного ремесла є свій набір хитрощів --- патернів, до яких практики тягнуться настільки інстинктивно, що перестають вважати їх хитрощами. Z80-демосценер тягнеться до технік із цього розділу.

Ці патерни --- розгорнуті цикли, самомодифікований код, стек як канал передачі даних, LDI-ланцюжки, генерація коду та RET-ланцюжок --- з'являються майже в кожному ефекті, який ми будуватимемо в частині II. Вони відрізняють демо, що вміщується в один кадр, від того, якому потрібно три. Вивчи їх тут, і ти впізнаватимеш їх усюди.

---

## Розгорнуті цикли та самомодифікований код

### Вартість циклу

Розглянемо найпростіший можливий внутрішній цикл: очищення 256 байтів пам'яті.

```z80 id:ch03_the_cost_of_looping
; Looped version: clear 256 bytes at (HL)
    ld   b, 0            ; 7 T   (B=0 means 256 iterations)
    xor  a               ; 4 T
.loop:
    ld   (hl), a         ; 7 T
    inc  hl              ; 6 T
    djnz .loop           ; 13 T  (8 on last iteration)
```

Each iteration costs 7 + 6 + 13 = 26 T-states to store a single byte. Only 7 of those T-states do the work --- the rest is overhead. That is 73% waste. For 256 bytes: 256 x 26 - 5 = 6,651 T-states. On a machine where you have 71,680 T-states per frame, those wasted T-states hurt.

### Unrolling: trade RAM for speed

Рішення — грубе й ефективне: випиши тіло циклу N разів і видали цикл.

```z80 id:ch03_unrolling_trade_ram_for_speed
; Unrolled version: clear 256 bytes at (HL)
    xor  a               ; 4 T
    ld   (hl), a         ; 7 T
    inc  hl              ; 6 T
    ld   (hl), a         ; 7 T
    inc  hl              ; 6 T
    ld   (hl), a         ; 7 T
    inc  hl              ; 6 T
    ; ... repeated 256 times total
```

Кожен байт тепер коштує 7 + 6 = 13 тактів. Жодного DJNZ. Жодного лічильника циклу. Загалом: 256 x 13 = 3 328 тактів --- половина від версії з циклом.

The cost is code size: 256 repetitions occupy 512 bytes vs. 7 for the loop. You are trading RAM for speed.

**Коли розгортати:** Внутрішні цикли, що виконуються тисячі разів за кадр --- очищення екрану, малювання спрайтів, копіювання даних.

**Коли НЕ розгортати:** Зовнішні цикли, що виконуються раз або двічі за кадр. Економія 5 тактів на 24 ітераціях дає 120 тактів --- менше ніж три NOP. Не варте роздування.

Практичний компроміс — *часткове розгортання*: розгорни 8 або 16 ітерацій усередині циклу, залиш DJNZ для зовнішнього лічильника. Приклад `push_fill.a80` у каталозі `examples/` цього розділу робить саме це: 16 PUSH'ів на ітерацію, 192 ітерації.

### Самомодифікований код: таємна зброя Z80

Z80 не має кешу інструкцій, буфера попередньої вибірки, конвеєра. Коли процесор витягує байт інструкції з RAM, він зчитує те, що там знаходиться *прямо зараз*. Якщо ти змінив цей байт один цикл тому, процесор побачить нове значення. Це гарантована властивість архітектури.

Самомодифікований код (SMC) означає запис у байти інструкцій під час виконання. Класичний патерн — підміна безпосереднього операнда:

```z80 id:ch03_self_modifying_code_the_z80_s
; Self-modifying code: fill with a runtime-determined value
    ld   a, (fill_value)       ; load the fill byte from somewhere
    ld   (patch + 1), a        ; overwrite the operand of the LD below
patch:
    ld   (hl), $00             ; this $00 gets replaced at runtime
    inc  hl
    ; ...
```

`ld (patch + 1), a` записує в безпосередній операнд наступної `ld (hl), $00`, змінюючи її на `ld (hl), $AA` або що завгодно ти завантажив. Процесор виконує ті байти, що знайде. Деякі поширені патерни SMC:

**Підміна опкодів.** Ти можеш навіть замінити саму інструкцію. Потрібен цикл, який іноді інкрементує HL, а іноді декрементує? Перед циклом запиши опкод INC HL ($23) або DEC HL ($2B) у байт інструкції. Усередині внутрішнього циклу немає жодного розгалуження --- правильна інструкція вже на місці. Порівняй це з підходом розгалуження на кожній ітерації, що коштував би 12 тактів (JR NZ) на кожному пікселі.

**Збереження та відновлення вказівника стеку.** Цей патерн з'являється постійно при використанні PUSH-трюків (нижче):

```z80 id:ch03_self_modifying_code_the_z80_s_2
    ld   (restore_sp + 1), sp     ; save SP into the operand below
    ; ... do stack tricks ...
restore_sp:
    ld   sp, $0000                ; self-modified: the $0000 was overwritten
```

`ld (nn), sp` зберігає поточний SP безпосередньо в операнд пізнішої `ld sp, nn`. Жодної тимчасової змінної. Це ідіоматичний Z80-демосценовий код.

### Self-modifying variables: the `$+1` pattern

The most pervasive SMC pattern on the ZX Spectrum is not patching opcodes or saving SP --- it is embedding a *variable* directly inside an instruction's immediate operand. The idea is simple: instead of storing a counter in a named memory location and loading it with `LD A,(nn)` at 13 T-states, you let the instruction's own operand byte *be* the variable.

```z80 id:ch03_smc_dollar_plus_one
.smc_counter:
    ld   a, 0                    ; 7T — this 0 is the "variable"
    inc  a                       ; 4T
    ld   (.smc_counter + 1), a   ; 13T — write back to the operand byte
```

The `ld a, 0` fetches its operand as part of the normal instruction decode --- 7 T-states total, and the value is already in A. Compare that to loading from a separate memory address: `ld a, (counter)` costs 13 T-states, plus you still need a separate `ld (counter), a` at 13 T-states to write it back. The SMC version reads the variable for free (it is part of the instruction fetch) and only pays the 13 T-states once for the write-back.

In sjasmplus, you can place a label at `$+1` to give the embedded variable a readable name:

```z80 id:ch03_smc_named_variable
    ld   a, 0                    ; 7T
.scroll_pos EQU $ - 1           ; .scroll_pos names the operand byte above
    add  a, 4                   ; 7T — advance by 4 pixels
    ld   (.scroll_pos), a       ; 13T — store back into the operand
```

This pattern appears everywhere in ZX Spectrum code: scroll positions, animation frame counters, effect phase accumulators, direction flags. Any single-byte value that persists between calls is a candidate. You will see it constantly in Parts II and V --- practically every effect routine in this book uses at least one self-modifying variable.

The convention is to prefix these labels with `.smc_` or place them immediately after the instruction they modify. Either way, the intent should be clear to anyone reading the source. As we noted in Chapter 2, local labels (`.label`) prevent naming collisions when multiple routines each have their own embedded variables.

**Застереження.** SMC безпечний на Z80, eZ80 та кожному клоні Spectrum. Він *не* безпечний на сучасних процесорах з кешуванням (x86, ARM) без явних інструкцій скидання кешу. Якщо ти портуєш на іншу архітектуру, це перше, що зламається.

---

## Стек як канал передачі даних

### Чому PUSH — найшвидший запис на Z80

Інструкція PUSH записує 2 байти в пам'ять і зменшує SP, все за 11 тактів. Порівняймо альтернативи для запису даних за екранною адресою:

| Метод | Записано байтів | Тактів | Тактів на байт |
|--------|--------------|----------|-------------------|
| `ld (hl), a` + `inc hl` | 1 | 13 | 13,0 |
| `ld (hl), a` + `inc l` | 1 | 11 | 11,0 |
| `ldi` | 1 | 16 | 16,0 |
| `ldir` (за байт) | 1 | 21 | 21,0 |
| `push hl` | 2 | 11 | **5,5** |

PUSH записує два байти за 11 тактів --- 5,5 тактів на байт. Майже в 4 рази швидше за LDIR. Підступ: PUSH записує туди, куди вказує SP, а SP зазвичай — це твій стек. Щоб використовувати PUSH як канал передачі даних, ти мусиш захопити вказівник стеку.

### Техніка

Патерн завжди однаковий:

1. Вимкни переривання (DI). Якщо переривання спрацює, поки SP вказує на екран, процесор покладе адресу повернення у твої піксельні дані. Настане хаос.
2. Збережи SP. Використай самомодифікований код, щоб зберегти його.
3. Встанови SP на *кінець* цільової області. Стек росте вниз --- PUSH зменшує SP перед записом. Отже, якщо ти хочеш заповнити від $4000 до $57FF, встанови SP на $5800.
4. Завантаж дані в регістрові пари та виконуй PUSH повторно.
5. Віднови SP та увімкни переривання (EI).

<!-- figure: ch03_push_fill_pipeline -->

```mermaid id:ch03_the_technique
graph TD
    A["DI — disable interrupts"] --> B["Save SP via self-modifying code"]
    B --> C["Set SP to screen bottom ($5800)"]
    C --> D["Load register pairs with fill data"]
    D --> E["PUSH loop: 16 PUSHes per iteration<br>11T × 16 = 176T → 32 bytes"]
    E --> F{All 192<br>iterations done?}
    F -- No --> E
    F -- Yes --> G["Restore SP from self-modified LD SP,nn"]
    G --> H["EI — re-enable interrupts"]

    style E fill:#f9f,stroke:#333
    style A fill:#fdd,stroke:#333
    style H fill:#fdd,stroke:#333
```

> **Why PUSH wins:** `LD (HL),A` + `INC HL` writes 1 byte in 13T (13.0 T/byte). `PUSH HL` writes 2 bytes in 11T (**5.5 T/byte**) — nearly 2.4× faster per byte. The cost: interrupts must be disabled while SP is hijacked.

Ось ядро прикладу `push_fill.a80` з каталогу `examples/` цього розділу:

```z80 id:ch03_the_technique_2
stack_fill:
    di                          ; critical: no interrupts while SP is moved
    ld   (restore_sp + 1), sp   ; self-modifying: save SP

    ld   sp, SCREEN_END         ; SP points to end of screen ($5800)
    ld   hl, $AAAA              ; pattern to fill

    ld   b, 192                 ; 192 iterations x 16 PUSHes x 2 bytes = 6144
.loop:
    push hl                     ; 11 T  \
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |  16 PUSHes = 32 bytes
    push hl                     ; 11 T   |  = 176 T-states
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T   |
    push hl                     ; 11 T  /
    djnz .loop                  ; 13 T (8 on last)

restore_sp:
    ld   sp, $0000              ; self-modified: restores original SP
    ei
    ret
```

Внутрішнє тіло з 16 PUSH записує 32 байти за 176 тактів. Загалом для повної 6 144-байтної піксельної області: приблизно 36 000 тактів. Порівняй з LDIR: 6 144 x 21 - 5 = 129 019 тактів. Метод PUSH приблизно в 3,6 рази швидший --- різниця між тим, щоб вміститися в один кадр, і виходом у наступний.

![PUSH-based screen fill — the entire pixel area filled in a single frame using the stack trick](../../build/screenshots/ch03_push_fill.png)

### POP as a fast read

PUSH is the fastest write, but POP is the fastest *read*. POP loads 2 bytes from (SP) into a register pair in 10 T-states --- that is 5.0 T-states per byte. Compare the alternatives:

| Method | Bytes read | T-states | T-states per byte |
|--------|-----------|----------|-------------------|
| `ld a, (hl)` + `inc hl` | 1 | 13 | 13.0 |
| `ld a, (hl)` + `inc l` | 1 | 11 | 11.0 |
| `ldi` (as a read+write) | 1 | 16 | 16.0 |
| `pop hl` | 2 | 10 | **5.0** |

The pattern: pre-build a table of 16-bit values in memory, point SP at the start of the table, and POP into register pairs. Each POP advances SP by 2, walking through the table automatically. This is the read-side complement of the PUSH write trick.

Combine POP and PUSH and you get a fast memory-to-memory pipe: POP a value from a source table (10T), process the register pair if needed, then PUSH it to the destination (11T). Total: 21 T-states for 2 bytes --- the same throughput as LDIR, but with the register pair available for processing between the read and write. You can mask bits, add offsets, swap bytes, or apply any register-to-register transformation at no extra memory-access cost. This POP-process-PUSH pipeline is the backbone of many compiled sprite routines.

### Де використовуються PUSH-трюки

- **Очищення екрану.** Найпоширеніше застосування. Кожне демо потребує очищення екрану між ефектами.
- **Скомпільовані спрайти.** Спрайт компілюється в послідовність інструкцій PUSH із попередньо завантаженими регістровими парами. Найшвидший можливий вивід спрайтів на Z80.
- **Швидкий вивід даних.** Будь-коли, коли потрібно швидко записати блок даних у суміжний діапазон адрес: заливка атрибутів, копіювання буферів, побудова списків відображення.

Ціна, яку ти платиш: переривання вимкнені. Якщо твій музичний програвач працює з IM2-переривання, він пропустить удар під час тривалої PUSH-послідовності. Кодери демо планують це заздалегідь --- розміщують PUSH-заливки під час бордюрного часу або розбивають їх на кілька кадрів.

---

## LDI-ланцюжки

### LDI проти LDIR

LDI копіює один байт з (HL) в (DE), інкрементує обидва та декрементує BC. LDIR робить те саме, але повторює, поки BC = 0. Різниця у таймінгу:

| Інструкція | Тактів | Примітки |
|-------------|----------|-------|
| LDI | 16 | Копіює 1 байт, завжди 16 T |
| LDIR (за байт) | 21 | Копіює 1 байт, повертається назад. Останній байт: 16 T |

LDIR коштує на 5 тактів більше за байт через внутрішню перевірку повернення. Ці 5 тактів швидко накопичуються.

Для 256 байтів:
- LDIR: 255 x 21 + 16 = 5 371 такт
- 256 x LDI: 256 x 16 = 4 096 тактів
- Економія: 1 275 тактів (24%)

A chain of individual LDI instructions is just 256 repetitions of the two-byte opcode `$ED $A0`. That is 512 bytes of code to save 24% --- the same RAM-for-speed trade-off as loop unrolling.

### Коли LDI-ланцюжки блищать

Оптимальна ситуація --- копіювання блоків відомого розміру. Ланцюжок з 32 LDI економить 160 тактів порівняно з LDIR для рядка спрайта. За 24 рядки це 3 840 тактів на кадр.

Але справжня потужність з'являється, коли ти поєднуєш LDI-ланцюжки з *арифметикою точки входу*. Якщо ти маєш ланцюжок з 256 LDI і хочеш скопіювати лише 100 байтів, стрибни в ланцюжок на позицію 156. Жодного лічильника циклу, жодного налаштування. Ця техніка використовується у хаос-зумері Introspec'а в Eager (2015):

```z80 id:ch03_when_ldi_chains_shine
; Chaos zoomer inner loop (simplified from Eager)
; Each line copies a different number of bytes from a source buffer.
; Entry point into the LDI chain is calculated per line.
    ld   hl, source_data
    ld   de, dest_screen
    ; ... calculate entry point based on zoom factor ...
    jp   (ix)             ; jump into the LDI chain at the right point

ldi_chain:
    ldi                   ; byte 255
    ldi                   ; byte 254
    ldi                   ; byte 253
    ; ... 256 LDIs total ...
    ldi                   ; byte 0
    ; falls through to next line setup
```

Це копіювання змінної довжини з нульовими побайтовими накладними витратами циклу — техніка, яку просто неможливо досягти з LDIR. Це одна з причин, чому LDI --- найкращий друг кожного в демосценовому коді.

![LDI chain vs LDIR — red stripes show LDI chain timing, blue stripes show LDIR; thinner red proves LDI is faster](../../build/screenshots/ch03_ldi_chain.png)

---

## Bit Tricks: SBC A,A and Friends

### SBC A,A as a conditional mask

After any instruction that produces a carry flag, `SBC A,A` converts that flag into a full byte: $FF if carry was set, $00 if not. The cost: 4 T-states. Compare this to the branching alternative --- `JR C,.set` / `LD A,0` / `JR .done` / `.set: LD A,$FF` / `.done:` --- which costs 17-22 T-states depending on which path is taken, plus the pipeline disruption of a conditional branch.

The canonical use case is *bit-to-byte expansion*. Given a byte where each bit represents a pixel (the Spectrum's pixel format), you can expand each bit into a full attribute byte:

```z80 id:ch03_sbc_bit_expand
    rlc  (hl)            ; rotate top bit into carry    — 15T
    sbc  a, a            ; A = $FF if set, $00 if not   — 4T
    and  $47             ; A = bright white ($47) or $00 — 7T
```

Three instructions, 26 T-states, no branches. To select between two *arbitrary* values rather than zero and a mask, use the pattern `SBC A,A : AND mask : XOR base`. The AND selects which bits change between the two values, and the XOR flips them to the desired base. This pattern replaces every "if bit set then value A else value B" test in your inner loops.

### ADD A,A vs SLA A

Both instructions shift A left by one bit. But `ADD A,A` is 4 T-states and 1 byte, while `SLA A` is 8 T-states and 2 bytes. There is no situation where SLA A is preferable --- `ADD A,A` is strictly faster and smaller. Similarly, `ADD HL,HL` shifts HL left in 11 T-states (1 byte), replacing the two-instruction sequence `SLA L : RL H` at 16 T-states (4 bytes). For a 16-bit left shift inside an inner loop running 192 times per frame, that substitution alone saves 960 T-states --- over four scanlines of border time.

These are not tricks. They are vocabulary. Just as a fluent speaker does not pause to conjugate common verbs, a Z80 programmer reaches for `ADD A,A` and `SBC A,A` without conscious thought. If you find yourself writing `SLA A` or a conditional branch to select between two values, stop and reach for the shorter form. The T-states add up.

---

## Генерація коду

### Code generation: writing the program that draws

Все перераховане вище --- фіксована оптимізація: код працює однаково кожен кадр. Генерація коду йде далі: твоя програма пише програму, що малює екран. Є два варіанти: офлайн (перед асемблюванням) та під час виконання.

### Офлайн: генерація асемблера з мови вищого рівня

Introspec використовував Processing (середовище креативного кодування на Java) для генерації Z80-асемблера для хаос-зумера в Eager (2015). Хаос-зумер змінює масштаб кожен кадр --- різні піксель-джерела відображаються в різні позиції на екрані. Замість обчислення цих відображень під час виконання, скрипт на Processing попередньо обчислював кожне відображення й виводив .a80-файли з оптимізованими LDI-ланцюжками та інструкціями LD.

Робочий процес: скрипт на Processing обчислює, для кожного кадру, який байт-джерело відображається на який байт екрану. Він виводить вихідний код Z80-асемблера --- послідовності `ld hl, source_addr` та інструкцій `ldi` --- які асемблер (sjasmplus) збирає разом з рукописним кодом рушія. Під час виконання рушій просто викликає попередньо згенерований код для поточного кадру.

Це не "шахрайство". Це фундаментальне прозріння, що розподіл праці між часом компіляції та часом виконання може повністю усунути розгалуження, пошуки та арифметику з внутрішнього циклу. Скрипт на Processing виконує важку математику один раз, повільно, на сучасній машині. Z80 робить легку частину --- копіювання байтів --- настільки швидко, наскільки фізично можливо.

### Під час виконання: програма пише машинний код під час виконання

Іноді параметри змінюються кожен кадр, тому офлайнової генерації недостатньо. Процедура відображення сфери в Illusion від X-Trade (ENLiGHT'96) генерує машинний код у RAM-буфер під час виконання. Геометрія сфери змінюється при обертанні --- різні пікселі потребують різних відстаней пропуску. Перед кожним кадром рушій видає байти опкодів у буфер, а потім виконує їх:

```z80 id:ch03_runtime_the_program_writes
; Runtime code generation (conceptual, simplified from Illusion)
; Generate an unrolled rendering loop for this frame's sphere slice

    ld   hl, code_buffer
    ld   de, sphere_table       ; per-frame skip distances

    ld   b, SPHERE_WIDTH
.gen_loop:
    ld   a, (de)                ; load skip distance for this pixel
    inc  de

    ; Emit: ld a, (hl) -- opcode $7E
    ld   (hl), $7E
    inc  hl

    ; Emit: add a, N   -- opcodes $C6, N
    ld   (hl), $C6
    inc  hl
    ld   (hl), a                ; the skip distance, as immediate operand
    inc  hl

    djnz .gen_loop

    ; Emit: ret -- opcode $C9
    ld   (hl), $C9

    ; Now execute the generated code
    call code_buffer
```

Згенерований код --- це прямолінійна послідовність без розгалужень, без пошуків, без накладних витрат циклу --- але це *різний код кожен кадр*. Замість "if pixel_skip == 3 then..." на 12 тактів за розгалуження, ти видаєш саме ті інструкції, що потрібні, й виконуєш їх без розгалужень.

### The cost of generation

Runtime code generation is not free. Look at the generator loop above: each emitted instruction requires loading an opcode byte, storing it, advancing the pointer, and possibly loading an operand --- roughly 30-50 T-states per emitted byte, depending on complexity. Call it ~40 T-states on average. For a generated routine of 100 instruction bytes, that is about 4,000 T-states of generation overhead.

The break-even point: generation pays off when the generated code runs more than once per frame, or when it replaces branching logic that costs more than the generation itself. In the Illusion sphere mapper, each generated rendering pass executes once per frame --- but it replaces per-pixel conditional branches that would cost far more. Alone Coder documented a similar trade-off in his rotation engine: generating a sequence of INC H/INC L instructions for coordinate stepping costs roughly 5,000 T-states to emit, but eliminates coordinate arithmetic that would cost approximately 146,000 T-states if computed inline. The generation overhead is under 4% of the cost it replaces.

The rule of thumb: if you find yourself writing a loop that contains branches selecting between different instruction sequences based on per-pixel or per-line data, that loop is a candidate for code generation. Emit the right instructions once, execute them branch-free, and regenerate only when the parameters change.

**Коли генерувати код:** Якщо ті самі операції відбуваються кожен кадр з лише зміною даних, самомодифікованого коду (підміна операндів) достатньо. Якщо змінюється *структура* --- інша кількість ітерацій, інші послідовності інструкцій --- генеруй код. Якщо ти можеш попередньо обчислити варіації на сучасній машині, віддай перевагу офлайн-генерації: вона зневаджувана, перевіряєма й не має витрат під час виконання. Генерація під час виконання окупається, коли згенерований код виконується набагато частіше, ніж коштує його генерація.

---

## RET-ланцюжок

### Перетворення стеку на таблицю диспетчеризації

У 2025 році DenisGrachev опублікував на Hype техніку, розроблену для його гри Dice Legends. Проблема: рендеринг тайлового ігрового поля вимагає малювання десятків тайлів за кадр. Наївний підхід використовує CALL:

```z80 id:ch03_turning_the_stack_into_a
; Naive approach: call each tile renderer
    call draw_tile_0
    call draw_tile_1
    call draw_tile_2
    ; ...
```

Кожен CALL коштує 17 тактів. Для ігрового поля 30 x 18 (540 тайлів) це 9 180 тактів лише на диспетчеризацію.

Прозріння DenisGrachev'а: встановити SP на *список рендерингу* --- таблицю адрес --- і завершувати кожну процедуру малювання тайлу командою RET. RET витягує 2 байти з (SP) у PC. Якщо SP вказує на твій список рендерингу, RET не повертається до викликача --- він стрибає до наступної процедури у списку.

```z80 id:ch03_turning_the_stack_into_a_2
; RET-chaining: zero call overhead
    di
    ld   (restore_sp + 1), sp   ; save SP
    ld   sp, render_list        ; SP points to our dispatch table

    ; "Call" the first tile routine by falling into it or using RET:
    ret                         ; pops first address from render_list

; Each tile routine ends with:
draw_tile_N:
    ; ... draw the tile ...
    ret                         ; pops NEXT address from render_list

; The render list is a sequence of addresses:
render_list:
    dw   draw_tile_42           ; first tile to draw
    dw   draw_tile_7            ; second tile
    dw   draw_tile_42           ; third tile (same tile type, different position)
    ; ... one entry per tile on screen ...
    dw   render_done            ; sentinel: address of cleanup code

render_done:
restore_sp:
    ld   sp, $0000              ; self-modified: restore SP
    ei
```

Кожна диспетчеризація тепер коштує 10 тактів (RET) замість 17 (CALL). Для 540 тайлів: 3 780 зекономлених тактів. Але справжній виграш --- безкоштовна диспетчеризація: кожен запис може вказувати на іншу процедуру (широкий тайл, порожній тайл, анімований тайл). Жодної таблиці стрибків, жодного непрямого виклику. Список рендерингу *і є* програмою.

### Три стратегії для списку рендерингу

DenisGrachev дослідив три підходи до побудови списку рендерингу:

1. **Карта як список рендерингу.** Сама тайлова карта є списком рендерингу: кожна клітинка містить адресу процедури малювання для цього типу тайла. Просто, але негнучко --- зміна тайла означає перезапис 2 байтів на карті.

2. **Сегменти на основі адрес.** Екран поділяється на сегменти. Список рендерингу кожного сегмента --- це блок адрес, скопійований з головної таблиці. Зміна тайлів означає копіювання нового блоку адрес.

3. **На основі байтів з 256-байтовими таблицями пошуку.** Кожен тип тайла --- це один байт (індекс тайла). 256-байтова таблиця пошуку відображає індекси тайлів на адреси процедур. Список рендерингу будується ітерацією через байти тайлової карти та пошуком кожної адреси. Саме цей підхід DenisGrachev обрав для Dice Legends.

Використовуючи підхід на основі байтів, він розширив ігрове поле з 26 x 15 тайлів (межа його попереднього рушія) до 30 x 18 тайлів, зберігаючи цільову частоту кадрів. Економія від усунення накладних витрат CALL у поєднанні з безкоштовною диспетчеризацією звільнила достатньо тактів для рендерингу на 40% більше тайлів.

### Компроміси

Як і з усіма стековими трюками, переривання мають бути вимкнені, поки SP захоплений. Кожна тайлова процедура має бути самодостатньою --- завершуватися RET і не використовувати CALL, оскільки справжній стек недоступний. На практиці тайлові процедури достатньо короткі, тож це не є обмеженням.

---

## Бічна панель: "Код мертвий" (Introspec, 2015)

У січні 2015 року Introspec опублікував на Hype коротке, провокативне есе під назвою "Код мертвий" (Kod myortv). Аргумент проводить паралель з "Смертю автора" Ролана Барта: так само як Барт стверджував, що значення тексту належить читачеві, а не автору, Introspec стверджує, що демосценовий код справді живе лише тоді, коли хтось його читає --- в зневаджувачі, в лістингу дизасемблера, у вихідному коді, що поділяється на форумі.

Незручна правда: сучасні демо споживаються як візуальні медіа. Люди дивляться їх на YouTube. Вони голосують на Pouet на основі відеозаписів. Ніхто не бачить внутрішніх циклів. Блискуча оптимізація, що економить 3 такти на піксель, невидима для 99% аудиторії. "Написання коду виключно заради коду," писав Introspec, "втратило актуальність."

І все ж.

Ти читаєш цю книгу. Ми відкриваємо зневаджувач. Ми рахуємо такти. Ми заглядаємо всередину. Техніки в цьому розділі --- не музейні експонати. Вони --- живі інструменти, і те, що більшість людей їх ніколи не побачить, не применшує їхню майстерність.

Есе Introspec'а --- це виклик, а не капітуляція. Він продовжив публікувати одні з найдетальніших технічних аналізів, які коли-небудь знала ZX-сцена --- включаючи розбір Illusion та бенчмарки стиснення, на які ми посилаємося протягом цієї книги. Код може бути мертвий для глядача YouTube. Але для читача з дизасемблером і допитливим розумом він дуже навіть живий.

---

## Збираючи все разом

Техніки в цьому розділі не ізольовані. На практиці вони компонуються:

- **Screen clearing** combines *unrolled loops* with *PUSH tricks*: a partially unrolled loop of 16 PUSHes per iteration, with SP hijacked via *self-modifying code*.
- **Compiled sprites** combine *code generation* (each sprite compiles to executable code), *POP reads* and *PUSH output* (the fastest way to move pixel data through registers), *bit tricks* (SBC A,A for mask expansion), and *self-modification* (patching screen addresses per frame).
- **Tile engines** combine *RET-chaining* for dispatch with *LDI chains* inside each tile routine for fast data copy.
- **Chaos zoomers** combine *offline code generation* (Processing scripts emitting assembly) with *LDI chains* (the generated code is mostly LDI sequences) and *self-modification* (patching source addresses per frame).
- **Attribute effects** combine *POP reads* from pre-computed tables with *bit tricks* (SBC A,A to expand bitmasks into colour values) and *PUSH writes* for fast attribute output.

The common thread: every technique eliminates something from the inner loop. Unrolling eliminates the loop counter. Self-modification eliminates branches. PUSH eliminates per-byte write overhead. POP eliminates per-byte read overhead. LDI chains eliminate the LDIR repeat penalty. Bit tricks eliminate conditional branches. Code generation eliminates the entire distinction between code and data. RET-chaining eliminates CALL overhead.

The Z80 runs at 3.5 MHz. You have 71,680 T-states per frame. Every T-state you save in the inner loop is a T-state you can spend on more pixels, more colours, more motion. The toolbox in this chapter is how you get there.

У розділах, що слідують, ти побачиш кожну з цих технік у дії в реальних демо --- текстурованій сфері Illusion, атрибутному тунелі Eager, мультиколорному рушії Old Tower. Мета цього розділу полягала в тому, щоб дати тобі словник. Тепер подивимось, що майстри збудували з ним.

---

## Спробуй сам

1. **Виміряй різницю.** Візьми тестову обв'язку з розділу 1 і виміряй три версії заповнення 256 байтів: (a) цикл `ld (hl), a : inc hl : djnz`, (b) повністю розгорнутий `ld (hl), a : inc hl` x 256, і (c) PUSH-заповнення з `examples/push_fill.a80`. Порівняй ширину бордюрних смуг. Смуга PUSH-версії має бути видимо коротшою.

2. **Побудуй самомодифіковане очищення.** Напиши процедуру очищення екрану, що приймає візерунок заповнення як параметр і підставляє його в PUSH-цикл заповнення за допомогою самомодифікованого коду. Виклич її двічі з різними візерунками й спостерігай за чергуванням екрану.

3. **Заміряй LDI-ланцюжок.** Напиши 32-байтове копіювання за допомогою LDIR та ще одне за допомогою 32 x LDI. Виміряй обидва технікою кольору бордюру. LDI-ланцюжок має заощадити 160 тактів --- видимо, якщо запускати копіювання у щільному циклі.

4. **Поекспериментуй з точками входу.** Побудуй LDI-ланцюжок на 128 записів та невелику процедуру, що обчислює точку входу на основі значення в регістрі A (0–128). Стрибай у ланцюжок у різних точках. Це спрощена версія копіювання змінної довжини, що використовується у реальних хаос-зумерах.

5. **Variable-length copier with calculated entry.** Build a 256-entry LDI chain and a front-end that accepts a byte count in register B (1--256). Calculate the entry point: each LDI is 2 bytes, so the offset is (256 - B) x 2 from the start of the chain. Add this to the chain's base address, then JP (HL) into it. Wrap the whole thing in the border-colour harness and compare the stripe width against LDIR for the same byte count. For small counts (under 16), the difference is slim. For counts above 64, the LDI chain pulls visibly ahead.

6. **Bit-to-attribute unpacker.** Write a routine that reads a byte from (HL), rotates each bit out with RLC (HL), and uses `SBC A,A : AND $47` to expand each bit into an attribute byte (bright white or black). Store the 8 resulting attribute bytes to a destination buffer using (DE) / INC DE. This is the seed of a compiled sprite's attribute writer --- in later chapters you will see this pattern generate entire sprite routines.

> **Джерела:** DenisGrachev "Tiles and RET" (Hype, 2025); Introspec "Making of Eager" (Hype, 2015); Introspec "Technical Analysis of Illusion" (Hype, 2017); Introspec "Code is Dead" (Hype, 2015)
