# Розділ 7: Ротозумер і чанкі-пікселі

> *"Трюк у тому, що ти не обертаєш екран. Ти обертаєш свій прохід по текстурі."*
> -- перефразування ключової ідеї, що стоїть за кожним ротозумером

---

Є момент в Illusion, коли екран заповнюється патерном — текстурою, монохромною, що повторюється — і потім вона починає обертатися. Обертання плавне і безперервне, зум дихає туди-сюди, і все це йде в такому темпі, що забуваєш, що дивишся, як Z80 штовхає пікселі на 3,5 МГц. Це не найтехнічніший ефект у демо. Сфера (Розділ 6) складніша математично. Скролер з точкового поля (Розділ 10) щільніший за тактовим бюджетом. Але ротозумер — це той, що виглядає невимушено, а на Spectrum зробити щось невимушеним — найважчий трюк з усіх.

Цей розділ простежує два потоки. Перший — аналіз Introspec'а 2017 року ротозумера з Illusion від X-Trade. Другий — стаття sq 2022 року на Hype про оптимізацію чанкі-пікселів, яка доводить підхід до 4x4 пікселів і каталогізує сімейство стратегій рендерингу з точними підрахунками тактів. Разом вони відображають простір проектування: як працюють чанкі-пікселі, як їх використовують ротозумери, і які компроміси продуктивності визначають, чи твій ефект біжить з 4 кадрів на екран чи з 12.

---

## Що насправді робить ротозумер

Ротозумер відображає 2D-текстуру, повернуту на деякий кут і масштабовану з деяким коефіцієнтом. Наївний підхід: для кожного екранного пікселя обчислити відповідну текстурну координату через тригонометричне обертання:

```text
    tx = sx * cos(theta) * scale  +  sy * sin(theta) * scale  +  offset_x
    ty = -sx * sin(theta) * scale  +  sy * cos(theta) * scale  +  offset_y
```

При 256x192 це 49 152 пікселі, кожному з яких потрібні два множення. Навіть з множенням через таблицю квадратів на 54 такти (Розділ 4), ти перевищуєш п'ять мільйонів тактів — приблизно 70 кадрів процесорного часу. Ефект математично тривіальний і обчислювально неможливий.

Ключова ідея в тому, що перетворення *лінійне*. Рух на один піксель вправо на екрані завжди додає однакове (dx, dy) до текстурних координат. Рух на один піксель вниз завжди додає однакове (dx', dy'). Попіксельна вартість схлопується з двох множень до двох додавань:

```text
Step right:   dx = cos(theta) * scale,   dy = -sin(theta) * scale
Step down:    dx' = sin(theta) * scale,  dy' = cos(theta) * scale
```

Почни кожен рядок з правильної текстурної координати і крокуй на (dx, dy) для кожного пікселя. Внутрішній цикл стає: зчитай тексель, просунься на (dx, dy), повтори. Два додавання на піксель, жодних множень. Підготовка на кадр — чотири множення для обчислення крокових векторів з поточного кута та масштабу. Все інше випливає з лінійності.

Це фундаментальна оптимізація за кожним ротозумером на будь-якій платформі. На Amiga, на PC, на Spectrum.

### Fixed-Point Stepping on the Z80

On a 16-bit or 32-bit platform, dx and dy would be fixed-point values: the integer part selects the texel, and the fractional part accumulates sub-pixel precision. On the Z80, we lack the registers and the bandwidth for true fixed-point inner loops. The classic Spectrum solution is to collapse the step to integer increments -- always exactly +1, -1, or 0 per axis -- and control the *ratio* of steps between axes to approximate the angle.

Consider a rotation of 30 degrees. The exact step vector would be (cos 30, -sin 30) = (0.866, -0.5). On a machine with fixed-point arithmetic, you would add 0.866 to the column coordinate and subtract 0.5 from the row coordinate per pixel. On the Z80, the inner loop instead alternates between two integer steps: some pixels step (+1 column, 0 rows) and others step (+1 column, -1 row). If you distribute these in a roughly 2:1 ratio -- two column-only steps for every diagonal step -- the average direction approximates the 0.866:0.5 ratio of a 30-degree walk. This is Bresenham's line algorithm applied to texture traversal.

The zoom factor determines how many texels you skip per screen pixel. At scale 1.0, every texel maps to one screen pixel. At scale 2.0, you skip every other texel, effectively zooming in. On the Spectrum, this is controlled by doubling the walk instructions: instead of one `INC L` per pixel, you execute two, stepping by 2 texels and producing a 2x zoom. Intermediate zoom levels again use Bresenham-like distribution: some pixels step by 1, others by 2, with the ratio controlled by an error accumulator.

The per-frame cost of computing these parameters is negligible: four lookups into a sine table, a few multiplications (or table lookups, see Chapter 4), and a Bresenham setup pass. All the heavy work is in the inner loop, which has been reduced to nothing but register increments and memory reads.

---

## Чанкі-пікселі: Обмін роздільності на швидкість

Навіть при двох додаваннях на піксель, записати 6 144 байти в черезрядкову відеопам'ять Spectrum за кадр непрактично — не якщо ти також хочеш оновити кут і залишити час для музики. Чанкі-пікселі вирішують це, зменшуючи ефективну роздільність. Замість одного текселя на екранний піксель, ти відображаєш один тексель на блок 2x2, 4x4 або 8x8.

Illusion використовує чанкі-пікселі 2x2: ефективна роздільність 128x96, зменшення роботи в 4 рази. Ефект виглядає блочним зблизька, але на тій швидкості, з якою текстура пролітає по екрану, рух приховує грубість. Око пробачає низьку роздільність, коли все рухається.

### Why 2x2 Is the Sweet Spot

The choice of chunk size involves a three-way tradeoff: visual quality, rendering speed, and memory. At 2x2, you get 128x96 effective pixels -- enough to read text and recognise patterns in the texture. At 4x4, the 64x48 grid is noticeably coarser; fine details in the texture become unreadable, but the effect still "reads" as a coherent rotating surface. At 8x8, you are down to 32x24 blocks, which is the attribute grid resolution -- any texture detail is lost, and the effect looks like coloured rectangles. The last case can be useful for colour-only effects (attribute tunnels, Chapter 9), but for a pixel-rendered rotozoomer, 2x2 or 4x4 is the practical range.

The memory cost matters too. Each chunky pixel stores one byte, so a 2x2 rotozoomer at 128x96 needs 12,288 texels per frame. With a 256-byte texture row (the natural width for 8-bit wrapping), the texture itself occupies 256 bytes per row times however many rows you need. A 4x4 version only processes 3,072 texels, which means the inner loop runs one-quarter as many iterations -- but the visual cost is significant.

In practice, Spectrum demos land on 2x2 for featured rotozoomer effects and reserve 4x4 for situations where the rotozoomer shares the screen with other effects (bumpmapping overlays, split-screen compositions).

### The $03 Encoding Trick

The encoding is designed for the inner loop. Each chunky pixel is stored as `$03` (on) or `$00` (off). This value is not arbitrary -- it encodes exactly the two low bits set: `%00000011`. Watch what happens as four pixels accumulate in the A register:

```text
After pixel 1:  A = %00000011                  ($03)
After 2x shift: A = %00001100                  ($0C)
After pixel 2:  A = %00001100 + %00000011      ($0F)
After 2x shift: A = %00111100                  ($3C)
After pixel 3:  A = %00111100 + %00000011      ($3F)
After 2x shift: A = %11111100                  ($FC)
After pixel 4:  A = %11111100 + %00000011      ($FF)
```

If all four pixels are "on", the result is `$FF` -- all bits set. If all four are "off" (`$00`), the shifts and additions produce `$00`. Mixed patterns produce the correct 2-bit-per-pixel stripe: for example, on-off-on-off gives `%11001100` = `$CC`. Each pair of bits in the output byte corresponds to one chunky pixel. Since each chunky pixel is 2 screen pixels wide (2x2), the 8-bit output byte covers exactly 8 screen pixels: four chunky columns times two pixels each.

The critical property: because we only ever add `$03` or `$00`, there is no carry between pixel fields. The two-bit groups never overflow into each other. This is what makes the encoding branchless -- no masking needed, no OR operations, just `ADD A,A` and `ADD A,(HL)`.

---

## Внутрішній цикл з Illusion

Дизасемблювання Introspec'а розкриває базову послідовність рендерингу. HL ходить по текстурі; H відстежує одну вісь, а L — іншу:

```z80 id:ch07_the_inner_loop_from_illusion
; Inner loop: combine 4 chunky pixels into one output byte
    ld   a,(hl)        ;  7T  -- read first chunky pixel ($03 or $00)
    inc  l             ;  4T  -- step right in texture
    dec  h             ;  4T  -- step up in texture
    add  a,a           ;  4T  -- shift left
    add  a,a           ;  4T  -- shift left (now shifted by 2)
    add  a,(hl)        ;  7T  -- add second chunky pixel
```

Послідовність повторюється для третього та четвертого пікселів. `inc l` і `dec h` разом трасують діагональний шлях по текстурі — а діагональний означає повернутий. Конкретна комбінація інструкцій інкременту та декременту визначає кут повороту.

| Крок | Інструкції | Такти |
|------|-------------|----------|
| Зчитати піксель 1 | `ld a,(hl)` | 7 |
| Хід | `inc l : dec h` | 8 |
| Зсув + Зчитати піксель 2 | `add a,a : add a,a : add a,(hl)` | 15 |
| Хід | `inc l : dec h` | 8 |
| Зсув + Зчитати піксель 3 | `add a,a : add a,a : add a,(hl)` | 15 |
| Хід | `inc l : dec h` | 8 |
| Зсув + Зчитати піксель 4 | `add a,a : add a,a : add a,(hl)` | 15 |
| Хід | `inc l : dec h` | 8 |
| Вивід + просування | `ld (de),a : inc e` | ~11 |
| **Разом на байт** | | **~95** |

Introspec виміряв приблизно 95 тактів на 4 чанки.

Критичне спостереження: напрямок ходу жорстко зашитий у потоці інструкцій. Інший кут повороту потребує інших інструкцій. Вісім основних напрямків можливі з використанням комбінацій `inc l`, `dec l`, `inc h`, `dec h` та `nop`. Це означає, що код рендерингу змінюється кожен кадр.

### Self-Modifying Code at the Byte Level

"Per-frame code generation" sounds exotic, but the mechanism is mundane. Each walk instruction is a single byte in memory. `INC L` is opcode `$2C`. `DEC L` is `$2D`. `INC H` is `$24`. `DEC H` is `$25`. `NOP` is `$00`. To change the walk direction from "right and up" (`INC L` + `DEC H`) to "pure right" (`INC L` + `NOP`), you write `$00` to the byte where `$25` currently sits. That is the entire code generation step: `LD A,$00 : LD (walk_target),A`. A few stores into the instruction stream, and the inner loop now walks in a different direction.

The targets are known at assembly time. Each SMC site is labelled (e.g., `.smc_walk_h_0:`) and the patching code uses those labels as literal addresses. There is no dynamic memory allocation, no instruction parsing, no runtime disassembly. You are writing known opcodes to known addresses. The Z80 has no instruction cache to invalidate, no pipeline to flush. The write takes effect immediately on the next fetch from that address.

In a fully unrolled inner loop (which Illusion uses for its 16-byte rows), there would be 64 walk-instruction sites to patch: 4 walk pairs per output byte times 16 bytes per row. Patching 64 bytes costs about 64 x 13 = 832 T-states (each `LD (nn),A` is 13 T-states), which is negligible compared to the 100,000+ T-states the rendering pass takes. The code generator is cheap. The generated code is what matters.

---

## Покадрова генерація коду

Код рендерингу генерується наново кожен кадр, з інструкціями напрямку ходу, пропатченими для поточного кута:

| Діапазон кутів | Крок H | Крок L | Напрямок |
|-------------|--------|--------|-----------|
| ~0 градусів | `nop` | `inc l` | Чисто вправо |
| ~45 градусів | `dec h` | `inc l` | Вправо і вгору |
| ~90 градусів | `dec h` | `nop` | Чисто вгору |
| ~135 градусів | `dec h` | `dec l` | Вліво і вгору |
| ~180 градусів | `nop` | `dec l` | Чисто вліво |
| ~225 градусів | `inc h` | `dec l` | Вліво і вниз |
| ~270 градусів | `inc h` | `nop` | Чисто вниз |
| ~315 градусів | `inc h` | `inc l` | Вправо і вниз |

Для проміжних кутів генератор розподіляє кроки нерівномірно, використовуючи накопичення помилки в стилі Брезенхема. Поворот на 30 градусів чергує `inc l : nop` та `inc l : dec h` приблизно у співвідношенні 2:1, наближаючи тангенс 30 градусів (1,73:1). Результуючий код — розгорнутий цикл, де кожна ітерація має свою специфічну пару ходу, налаштовану на поточний кут.

The rendering cost for 128x96 at 2x2 chunky. The 128x96 area is 96 pixel rows, but each 2x2 texel covers two pixel rows, giving 48 texel rows. Each texel row produces 16 output bytes (128 pixels / 8 bits per byte, with 4 chunky pixels packed per byte):

```text
16 output bytes/row x 95 T-states = 1,520 T-states/row
1,520 x 48 texel rows = 72,960 T-states total
```

Roughly 1 frame on a Pentagon (71,680 T-states per frame). But this is the bare inner loop only. A complete accounting adds:

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

On a standard 48K/128K Spectrum at 69,888 T-states per frame, the rendering takes roughly 1.4 frames. Introspec's estimate of 4-6 frames per screen accounts for the more complex code path in Illusion (which handles the full 256x192 screen, not just a 128x96 strip) and the cost of the music engine running in the interrupt. On a Pentagon with its slightly longer frame (71,680 T-states) and no contention, the inner loop runs about 3% faster.

Memory contention on the 48K/128K Spectrum adds another hidden cost. During the top 192 scanlines, the ULA steals cycles from the CPU when accessing the lower 16KB of RAM ($4000-$7FFF). The inner loop reads from the texture (which should be above $8000, out of contended memory) and writes to a buffer (also above $8000), so it avoids contention entirely. The buffer-to-screen transfer, however, writes directly to video RAM and will be slowed by contention if it overlaps with the display period. This is why demos synchronise the screen transfer to the border period or to the bottom of the display.

---

## Перенос буфера на екран

Ротозумер рендерить у позаекранний буфер, потім переносить у відеопам'ять. Черезрядкова розкладка екрану робить прямий рендеринг болючим, а буферизація уникає розривів.

Перенос використовує стек:

```z80 id:ch07_buffer_to_screen_transfer
    pop  hl                   ; 10T -- read 2 bytes from buffer
    ld   (screen_addr),hl     ; 16T -- write 2 bytes to screen
```

Екранні адреси вбудовані як літеральні операнди, попередньо обчислені для черезрядковості Spectrum — ще один приклад генерації коду. При 26 тактах на два байти повний перенос 1 536 байтів коштує менше 20 000 тактів. Прохід рендерингу — вузьке місце, не перенос.

---

## Глибоке занурення: Чанкі-пікселі 4x4 (sq, Hype 2022)

Стаття sq доводить чанкі-пікселі до 4x4 — ефективна роздільність 64x48. Візуальний результат грубіший, але виграш у продуктивності відкриває ефекти на кшталт бамп-мапінгу та черезрядкового рендерингу. Стаття — це дослідження методології оптимізації: почни просто, ітеративно покращуй, вимірюй на кожному кроці.

**Підхід 1: Базовий LD/INC (101 такт на пару).** Завантаж чанкі-значення, запиши в буфер, просунь вказівники. Вузьке місце — керування вказівниками: `INC HL` на 6 тактів накопичується за тисячі ітерацій.

**Підхід 2: Варіант з LDI (104 такти — повільніше!).** `LDI` копіює байт і автоінкрементує обидва вказівники однією інструкцією. Але вона також декрементує BC, споживаючи регістрову пару. Накладні витрати на збереження/відновлення роблять її *повільнішою* за наївний підхід. Повчальна історія: на Z80 "розумна" інструкція — не завжди швидка.

**Підхід 3: LDD подвійний байт (80 тактів на пару).** Розташувавши джерело і призначення у зворотному порядку, автодекремент `LDD` працює на твою користь. Комбінована двобайтна послідовність використовує це для покращення на 21% порівняно з базовою лінією.

**Підхід 4: Самомодифікований код (76-78 тактів на пару).** Попередньо згенеруй 256 процедур рендерингу, по одній на кожне можливе значення байта, кожна з піксельним значенням, впеченим як безпосередній операнд:

```z80 id:ch07_deep_dive_4x4_chunky_pixels
; One of 256 pre-generated procedures
proc_A5:
    ld   (hl),$A5        ; 10T  -- value baked into instruction
    inc  l               ;  4T
    ld   (hl),$A5        ; 10T  -- 4x4 block spans 2 bytes horizontally
    ; ... handle vertical repetition ...
    ret                  ; 10T
```

256 процедур займають приблизно 3 КБ. Попіксельний рендеринг падає до 76-78 тактів — на 23% швидше за базову лінію, на 27% швидше за LDI.

### Порівняння продуктивності

| Підхід | Тактів/пара | Відносно | Пам'ять |
|----------|------------|----------|--------|
| Базовий LD/INC | 101 | 1.00x | Мінімум |
| Варіант з LDI | 104 | 0.97x | Мінімум |
| LDD подвійний байт | 80 | 1.26x | Мінімум |
| Самомодифікований (256 процедур) | 76-78 | 1.30x | ~3 КБ |

Самомодифікований підхід виграє, але перевага над LDD невелика. У демо на 128K 3 КБ легко доступні. У продукції на 48K підхід з LDD може бути кращим інженерним рішенням.

### Historical Roots: Born Dead #05 and the Scene Lineage

sq notes these techniques build on work published in Born Dead #05, a Russian demoscene newspaper from approximately 2001. Born Dead was one of several Russian-language disk magazines that served as technical journals for the ZX Spectrum demoscene. Unlike Western PC demoscene publications that could assume 486-class hardware, the Spectrum magazines operated under the constraints of a community that was still actively developing new techniques for a machine from 1982. The foundational article described basic chunky rendering -- the idea that you could treat the Spectrum's bit-mapped display as a lower-resolution chunky-pixel buffer and gain speed at the expense of resolution.

sq's contribution, twenty-one years later, was the systematic optimisation and the pre-generated procedure variant. But between Born Dead #05 and sq's 2022 article, the chunky rotozoomer appeared in numerous Spectrum demos. X-Trade's Illusion (ENLiGHT'96) was among the earliest full implementations. Other notable examples include Exploder^XTM's GOA4K and Refresh, 4D's productions, and later work from the Russian and Polish scenes. The technique spread partly through disassembly -- Introspec's 2017 analysis of Illusion is itself an example of the scene's tradition of learning by reverse engineering -- and partly through the informal knowledge network of disk magazines, BBS postings, and direct communication between coders.

This is how scene knowledge evolves: a technique surfaces in an obscure disk magazine, circulates within the community, and twenty-one years later someone revisits it with fresh measurements and new tricks. The chain from Born Dead to sq to this chapter is unbroken.

---

## Практика: Побудова простого ротозумера

Ось структура робочого ротозумера з чанкі-пікселями 2x2 та шахматною текстурою.

**Текстура.** 256-байтна таблиця, вирівняна за сторінкою, де кожен байт дорівнює `$03` або `$00`, утворюючи 8-піксельні смуги. Регістр H забезпечує другий вимір; XOR H у пошук створює повну шахматку:

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

**Таблиця синусів і покадрова підготовка.** 256-елементна таблиця синусів, вирівняна за сторінкою, керує обертанням. Кожен кадр зчитує `sin(frame_counter)` і `cos(frame_counter)` (косинус через зсув індексу на 64) для обчислення крокових векторів, потім патчить інструкції ходу внутрішнього циклу правильними опкодами.

**Цикл рендерингу.** Зовнішній цикл задає початкову текстурну координату для кожного рядка (крокуючи перпендикулярно до напрямку ходу). Внутрішній цикл ходить по текстурі:

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

Інструкції `inc l` — це цілі генератора коду. Перед кожним кадром вони патчаться відповідною комбінацією `inc l`/`dec l`/`inc h`/`dec h`/`nop` на основі поточного кута. Для некардинальних кутів акумулятор помилки Брезенхема розподіляє кроки по мінорній осі по всьому рядку, тому кожна інструкція ходу в розгорнутому циклі може відрізнятися від своїх сусідів.

![Rotozoomer output — the texture rotates and scales in real-time, rendered with 2x2 chunky pixels](../../build/screenshots/ch07_rotozoomer.png)

**Основний цикл.** `HALT` для vsync, обчисли крокові вектори, згенеруй код ходу, відрендери в буфер, стекове копіювання буфера на екран, інкрементуй лічильник кадрів, повтори.

---

## Texture Design and Boundary Handling

The texture is the most constrained data structure in the rotozoomer. Every design decision in the inner loop -- the page alignment, the wrapping behaviour, the power-of-two sizing -- traces back to how the texture is laid out in memory.

### Why Page-Aligned, Why 256 Columns

The texture is page-aligned so that H selects the row and L selects the column. This is not merely convenient; it makes the inner loop possible. `INC L` and `DEC L` wrap at the 256-byte page boundary automatically -- when L overflows from `$FF` to `$00`, H is unchanged. The texture wraps horizontally for free, with zero branch overhead. If the texture were not page-aligned, L increments would carry into H, corrupting the row address. You would need explicit masking (`AND $3F` after every step), which would add 4-8 T-states per pixel and destroy the tight inner loop.

The vertical axis (H) also wraps, but over the full range of rows allocated to the texture. If you allocate 64 rows (pages), H ranges from the texture base page to base+63. `INC H` and `DEC H` will happily walk past the end of the texture into whatever memory follows. Illusion handles this by masking H to the texture height at the start of each row (not per pixel -- per-pixel masking would be too expensive). This works because within a single 16-byte row, the H coordinate changes by at most 16 steps, and if the texture is tall enough relative to the row width, an overflow within a row cannot reach memory that produces visual garbage. A 64-row texture with 16 H-steps per row has a comfortable margin.

### Choosing Texture Size

The texture must be a power-of-two in width (always 256, since L is 8 bits) and ideally a power-of-two in height for easy masking. Common choices:

- **256x256** (64KB): fills all of upper RAM on a 128K Spectrum. Maximum resolution, but leaves no room for code or buffers.
- **256x64** (16KB): the practical choice. Fits in one 16KB bank on 128K hardware. The 6-bit height mask (`AND $3F`) is fast and tiles seamlessly.
- **256x32** (8KB): fits on a 48K Spectrum with room for everything else. The texture repeats more visibly, but for a checkerboard or stripe pattern, repetition *is* the design.
- **256x16** (4KB): minimal. Works for very simple patterns like single-axis stripes.

For non-repeating textures (images, logos), the height should be at least as large as the effective screen height divided by the scale factor. A 2x2 rotozoomer with 96 effective rows needs at least 96 texture rows to avoid visible tiling when the zoom is at 1:1. At higher zoom levels, fewer rows are needed because the camera is "closer" to the texture surface.

### What About Screen Boundaries?

The Spectrum's 256x192 screen is 32 bytes wide by 192 lines. If your rotozoomer fills a 128x96 strip in the centre, you never approach the edge of video memory. But a full-screen rotozoomer at 256x192 (or even 128x192 with 2x2 chunky) must handle the case where the output address reaches the attribute area at `$5800`. The simplest approach: render into a buffer and only copy the portion that fits. A more aggressive approach: clip the row count to the visible area during code generation, which avoids wasted computation but adds complexity to the row loop.

In practice, most Spectrum rotozoomers render a strip smaller than the full screen. The visual framing -- a border, a title bar, a music credit -- hides the cropping and buys back T-states for other effects.

---

## Простір проектування

Розмір чанкі-пікселя — найважливіше проектне рішення в ротозумері:

| Parameter | 2x2 (Illusion) | 4x4 (sq) | 8x8 (attributes) |
|-----------|----------------|----------|-------------------|
| Resolution | 128x96 | 64x48 | 32x24 |
| Texels/frame | 12,288 | 3,072 | 768 |
| Inner loop cost | ~73,000 T | ~29,000 T | ~7,300 T |
| Frames/screen | ~1.3 | ~0.5 | ~0.1 |
| Visual quality | Good motion | Chunky but fast | Very blocky |
| Use case | Featured effects | Bumpmapping, overlays | Attribute-only FX |

The 4x4 version fits within a single frame with room for a music engine and other effects. The 2x2 version takes roughly 1.3-1.5 frames (including overhead) but looks substantially better. The 8x8 case is the attribute tunnel from Chapter 9.

Коли у тебе є швидкий чанкі-рендерер, ротозумер — лише одне застосування. Той самий рушій керує **бамп-мапінгом** (зчитуй різниці висот замість сирих текселів, виводь тінювання), **черезрядковими ефектами** (рендери непарні/парні рядки на чергових кадрах, подвоюючи ефективну частоту кадрів ціною мерехтіння) та **спотворенням текстури** (варіюй напрямок ходу по рядках для хвильових або пульсуючих ефектів). Ротозумер 4x4 може ділити кадр зі скролтекстом, музичним рушієм та переносом екрану. Робота sq була мотивована саме цією універсальністю.

---

## Three Approaches to Texture Rotation

Everything above treats the rotozoomer as one technique with a tuneable chunk size. But "rotozoomer" on the Spectrum is really a family of three distinct approaches, each with different inner loops, different visual character, and different performance profiles. They share the same mathematical foundation -- the linear step vectors, the Bresenham-style angle distribution -- but diverge completely at the rendering level.

### Variant 1: Monochrome Bitmap (Full Pixel Resolution)

The purest form: every screen pixel maps to one texel. The texture is monochrome -- one bit per pixel -- so reading a texel means testing a single bit, and writing to the screen means setting or clearing a single bit. No chunky encoding, no block grouping. The result is a rotated texture at the full 256x192 resolution of the Spectrum display.

The inner loop skeleton looks something like this:

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

Note that SET and RES only work with (HL), (IX+d), or (IY+d) -- not (DE) or (BC). This forces HL to serve as the screen pointer, while DE handles the texture coordinates.

The per-pixel cost is brutal: 35-45 T-states minimum, with branching on every pixel. Across 49,152 pixels, that is 1.5 to 2 million T-states for the rendering pass alone -- roughly 21-28 frames on a standard Spectrum. A full-screen monochrome rotozoomer at 50fps is not happening.

But nobody said you need to fill the whole screen. The technique shines when applied to a smaller region -- a 128x64 strip, a circular viewport, a masked area -- or when you accept a lower frame rate in exchange for the visual impact of full-resolution rotation. It also works beautifully for distortion effects where the "rotation" is not uniform: varying the step vectors per scanline produces wave distortions, barrel effects, and the "sonic ripple" look seen in parts of Illusion by Dark/X-Trade. The coordinate mapping is no longer a simple rotation but a per-line warp through the texture. The maths is the same -- fixed-point stepping along a direction -- but the direction itself changes every row.

The visual payoff is striking. Where a 2x2 chunky rotozoomer looks like a rotating mosaic, the monochrome bitmap version looks like a rotating *image*. On a machine where every effect fights the same 69,888 T-state budget, dedicating multiple frames to full-resolution rendering is a deliberate aesthetic choice.

### Variant 2: Chunky Rotozoomer (2x2 or 4x4 Blocks)

This is the technique covered in the bulk of this chapter. Each screen block (2x2 or 4x4 pixels) maps to one texel. The `$03`/`$00` encoding, the `add a,a : add a,(hl)` accumulation, the walk-instruction patching -- all of it targets this approach.

At 2x2 (128x96 effective resolution), the inner loop runs at approximately 95 T-states per output byte, producing the smooth, recognisable rotozoomer seen in Illusion. At 4x4 (64x48), sq's pre-generated procedure variant eliminates the loop overhead entirely, bringing the cost down to 76-78 T-states per output pair and leaving room for multi-effect compositions within a single frame.

The chunky rotozoomer occupies the middle ground: fast enough for real-time, detailed enough to carry a featured effect. It is the workhorse of the Spectrum rotozoomer repertoire.

### Variant 3: Attribute Rotozoomer (8x8 Block "Pixels")

The Spectrum's attribute area at `$5800`-`$5AFF` stores colour information for each 8x8 pixel character cell: 32 columns by 24 rows, 768 bytes total. Each byte encodes INK, PAPER, BRIGHT, and FLASH for a single 8x8 block. The attribute rotozoomer ignores the bitmap entirely and treats these 768 attribute cells as the display surface. Each cell becomes one "pixel" in a 32x24 image.

The inner loop is structurally identical to the chunky version -- step through texture coordinates, read a value, write it to the output -- but the output is the attribute area, and the "texel" value is a colour attribute byte rather than a bit pattern. The effective resolution is just 32x24, which means the entire rendering pass is 768 iterations of the stepping loop.

The maths:

```text
32 columns x 24 rows = 768 attribute cells
~10 T-states per cell (read texel + write attribute + step)
768 x 10 = ~7,680 T-states total
```

That is roughly 11% of a single frame. You could run the attribute rotozoomer nine times over and still have room for a music engine. The cost is so low that the effect is essentially free.

But the visual payoff is different from the bitmap variants. You are not rotating pixels -- you are rotating coloured blocks. At 32x24, fine detail is invisible. What you get instead is a sweeping field of colour, a vivid mosaic that turns and breathes. The attribute rotozoomer in Illusion uses exactly this: a boldly coloured texture (not a monochrome bitmap) mapped through the attribute grid, producing the characteristic "stained glass" look of rotating colour fields that Illusion is known for. The PAPER and INK fields in each attribute byte give you two colours per cell, so a carefully designed texture can pack more visual information than the raw resolution suggests.

The attribute rotozoomer is perfect for backgrounds, transitions, or as a base layer with pixel-level effects composited on top. Because it only writes to the attribute area, the bitmap can be used simultaneously for a different effect -- a scroller, a logo, a particle field -- running at its own pace. This layered approach is a hallmark of multi-effect demo screens on the Spectrum.

### Comparison

| Variant | Effective resolution | Bytes written/frame | ~T-states (render) | Colour | Typical use |
|---------|---------------------|--------------------|--------------------|--------|-------------|
| Monochrome bitmap | 256x192 (or subregion) | 6,144 (full screen) | 1,500,000-2,000,000 | 1-bit | Hero effect, distortion, warp |
| Chunky 2x2 | 128x96 | 1,536 | ~73,000 | 1-bit | Featured rotozoomer |
| Chunky 4x4 | 64x48 | 384 | ~29,000 | 1-bit | Multi-effect, overlay |
| Attribute | 32x24 | 768 | ~7,700 | INK+PAPER (2 colours/cell) | Background, colour wash, transition |

The progression from top to bottom is a smooth trade: resolution for speed, detail for headroom. The monochrome bitmap gives you everything the Spectrum's display can show, at a cost that demands dedication. The attribute version gives you almost nothing in resolution, but it runs so fast that the rotozoomer becomes just another instrument in a multi-effect composition rather than the main event.

All four rows in this table share the same core algorithm. The step vectors are computed the same way. The Bresenham distribution works the same way. The difference is only where you write and how many iterations you run. Once you have built one rotozoomer, you have built all of them.

---

## Ротозумер у контексті

Ротозумер — це не алгоритм обертання. Це *патерн обходу пам'яті*. Ти йдеш по буферу прямою лінією, і напрямок ходу визначає, що ти бачиш. Обертання — це один вибір напрямку. Зум — це вибір розміру кроку. Z80 не знає тригонометрію. Він знає `INC L` і `DEC H`. Все інше — інтерпретація програміста.

В Illusion ротозумер сусідить зі сферою та скролером з точкового поля. Усі три ділять одну архітектуру: попередньо обчислені параметри, згенеровані внутрішні цикли, послідовний доступ до пам'яті. Сфера використовує таблиці пропуску та змінну кількість `INC L`. Ротозумер використовує пропатчені за напрямком інструкції ходу. Точкове поле використовує стекові таблиці адрес. Три ефекти, одна філософія рушія.

Dark побудував їх усі. Introspec відстежив їх усі. Патерн, що їх з'єднує, — це урок Частини II: обчисли те, що потрібно, до початку внутрішнього циклу, згенеруй код, що не робить нічого, крім зчитати-зсунути-записати, і тримай доступ до пам'яті послідовним.

---

## Підсумок

- Ротозумер відображає повернуту та масштабовану текстуру, ходячи по ній під кутом. Лінійність зменшує попіксельну вартість з двох множень до двох додавань.
- Чанкі-пікселі (2x2, 4x4) зменшують ефективну роздільність і вартість рендерингу пропорційно. Illusion використовує 2x2 при 128x96; система sq використовує 4x4 при 64x48.
- Внутрішній цикл Illusion: `ld a,(hl) : add a,a : add a,a : add a,(hl)` з інструкціями ходу між зчитуваннями. Вартість: ~95 тактів на байт для 4 чанкі-пікселів.
- Напрямок ходу змінюється кожен кадр, вимагаючи генерації коду — цикл рендерингу патчиться перед кожним кадром.
- Шлях оптимізації sq для 4x4: базовий LD/INC (101 такт) до LDI (104 такти, повільніше) до LDD (80 тактів) до самомодифікованого коду з 256 попередньо згенерованими процедурами (76-78 тактів, ~3 КБ). Базується на ранній роботі в Born Dead #05 (~2001).
- Перенос буфера на екран через `pop hl : ld (nn),hl` при ~26 тактах на два байти.
- Ротозумер ділить свою архітектуру зі сферою (Розділ 6) та точковим полем (Розділ 10): попередньо обчислені параметри, згенеровані внутрішні цикли, послідовний доступ до пам'яті.

---

> **Джерела:** Introspec, "Technical Analysis of Illusion by X-Trade" (Hype, 2017); sq, "Chunky Effects on ZX Spectrum" (Hype, 2022); Born Dead #05 (~2001, оригінальні техніки чанкі-пікселів).
