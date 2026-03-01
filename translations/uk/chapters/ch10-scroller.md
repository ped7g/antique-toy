# Розділ 10: Скролер з точкового поля та 4-фазний колір

> *"Два нормальних кадри та два інвертованих кадри. Око бачить середнє."*
> -- Introspec, Making of Eager (2015)

---

ZX Spectrum відображає два кольори на комірку 8x8. Текст прокручується по екрану з будь-якою швидкістю, яку може забезпечити процесор. Це фіксовані обмеження — залізо робить те, що робить, і жодна хитрість не змінить кремній.

Але хитрість може змінити те, що *сприймає* глядач.

Цей розділ зводить разом дві техніки з двох різних демо, розділених майже двадцятьма роками, але пов'язаних спільним принципом. Скролер з точкового поля з *Illusion* від X-Trade (ENLiGHT'96) рендерить текст як хмару окремих точок, що підстрибують, кожна розміщена ціною лише 36 тактів. 4-фазна колірна анімація з *Eager* від Introspec'а (3BM Open Air 2015) чергує чотири ретельно побудованих кадри на 50 Гц, щоб обманути око і показати кольори, які залізо не може видати. Одна використовує просторову роздільність — розміщує точки де завгодно, без обмежень символьних комірок. Інша використовує часову роздільність — перемикає кадри швидше, ніж може встигнути око. Разом вони демонструють дві основні осі обману на обмеженому залізі: простір і час.

---

## Частина 1: Скролер з точкового поля

### Що бачить глядач

Уяви повідомлення — "ILLUSION BY X-TRADE" — відрендерене не суцільними блочними символами, а як поле окремих точок, кожна точка — один піксель. Текст плавно дрейфує горизонтально по екрану. Але точки не сидять на плоских рядках розгортки. Вони підстрибують. Усе точкове поле хвилясто коливається синусоїдою, кожна колонка зміщена вертикально відносно сусідів, створюючи враження тексту, що пульсує на водній поверхні.

### Шрифт як текстура

Шрифт зберігається як бітмап-текстура у пам'яті — один біт на точку. Якщо біт 1, точка з'являється на екрані. Якщо біт 0, нічого не відбувається. Критичне слово — *прозорий*. У звичайному рендерері ти записуєш кожну піксельну позицію. У скролері з точкового поля прозорі пікселі майже безкоштовні. Ти перевіряєш біт, і якщо він нульовий, пропускаєш. Лише встановлені пікселі потребують запису у відеопам'ять.

Це означає, що вартість рендерингу пропорційна кількості видимих точок, а не загальній площі. Типовий символ 8x8 може мати 20 встановлених пікселів із 64. Для великого прокручуваного повідомлення ця економія має величезне значення. BC вказує на дані шрифту; RLA зсуває кожен біт у прапорець переносу для визначення увімкнено чи вимкнено.

![Dotfield scroller prototype — each character rendered as individual pixels bouncing on a sine wave, producing the classic demoscene text effect](../../build/screenshots/proto_ch10_dotfield.png)

### Стекові таблиці адрес

У звичайному скролері екранна позиція кожного пікселя обчислюється з координат (x, y) за допомогою формули черезрядкових адрес Spectrum. Це обчислення включає зсуви, маски та пошук по таблицях. Робити це для тисяч пікселів за кадр з'їло б увесь бюджет.

Розв'язок Dark'а: попередньо обчисли кожну екранну адресу та зберігай їх як таблицю, по якій ходить вказівник стеку. POP зчитує 2 байти та автоінкрементує SP, усе за 10 тактів. Вкажи SP на таблицю замість реального стеку, і POP стає найшвидшим можливим отриманням адреси — жодних індексних регістрів, жодної арифметики вказівників, жодних накладних витрат.

Compare POP to the alternatives. `LD A,(HL) : INC HL` fetches one byte in 11 T-states -- you would need two such pairs (22 T) to fetch an address, plus `LD L,A / LD H,A` bookkeeping. An indexed load like `LD L,(IX+0) : LD H,(IX+1)` costs 38 T-states for the pair. POP fetches both bytes, increments the pointer, and loads a register pair -- 10 T-states, no contest. The price is that you surrender the stack pointer to the renderer. Nothing else can use SP while the inner loop runs.

This means interrupts are fatal. If an interrupt fires while SP points into the address table, the Z80 pushes the return address onto the "stack" -- which is actually your data table. Two bytes of carefully computed screen addresses get overwritten with a return address, and the interrupt service routine proceeds to execute whatever garbage sits at the corrupted location. The result is anything from a garbled frame to a hard crash. The solution is simple and non-negotiable: `DI` before hijacking SP, `EI` after restoring it. Every POP-trick routine in every Spectrum demo follows this pattern:

```z80 id:ch10_stack_based_address_tables
    di
    ld   (.smc_sp+1), sp  ; save SP via self-modifying code
    ld   sp, table_addr    ; point SP at pre-computed data
    ; ... inner loop using POP ...
.smc_sp:
    ld   sp, $0000          ; self-modified: restores original SP
    ei
```

The save/restore uses self-modifying code because it is the fastest way to both save and restore SP in one step. `EX (SP),HL` requires a valid stack. `LD (addr),SP` exists (opcode ED 73, 20 T-states), but it saves SP to a fixed address -- you would then need a separate `LD SP,(addr)` to restore it later (also 20 T-states), and the restore is no faster than the self-modifying approach. The SMC technique writes SP's value directly into the operand field of a later `LD SP,nnnn` instruction: `LD (.smc+1),SP` costs 20 T-states for the save, and the restore (`LD SP,nnnn` with the patched operand) costs just 10 T-states. The combined save+restore is 30 T-states versus 40 T-states for the LD (addr),SP / LD SP,(addr) pair -- a small saving that also avoids reserving a separate memory location.

One subtle consequence: the DI/EI window blocks the frame interrupt. If the inner loop runs long, HALT at the top of the main loop will still catch the next interrupt -- but if the rendering overshoots an entire frame, you lose sync. This is why the budget arithmetic matters. You must know your worst-case timing before committing to the POP trick.

Рух підстрибування закодований цілком у таблиці адрес. Кожен запис — екранна адреса, що вже включає вертикальний синусоїдальний зсув. "Підстрибування" не відбувається під час рендерингу. Воно відбулося, коли таблиця була побудована. Усі три виміри анімації — позиція скролу, хвиля підстрибування, форма символу — згортаються в єдину лінійну послідовність 16-бітних адрес, споживаних на повній швидкості через POP.

### Внутрішній цикл

Аналіз Introspec'а 2017 року Illusion розкриває внутрішній цикл. Один байт даних шрифту містить 8 бітів — 8 пікселів. `LD A,(BC)` зчитує байт один раз, потім RLA зсуває по одному біту за раз через 8 розгорнутих ітерацій:

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

Попіксельна вартість, за винятком амортизованого зчитування байта:

| Шлях | Інструкції | Такти |
|------|-------------|----------|
| Непрозорий піксель | `pop hl` + `rla` + `jr nc` (не взято) + `set ?,(hl)` | **36** |
| Прозорий піксель | `pop hl` + `rla` + `jr nc` (взято) | **26** |

![Bouncing dotfield text scroller in action -- text rendered as individual pixels undulating on a sine wave](../../build/screenshots/ch10_dotscroll.png)

`LD A,(BC)` та `INC BC` коштують 13 тактів, амортизованих на 8 пікселів — приблизно 1,6 T на піксель. "36 тактів на піксель" Introspec'а — це найгірша вартість у межах розгорнутого байта, без цих накладних витрат.

Бітова позиція SET змінюється для кожного пікселя (7, 6, 5 ... 0), тому цикл розгорнутий 8 разів, а не повторюється. Параметризувати бітову позицію в SET без IX/IY індексації (надто повільно) або самомодифікованого коду (накладні витрати) неможливо. Розгортання — чисте рішення.

### Бюджетна арифметика

Let us work the numbers properly. The standard Spectrum 48K frame is 69,888 T-states (the Pentagon clone runs slightly longer at 71,680). Of that, the ULA steals T-states during the active display for memory contention, but the scroller writes to screen memory during the entire frame, not just during the border, so contention is a real factor. In practice, assume about 60,000 usable T-states on a 48K and 65,000 on a Pentagon. Subtract music playback (a typical AY player costs 3,000-5,000 T per frame), screen clearing, and table construction. That leaves roughly 40,000-50,000 T-states for the actual dot rendering.

Consider a display of 8 characters of 8x8 font = 512 font bits per frame (8 chars x 8 bytes x 8 bits). With a typical font fill rate of about 30%, roughly 154 bits are set (opaque) and 358 are clear (transparent). The inner loop cost:

- 154 opaque pixels at 36 T each = 5,544 T
- 358 transparent pixels at 26 T each = 9,308 T
- 64 byte-fetches (`LD A,(BC) : INC BC`) at 13 T each = 832 T
- Total: approximately 15,684 T-states

That is well within a single frame. You could render 20+ characters before hitting the budget ceiling. The bottleneck is not the inner loop -- it is the table construction. Building 512 address entries with sine lookups and screen address calculation costs roughly 100-150 T-states per entry (depending on implementation), adding 50,000-75,000 T to the frame. Illusion solves this by pre-computing the entire table set into memory and cycling through offsets, or by building incrementally: when the scroll advances by one pixel, most table entries shift by one position and only the new column needs full recalculation.

The numbers work because two optimisations compound. Stack-based addressing eliminates all coordinate calculation from the inner loop. Texture-driven transparency eliminates all writes for empty pixels. The table build is expensive, but it runs outside the time-critical DI window and can be spread across the frame.

### Як закодоване підстрибування

Таблиця адрес — це місце, де живе мистецтво. Для створення руху підстрибування таблиця синусів зміщує вертикальну позицію кожної колонки:

```text
y_offset = sin_table[(column * phase_freq + scroll_pos * speed_freq) & 255]
```

The two frequency parameters control the visual character of the wave. `phase_freq` determines the spatial frequency -- how many wave cycles fit across the visible dot columns. A value of 4 means each dot column advances 4 positions into the sine table, so 256/4 = 64 columns span one full wave cycle. A value of 8 doubles the frequency, creating a tighter ripple. `speed_freq` controls how fast the wave propagates over time: higher values make the bounce scroll faster independently of the text scroll.

The sine table itself is a 256-byte array of signed offsets, page-aligned for fast lookup. Page alignment means the high byte of the table address is fixed; only the low byte changes, so the lookup reduces to:

```z80 id:ch10_how_the_bounce_is_encoded_2
    ld   hl, sin_table    ; H = page, L = don't care
    ld   l, a             ; A = (column * freq + phase) & $FF
    ld   a, (hl)          ; 7 T — one memory read, no arithmetic
```

The values in the table are signed: positive offsets push the dot down, negative offsets push it up. The amplitude is baked into the table at generation time. A table with range -24 to +24 gives a bounce of 48 scanlines peak-to-peak. Generating the table is a one-time cost, typically done offline or during initialisation using a lookup or a simple approximation. On the Z80, computing true sine values at runtime is expensive, so demoscene coders either pre-compute tables externally or use quadrant symmetry: calculate one quarter-wave (64 entries), then mirror and negate to fill the remaining three quarters.

Given each dot's (x, y + y_offset), the Spectrum screen address is calculated and stored in the table. The table-building code runs once per frame, outside the inner loop. The inner loop sees only a stream of pre-computed addresses.

### Beyond Simple Sine: Lissajous, Helix, and Multi-Wave Patterns

The beauty of the pre-computed table approach is that the inner loop does not care what shape the motion follows. It consumes addresses at a fixed cost regardless of the trajectory that generated them. This makes it trivial to experiment with different movement patterns -- all the complexity lives in the table-building code.

A **Lissajous pattern** adds a horizontal sine offset as well as the vertical one. Instead of each column mapping to a fixed x byte on screen, the x position also oscillates:

```text
x_offset = sin_table[(column * x_freq + phase_x) & 255]
y_offset = sin_table[(column * y_freq + phase_y) & 255]
```

When `x_freq` and `y_freq` are coprime (say 3 and 2), the dot field traces a Lissajous figure -- the classic oscilloscope pattern. The text becomes a ribbon weaving through space. Different frequency ratios produce dramatically different shapes: 1:1 gives a circle or ellipse, 1:2 gives a figure-eight, 2:3 gives the trefoil pattern familiar from old analogue test equipment.

A **helix** or spiral effect uses a single phase that advances per column, but varies the amplitude:

```text
amplitude = base_amp + sin_table[(column * 2 + time) & 255] * depth_scale
y_offset = sin_table[(column * freq + phase) & 255] * amplitude / max_amp
```

This creates the illusion of dots receding into depth -- the wave flattens at the "far" point of the spiral and expands at the "near" point.

**Multi-wave superposition** is the simplest technique with the most dramatic payoff. Add two sine terms with different frequencies:

```text
y_offset = sin_table[(col * 4 + phase1) & 255] + sin_table[(col * 7 + phase2) & 255]
```

The result is a complex, organic-looking undulation that never quite repeats. Advancing `phase1` and `phase2` at different speeds produces continuously evolving motion from just two table lookups per column. Three or more harmonics create waves that look almost fluid-dynamic. This is the cheapest possible way to generate complex motion -- each additional harmonic costs one table lookup and one addition per column in the table builder, and the inner loop cost remains unchanged.

---

## Частина 2: 4-фазна колірна анімація

### Проблема кольору

Кожна комірка 8x8 має один колір чорнила (0-7) і один колір паперу (0-7). В межах одного кадру ти отримуєш рівно два кольори на комірку. Але Spectrum працює на 50 кадрах за секунду, і людське око не бачить окремих кадрів на такій частоті. Воно бачить середнє.

### Трюк

4-фазна техніка Introspec'а циклічно проходить чотири кадри:

1. **Нормальний A:** чорнило = C1, папір = C2. Піксельні дані = патерн A.
2. **Нормальний B:** чорнило = C3, папір = C4. Піксельні дані = патерн B.
3. **Інвертований A:** чорнило = C2, папір = C1. Піксельні дані = патерн A (ті самі пікселі, поміняні кольори).
4. **Інвертований B:** чорнило = C4, папір = C3. Піксельні дані = патерн B (ті самі пікселі, поміняні кольори).

При 50 Гц кожен кадр відображається 20 мілісекунд. Чотирикадровий цикл завершується за 80 мс — 12,5 циклів на секунду, вище порогу злиття мерехтіння на CRT-дисплеях.

### Математика сприйняття

Простежимо один піксель, що "увімкнений" у патерні A та "вимкнений" у патерні B:

| Кадр | Стан пікселя | Відображений колір |
|-------|-------------|-----------------|
| Нормальний A | увімкнений (чорнило) | C1 |
| Нормальний B | вимкнений (папір) | C4 |
| Інвертований A | увімкнений (чорнило) | C2 |
| Інвертований B | вимкнений (папір) | C3 |

Око сприймає середнє: (C1 + C2 + C3 + C4) / 4.

Тепер перевіримо: піксель, "увімкнений" в обох патернах, бачить C1, C3, C2, C4. Піксель, "вимкнений" в обох, бачить C2, C4, C1, C3. Усі випадки дають однакове середнє. Піксельний патерн не впливає на сприйнятий відтінок — лише вибір C1 по C4 впливає.

Тоді навіщо два патерни? Тому що *проміжні* переходи мають значення. Піксель, що чергується між яскраво-червоним і яскраво-зеленим, помітно мерехтить на 12,5 Гц. Піксель, що чергується між подібними відтінками, ледве мерехтить. Патерни дизерингу — шахматки, напівтонові сітки, впорядковані матриці — контролюють *текстуру* мерехтіння. Introspec обрав патерни так, щоб переходи між кадрами давали мінімальне видиме коливання. Це антиклешовий підбір пікселів: ретельне розташування бітів "увімкнено" та "вимкнено", щоб жоден піксель не перемикався між драматично різними кольорами в послідовних кадрах.

### Чому інвертування суттєве

Без кроку інвертування "увімкнені" пікселі завжди показували б чорнило, а "вимкнені" — завжди папір. Ти отримав би рівно два видимих кольори на комірку, що мерехтять між двома різними парами. Інвертування гарантує, що і чорнило, і папір вносять вклад в обидва стани пікселів протягом циклу, змішуючи всі чотири кольори в сприйнятий вивід.

On the Spectrum, inversion is cheap. The attribute byte layout is `FBPPPIII` -- Flash, Bright, 3 bits of paper colour, 3 bits of ink colour. Swapping ink and paper means rotating the lower 6 bits: paper moves to ink position, ink moves to paper position, while Flash and Bright stay put. In code:

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

The alternative is to pre-compute both normal and inverted attribute buffers at initialisation and simply cycle buffer pointers at runtime. This trades 3,072 bytes of memory for zero per-frame computation -- a worthwhile trade on 128K machines with memory to spare.

### Практична вартість

Four pre-built attribute buffers, cycled once per frame. The per-frame cost is a block copy of 768 bytes into attribute RAM ($5800-$5AFF). Using LDIR, this costs 21 T-states per byte: 768 x 21 = 16,128 T-states. Using the stack trick (POP from the source buffer, switch SP, PUSH to attribute RAM, batching through register pairs and shadow registers), a realistic cost is around 11,000-13,000 T-states depending on batch size and loop overhead -- a modest 1.2-1.5x speedup over LDIR. The gain is smaller than you might expect because each batch requires two SP switches (save source position, load destination, then swap back), and that overhead largely offsets the raw speed advantage of POP+PUSH over LDIR. For a *fill* (writing the same value to every byte), the PUSH trick is far more effective -- load register pairs once, then PUSH repeatedly -- but a copy from varying source data cannot avoid the read cost.

The cycle logic itself is trivial. A single variable holds the phase (0-3). Each frame, increment it and AND with 3 to wrap. Index into a 4-entry table of buffer base addresses:

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

Memory: 4 x 768 = 3,072 bytes for the buffers. On a 48K machine that is a significant chunk; on 128K you can place buffers in paged banks. The pixel patterns (A and B) are written once at initialisation and never touched again -- only the attribute RAM changes each frame.

### Накладення тексту

In Eager, scrolling text overlays the colour animation. There are several approaches, each with different trade-offs.

The simplest is **cell exclusion**: reserve certain character cells for text, skip them during the colour cycle, and write fixed white-on-black attributes with actual font glyphs. This is easy to implement -- just mask those cells out of the LDIR copy -- but creates a hard visual boundary between the animated background and the static text region. The text looks pasted on.

A more sophisticated approach is **pattern integration**: the glyph shapes override specific bits in both pixel patterns A and B. Where the font has a set bit, both patterns get that bit set (or cleared, depending on the desired text colour). This ensures the text pixel shows the same colour in all four phases -- it does not flicker because it never transitions between different colour states. The surrounding pixels continue to cycle normally. The result is text that appears to float on the animated background, with colour bleeding up to the edges of each letterform. The cost is that you must regenerate (or patch) the pixel patterns whenever the text scrolls, which adds a few thousand T-states per frame depending on how many cells contain text.

A third option for 128K machines is **layer compositing**: maintain the 4-phase background in one set of memory pages and the text scroller in another, then combine them during the attribute copy. This keeps the two systems independent -- the scroller does not need to know about the colour animation and vice versa -- at the cost of a slightly more complex copy loop that masks text cells.

---

## Demoscene Lineage

The dotfield scroller did not appear from nowhere. The technique sits in a lineage of ZX Spectrum effects that stretches from the mid-1980s to the present.

The earliest Spectrum scrollers were simple character-cell affairs: LDIR-based horizontal scrolls that shifted an entire line of character cells, one byte at a time. Pixel-smooth scrolling was harder -- the Spectrum has no hardware scroll register, so every pixel shift requires rewriting the bitmap data. By the early 1990s, demo coders had developed several approaches: RL/RR-based pixel scrolling (shifting every byte in a screen line), look-up table scrollers (pre-shifted copies of each character), and the double-buffer technique (draw into a back buffer, copy to screen). All of these were limited by the fundamental cost of moving bytes in and out of video RAM.

The dotfield approach breaks from this tradition entirely. Instead of scrolling a contiguous block of pixels, it decomposes the text into individual dots and places each one independently. This was Dark's insight in the mid-1990s: if you give up the idea of a solid font and accept a pointillist rendering, you can use the POP trick to place each dot with minimal overhead. The visual result -- text dissolving into a cloud of particles, bouncing on a sine wave -- became one of the signature effects of the Russian demoscene.

X-Trade's *Illusion* (ENLiGHT'96) was the demo that made the technique famous in the Spectrum world. The dotfield scroller was its centrepiece effect, running smoothly alongside music and other visual elements. Dark published the algorithmic principles in *Spectrum Expert* issues #01 and #02 (1997-98), where he described the general approach to POP-based rendering and sine-table animation. Two decades later, Introspec's detailed reverse-engineering of the Illusion binary (published in *Hype* magazine, 2017) confirmed Dark's claims and provided the exact cycle counts that the community had long speculated about.

The 4-phase colour technique has a different pedigree. Colour-cycling on the Spectrum has been explored since the 1980s -- simple two-frame alternation (flash-like effects) was common in games and demos. But the systematic four-phase approach, with its careful inversion step to ensure all four colours contribute equally, was refined by Introspec for *Eager* (3BM Open Air 2015). The party version's file_id.diz explicitly mentions the technique, and Introspec's "Making of Eager" article in *Hype* (2015) describes the design process: choosing colours so that adjacent phases minimise visible flicker, and using dithering patterns that distribute the transitions evenly across the cell.

The broader principle -- temporal multiplexing of colour -- appears on other platforms too. The Atari 2600 famously alternates frames to create flickering pseudo-sprites. The Game Boy uses a similar trick for pseudo-transparency. On the Spectrum, the technique is particularly effective because the CRT phosphor persistence smooths the transitions more than an LCD would. This is worth noting for modern viewers: 4-phase colour looks substantially better on a real CRT or a good CRT emulator (with phosphor simulation) than on a raw pixel-perfect display.

---

## Спільний принцип: Часове шахрайство

Скролер з точкового поля використовує 50 кадрів за секунду для *просторової* гнучкості. Кожен кадр — знімок позицій точок в один момент; мозок глядача інтерполює між знімками, сприймаючи плавний рух. Завдання процесора — *розмістити* точки якомога швидше, зчитуючи попередньо обчислені адреси зі стеку.

4-фазна колірна анімація використовує 50 кадрів за секунду для *колірної* гнучкості. Кожен кадр відображає один з чотирьох колірних станів; сітківка глядача усереднює їх. Жоден окремий кадр не містить сприйнятий результат — він існує лише в інерції зору.

Обидві використовують одну й ту саму фізичну реальність: CRT оновлюється на 50 Гц, і зорова система людини не може розрізнити окремі кадри на такій частоті. *Часова* роздільність Spectrum значно багатша за його просторову чи колірну роздільність. Кодери демосцени відкрили, що часова роздільність — найдешевша вісь для експлуатації.

Обидві зводять свої внутрішні цикли до абсолютного мінімуму. Скролер до 36 тактів на точку. Колірна анімація до єдиного копіювання буфера за кадр. Обидві виносять складність із внутрішнього циклу в попередні обчислення. І обидві дають результати, які виглядають для непідготовленого глядача так, ніби залізо не повинно бути на це здатне.

Ось що робить демосцену часовою формою мистецтва. Скріншот скролера з точкового поля показує розсип пікселів. Скріншот 4-фазної колірної анімації показує два кольори на комірку, точно як залізо специфікує. Їх потрібно побачити *у русі*, щоб побачити, як вони працюють. Краса — в послідовності, а не в кадрі.

---

## Практика 1: Скролер підстрибуючого точкового тексту

Побудуй спрощений скролер з точкового поля: коротке текстове повідомлення, відрендерене як підстрибуюче точкове поле з використанням POP-адресації.

**Структури даних.** Вирівняний за сторінкою бітмап-шрифт 8x8 (ROM-шрифт за адресою `$3D00` працює). 256-байтна таблиця синусів для зміщення підстрибування. RAM-буфер для таблиці адрес (до 4 096 x 2 байтів).

**Побудова таблиці.** Перед кожним кадром пройди по видимих символах. Для кожного біта кожного байта шрифту обчисли екранну адресу, що включає синусоїдальне зміщення підстрибування, та збережи її в таблиці адрес. Це виконується один раз за кадр поза внутрішнім циклом.

**Рендеринг.** Вимкни переривання. Збережи SP через самомодифікований код. Вкажи SP на таблицю адрес. Виконай розгорнутий внутрішній цикл: `ld a,(bc) : inc bc`, потім 8 повторень `pop hl : rla : jr nc,skip : set N,(hl)` з N від 7 до 0. Віднови SP. Увімкни переривання.

**Основний цикл.** `halt` (синхронізація з 50 Гц), очисти екран (очищення через PUSH з Розділу 3), побудуй таблицю адрес, відрендери точкове поле, просунь позицію скролу та фазу підстрибування.

**Розширення.** Часткове очищення екрану (відстежуй обмежувальний прямокутник). Подвійна буферизація через тіньовий екран на 128K. Кілька гармонік підстрибування. Змінна щільність точок для розрідженого, більш ефірного вигляду.

---

## Практика 2: 4-фазна циклічна колірна анімація

Побудуй 4-фазну колірну анімацію, що створює плавні градієнти.

**Піксельні патерни.** Заповни бітмап-пам'ять двома комплементарними патернами дизерингу. Найпростіше: парні піксельні рядки отримують `$55` (01010101), непарні рядки — `$AA` (10101010). Для виробничої якості використовуй впорядковану матрицю Баєра 4x4.

**Буфери атрибутів.** Попередньо обчисли чотири 768-байтні буфери. Буфери 0 та 1 містять нормальні атрибути з двома різними колірними схемами (змінне чорнило/папір по екрану для діагонального градієнта). Буфери 2 та 3 — інвертовані версії — біти чорнила та паперу поміняні. Обмін — це бітова ротація: три RRCA для переміщення бітів чорнила на позицію паперу, три RLCA в інший бік, маскування та комбінування.

**Основний цикл.** Кожен кадр: `halt`, індексуй у 4-елементну таблицю вказівників на буфери, використовуючи лічильник фази (AND 3), LDIR 768 байтів у `$5800`, інкрементуй лічильник фази. Це весь runtime-рушій — приблизно 16 000 тактів на кадр.

**Анімація.** Для рухомого градієнта регенеруй один буфер за кадр (той, що стає найстарішим у 4-кадровому циклі) з просуваючим колірним зміщенням. Це підтримує конвеєр: відображай кадр N, генеруючи кадр N+4. Альтернативно, попередньо обчисли всі буфери по банках 128K для нульової вартості виконання.

---

## Підсумок

- **Скролер з точкового поля** рендерить текст як окремі точки. Внутрішній цикл — `pop hl : rla : jr nc,skip : set ?,(hl)` — коштує 36 тактів на непрозорий піксель, 26 на прозорий.
- **Стекова адресація** кодує траєкторію підстрибування як попередньо побудовані екранні адреси. POP отримує їх за 10 тактів кожну — найшвидший довільний доступ на читання на Z80.
- **4-фазний колір** циклічно перемикає 4 атрибутних кадри (2 нормальних + 2 інвертованих) на 50 Гц. Інерція зору усереднює кольори, створюючи ілюзію більш ніж 2 кольорів на комірку.
- Крок **інвертування** гарантує, що всі чотири кольори вносять вклад у кожну піксельну позицію.
- Обидві техніки використовують **часову роздільність** для створення ефектів, неможливих у будь-якому окремому кадрі.
- Скролер використовує стек для просторової гнучкості; колірна анімація використовує чергування кадрів для колірної гнучкості — дві основні осі демосценового обману.

---

## Спробуй сам

1. Побудуй скролер з точкового поля. Почни з одного статичного символу, нанесеного через POP-базований внутрішній цикл. Перевір очікуваний таймінг тестовою обв'язкою з бордюру Розділу 1. Потім додай таблицю підстрибування та спостерігай, як він хвилясто коливається.

2. Експериментуй з параметрами підстрибування. Зміни амплітуду синуса, просторову частоту та швидкість фази. Невеликі зміни дають драматичні візуальні відмінності.

3. Побудуй 4-фазну колірну анімацію. Почни з рівномірного кольору (всі комірки однакові в кожній фазі). Переконайся, що бачиш стабільний колір, який не є ні чорнилом, ні папером жодного окремого кадру. Потім додай діагональний градієнт.

4. Спробуй різні патерни дизерингу. Шахматка, блоки 2x2, матриця Баєра, випадковий шум. Які мінімізують видиме мерехтіння? Які дають найплавніші сприйняті градієнти?

5. Поєднай обидві техніки: 4-фазний колірний фон з монохромним скролером з точкового поля зверху.

---

> **Джерела:** Introspec, "Technical Analysis of Illusion by X-Trade" (Hype, 2017); Introspec, "Making of Eager" (Hype, 2015); Dark, "Programming Algorithms" (Spectrum Expert #01, 1997). Дизасемблювання внутрішнього циклу та підрахунки тактів слідують аналізу Introspec'а 2017 року. 4-фазна колірна техніка описана у статті making-of Eager та file_id.diz партійної версії.
