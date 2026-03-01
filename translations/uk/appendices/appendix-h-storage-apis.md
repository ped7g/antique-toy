# Додаток H: API зберігання --- TR-DOS та esxDOS

> *"Технічно вражаюче демо, яке подається як .tzx, коли правила вимагають .trd, буде дискваліфіковано."*
> -- Розділ 20

Дві API зберігання домінують у світі ZX Spectrum: **TR-DOS** (дискова операційна система радянського інтерфейсу Beta Disk 128, стандартна на клонах Pentagon та Scorpion) та **esxDOS** (сучасна операційна система для SD-карт, що працює на апаратному забезпеченні DivMMC та DivIDE). Більшість релізів російської та української демосцени поширюються як дискові образи `.trd`. Більшість сучасних західних релізів використовують касетні образи `.tap` або файлову структуру, сумісну з esxDOS. Якщо ти випускаєш демо чи гру сьогодні, практичним вибором буде надати образ `.trd` для сумісності з величезною російсько-українською базою користувачів, і файл `.tap` для решти. Якщо твій завантажувач підтримує виявлення esxDOS (як описано в Розділі 21), користувачі з апаратним забезпеченням DivMMC отримують швидке завантаження з SD-картки безкоштовно.

Цей додаток --- довідник з API, який тримаєш відкритим, поки пишеш свій завантажувач. Розділ 21 охоплює інтеграцію у повноцінний ігровий проєкт. Розділ 15 охоплює апаратні деталі перемикання банків пам'яті та маппінгу портів, на яких базуються обидва API.

---

## 1. TR-DOS (Beta Disk 128)

### Апаратне забезпечення

Інтерфейс Beta Disk 128 --- це стандартний контролер гнучких дисків для Pentagon, Scorpion та більшості радянських клонів ZX Spectrum. Він побудований на мікросхемі контролера гнучких дисків Western Digital WD1793, яка спілкується з Z80 через п'ять портів введення-виведення.

ПЗП TR-DOS (8 КБ) займає `$0000`--`$3FFF`, коли інтерфейс Beta Disk активний. Воно автоматично підключається, коли Z80 виконує код за адресою `$3D13` (магічна точка входу), та відключається, коли виконання повертається до області основного ПЗП.

### Формат диска

| Властивість | Значення |
|-------------|----------|
| Доріжки | 80 |
| Сторони | 2 |
| Секторів на доріжку | 16 |
| Байтів на сектор | 256 |
| Загальна ємність | 640 КБ (655 360 байтів) |
| Формат образу | `.trd` (необроблений образ диска, 640 КБ) |
| Системна доріжка | Доріжка 0, сторона 0 |

Доріжка 0 містить каталог диска (сектори 1--8) та інформаційний сектор диска (сектор 9). Каталог вміщує до 128 файлових записів. Кожен запис --- 16 байтів:

```
Bytes 0-7:   Filename (8 characters, space-padded)
Byte  8:     File type: 'C' = code, 'B' = BASIC, 'D' = data, '#' = sequential
Bytes 9-10:  Start address (or BASIC line number)
Bytes 11-12: Length in bytes
Byte  13:    Length in sectors
Byte  14:    Starting sector
Byte  15:    Starting track
```

### Карта портів WD1793

| Порт | Читання | Запис |
|------|---------|-------|
| `$1F` | Регістр стану | Регістр команд |
| `$3F` | Регістр доріжки | Регістр доріжки |
| `$5F` | Регістр сектора | Регістр сектора |
| `$7F` | Регістр даних | Регістр даних |
| `$FF` | Системний регістр TR-DOS | Системний регістр TR-DOS |

Порт `$FF` --- це системний порт Beta Disk. Він керує вибором дисковода, вибором сторони, підведенням голівки та щільністю. Старші біти також відображають сигнали DRQ (Data Request) та INTRQ (Interrupt Request) від WD1793.

### Команди WD1793

| Команда | Код | Опис |
|---------|-----|------|
| Restore | `$08` | Перемістити голівку на доріжку 0. Перевірити доріжку. |
| Seek | `$18` | Перемістити голівку на доріжку з регістра даних. |
| Step In | `$48` | Зробити крок голівкою на одну доріжку до центру. |
| Step Out | `$68` | Зробити крок голівкою на одну доріжку до краю. |
| Read Sector | `$88` | Прочитати один 256-байтний сектор. |
| Write Sector | `$A8` | Записати один 256-байтний сектор. |
| Read Address | `$C0` | Прочитати наступне поле ідентифікатора сектора. |
| Force Interrupt | `$D0` | Перервати поточну команду. |

Молодша тетрада кожного байта команди містить прапорці-модифікатори (швидкість кроку, перевірка, вибір сторони, затримка). Значення вище використовують типові значення за замовчуванням. Звертайся до даташиту WD1793 для повного опису бітової структури.

### ROM API: завантаження файлу

Стандартний підхід до файлового вводу-виводу під TR-DOS --- це виклик підпрограм ПЗП за адресою `$3D13`. ПЗП TR-DOS надає високорівневі файлові операції через систему команд: ти розміщуєш параметри в регістрах та в системній області за адресами `$5D00`--`$5FFF`, а потім робиш виклик у ПЗП.

```z80
; TR-DOS: Load a file by name
; Loads a code file ('C' type) to its stored start address
;
; The filename must be placed at $5D02 (8 bytes, space-padded).
; The file type goes to $5D0A.
;
; Call $3D13 with C = $08 (load file command)

load_trdos_file:
    ; Set up filename at TR-DOS system area
    ld   hl, my_filename
    ld   de, $5D02
    ld   bc, 8
    ldir                    ; copy 8-char filename

    ld   a, 'C'             ; file type: code
    ld   ($5D0A), a

    ld   c, $08             ; TR-DOS command: load file
    call $3D13              ; enter TR-DOS ROM
    ret

my_filename:
    db   "SCREEN  "         ; 8 characters, space-padded
```

Для завантаження за конкретною адресою (з перевизначенням збереженої стартової адреси):

```z80
; TR-DOS: Load file to explicit address
; HL = destination address
; DE = length to load
; Filename already at $5D02, type at $5D0A

load_trdos_to_addr:
    ld   hl, $4000          ; load to screen memory
    ld   de, 6912           ; 6912 bytes (one screen)
    ld   ($5D03), hl        ; override start address
    ld   ($5D05), de        ; override length
    ld   c, $08             ; load file
    call $3D13
    ret
```

### Прямий доступ до секторів

Для демо, які потоково зчитують дані з диска --- повноекранні анімації, музичні дані, що перевищують доступну ОЗП, або багаточастинні демо, що завантажують ефекти "на льоту" --- прямий доступ до секторів обходить файлову систему повністю. Ти контролюєш позицію голівки, читаєш сектори один за одним та обробляєш дані по мірі їх надходження.

```z80
; Read a single sector directly via WD1793 ports
; B = track number (0-159, with side encoded in bit 0 of $FF)
; C = sector number (1-16)
; HL = destination buffer (256 bytes)

read_sector:
    ld   a, b
    out  ($3F), a           ; set track register
    ld   a, c
    out  ($5F), a           ; set sector register

    ld   a, $88             ; Read Sector command
    out  ($1F), a           ; issue command

    ; Wait for DRQ and read 256 bytes
    ld   b, 0               ; 256 bytes to read
.wait_drq:
    in   a, ($FF)           ; read system register
    bit  6, a               ; test DRQ bit
    jr   z, .wait_drq       ; wait until data ready
    in   a, ($7F)           ; read data byte
    ld   (hl), a
    inc  hl
    djnz .wait_drq

    ; Wait for command completion
.wait_done:
    in   a, ($1F)           ; read status register
    bit  0, a               ; test BUSY bit
    jr   nz, .wait_done
    ret
```

**Увага:** Прямий доступ до секторів чутливий до часу. Переривання мають бути вимкнені під час циклу передачі даних, інакше байти будуть втрачені. WD1793 утримує DRQ протягом обмеженого часового вікна; якщо Z80 не прочитає регістр даних до надходження наступного байта, дані будуть перезаписані. На швидкості 250 кбіт/с (подвійна щільність) ти маєш приблизно 32 мікросекунди на байт --- близько 112 тактів (T-state) на Pentagon. Щільний цикл вище виконується приблизно за 50--60 тактів (T-state) на байт, залишаючи достатній запас.

### Виявлення диска

Для виявлення наявності інтерфейсу Beta Disk:

```z80
; Detect Beta Disk 128
; Returns: carry clear if present, carry set if absent
detect_beta_disk:
    ; The TR-DOS ROM signature is at $0069 when paged in.
    ; We can check port $FF for a sane response:
    ; If no Beta Disk is present, port $FF reads as floating bus.
    in   a, ($1F)           ; read WD1793 status
    cp   $FF                ; floating bus returns $FF
    scf
    ret  z                  ; probably no controller
    or   a                  ; clear carry = present
    ret
```

Більш надійний метод --- спробувати викликати `$3D13` і перевірити, чи присутні байти сигнатури ПЗП TR-DOS. Виробничий код зазвичай перевіряє відому послідовність байтів у точках входу ПЗП TR-DOS.

---

## 2. esxDOS (DivMMC / DivIDE)

### Апаратне забезпечення

DivMMC (та його старший побратим DivIDE) --- це інтерфейс масового зберігання, що підключає SD-картку до ZX Spectrum. Прошивка esxDOS надає POSIX-подібний файловий API, доступний з Z80-коду через `RST $08`. esxDOS підтримує файлові системи FAT16 та FAT32, довгі імена файлів, підкаталоги та кілька одночасно відкритих файлових дескрипторів.

DivMMC використовує автоматичне маппування: коли Z80 зчитує інструкцію з певних "перехоплюючих" адрес (зокрема `$0000`, `$0008`, `$0038`, `$0066`, `$04C6`, `$0562`), апаратне забезпечення DivMMC автоматично підключає власне ПЗП за адресою `$0000`--`$1FFF`. Перехоплення `RST $08` --- це основна точка входу API.

### Шаблон API

Кожен виклик esxDOS слідує одному шаблону:

```z80
    rst  $08              ; trigger DivMMC auto-map
    db   function_id      ; function number (byte after RST)
    ; Returns:
    ;   Carry clear = success
    ;   Carry set   = error, A = error code
```

Номер функції --- це байт, що йде безпосередньо за інструкцією `RST $08` у пам'яті. Z80 виконує `RST $08`, що переходить за адресою `$0008`. DivMMC автоматично підключає своє ПЗП за цією адресою, зчитує наступний байт (номер функції), відправляє виклик, потім відключає своє ПЗП та повертається до інструкції після `DB`.

### Довідник функцій

| Функція | ID | Опис | Вхід | Вихід |
|---------|-----|------|------|-------|
| `M_GETSETDRV` | `$89` | Отримати/встановити диск за замовчуванням | A = `'*'` для типового | A = літера диска |
| `F_OPEN` | `$9A` | Відкрити файл | IX = ім'я файлу (нуль-термінований), B = режим, A = диск | A = файловий дескриптор |
| `F_CLOSE` | `$9B` | Закрити файл | A = файловий дескриптор | -- |
| `F_READ` | `$9D` | Прочитати байти | A = дескриптор, IX = буфер, BC = кількість | BC = прочитано байтів |
| `F_WRITE` | `$9E` | Записати байти | A = дескриптор, IX = буфер, BC = кількість | BC = записано байтів |
| `F_SEEK` | `$9F` | Переміщення у файлі | A = дескриптор, L = whence, BCDE = зміщення | BCDE = нова позиція |
| `F_FSTAT` | `$A1` | Стан файлу (за дескриптором) | A = дескриптор, IX = буфер | 11-байтний блок статусу |
| `F_OPENDIR` | `$A3` | Відкрити каталог | IX = шлях (нуль-термінований) | A = дескриптор каталогу |
| `F_READDIR` | `$A4` | Прочитати запис каталогу | A = дескриптор каталогу, IX = буфер | запис за (IX) |
| `F_CLOSEDIR` | `$A5` | Закрити каталог | A = дескриптор каталогу | -- |
| `F_GETCWD` | `$A8` | Отримати поточний каталог | IX = буфер | шлях за (IX) |
| `F_CHDIR` | `$A9` | Змінити каталог | IX = шлях | -- |
| `F_STAT` | `$AC` | Стан файлу (за ім'ям) | IX = ім'я файлу | 11-байтний блок статусу |

### Режими відкриття файлу

| Режим | Значення | Опис |
|-------|----------|------|
| Тільки читання | `$01` | Відкрити існуючий файл для читання |
| Створити/урізати | `$06` | Створити новий або урізати існуючий для запису |
| Тільки створити | `$04` | Створити новий файл; помилка, якщо існує |
| Дописування | `$0E` | Відкрити для запису в кінець файлу |

### Значення Seek Whence

| Whence | Значення | Опис |
|--------|----------|------|
| `SEEK_SET` | `$00` | Зміщення від початку файлу |
| `SEEK_CUR` | `$01` | Зміщення від поточної позиції |
| `SEEK_END` | `$02` | Зміщення від кінця файлу |

### Приклад коду: завантаження файлу

```z80
; esxDOS: Load a binary file into memory
;
; Uses register conventions from esxDOS API documentation.
; Note: F_READ uses IX for the destination buffer, not HL.

    ld   a, '*'             ; use default drive
    ld   ix, filename       ; pointer to zero-terminated filename
    ld   b, $01             ; FA_READ: open for reading
    rst  $08
    db   $9A                ; F_OPEN
    jr   c, .error          ; carry set = error

    ld   (.file_handle), a  ; save file handle

    ld   ix, $4000          ; destination buffer (screen memory)
    ld   bc, 6912           ; bytes to read (one full screen)
    ld   a, (.file_handle)
    rst  $08
    db   $9D                ; F_READ
    jr   c, .error

    ld   a, (.file_handle)
    rst  $08
    db   $9B                ; F_CLOSE
    ret

.error:
    ; A contains the esxDOS error code
    ; Common errors:
    ;   5 = file not found
    ;   7 = file already exists (on create)
    ;   9 = invalid file handle
    ret

filename:
    db   "screen.scr", 0

.file_handle:
    db   0
```

### Приклад коду: потокове зчитування даних з файлу

Для демо, які завантажують дані поступово --- розпаковуючи фрагменти рівнів між кадрами, потоково відтворюючи попередньо відрендерену анімацію або завантажуючи музичні патерни за запитом --- шаблон такий: відкрити файл один раз, читати по фрагменту за кадр, закрити, коли завершено.

```z80
; Streaming: read N bytes per frame from an open file
; Call stream_init once, then stream_chunk from your main loop.

CHUNK_SIZE  equ  256        ; bytes per frame (tune to budget)

stream_handle:  db 0
stream_done:    db 0

; Initialise: open the file
stream_init:
    ld   a, '*'
    ld   ix, stream_file
    ld   b, $01             ; FA_READ
    rst  $08
    db   $9A                ; F_OPEN
    ret  c                  ; error
    ld   (stream_handle), a
    xor  a
    ld   (stream_done), a   ; not done yet
    ret

; Per-frame: read one chunk into buffer
; Returns: BC = bytes actually read (may be < CHUNK_SIZE at EOF)
stream_chunk:
    ld   a, (stream_done)
    or   a
    ret  nz                 ; already finished

    ld   a, (stream_handle)
    ld   ix, stream_buffer
    ld   bc, CHUNK_SIZE
    rst  $08
    db   $9D                ; F_READ
    jr   c, .eof

    ; BC = bytes actually read
    ld   a, b
    or   c
    jr   z, .eof            ; zero bytes read = end of file
    ret

.eof:
    ld   a, (stream_handle)
    rst  $08
    db   $9B                ; F_CLOSE
    ld   a, 1
    ld   (stream_done), a
    ret

stream_file:
    db   "anim.bin", 0

stream_buffer:
    ds   CHUNK_SIZE
```

### Виявлення esxDOS

```z80
; Detect esxDOS presence
; Returns: carry clear = esxDOS available, carry set = not available
;
; Strategy: attempt M_GETSETDRV. If esxDOS is present, it returns
; the current drive letter. If not present, RST $08 goes to the
; Spectrum ROM's error handler at $0008 (a benign instruction on
; the 128K ROM) and does not crash.

detect_esxdos:
    ld   a, '*'             ; request default drive
    rst  $08
    db   $89                ; M_GETSETDRV
    ret                     ; carry flag set by esxDOS on error
```

Більш консервативний підхід перевіряє наявність сигнатури перехоплення DivMMC перед викликом будь-яких функцій API. На практиці метод вище працює на всіх моделях 128K, оскільки обробник `$0008` у ПЗП 128K не спричиняє збій --- він виконує безпечну послідовність і повертається. На машині 48K без esxDOS, `RST $08` переходить до рестарту обробки помилок, що може потребувати спеціальної обробки. Розділ 21 обговорює це в контексті виробничого ігрового завантажувача.

---

## 3. +3DOS (Amstrad +3)

Amstrad Spectrum +3, з вбудованим 3-дюймовим дисководом, має власну DOS: +3DOS. API використовує інший механізм --- виклики точок входу в ПЗП +3DOS на сторінці `$01`, доступних через `RST $08` з іншим набором кодів функцій.

+3DOS рідко використовується в демосцені з двох причин. По-перше, +3 продавався переважно в Західній Європі і ніколи не був домінуючою моделлю Spectrum в жодній спільноті сцени. По-друге, нестандартна карта пам'яті та схема перемикання ПЗП +3 роблять його несумісним з більшістю демосценового коду, написаного для архітектури 128K/Pentagon. Якщо тобі потрібна сумісність з +3, API +3DOS описано в технічному посібнику Spectrum +3 (Amstrad, 1987). Для більшості демо- та ігрових проєктів достатньо надати файл `.tap` --- +3 завантажує файли `.tap` нативно через режим сумісності з касетою.

---

## 4. Практичні шаблони

### Завантаження екрана з диска (TR-DOS)

Завантажувальний екран --- це перше враження користувача. Під TR-DOS файл екрана (`SCREEN  C`, 6912 байтів) завантажується безпосередньо за адресою `$4000` і з'являється миттєво:

```z80
; TR-DOS: Load a .scr file directly to screen memory
; The screen appears as it loads, line by line.
load_screen_trdos:
    ld   hl, scr_filename
    ld   de, $5D02
    ld   bc, 8
    ldir
    ld   a, 'C'
    ld   ($5D0A), a
    ld   hl, $4000          ; destination: screen memory
    ld   ($5D03), hl
    ld   de, 6912           ; length: full screen
    ld   ($5D05), de
    ld   c, $08             ; load file
    call $3D13
    ret

scr_filename:
    db   "SCREEN  "         ; 8 chars, padded
```

### Завантаження екрана з SD (esxDOS)

Той самий візуальний результат, інший API:

```z80
; esxDOS: Load a .scr file to screen memory
load_screen_esxdos:
    ld   a, '*'
    ld   ix, scr_filename_esx
    ld   b, $01             ; FA_READ
    rst  $08
    db   $9A                ; F_OPEN
    ret  c

    push af                 ; save handle
    ld   ix, $4000          ; destination: screen memory
    ld   bc, 6912
    pop  af
    push af
    rst  $08
    db   $9D                ; F_READ
    pop  af
    rst  $08
    db   $9B                ; F_CLOSE
    ret

scr_filename_esx:
    db   "screen.scr", 0
```

### Двохрежимний завантажувач

Виробничий завантажувач повинен визначити доступне сховище та використати його:

```z80
; Unified loader: try esxDOS first, fall back to TR-DOS, then tape
load_data:
    call detect_esxdos
    jr   nc, .use_esxdos    ; carry clear = esxDOS present

    call detect_beta_disk
    jr   nc, .use_trdos     ; carry clear = Beta Disk present

    ; Fall back to tape loading
    jp   load_from_tape

.use_esxdos:
    jp   load_from_esxdos

.use_trdos:
    jp   load_from_trdos
```

### Потокова передача стиснутих даних

Найпотужніший шаблон поєднує API зберігання зі стисненням (Додаток C). Відкрий файл зі стиснутими даними, зчитуй фрагменти в буфер кожен кадр, розпаковуй у цільову область та просувайся далі:

```
Frame 1:  F_READ 256 bytes -> buffer   |  decompress buffer -> screen
Frame 2:  F_READ 256 bytes -> buffer   |  decompress buffer -> screen
Frame 3:  F_READ 256 bytes -> buffer   |  decompress buffer -> screen
...
Frame N:  F_READ < 256 bytes (EOF)     |  decompress, close file
```

При 256 байтах за кадр та 50 кадрах/с ти потоково передаєш 12,5 КБ/с з SD-картки --- достатньо для стиснутої повноекранної анімації. Під TR-DOS пряме зчитування секторів по одному сектору за кадр дає 12,8 КБ/с (256 байтів * 50 кадрів/с). Вузьке місце --- швидкість розпакування, а не введення-виведення.

---

## 5. Довідник форматів файлів

| Формат | Розширення | Використання | Примітки |
|--------|------------|--------------|----------|
| Образ диска TR-DOS | `.trd` | Стандарт для релізів Pentagon/Scorpion | Необроблений образ 640 КБ. Підтримується кожним емулятором. |
| Файловий контейнер TR-DOS | `.scl` | Простіший за .trd | Містить файли без повної структури диска. Добре для поширення. |
| Касетний образ | `.tap` | Універсальний касетний формат | Працює на кожній моделі Spectrum та в кожному емуляторі. Без файлової системи. |
| Розширений касетний образ | `.tzx` | Касета з захистом від копіювання / турбозавантажувачами | Зберігає точний тайминг касети. Рідко потрібен для нових релізів. |
| Знімок (48K/128K) | `.sna` | Швидке завантаження, без файлової системи | Захоплює повний стан машини. Код завантажувача не потрібен. |
| Знімок (стиснутий) | `.z80` | Як .sna, але стиснутий | Кілька версій; .z80 v3 підтримує 128K. |
| Дистрибуція Next | `.nex` | Виконуваний файл ZX Spectrum Next | Самодостатній бінарний файл із заголовком, що визначає розкладку банків. |

**Вибір формату релізу:** Для демосценового релізу надай принаймні два формати:

1. **`.trd`** для користувачів TR-DOS (російсько-українська спільнота, власники Pentagon/Scorpion та користувачі емуляторів, які віддають перевагу дисковим образам). Це стандарт для паті на кшталт Chaos Constructions та DiHalt.
2. **`.tap`** для всіх інших (реальне 128K-апаратне забезпечення з касетним входом, користувачі DivMMC через завантажувач `.tap`, та всі емулятори). sjasmplus може генерувати вихідні файли `.tap` напряму за допомогою директиви `SAVETAP`.

Якщо твоє демо достатньо мале (менше 48 КБ), знімок `.sna` також підходить --- він завантажується миттєво без коду завантажувача.

---

## 6. Див. також

- **Розділ 15** --- Анатомія апаратного забезпечення: перемикання банків пам'яті, порт `$7FFD`, повна карта портів, поруч з якими працюють TR-DOS та esxDOS.
- **Розділ 20** --- Робочий процес демо: формати релізів, правила подачі на паті, вимоги `.trd` проти `.tap`.
- **Розділ 21** --- Повноцінна гра: виробничий код завантаження з касети та esxDOS, виявлення подвійного режиму, побанкове завантаження.
- **Додаток C** --- Стиснення: які компресори поєднувати з потоковим вводом-виводом.
- **Додаток E** --- eZ80 / Agon Light 2: файловий API MOS на Agon, який надає подібні файлові операції (`mos_fopen`, `mos_fread`, `mos_fclose`) через інший механізм (RST $08 з кодами функцій MOS у режимі ADL).

---

> **Джерела:** WD1793 datasheet (Western Digital, 1983); TR-DOS v5.03 disassembly (various, public domain); esxDOS API documentation (Wikipedia, zxe.io); DivMMC hardware specification (Mario Prato / ByteDelight); Spectrum +3 Technical Manual (Amstrad, 1987); Introspec, "Loading and saving on the Spectrum" (Hype, 2016)
