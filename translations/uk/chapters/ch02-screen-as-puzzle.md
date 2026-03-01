# Розділ 2: Екран як головоломка

> "Чому рядки йдуть саме в такому порядку?"
> -- Кожен програміст ZX Spectrum, рано чи пізно

Відкрий будь-який емулятор, набери `PEEK 16384`, і ти зчитаєш перший байт екрану Spectrum. Але який це байт? Не верхній лівий кут екрану в простому розумінні. Піксель з координатами (0,0) справді там — але піксель (0,1), наступний рядок униз, живе на 256 байтів далі. Піксель (0,8), верхній рядок другої символьної клітинки, розташований лише за 32 байти від початку. А піксель (0,64) — перший рядок середньої третини екрану — живе рівно за 2 048 байтів від початку, за адресою `$4800`.

Це найвідоміша головоломка Spectrum. Розкладка екранної пам'яті не послідовна, не інтуїтивна і не випадкова. Це наслідок апаратних рішень, ухвалених у 1982 році, і вона формує кожен фрагмент коду, що торкається дисплея. Розуміння цієї розкладки — та вивчення трюків, що дозволяють швидко по ній переміщатися — є фундаментом для всього, що слідує в цій книзі.

---

## Карта пам'яті: 6 912 байтів екрану

Дисплей Spectrum займає фіксовану область пам'яті:

```text
$4000 - $57FF    Pixel data      6,144 bytes   (256 x 192 pixels, 1 bit per pixel)
$5800 - $5AFF    Attributes        768 bytes   (32 x 24 colour cells)
```

Піксельна область містить бітову карту: 256 пікселів по горизонталі, упаковані по 8 на байт, що дає 32 байти на рядок. З 192 рядками маємо 32 x 192 = 6 144 байти. Кожен байт представляє 8 горизонтальних пікселів, де біт 7 — крайній лівий, а біт 0 — крайній правий.

Область атрибутів містить інформацію про кольори: один байт на кожну символьну клітинку 8x8. Є 32 стовпці та 24 рядки, що дає 32 x 24 = 768 байтів.

Разом: 6 144 + 768 = 6 912 байтів. Це весь дисплей.

<!-- figure: ch02_screen_layout -->
![ZX Spectrum screen memory layout with thirds, character cells, and attribute area](illustrations/output/ch02_screen_layout.png)

Піксельні дані та дані атрибутів виконують різні функції, але тісно пов'язані. Кожен піксельний байт контролює 8 точок на екрані; байт атрибутів для відповідної клітинки 8x8 контролює, якого кольору ці точки будуть. Зміни піксель — і ти змінюєш форму. Зміни атрибут — і ти змінюєш колір. Але змінити колір можна лише для цілого блоку 8x8 — не для окремого пікселя. Це і є "конфлікт атрибутів", що визначає візуальний характер Spectrum, і ми повернемося до нього незабаром.

Спочатку — головоломка: чому піксельні рядки перемішані?

---

## Черезрядковість: Де живуть рядки

Якби Spectrum зберігав піксельні рядки послідовно, рядок 0 був би за адресою `$4000`, рядок 1 — за `$4020`, рядок 2 — за `$4040`, і так далі. Кожен рядок — 32 байти, тому рядок N просто знаходився б за адресою `$4000 + N * 32`. Просто, швидко, розумно.

Але так не відбувається.

Екран поділений на три **третини**, кожна по 64 піксельних рядки заввишки. Усередині кожної третини рядки переплетені за символьними рядками. Ось де фактично розташовані перші 16 рядків:

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

Подивись на закономірність. Перші 8 рядків — це 8 рядків розгортки символьного рядка 0, але вони розташовані через 256 байтів, а не через 32. У межах цих 8 рядків старший байт адреси зростає на 1 кожного разу: `$40`, `$41`, `$42`, ... `$47`. Потім рядок 8 стрибає до `$4020` — назад до старшого байта `$40`, але з молодшим байтом, зміщеним на 32.

Ось повна картина для верхньої третини екрану:

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

Середня третина починається з `$4800` і слідує тому самому патерну. Нижня третина починається з `$5000`.

### Чому?

Причина — ULA — Uncommitted Logic Array, що генерує відеосигнал. ULA зчитує один байт піксельних даних та один байт даних атрибутів для кожної 8-піксельної символьної клітинки, яку малює. Їй потрібні обидва байти в конкретні моменти, поки вона растеризує екран зліва направо.

Черезрядкова розкладка означала, що логіку адресного лічильника ULA можна було побудувати з меншою кількістю вентилів. Коли ULA сканує зліва направо по символьному рядку, вона інкрементує молодші 5 біт адреси (стовпець). Коли досягає правого краю, вона інкрементує старший байт, щоб перейти до наступного рядка розгортки в тому ж символьному рядку. Коли завершує всі 8 рядків розгортки, вона скидає старший байт і просуває біти рядка в молодшому байті.

Це елегантно з апаратної перспективи. Генерація адрес ULA — це проста комбінація лічильників — жодного множення, жодної складної адресної арифметики. Розводка плати була простішою, кількість вентилів меншою, а мікросхема дешевшою у виробництві.

Програміст платить ціну.

---

## Бітова розкладка: Декодування (x, y) в адресу

![ZX Spectrum screen memory layout — interleaved thirds with colour-coded address bit mapping](../../build/screenshots/proto_ch02_screen_layout.png)

Щоб точно зрозуміти черезрядковість, подивись, як координата Y відображається у 16-бітну екранну адресу. Розглянемо піксель у стовпці `x` (0–255) та рядку `y` (0–191). Байт, що містить цей піксель, знаходиться за адресою:

```text
High byte:  0 1 0 T T S S S
Low byte:   L L L C C C C C
```

Де:
- `TT` = яка третина екрану (0, 1 або 2). Біти 7–6 координати y.
- `SSS` = рядок розгортки в межах символьної клітинки (0–7). Біти 2–0 координати y.
- `LLL` = символьний рядок у межах третини (0–7). Біти 5–3 координати y.
- `CCCCC` = стовпець у байтах (0–31). Це x / 8, або еквівалентно біти 7–3 координати x.

Ключовий момент: біти y розташовані не по порядку. Біти 7-6 йдуть в одне місце, біти 5-3 — в інше, а біти 2-0 — ще в інше. Координата y розрізається й розподіляється по адресі.

Візуалізуймо це на конкретному прикладі. Піксель (80, 100):

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

Біт у межах цього байта визначається молодшими 3 бітами x. Біт 7 — крайній лівий піксель, тому позиція пікселя (x AND 7) відображається на біт 7 - (x AND 7).

### Обчислення адреси на Z80

Перетворення (x, y) в екранну адресу — це те, що потрібно робити швидко й часто. Ось стандартна процедура:

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

91 такт — це не дешево. У щільному внутрішньому циклі, що обробляє тисячі пікселів, ти б не викликав цю процедуру для кожного пікселя. Натомість ти обчислюєш початкову адресу один раз, а потім переміщуєшся по екрану за допомогою швидкої маніпуляції вказівниками — що підводить нас до найважливішої процедури в графічному програмуванні Spectrum.

![Pixel plotting demo — individual pixels placed on screen using the address calculation routine](../../build/screenshots/ch02_pixel_demo.png)

---

## DOWN_HL: Переміщення на один піксельний рядок униз

Ти маєш вказівник у HL на якийсь байт на екрані. Ти хочеш перемістити його на один піксельний рядок униз — до байта в тому ж стовпці, на один рядок розгортки нижче. Наскільки це може бути складно?

На лінійному фреймбуфері ти додаєш 32 (кількість байтів на рядок). Одна команда `ADD HL, DE` з DE = 32: 11 тактів, готово.

На Spectrum це головоломка в головоломці. Переміщення на один піксельний рядок униз означає:

1. **У межах символьної клітинки** (рядки розгортки 0–6 до 1–7): інкрементуй H. Біти рядка розгортки знаходяться в молодших 3 бітах H, тому `INC H` переміщує тебе на один рядок униз.

2. **Перетин межі символьної клітинки** (рядок 7 до рядка 0 наступного рядка): скинь біти рядка розгортки H назад до 0 і додай 32 до L, щоб перейти до наступного символьного рядка.

3. **Перетин межі третини** (низ символьного рядка 7 однієї третини до верху символьного рядка 0 наступної): скинь L назад і додай 8 до H, щоб перейти до наступної третини. Еквівалентно, додай `$0800` до адреси.

Класична процедура обробляє всі три випадки:

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

Ця процедура займає різну кількість часу залежно від того, який випадок спрацьовує:

| Case | Frequency | T-states |
|------|-----------|----------|
| Within a character cell | 7 out of 8 rows | 4 + 4 + 7 + 11 = **26** |
| Character boundary, same third | 7 out of 64 rows | 4 + 4 + 7 + 5 + 4 + 7 + 4 + 5 + 4 + 7 + 4 + 10 = **65** |
| Third boundary | 2 out of 192 rows | 4 + 4 + 7 + 5 + 4 + 7 + 4 + 11 = **46** |

The common case -- staying within a character cell -- is fast: 26 T-states (a conditional RET that fires costs 11T, not 5T). The uncommon case (crossing a character row boundary within the same third) is 65 T-states. Averaged over all 192 rows, the cost works out to about **30.5 T-states per call**.

That average hides a problem. If you are iterating down the full screen and calling DOWN_HL on every row, those occasional 65-T-state calls spike your per-line timing unpredictably. For a demo effect that needs consistent timing per scanline, this jitter is unacceptable.

### Оптимізація Introspec'а

У грудні 2020 року Introspec (spke) опублікував на Hype детальний аналіз під назвою "Eshchyo raz pro DOWN_HL" (Ще раз про DOWN_HL). Стаття досліджувала проблему ефективної ітерації по всьому екрану вниз — не лише вартість одного виклику, а загальну вартість переміщення HL через усі 192 рядки.

The naive approach -- calling the classic DOWN_HL routine 191 times -- costs **5,825 T-states** for a full screen traversal. Introspec's goal was to find the fastest way to iterate through all 192 rows, visiting every screen address in top-to-bottom order.

Його ключове прозріння полягало у використанні **роздільних лічильників**. Замість перевірки бітів адреси після кожного інкремента для виявлення перетину меж, він структурував цикл відповідно до триступеневої ієрархії екрану:

```text id:ch02_introspec_s_optimisation
For each third (3 iterations):
    For each character row within the third (8 iterations):
        For each scan line within the character cell (8 iterations):
            process this row
            INC H                  ; next scan line
        undo 8 INC H's, ADD 32 to L   ; next character row
    undo 8 ADD 32's, advance to next third
```

Найвнутрішня операція — це просто `INC H` — 4 такти. Жодних перевірок, жодних розгалужень. Переходи символьних рядків і третин відбуваються у фіксованих, передбачуваних точках циклу, тому у внутрішньому циклі взагалі немає умовної логіки.

Результат: **2 343 такти** для повного обходу екрану. Це покращення на 60% порівняно з класичним підходом, і вартість кожного рядка абсолютно передбачувана — жодного тремтіння.

Існувала також елегантна варіація, що приписується RST7, з використанням підходу двох лічильників, де зовнішній цикл підтримує пару лічильників, що природно відстежують межі символьних рядків і третин. Тіло внутрішнього циклу зводиться до одного `INC H`, а обробка меж інтегрована в маніпуляцію лічильниками на рівні зовнішнього циклу.

Практичний урок: коли тобі потрібно ітерувати через екран Spectrum по порядку, не викликай загальну процедуру DOWN_HL 191 раз. Переструктуруй свій цикл відповідно до природної ієрархії екрану, і розгалуження зникнуть.

Ось спрощена версія підходу з роздільними лічильниками:

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

Директива `REPT 7` (підтримувана sjasmplus) повторює блок 7 разів під час асемблювання — часткове розгортання. Усередині цього блоку переміщення на один рядок розгортки вниз — це одна команда `INC H`. Жодних перевірок, жодних розгалужень. Просування символьного рядка та просування третини відбувається на фіксованих межах зовнішнього циклу.

---

## Пам'ять атрибутів: 768 байтів, що змінили все

Нижче за піксельні дані, за адресами `$5800`–`$5AFF`, знаходиться пам'ять атрибутів. Це 768 байтів — по одному на кожну символьну клітинку 8x8 на екрані, розташовані послідовно зліва направо, зверху вниз. На відміну від піксельної області, розкладка атрибутів повністю лінійна: клітинка (стовпець, рядок) знаходиться за адресою `$5800 + рядок * 32 + стовпець`.

Кожен байт атрибутів має таку структуру:

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

3-бітні коди кольорів відповідають:

```text
  0 = Black       4 = Green
  1 = Blue        5 = Cyan
  2 = Red         6 = Yellow
  3 = Magenta     7 = White
```

З бітом BRIGHT кожен колір має нормальний і яскравий варіант. Чорний залишається чорним незалежно від яскравості, тому загальна палітра — 15 окремих кольорів:

```text
Normal:  Black  Blue  Red  Magenta  Green  Cyan  Yellow  White
Bright:  Black  Blue  Red  Magenta  Green  Cyan  Yellow  White
                (brighter versions of each)
```

<!-- figure: ch02_attr_byte -->
![Attribute byte bit layout showing flash, bright, paper, and ink fields](illustrations/output/ch02_attr_byte.png)

An attribute byte of `$47` = `01000111`: flash off (bit 7 = 0), bright **on** (bit 6 = 1), paper = 000 (black), ink = 111 (white). Bright white text on a black background. The non-bright version is `$07` = `00000111` -- the Spectrum's default after `BORDER 0: PAPER 0: INK 7`.

Такі бітові деталі мають значення, коли ти конструюєш значення атрибутів на швидкості. Поширений патерн:

```z80 id:ch02_attribute_memory_768_bytes_4
; Build an attribute byte: bright white ink on blue paper
; Bright = 1, Paper = 001 (blue), Ink = 111 (white)
; = 01 001 111 = $4F
    ld   a, $4F
```

### Конфлікт атрибутів

Ось визначальне обмеження ZX Spectrum: у межах кожної 8-піксельної клітинки ти можеш мати лише **два кольори** — ink і paper. Кожен встановлений піксель (1) відображається кольором ink. Кожен скинутий піксель (0) відображається кольором paper. Ти не можеш мати три кольори, градієнти чи попіксельне забарвлення в одній клітинці.

Це означає, що якщо червоний спрайт перетинається із зеленим фоном, клітинка 8x8, що містить перетин, мусить вибрати: всі встановлені пікселі в цій клітинці або червоні, або зелені. Ти не можеш мати частину червоних і частину зелених встановлених пікселів у тій самій клітинці. Візуальний результат — різкий блок кольору, що "конфліктує" з оточенням — сумнозвісний конфлікт атрибутів.

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

Багато ранніх ігор для Spectrum просто уникали проблеми: монохромна графіка або символи, ретельно спроєктовані для вирівнювання з сіткою 8x8. Ігри на кшталт Knight Lore та Head Over Heels використовували одну пару ink/paper для всієї ігрової зони, повністю усуваючи конфлікт ціною кольору.

Але демосцена бачила це інакше. Конфлікт атрибутів — це не лише обмеження, а **творче обмеження**. Сітка 8x8 нав'язує особливу естетику: сміливі блоки кольору, чіткі геометричні візерунки, свідоме використання контрасту. Демо-ефекти, що працюють повністю в просторі атрибутів — тунелі, плазми, скролери — можуть оновлювати 768 байтів за кадр замість 6 144, звільняючи величезну кількість тактів для обчислень. Коли весь дисплей побудований на атрибутах, конфлікт стає несуттєвим, бо ти не змішуєш спрайти з фоном — атрибути *і є* графікою.

Демо Introspec'а Eager (2015) побудувало свою візуальну мову повністю навколо цього прозріння. Ефект тунелю, хаос-зумер і кольорова циклічна анімація — усі працюють з атрибутами, а не з пікселями. Результат — ефект, що працює на повній частоті кадрів із запасом для цифрових барабанів та складного скриптового рушія. Конфлікт не є проблемою, бо обмеження було прийняте від самого початку.

---

## Бордюр: Більше ніж декорація

Піксельна область 256x192 розташована в центрі екрану, оточена широким бордюром. Колір бордюру встановлюється записом у порт `$FE`:

```z80 id:ch02_the_border_more_than
    ld   a, 1          ; 7T   blue = colour 1
    out  ($FE), a       ; 11T  set border colour
```

Лише біти 0–2 записаного в `$FE` байта впливають на колір бордюру. Є 8 кольорів (0–7), без яскравих варіантів — палітра бордюру використовує набір нормальної яскравості. Біти 3 і 4 порту `$FE` контролюють виходи MIC та EAR (інтерфейс магнітофона та звук біпера), тому ти маєш відповідно маскувати або встановлювати ці біти, якщо не збираєшся видавати звук.

Зміна кольору бордюру набуває чинності негайно — на наступному ж рядку розгортки. Ось що робить бордюр таким корисним як інструмент зневадження. Як ми бачили в розділі 1, зміна кольору бордюру до і після секції коду створює видиму смугу, висота якої розкриває вартість коду в тактах. Бордюр — це твій осцилограф.

### Ефекти бордюру

Оскільки зміни кольору бордюру видимі на наступному рядку розгортки, точно розраховані інструкції `OUT` можуть створювати багатокольорові смуги, растрові бари і навіть грубу графіку в бордюрній зоні.

Базовий принцип: ULA малює один рядок розгортки кожні 224 такти (на Pentagon). Якщо ти виконаєш інструкцію `OUT ($FE), A` в потрібний момент, ти зміниш колір бордюру у конкретній горизонтальній позиції на поточному рядку розгортки. Виконуючи швидку послідовність інструкцій `OUT` з різними значеннями кольору, можна малювати горизонтальні смуги кольору на бордюрі.

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

Складніші бордюрні ефекти можуть створювати градієнтні смуги, текст, що прокручується, або навіть зображення з низькою роздільністю. Складність екстремальна: ти маєш 224 такти на рядок розгортки, і кожна зміна кольору коштує мінімум 18 тактів (7 для `LD A,n` + 11 для `OUT`). Це дає тобі приблизно 12 змін кольору на рядок, що означає максимум 12 горизонтальних кольорових смуг на лінію.

Кодери демо довели це до вражаючих крайнощів. Завантажуючи значення кольорів у кілька регістрів заздалегідь і використовуючи швидші послідовності типу `OUT (C), A` з подальшим обміном регістрів, вони вичавлюють більше змін кольору на рядок. Бордюр стає самостійним дисплеєм — полотном за межами полотна.

Для наших цілей найважливіша роль бордюру — та сама, що й у розділі 1: безкоштовний, завжди доступний візуалізатор таймінгу. Коли ти оптимізуватимеш процедуру заповнення екрану далі в цьому розділі, бордюр — це те, як ти побачиш свій прогрес.

---

## Практика: Шахова заливка

Приклад у `chapters/ch02-screen-as-puzzle/examples/fill_screen.a80` заповнює піксельну область шаховим візерунком, а атрибути — яскравим білим на синьому. Розберімо його по секціях.

```z80 id:ch02_practical_the_checkerboard
    ORG $8000

SCREEN  EQU $4000       ; pixel area start
ATTRS   EQU $5800       ; attribute area start
SCRLEN  EQU 6144        ; pixel bytes (256*192/8)
ATTLEN  EQU 768         ; attribute bytes (32*24)
```

Код розміщений за адресою `$8000` — безпечно в неспірній пам'яті на всіх моделях Spectrum. Константи іменують ключові адреси та розміри.

```z80 id:ch02_practical_the_checkerboard_2
start:
    ; --- Fill pixels with checkerboard pattern ---
    ld   hl, SCREEN
    ld   de, SCREEN + 1
    ld   bc, SCRLEN - 1
    ld   (hl), $55       ; checkerboard: 01010101
    ldir
```

Тут використовується класичний трюк самокопіювання LDIR. Він записує `$55` (двійкове `01010101`) у перший байт за адресою `$4000`, потім копіює кожен байт у наступний для 6 143 байтів. Результат: кожен байт піксельної області — `$55`, що дає чергування встановлених і скинутих пікселів — шахматку. Оскільки візерунок однаковий у кожному байті, черезрядковий порядок рядків не має значення — кожен рядок отримує той самий візерунок незалежно.

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

Та сама техніка для атрибутів. Значення `$4F` декодується як: мерехтіння вимкнено (0), яскравість увімкнена (1), paper синій (001), ink білий (111). Кожна клітинка 8x8 отримує яскравий білий ink на синьому paper. Шахові пікселі встановлені/скинуті, тому ти бачиш чергування білих і синіх точок — класичний візуальний патерн ZX Spectrum.

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

Встановлює бордюр у синій (колір 1), щоб відповідати кольору paper, створюючи візуально чисту рамку. Потім крутиться нескінченно, зупиняючись між кадрами. `HALT` чекає на наступне масковане переривання, яке генерується раз на кадр — це серцебиття простою кожної програми Spectrum.

![Screen fill with alternating bytes — checkerboard pattern in bright white on blue](../../build/screenshots/ch02_fill_screen.png)

### Що спробувати

Завантаж `fill_screen.a80` у свій асемблер та емулятор. Потім поекспериментуй:

- Зміни `$55` на `$AA` для інвертованої шахматки, або на `$FF` для суцільної заливки, або на `$81` для вертикальних смуг.
- Зміни `$4F` на `$07`, щоб побачити той самий візерунок без BRIGHT, або на `$38` для білого paper з чорним ink (інверсія стандарту).
- Спробуй `$C7` — це встановлює біт flash. Спостерігай, як символи чергуються між кольорами ink і paper з частотою близько 1,6 Гц.
- Заміни піксельну заливку LDIR на цикл DOWN_HL, що записує різні візерунки в різні рядки. Тепер ти побачиш черезрядковість у дії: якщо ти запишеш `$FF` у рядки 0-7 (рядки розгортки першої символьної клітинки), заповнена область виглядатиме як 8 горизонтальних смуг, розділених пропусками — тому що ці рядки розташовані через 256 байтів, а не через 32.

---

## Навігація по екрану: Практичний підсумок

Ось основні операції з вказівниками для екрану Spectrum, зібрані в одному місці. Це будівельні блоки кожної графічної процедури.

### Переміщення вправо на один байт (8 пікселів)

```z80 id:ch02_moving_right_one_byte_8
    inc  l             ; 4T
```

Це працює в межах символьного рядка, бо стовпець знаходиться в молодших 5 бітах L. Якщо тобі потрібно перетнути межу байтів на правому краю (стовпець 31 до стовпця 0 наступного рядка), потрібен повний DOWN_HL плюс скидання L — але зазвичай це не потрібно, бо твої цикли мають ширину 32 байти.

### Переміщення на один піксельний рядок униз

```z80 id:ch02_moving_down_one_pixel_row
    inc  h             ; 4T    (within a character cell)
```

Це працює для 7 з 8 рядків. На 8-му рядку потрібна повна логіка перетину меж з процедури DOWN_HL вище.

### Переміщення на один символьний рядок униз (8 пікселів)

```z80 id:ch02_moving_down_one_character_row
    ld   a, l          ; 4T
    add  a, 32         ; 7T
    ld   l, a          ; 4T    total: 15T (if no third crossing)
```

Це просуває на один символьний рядок у межах третини. Якщо L переповнюється (встановлюється прапорець перенесення), ти перетнув межу наступної третини й потрібно додати 8 до H.

### Переміщення на один піксельний рядок угору

```z80 id:ch02_moving_up_one_pixel_row
    dec  h             ; 4T    (within a character cell)
```

Зворотне до `INC H`. Ті самі проблеми з межами символьних клітинок і третин. Ось повна процедура UP_HL, дзеркало DOWN_HL:

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

Той самий трюк `CPL / AND 7` працює і в DOWN_HL, хоча умова межі там перевіряє `000` (які CPL перетворює на `111`, що також ненульове після AND), тому він не допомагає при русі вниз. Саме *вгору* класичний код потребує додаткової `CP 7`, яку оптимізація усуває.

### Обчислення адреси атрибутів з піксельної адреси

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

Це працює, бо L вже містить `LLL CCCCC` — символьний рядок у межах третини (0–7), скомбінований зі стовпцем (0–31) — і це саме молодший байт адреси атрибутів. Старший байт просто потребує номер третини, доданий до `$58`. Елегантно.

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

Це на 2 такти швидше за загальний метод і уникає послідовності `AND / OR`. Компроміс у тому, що це працює лише коли біти рядка розгортки дорівнюють `111` — але саме така ситуація після циклу рендерингу символьної клітинки зверху вниз, що є одним з найпоширеніших випадків використання.

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

## Збираючи все разом: Що означає розкладка екрану для коду

Кожна техніка в решті цієї книги сформована розкладкою екрану, описаною в цьому розділі. Ось чому кожна частина має значення:

**Малювання спрайтів** вимагає обчислення екранної адреси для позиції спрайта, а потім ітерації вниз через рядки спрайта. Кожен рядок означає `INC H` (7 з 8 разів) або повний перетин межі символьної клітинки. 16-піксельний спрайт займає рівно 2 символьні клітинки — ти перетнеш одну межу. 24-піксельний спрайт займає 3 клітинки, перетинаючи 2 межі. Вартість перетину межі — це фіксований податок на кожен спрайт.

**Очищення екрану** (розділ 3) використовує PUSH-трюк — встановлення SP на `$5800` і запис даних вниз через піксельну область. Черезрядковість не має значення для очищення, бо кожен байт отримує те саме значення. Але для *візерункових* очищень (смугасті фони, градієнтні заливки) черезрядковість означає, що потрібно ретельно думати, які рядки отримують які дані.

**Скролінг** (розділ 17) — це де розкладка шкодить найбільше. Прокручування екрану вгору на один піксель означає переміщення 32 байтів кожного рядка на адресу рядка вище. На лінійному фреймбуфері це одне велике блокове копіювання. На Spectrum адреси джерела та призначення для кожного рядка пов'язані логікою DOWN_HL — не фіксованим зміщенням. Процедура скролінгу мусить орієнтуватися в черезрядковості для кожного рядка, який копіює.

**Ефекти атрибутів** (розділи 8–9) — це де розкладка допомагає. Оскільки область атрибутів лінійна й мала (768 байтів), оновлення кольорів є швидким. Повне оновлення атрибутів екрану через LDIR коштує близько 16 000 тактів — менше чверті кадру. Ось чому ефекти на базі атрибутів (тунелі, плазми, зміна кольорів) є фундаментом демосцени Spectrum.

---

## Підсумок

- The Spectrum's 6,912-byte display consists of **6,144 bytes of pixel data** at `$4000`--`$57FF` and **768 bytes of attributes** at `$5800`--`$5AFF`.
- Pixel rows are **interleaved** by character cell: the address encodes y as `010 TT SSS` (high byte) and `LLL CCCCC` (low byte), where the bits of y are shuffled across the address.
- Moving **one pixel row down** within a character cell is just `INC H` (4 T-states). Crossing character and third boundaries requires additional logic.
- The classic **DOWN_HL** routine handles all cases but costs up to 65 T-states at boundaries. For full-screen iteration, **split-counter loops** (Introspec's approach) reduce total cost by 60% and eliminate timing jitter.
- Each attribute byte encodes **Flash, Bright, Paper, and Ink** in the format `FBPPPIII`. Only **two colours per 8x8 cell** -- this is the attribute clash.
- Attribute clash is not just a limitation but a **creative constraint** that defined the Spectrum's visual aesthetic and led to efficient attribute-only demo effects.
- The **border** colour is set by `OUT ($FE), A` (bits 0--2) and changes are visible on the next scanline, making it a **timing debug tool** and a canvas for demoscene raster effects.
- The **Agon Light 2** has no interleaved layout, no attribute clash, and no direct framebuffer access -- it replaces the puzzle with a VDP command API.

---

## Спробуй сам

1. **Зістав адреси.** Обери 10 випадкових координат (x, y) та обчисли екранну адресу вручну за бітовою розкладкою `010TTSSS LLLCCCCC`. Потім напиши невелику Z80-процедуру, що малює один піксель за кожною координатою, і перевір, що твої обчислення збігаються.

2. **Візуалізуй черезрядковість.** Зміни `fill_screen.a80`, щоб записати різні значення в перші 8 рядків. Запиши `$FF` (суцільний) у рядок 0 та `$00` (порожній) у рядки 1–7. Оскільки рядки 0–7 знаходяться за адресами `$4000`, `$4100`, ..., `$4700`, тобі потрібно змінювати H для доступу до кожного рядка. Результат має бути одна яскрава лінія на самому верху з проміжком у 7 порожніх ліній перед наступною суцільною лінією на рядку 8.

3. **Заміряй DOWN_HL.** Використай тестову обв'язку з кольором бордюру з розділу 1. Виклич класичну процедуру DOWN_HL 191 раз (для повного обходу екрану) і виміряй смугу. Потім реалізуй версію з роздільними лічильниками й порівняй. Версія з роздільними лічильниками має дати видимо коротшу смугу.

4. **Малювальник атрибутів.** Напиши процедуру, що заповнює область атрибутів градієнтом: стовпець 0 отримує колір 0, стовпець 1 — колір 1, і так далі (циклічно через 0–7). Кожен рядок має мати той самий візерунок. Потім зміни так, щоб кожен рядок зсував візерунок на одну позицію — діагональна веселка. Це зародок демо-ефекту на базі атрибутів.

5. **Бордюрні смуги.** Після `HALT` виконай щільний цикл, що змінює колір бордюру на кожному рядку розгортки протягом 64 ліній. Використай 8 кольорів бордюру послідовно (0, 1, 2, 3, 4, 5, 6, 7, повтор). Ти маєш побачити горизонтальні веселкові смуги у верхньому бордюрі. Підбери затримку між інструкціями `OUT`, поки смуги не стануть чистими й стабільними.

---

> **Sources:** Introspec "Eshchyo raz pro DOWN_HL" (Hype, 2020); Introspec "GO WEST Part 1" (Hype, 2015) for contended memory effects at screen addresses; Introspec "Making of Eager" (Hype, 2015) for attribute-based effect design; the Spectrum's ULA documentation for memory layout rationale; Art-top (personal communication, 2026) for the optimised UP_HL and fast pixel-to-attribute conversion.

*Далі: Розділ 3 — Інструментарій демосценера. Розгорнуті цикли, самомодифікований код, стек як канал передачі даних та техніки, що дозволяють робити неможливе в межах бюджету.*
