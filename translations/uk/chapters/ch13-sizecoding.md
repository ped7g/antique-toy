# Розділ 13: Мистецтво sizecoding

> "It was like playing puzzle-like games -- constant reshuffling of code to find shorter encodings."
> -- UriS, про написання NHBF (2025)

Існує категорія змагань на демосцені, де обмеженням є не час, а *простір*. Вся твоя програма -- код, що малює екран, створює звук, обробляє кадровий цикл, зберігає будь-які потрібні дані -- повинна вміститися у 256 байт. Або 512. Або 1K, або 4K, або 8K. Жодного байта більше. Файл вимірюється, і якщо він 257 байт, його дискваліфіковано.

These are **size-coding** competitions, and they produce some of the most remarkable work on the ZX Spectrum scene. A 256-byte intro that fills the screen with animated patterns and plays a recognisable melody is a form of compression so extreme it is hard to believe until you read the code. The gap between what the audience sees and the file size that produces it -- that gap is the art.

Цей розділ про мислення, техніки та конкретні трюки, що роблять sizecoding можливим.

---

## 13.1 Що таке sizecoding?

Змагання на демо зазвичай пропонують кілька категорій з обмеженням розміру:

| Категорія | Ліміт | Що вміщується |
|-----------|-------|---------------|
| 256 байт | 256 | Один щільний ефект, можливо простий звук |
| 512 байт | 512 | Ефект з базовою музикою або два простих ефекти |
| 1K інтро | 1 024 | Кілька ефектів, повноцінна музика, переходи |
| 4K інтро | 4 096 | Коротке демо з кількома частинами |
| 8K інтро | 8 192 | Відполіроване міні-демо |

Ліміти абсолютні. Файл вимірюється в байтах, і переговорів немає.

Те, що робить sizecoding захоплюючим -- це інверсія звичної ієрархії оптимізації. У світі підрахованих тактів демосценних ефектів ти оптимізуєш для *швидкості* -- розгортаєш цикли, дублюєш дані, генеруєш код, все заради обміну простору на час. Sizecoding це інвертує. Швидкість не має значення. Читабельність не має значення. Єдине питання: чи можна зробити на один байт коротше?

UriS, який написав 256-байтне інтро NHBF для Chaos Constructions 2025, описав процес як "гру в головоломки." Опис точний. Sizecoding -- це головоломка, де фігури -- це інструкції Z80, дошка -- 256 байт ОЗП, і найкращі рішення включають ходи, що вирішують кілька проблем одночасно.

Зміна мислення:

- **Кожний байт цінний.** 3-байтна інструкція там, де достатньо 2-байтної -- це 0,4% всієї твоєї програми. На 256 байтах один збережений байт -- це як заощадити 250 байт у 64K програмі.

- **Код і дані перетинаються.** Ті самі байти, що виконуються як інструкції, можуть слугувати даними. Z80 не розрізняє їх -- лише шлях лічильника команд через пам'ять відрізняє код від даних.

- **Вибір інструкцій визначається розміром, не швидкістю.** `RST $10` коштує 1 байт. `CALL $0010` робить те саме за 3 байти. У звичайному демо ти б ніколи не помітив. На 256 байтах ці 2 байти -- різниця між наявністю звуку чи ні.

- **Початковий стан -- це безкоштовні дані.** Після завантаження регістри мають відомі значення. Пам'ять за певними адресами містить відомі дані. Кодер розміру використовує кожний біт цього безкоштовного стану.

- **Самомодифікований код (SMC) -- не трюк, а необхідність.** Коли ти не можеш дозволити собі окрему змінну, ти модифікуєш операнд інструкції на місці.

### The Z80 Size-Coder's Toolkit

Some tricks recur so often in size-coded intros that they form a shared vocabulary. Knowing these by heart -- their byte costs, their side effects -- is the prerequisite to serious size-coding.

**Register initialization assumptions.** When a Spectrum program launches from BASIC (via `RANDOMIZE USR`), the CPU state is not random. After `CLEAR` and before the USR call, A is typically 0, BC holds the USR address, DE and HL have known values from the BASIC interpreter, the stack pointer sits at the CLEAR address, and interrupts are enabled. Many of these are stable enough to rely on. If your program needs A = 0 at the start, do not write `XOR A` -- it is already zero. If you need a 16-bit counter starting at 0, check whether DE or HL already holds 0 or a useful value. One byte saved here, two bytes saved there -- these add up to the difference between 260 bytes and 256.

The system variables area ($5C00-$5CB5) is another source of free data. The BASIC interpreter maintains over 100 bytes of state at known addresses. If you need the value 2, you might find it at the address holding the current stream number. If you need $FF, several system variable fields contain it. Reading from a fixed address costs 3 bytes (`LD A, (nn)`), but if it replaces a 2-byte load *plus* some computation, you come out ahead.

**DJNZ as a short backwards jump.** `DJNZ label` is 2 bytes, same as `JR label` -- but it also decrements B. If B is nonzero and you need a backwards jump, `DJNZ` does both for free. Even when you do not care about B's decrement, `DJNZ` is still 2 bytes, the same cost as `JR`. But if B happens to reach zero at the exact moment you want to fall through, you have merged a loop counter and a branch into a single instruction. Size-coders routinely structure loops so that B's natural countdown aligns with the exit condition.

**RST as a 1-byte CALL.** The Z80 reserves eight restart addresses: $00, $08, $10, $18, $20, $28, $30, $38. `RST n` pushes the return address and jumps to the target -- the same as `CALL n` -- but in 1 byte instead of 3. On the Spectrum, the ROM places useful routines at several of these addresses:

- `RST $10` -- print a character (ROM routine at $0010)
- `RST $20` -- collect next character from BASIC (less useful for demos)
- `RST $28` -- enter the floating-point calculator (useful for math)
- `RST $38` -- the maskable interrupt handler (IM 1 jumps here)

In a normal demo, these ROM routines are too slow to call in a tight loop. In a 256-byte intro, saving 2 bytes per call is worth the speed penalty. If your program calls `RST $10` six times to print characters, that is 12 bytes saved over six `CALL $0010` instructions. Twelve bytes is nearly 5% of 256.

**Overlapping instructions.** The Z80 decodes instructions byte by byte, with no alignment requirements. If you jump into the middle of a multi-byte instruction, the CPU decodes fresh from that point. This means you can hide one instruction inside another:

```z80 id:ch13_the_z80_size_coder_s_toolkit
    ld   a, $AF              ; opcode $3E, operand $AF
                              ; BUT: $AF is XOR A
```

If the CPU executes from the start, it sees `LD A, $AF` (2 bytes). If another code path jumps to the second byte, it sees `XOR A` (1 byte). One byte serves two purposes. The technique is fragile -- it demands perfect control of all execution paths -- but in competition code, fragility is acceptable.

A common pattern: the byte `$18` is `JR d` (relative jump). If you need the value $18 as data *and* need a branch at that location, the same byte does both. The operand that follows is both the jump offset and (from another perspective) the next piece of data.

**Abusing flag state.** Every arithmetic and logical instruction sets flags. Size-coders memorise which flags each instruction affects and exploit the results instead of computing them separately. After `DEC B`, the zero flag tells you whether B hit zero -- no `CP 0` needed. After `ADD A, n`, the carry flag tells you whether the result overflowed past 255. After `AND mask`, the zero flag tells you whether any masked bits were set.

The deepest flag trick is `SBC A, A`: if carry is set, A becomes $FF; if carry is clear, A becomes $00. One byte, no branch, a full bitmask from a flag. Compare this to the branching alternative:

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

Five bytes saved. In a 256-byte intro, that is two percent of the entire program.

---

## 13.2 Анатомія 256-байтного інтро: NHBF

**NHBF** (No Heart Beats Forever) було створено UriS для Chaos Constructions 2025, натхненне RED REDUX з Multimatograf 2025. Воно створює текст з екранними ефектами та музику -- зациклені прямокутнохвильові пауер-акорди з випадковими мелодійними нотами пентатоніки -- все за 256 байт.

### Музика

На 256 байтах ти не можеш включити трекерний програвач або таблиці нот. NHBF керує чипом AY безпосередньо. Пауер-акорди захардкоджені як безпосередні значення в інструкціях запису регістрів AY -- ті самі байти, що формують операнд `LD A, n`, *є* музичною нотою. Мелодійний канал використовує псевдовипадковий генератор (зазвичай `LD A, R` -- зчитування регістра оновлення -- з наступним AND для маскування діапазону) для вибору з пентатонічної гами. Пентатонічна гама звучить приємно незалежно від того, які ноти опиняються поруч, тому мелодія звучить навмисно, хоча вона випадкова. Два байти на "випадкове" число; п'ять нот, що ніколи не конфліктують.

### Візуальна частина

Друк тексту через ROM -- `RST $10` виводить символ за 1 байт виклику -- це найдешевший спосіб отримати пікселі на екрані. Але навіть 20-символьний рядок коштує 40 байт (коди символів + виклики RST). Кодери розміру шукають способи ще більшого стиснення: перетинання рядкових даних з іншим кодом або обчислення символів за формулою.

### Головоломка: Пошук перетинань

UriS описує ключовий процес як постійне перетасовування. Ти пишеш першу версію на 300 байт, потім вдивляєшся в неї. Помічаєш, що лічильник циклу для візуального ефекту закінчується значенням, яке тобі потрібне як номер регістра AY. Прибери `LD A, 7`, що його встановлювала -- цикл вже залишив 7 в A. Два байти збережено. Процедура очищення екрану використовує LDIR, що зменшує BC до нуля. Розташуй код так, щоб наступна секція потребувала BC = 0, і збережи `LD BC, 0` -- ще 3 байти.

Кожна інструкція створює побічні ефекти -- значення регістрів, стани прапорців, вміст пам'яті -- і мистецтво полягає в розташуванні інструкцій так, щоб побічні ефекти однієї процедури були вхідними даними іншої.

### Відкриття Art-Top

Під час розробки Art-Top помітив щось дивовижне: значення регістрів, що залишилися від процедури очищення екрану, випадково збіглися з точною довжиною, потрібною для текстового рядка. Не заплановано. UriS написав очищення екрану, потім вивід тексту, і ці два випадково поділили стан регістрів, що усунув окремий лічильник довжини.

Такий серендипний збіг -- серце кодування на 256 байтах. Ти не можеш його спланувати. Ти можеш лише створити умови, за яких він може статися, постійно перетасовуючи код і стежачи за випадковими збігами. Коли знаходиш такий -- це відчувається як відкриття, що два елементи пазла з різних наборів ідеально з'єднуються.

### The Byte Budget

When working at 256 bytes, a rough budget helps you plan before writing a single instruction. Here is a realistic breakdown for a typical ZX Spectrum 256-byte intro with both visuals and sound:

| Component | Bytes | Notes |
|-----------|-------|-------|
| Pixel fill (dither/clear) | 18-25 | LD HL, LDIR or a compact fill loop |
| AY initialisation | 16-22 | Mixer, volume, initial tone — via port writes |
| Main loop frame sync | 1 | HALT |
| AY tone update per frame | 10-14 | Select register, write tone period |
| Visual effect core | 30-50 | The inner loop that computes and writes attributes |
| Outer loop / row control | 8-12 | Row counter, column counter, branches |
| Frame counter update (SMC) | 6-8 | Read, increment, write back into instruction |
| Loop back to main | 2 | JR main_loop |
| **Total framework** | **~91-134** | Before any effect-specific code |

That leaves 122-165 bytes for the actual creative content -- the visual formula, data tables, extra sound logic, text strings, or anything else that makes the intro *yours*. The framework is expensive. This is why size-coders fight so hard for every byte in the scaffolding: each byte saved in the framework is a byte gained for art.

Look at the companion example `intro256.a80`. Its pixel fill loop uses 18 bytes. The AY setup takes 20 bytes. The main loop framework (HALT, frame counter read, border update) is 8 bytes. The AY tone update is 13 bytes. The visual effect -- a Moire interference pattern computed purely from register arithmetic -- consumes 36 bytes. The frame counter writeback and loop jump take 8 bytes. Total: around 103 bytes of framework and 36 bytes of effect. That ratio -- roughly 3:1 framework to effect -- is typical. The better you compress the framework, the more room you have for creative expression.

![Output of a 256-byte intro -- animated Moire interference pattern with colour cycling, generated entirely from register arithmetic](../../build/screenshots/ch13_intro256.png)

### Ключові техніки на 256 байтах

**1. Використовуй початковий стан регістрів і пам'яті.** Після стандартного завантаження з стрічки регістри мають відомі значення: A часто містить останній завантажений байт, BC -- довжину блоку, HL вказує біля кінця завантажених даних. Область системних змінних ($5C00-$5CB5) містить відомі значення. Екранна пам'ять чиста після CLS. Кожне відоме значення, яке ти використовуєш замість явного завантаження, економить 1-3 байти.

**2. Перетинай код і дані.** Байт $3E -- це опкод `LD A, n`, а також значення 62 -- символ ASCII, координата екрана або значення регістра AY. Якщо твоя програма виконує цей байт як інструкцію *і* читає його як дані з іншого шляху коду, ти змусив один байт виконувати дві роботи. Поширений патерн: безпосередній операнд `LD A, n` подвоюється як дані, які інша процедура читає через `LD A, (addr)`, вказуючи на instruction_address + 1.

**3. Обирай інструкції за розміром.**

| Велике кодування | Мале кодування | Економія |
|-----------------|----------------|----------|
| `CALL $0010` (3 байти) | `RST $10` (1 байт) | 2 байти |
| `JP label` (3 байти) | `JR label` (2 байти) | 1 байт |
| `LD A, 0` (2 байти) | `XOR A` (1 байт) | 1 байт |
| `CP 0` (2 байти) | `OR A` (1 байт) | 1 байт |

Інструкції RST критичні. `RST n` -- це 1-байтний CALL на одну з восьми адрес ($00, $08, $10, $18, $20, $28, $30, $38). На Spectrum `RST $10` викликає виведення символу ROM, `RST $28` входить у калькулятор. У звичайному демо ці ROM-процедури занадто повільні. На 256 байтах збереження 2 байт на CALL -- це все.

**Кожний JP у 256-байтному інтро повинен бути JR** -- вся програма вміщується в діапазон -128..+127.

**4. Самомодифікований код (SMC) для повторного використання послідовностей.** Потрібна підпрограма для роботи з двома різними адресами? Захардкодь першу і пропатч операнд для другого виклику. Дешевше, ніж передача параметрів.

**5. Математичні зв'язки між константами.** Якщо твоїй музиці потрібен період тону 200 і твоєму ефекту потрібен лічильник циклу 200, використовуй той самий регістр. Якщо одне значення вдвічі більше за інше, використовуй `ADD A, A` (1 байт) замість завантаження другої константи (2 байти).

---

## 13.3 Famous 256-Byte Intros: What Made Them Clever

The ZX Spectrum 256-byte category has a rich history. Studying winning entries reveals what kinds of effects fit into 256 bytes and which creative strategies succeed.

**Attribute-based effects dominate.** The reason is arithmetic: the Spectrum's attribute area is 768 bytes (32 x 24), and you can fill it with a computed pattern using a tight nested loop of 15-20 bytes. Pixel-level effects require addressing 6,144 bytes of interleaved screen memory -- much more code for address calculation alone. At 256 bytes, you simply cannot afford the overhead. So the vast majority of 256-byte intros work in attribute space: colour plasmas, interference patterns, gradient animations, colour cycling. The pixel memory either stays blank, gets a one-time dither fill, or is left with whatever the ROM puts there.

**Generative sound beats sequenced sound.** A note table for a melody costs bytes -- even a simple 8-note sequence is 8 bytes, plus the indexing logic. At 256 bytes, the winning strategy is to derive sound from the effect state. Use the frame counter as a tone period (pitch sweeps continuously). Use a byte from the visual computation as a noise parameter. Or use `LD A, R` -- read the Z80's refresh register, which increments on every instruction fetch -- as a pseudo-random source, then mask it to a pentatonic range. The sound will not be a composition, but it will be *present*, and the audience will remember "that tiny intro that had music."

**The ROM is your library.** Every byte of the Spectrum's 16K ROM is available and does not count against your size limit. `RST $10` prints characters using the ROM's full font rendering -- 96 printable characters, 8x8 pixels each, with cursor management. That is thousands of bytes of rendering code available for 1 byte per call. `RST $28` accesses the floating-point calculator, which can compute sine, cosine, and square roots -- operations that would cost dozens of bytes to implement. The cost is speed (the ROM routines are slow), but in a 256-byte intro running at 50fps with a simple effect, you often have cycles to spare.

**The entries that win are the ones that look impossible at their size.** Judges and audiences react to the gap between perceived complexity and file size. A 256-byte intro with a smooth colour plasma and a recognisable melody generates more applause than one with a slightly better visual but no sound. The trick is choosing an effect that *looks* complex but *encodes* cheaply. XOR-based interference patterns are perfect: visually intricate, mathematically trivial. Colour cycling through attributes is another: the eye perceives motion and depth, but the code is just incrementing values in a loop. Diagonal scrolling patterns, checkerboard animations, expanding rings -- all can be produced with fewer than 20 bytes of inner-loop code if the formula is chosen carefully.

---

## 13.4 The LPRINT Trick

У 2015 році diver4d опублікував "Secrets of LPRINT" на Hype, документуючи техніку, старішу за саму демосцену -- таку, що вперше з'явилася у піратських завантажувачах касетного ПЗ у 1980-х.

### Як це працює

Системна змінна за адресою 23681 ($5C81) контролює, куди процедури виведення BASIC направляють дані. Зазвичай вона вказує на буфер принтера. Зміни її так, щоб вона вказувала на екранну пам'ять, і LPRINT записує безпосередньо на екран:

```basic
10 POKE 23681,64: LPRINT "HELLO"
```

Цей єдиний POKE перенаправляє канал принтера на $4000 -- початок екранної пам'яті.

### Ефект транспозиції

Візуальний результат -- це не просто текст на екрані, а *транспонований* текст. Екранна пам'ять Spectrum має черезрядкову розкладку (Розділ 2), але драйвер принтера записує послідовно. Дані потрапляють в екранну пам'ять відповідно до лінійної логіки драйвера, але *відображаються* відповідно до черезрядкової розкладки. Результат циклує через 8 візуальних станів у міру просування через третини екрану -- каскад даних, що будується горизонтальними смугами, зсуваючись і перекомбінуючись.

З різними символьними даними -- графічними символами, UDG або ретельно обраними ASCII-послідовностями -- транспозиція створює вражаючі візуальні патерни. Оператор LPRINT обробляє всю адресацію екрану, рендеринг символів та просування курсору. Твоя програма надає лише дані.

### Від піратських завантажувачів до демо-мистецтва

diver4d простежив цей трюк до піратських завантажувачів касет. Пірати, що додавали власні екрани завантаження, потребували візуальних ефектів у дуже небагатьох байтах BASIC -- LPRINT був ідеальним. Техніка вийшла з ужитку, коли сцена перейшла на машинний код.

Але у 2011 році JtN та 4D випустили **BBB** -- демо, що свідомо повернулося до LPRINT як мистецьке висловлювання. Старий трюк піратських завантажувачів, оформлений з наміром, став демо-мистецтвом. Обмеження -- BASIC, хак з перенаправленням принтера, без машинного коду -- стало медіумом.

### Чому це важливо для sizecoding

LPRINT забезпечує складне виведення на екран при майже нульовій кількості твого власного коду. ROM виконує важку роботу. Твій внесок: POKE для перенаправлення виведення, дані для друку та `RST $10` (або LPRINT) для запуску. Ти використовуєш 16-КБ ROM Spectrum як "безкоштовний" рушій виведення на екран -- код, що не враховується у твоєму ліміті розміру.

---

## 13.5 512-Byte Intros: Room to Breathe

Подвоєння від 256 до 512 байт -- це не вдвічі більше, а якісно інше. На 256 ти борешся за кожну інструкцію і звук мінімальний. На 512 ти можеш мати повноцінний ефект *і* повноцінний звук, або два ефекти з переходом.

### What Each Size Tier Enables

The jump between size categories is not linear. Each doubling opens qualitative new possibilities:

**256 bytes** is one effect and maybe primitive sound. You cannot afford a data table longer than about 16 bytes. Every variable lives in a register or in the instruction stream (self-modifying code). Text output is limited to a few characters. You have room for one nested loop with 2-3 arithmetic operations in the inner body. The visual will be attribute-based, generated purely from arithmetic. Sound, if present, is a tone sweep or random notes.

**512 bytes** lets you add a sine table (32-64 bytes), a real AY music engine (melody + bass on two channels), or a second visual effect with a transition. You can afford a proper frame-counted state machine that switches between two parts. Self-modifying code becomes structural rather than desperate. You might even have room for a short text string (10-20 characters) displayed with `RST $10`.

**1K (1,024 bytes)** is a different world. You can have a tracker-style music player with a compressed pattern (one channel with a 32-step loop takes about 80-120 bytes including the player). Multiple effects with transitions become standard. Pixel-level effects -- simple plasma in pixel space, scrolling text, raster bars -- become feasible because you can afford the screen memory address calculation. You can include a 256-byte sine table, or generate one at startup and keep it in a buffer. At 1K, the constraint still shapes every decision, but the decisions are about *which features to include*, not about *which instructions you can afford*.

**4K and 8K** intros approach the territory of short demos. At 4K, compression becomes viable and you can fit multi-effect compositions with music -- a qualitative leap covered in Section 13.6. An 8K intro is a polished mini-demo where the constraint is more about data compression than instruction-level size tricks. The techniques from this chapter still apply, but the focus shifts from "can I save one byte?" to "can I compress this data stream?"

The sweet spot for learning size-coding is 256 bytes. At that size, every technique in this chapter is mandatory. At 512, you have enough room to choose. At 1K, the size-coding mindset helps but does not dominate.

### Поширені 512-байтні патерни

**Плазма через суми синусних таблиць.** Синусна таблиця -- це дорога частина. Повна 256-байтна таблиця споживає половину твого бюджету. Рішення: 64-елементна чверть-хвильова таблиця з дзеркальним відображенням під час виконання (економить 192 байти), або генерація таблиці при запуску за допомогою параболічної апроксимації з Розділу 4 (~20 байт коду замість 256 байт даних).

**Тунель через пошук кута/відстані.** На 512 байтах ти обчислюєш кут і відстань на ходу, використовуючи грубі апроксимації. Нижча візуальна якість, ніж у тунелі Eager (Розділ 9), але впізнавано тунель.

**Вогонь через клітинний автомат.** Кожна клітина усереднює своїх сусідів знизу, мінус згасання. Кілька інструкцій на піксель, переконлива анімація, і на 512 байтах ти можеш додати атрибути для кольору *та* біперний звук.

### Трюки із самомодифікацією

Самомодифікація стає структурною на 512 байтах. Вбудуй лічильник кадрів *всередину* інструкції:

```z80 id:ch13_self_modifying_tricks
frame_ld:
    ld   a, 0               ; this 0 is the frame counter
    inc  a
    ld   (frame_ld + 1), a  ; update the counter in place
```

Окремої змінної немає. Лічильник живе в потоці інструкцій.

Патч зсувів переходів для перемикання між ефектами:

```z80 id:ch13_self_modifying_tricks_2
effect_jump:
    jr   effect_1               ; this offset gets patched
    ; ...
effect_1:
    ; render effect 1, then:
    ld   a, effect_2 - effect_jump - 2
    ld   (effect_jump + 1), a   ; next frame jumps to effect 2
```

### Трюк з ORG

Обери адресу ORG твоєї програми так, щоб байти адреси самі по собі були корисними даними. Розмісти код за адресою $4000, і кожний JR/DJNZ, що посилається на мітки біля початку, генерує малі байти зсуву -- придатні як лічильники циклів, значення кольорів або номери регістрів AY. Якщо твоєму ефекту потрібен $40 (старший байт екранної пам'яті) як константа, розмісти код за адресою, де $40 природно з'являється в операнді адреси. *Кодування самого коду* надає дані, потрібні деінде.

Це найглибший рівень головоломки sizecoding.

---

## 13.6 4K Intros: The Mini-Demo

4096 bytes is where size-coding transitions from "one trick" to "mini-demo." At 256 bytes, you have room for a single effect and maybe primitive sound. At 512 or 1K, you can have a proper effect with music. At 4K, you can have multiple effects, transitions between them, a full soundtrack, and a coherent narrative arc. The difference between 1K and 4K is qualitative, not just quantitative -- it is the difference between "clever trick" and "tiny production."

### Compression Becomes Viable

The single biggest change at 4K is that data compression pays for itself. A good Z80 decompressor -- ZX0, Exomizer, or similar -- costs roughly 150-200 bytes of code. At 256 or 512 bytes, that overhead is catastrophic. At 4K, it is less than 5% of your budget, and the return is enormous: a 4K intro might contain 6-8K of uncompressed code and data, packed down to fit the limit. Your actual working space nearly doubles.

The workflow becomes a feedback loop: write code, assemble to a raw binary, compress with ZX0, check the output size, iterate. The number that matters is no longer the assembled size -- it is the *compressed* size. This changes your optimisation strategy. You are no longer counting individual instruction bytes. You are thinking about what compresses well.

Code with repetitive patterns compresses better than code with high entropy. A table of sine values compresses well (smooth, predictable). A table of random bytes does not. Effect code that reuses similar instruction sequences across routines compresses better than code where every routine has a unique structure. This is a subtle shift: you optimise not just for *small code* but for *compressible code*.

### Music Fits

At 256 bytes, sound is a luxury -- a tone sweep or random pentatonic notes. At 4K, you can have a real soundtrack. A tiny AY player engine -- something like Beepola's output or a custom minimal tracker -- takes 200-400 bytes. Add 500-1000 bytes of pattern data (compressed) and you have a full three-channel AY composition with melody, bass, and drums. These numbers compress well because music pattern data is highly repetitive.

The impact on the audience is disproportionate. Sound transforms a size-coding entry from a visual curiosity into an *experience*. At compo screenings, intros with music score dramatically higher than silent ones of equal visual quality. If you have 4K to work with and you are not including music, you are leaving points on the table.

### Multi-Effect Structure

Unlike 256 bytes where you are locked into a single visual, 4K gives you room for 2-4 distinct effects with transitions. The structural framework is lightweight: a scene table mapping effect pointers to durations costs perhaps 30 bytes:

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

Each individual effect might run 500-1000 bytes of code. At 4K compressed, you can afford three substantial effects, a scene table, a music player, and transition logic (fade to black between scenes is cheap -- just zero the attribute area).

### GOA4K, inal, and Megademica

**GOA4K** by Exploder^XTM is a landmark ZX Spectrum 128K 4K intro that demonstrates what is achievable when compression meets clever coding. It packs a chunk rotozoomer and other effects into 4096 bytes -- visuals that would be respectable in a full-size demo, compressed down to a size you could fit in a single disk sector.

The story does not end there. **SerzhSoft** took GOA4K and remade it as **inal** -- a 48K-only version in just 2980 bytes. The same visual impact, on a more constrained machine, in fewer bytes. This is the size-coding community at work: one coder sets a bar, another clears it from a harder starting position.

SerzhSoft went on to win the 4K intro compo at **Revision 2019** with **Megademica** -- competing not in a ZX-specific category, but against all platforms at the world's largest demoscene event. A ZX Spectrum 4K intro, judged alongside PC and Amiga entries, took first place. This is the trajectory that 4K size-coding enables: from local scene technique to global recognition.

Studying entries like these reveals a pattern: the best 4K intros choose effects that are visually impressive *and* compress well, then squeeze every byte through a tight pack-test-iterate cycle.

### The 4K Tradeoffs

Working at 4K introduces tradeoffs that do not exist at smaller sizes:

**Compression ratio drives effect choice.** Not all effects compress equally. A plasma that relies on a smooth sine table compresses beautifully -- the table data is predictable, and the rendering loop reuses similar instruction patterns. A pseudo-random dithering effect where every pixel is computed from a different formula produces high-entropy code that barely compresses at all. At 4K, you choose effects partly on their visual merit and partly on how well their implementation packs.

**Boot time is visible.** Decompression takes real time -- typically 1-3 seconds on a 3.5MHz Z80 for a few kilobytes of data. The audience sees a pause before the intro starts. Most 4K intros mask this with a simple loading effect: fill the border with colour cycling, draw a quick pattern in attributes, or flash a single-frame title screen. The decompressor itself runs from a small uncompressed stub at the start of the file. Once decompression finishes, the stub jumps to the unpacked code and the real show begins.

**You optimise for packed size, not runtime speed.** In a 256-byte intro, the same code that runs is the code you measure. At 4K, you write code that decompresses into RAM and then executes from there. ROM constraints disappear -- your unpacked code sits in free RAM. But the optimisation target shifts: you care about how many bytes the packed binary occupies, not the raw assembled size. An effect that assembles to 900 bytes but compresses to 400 is better than one that assembles to 600 but compresses to 500.

**Counting packed bytes.** The build process gains a compression step. Assemble to binary, compress with ZX0 (or your compressor of choice), check the output file size. With sjasmplus:

```sh
sjasmplus --nologo --raw=build/intro4k.bin intro4k.a80
zx0 build/intro4k.bin build/intro4k.zx0
ls -l build/intro4k.zx0    # this is the number that must be <= 4096
```

The decompressor stub prepended to the final file must also fit within the 4096-byte limit. Total file = decompressor stub + compressed payload. A typical ZX0 decompressor is about 70 bytes in its smallest form, leaving roughly 4026 bytes for compressed data.

### Competition Categories

Demoscene parties offer various size-limited categories beyond the classic 256. Common competition tiers include 4K, 8K, and sometimes 16K, alongside the smaller 256 and 512. The specific categories vary by party -- Chaos Constructions, DiHalt, and Forever have all hosted 4K compos for the Spectrum. Some parties combine platforms (a "4K intro" compo accepting entries for any 8-bit platform), while others are Spectrum-specific. Check the party rules before starting -- the measurement method (raw file size vs. loaded memory image) and the exact byte limit matter.

At 8K and 16K, the approach is essentially the same as 4K but with more breathing room. An 8K intro is a polished mini-demo where the compression pipeline is standard and the creative challenge is more about art direction than byte-counting. At 16K, you are essentially making a short demo that happens to fit in 16K -- the size constraint shapes your ambition but does not dictate your instruction choices. The size-coding techniques from this chapter still help at these larger budgets, but their impact is proportionally smaller.

---

## 13.7 Practical: Writing a 256-Byte Intro Step by Step

Почни з працюючої атрибутної плазми (~400 байт) і оптимізуй її до 256.

### Крок 1: Неоптимізована версія

Проста атрибутна плазма: заповни 768 байт пам'яті атрибутів значеннями із сум синусів, зміщеними лічильником кадрів. Звук: циклічна мелодія на каналі A AY. Ця версія чиста, читабельна і приблизно 400 байт -- синусна таблиця (32 байти), таблиця нот (16 байт), інлайнові записи AY та цикл плазми з табличними пошуками.

### Крок 2: Заміни CALL на RST

Будь-який виклик ROM-адреси, що збігається з вектором RST, економить 2 байти за кожне використання. Для виведення AY заміни шість багатослівних інлайнових записів регістрів (~60 байт) невеликою підпрограмою:

```z80 id:ch13_step_2_replace_call_with_rst
ay_write:                      ; register in A, value in E
    ld   bc, $FFFD
    out  (c), a
    ld   b, $BF
    out  (c), e
    ret                        ; 8 bytes total
```

Шість викликів (5 байт кожний: завантаження A + завантаження E + CALL) = 30 + 8 = 38 байт. Економія: ~22 байти.

### Крок 3: Перетини дані з кодом

32-байтна синусна таблиця на точці входу декодується як здебільшого нешкідливі інструкції Z80 ($00=NOP, $06=LD B,n, $0C=INC C...). Розмісти її на початку програми. При першому виконанні процесор спотикається через ці "інструкції", псуючи деякі регістри. Головний цикл потім перестрибує таблицю і більше ніколи не виконує її -- але дані залишаються для пошуків. Байти таблиці виконують подвійну функцію.

### Крок 4: Використовуй стан регістрів

Після того, як цикл плазми записав 768 атрибутів, HL = $5B00 і BC = 0 (від будь-якого LDIR, використаного при ініціалізації). Якщо наступна операція потребує ці значення, пропусти явні завантаження. Відкриття Art-Top у NHBF було саме цим: значення регістрів від очищення екрану збіглися з довжиною текстового рядка. Не заплановано. Помічено.

Після кожного проходу оптимізації анотуй, що кожний регістр містить у кожній точці. Стан регістрів -- це спільний ресурс, фундаментальна валюта sizecoding.

### Крок 5: Менші кодування скрізь

- `LD A, 0` -> `XOR A` (економія 1 байт)
- `LD HL, nn` + `LD A, (HL)` -> `LD A, (nn)` (економія 1 байт, якщо HL не потрібен)
- `JP` -> `JR` скрізь (економія 1 байт кожний)
- `CALL sub : ... : RET` -> пряме проходження (економія 4 байти)
- `PUSH AF` для тимчасових збережень проти `LD (var), A` (економія 2 байти)

### Step 6: Counting Bytes Precisely

Intuition about "how big is this" is unreliable. You need to count. There are three methods, and serious size-coders use all three.

**Assembler output.** sjasmplus can report the assembled size. The `DISPLAY` directive prints to the console during assembly, and `ASSERT` enforces the limit:

```z80 id:ch13_step_6_counting_bytes
intro_end:
    ASSERT intro_end - init <= 256, "Intro exceeds 256 bytes!"
    DISPLAY "Intro size: ", /D, intro_end - init, " bytes"
```

Run the assembler after every change. The DISPLAY line tells you where you stand; the ASSERT catches overflows before you waste time testing a broken binary.

**Symbol file analysis.** Assemble with `--sym=build/intro.sym` to get a symbol table. Compare label addresses to find exactly how many bytes each section occupies. When your intro is 262 bytes and you need to cut 6, the symbol file tells you that the AY init is 22 bytes (can you cut 2?), the effect loop is 38 bytes (can you merge the row and column counters?), the frame counter writeback is 8 bytes (can you restructure to make it 5?). Without this breakdown, you are guessing.

**Hex dump inspection.** After assembling, examine the raw binary in a hex editor (or `xxd build/intro.bin`). The hex dump shows you the actual bytes the CPU will execute. You will spot redundancies invisible in the source: two consecutive loads that could be one, an opcode whose value happens to match data you need elsewhere, a sequence of NOPs left by an accidental alignment. The hex dump is the ground truth. The source is an abstraction over it.

### Фінальний ривок

Останні 10-20 байт -- найскладніші. Структурне перегрупування: зміни порядок коду так, щоб прямі переходи усували інструкції JR. Об'єднай звуковий та візуальний цикли. Вбудуй байти даних у потік інструкцій -- якщо тобі потрібен $07 як дані і також потрібен `RLCA` (опкод $07), розташуй так, щоб один слугував обома.

At this stage, keep a log. Write down every change you try: "moved AY init before pixel fill: saved 2 bytes (C register reuse), lost 1 byte (need extra LD B). Net: +1 byte." Many changes do not help. Some make things worse. Without a log, you will try the same dead-end twice. With a log, you build a map of the solution space.

Try radical restructuring. Can the visual effect loop also update the AY? If the inner loop iterates 768 times (once per attribute cell), and you write a new tone value every 32 iterations (once per row), the sound update happens inside the visual loop at the cost of one `BIT 4, E` / `JR NZ` check -- 4 bytes to merge two routines that previously needed separate framework code. Sometimes merging saves 10 bytes; sometimes it costs 5. You will not know until you try.

**The escape hatch: choose a different effect.** If your plasma needs a sine table and you are 30 bytes over, no amount of micro-optimisation will save you. Switch to an effect that generates its visual from pure register arithmetic: XOR patterns, modular arithmetic, bit manipulation. An XOR interference pattern like the one in `intro256.a80` needs zero data bytes. The visual is less smooth than a sine plasma, but it fits. At 256 bytes, "fits" is the only criterion that matters.

Ти вдивляєшся в шістнадцятковий дамп. Ти пробуєш перемістити звукову процедуру перед візуальною. Ти пробуєш замінити синусну таблицю генератором часу виконання. Кожна спроба перетасовує байти. Іноді все вишиковується.

Задоволення від вміщення цілісного аудіовізуального досвіду у 256 байт -- від розв'язання головоломки -- реальне, специфічне і несхоже на жодне інше відчуття в програмуванні.

---

## 13.8 Size-Coding Music: Bytebeat on AY

In the PC demoscene, **bytebeat** is a formula-driven approach to sound: a single expression like `t*((t>>12|t>>8)&63&t>>4)` generates PCM samples, producing surprisingly complex music from a few bytes of code. The concept was popularised by Viznut (Ville-Matias Heikkilä) in 2011, and 256-byte PC intros routinely use bytebeat for their soundtracks.

On the ZX Spectrum, the situation is different. The AY-3-8910 is not a DAC -- it is a tone and noise generator with per-channel period and volume registers. You cannot feed it PCM samples in the traditional sense (volume-register sample playback exists but costs too many cycles for a size-coded intro). Instead, "AY bytebeat" means computing **tone periods and volume envelopes from mathematical formulas** driven by a frame counter.

The principle is the same as PC bytebeat: replace stored music data with a formula. The output target is different.

### The Minimal AY Formula Engine

A typical approach in a 256-byte intro:

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

This produces a cycling tone that sweeps through periods and fades in/out -- not music in any traditional sense, but recognisably structured sound. The trick is choosing formulas that produce **musically interesting patterns** from simple bitwise operations.

### Techniques for Better-Sounding Formulas

**Pentatonic masking.** Raw bitwise formulas produce chromatic noise. Mask the period value through a pentatonic lookup (5 bytes: the note intervals) to constrain output to a pleasant scale. Five bytes of data buys musically coherent sound.

**Multi-channel formulas.** The AY has three tone channels. Use different bit rotations of the same frame counter for each channel -- they will produce related but distinct patterns, creating an impression of harmony:

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

**Noise percussion.** Toggle the noise generator on specific frame intervals (every 8th or 16th frame) for a rhythmic pulse. Cost: one `AND` + one `OUT` — about 6 bytes for a basic kick pattern.

**LD A,R as entropy.** The R register (memory refresh counter) is effectively random from a musical perspective. Mix it with the frame counter: `ld a,r : xor (frame)` produces evolving textures that never quite repeat. Useful for ambient or experimental soundscapes.

### Bytebeat vs. Sequenced Music

| | Bytebeat (formula) | Sequenced (pattern data) |
|---|---|---|
| **Bytes** | 10-30 (code only) | 200-400 (player) + 500+ (patterns) |
| **Musical quality** | Abstract, generative, alien | Melodic, structured, human |
| **Best at** | 256b, 512b | 1K, 4K |
| **Sound** | Rhythmic noise, sweeps, drones | Actual tunes |

At 256 bytes, bytebeat is your only realistic option -- there is no room for a pattern player. At 512, you can afford a tiny sequencer with 4-8 notes. At 4K, use a real player. The bytebeat approach is not inferior -- it produces a *different kind* of sound that fits the aesthetic of tiny programs. Some of the most memorable 256-byte intros are memorable precisely because their sound is alien and generative, not because it imitates conventional music.

---

## 13.9 Procedural Graphics: The Rendered GFX Compo

Some demoscene parties run a **rendered graphics** (or **procedural graphics**) competition: submit a program that generates a static image. No pre-drawn bitmaps, no loaded data -- every pixel must be computed. The visual output is judged as artwork, but it must be born from code.

On the Spectrum, this means your program fills the 6,912-byte screen area (bitmap + attributes) algorithmically, then halts. The image stays on screen for judging. File size limits vary -- some compos allow any size, others impose 256-byte or 4K limits, turning it into a hybrid of size-coding and digital art.

### Why the Spectrum Is Interesting for This

The Spectrum's display constraints -- 1-bit pixels with 8×8 attribute colour -- make procedural graphics a genuinely different challenge from doing it on a 256-colour VGA or 24-bit framebuffer. You cannot just compute RGB values per pixel. You must think in terms of:

- **Pixel patterns** within 8×8 character cells (dithering, halftone)
- **Attribute colour** per cell (2 colours from a palette of 15)
- **The interaction** between pixel pattern and attribute -- a gradient needs both smooth dithering AND smooth attribute transitions

This constraint creates a distinctive visual style. Procedural Spectrum graphics look like nothing else -- the colour grid gives them a mosaic quality that is part of the aesthetic, not a limitation to hide.

### Common Approaches

**Mandelbrot and Julia sets.** The classic choice. The iteration loop is compact (~30-50 bytes for the core), and the fractal detail is infinite -- zoom coordinates and iteration count are the only parameters. Map iteration count to dither pattern for pixel data, map to palette index for attributes. A Mandelbrot renderer fits comfortably in 256 bytes and produces images that look hand-crafted.

**Interference patterns.** Multiple overlapping sine or cosine waves, sampled at each pixel position. `pixel = sin(x*freq1 + phase1) + sin(y*freq2 + phase2) > threshold`. Produces organic, flowing shapes. On the Spectrum, threshold the sum to get the pixel bit, quantise to get the attribute colour.

**Distance fields.** Compute the distance from each pixel to a set of shapes (circles, lines, Bézier curves). Threshold the distance for pixel data, map it to colour for attributes. A few shapes can produce surprisingly complex images -- overlapping circles alone can create intricate patterns.

**L-systems and fractals.** Recursive branching structures (trees, ferns, Sierpinski triangles). The recursion maps naturally to stack-based Z80 code, and the visual output has organic complexity from minimal code. A Sierpinski triangle renderer is about 20 bytes; a branching tree with random angles is perhaps 80.

### The Byte Budget for Art

In a size-limited rendered GFX compo, every byte goes toward visual complexity. There is no frame loop, no sound, no animation -- just a straight-line program that fills the screen and stops. This means your full budget goes to rendering code and coordinate generation. At 256 bytes, you can produce a detailed fractal. At 4K (compressed), you can generate images with multiple layers, computed textures, and careful dithering that approach hand-drawn quality.

The judging criterion is purely visual -- the audience votes on the image, not the code. But the code constraint shapes the aesthetic. Procedural Spectrum graphics have a recognisable look: mathematical precision, fractal detail, and the characteristic colour grid of attribute-based rendering. The best entries embrace these constraints as style rather than fighting them.

---

## 13.10 Size-Coding as Art

Size-coding teaches you things that improve all your coding: the discipline of questioning every byte sharpens instruction-encoding awareness, the habit of looking for overlaps transfers to any optimisation work, and the practice of exploiting initial state and side effects makes you a better systems programmer.

---

## Підсумок

- **Size-coding** competitions require complete programs in 256, 512, 1K, 4K, or 8K bytes -- strict limits that demand a fundamentally different approach to programming.
- **The size-coder's toolkit** includes register initialization assumptions, DJNZ as a combined decrement-and-branch, RST as a 1-byte CALL, overlapping instructions, and flag abuse via SBC A,A -- tricks that save 1-5 bytes each but compound across a program.
- **NHBF** (UriS, CC 2025) demonstrates the 256-byte mindset: every byte does double duty, register states from one routine feed into the next, instruction choice is driven purely by encoding size.
- **The byte budget** for a typical 256-byte intro allocates ~90-130 bytes to framework (screen fill, AY init, frame sync, loop structure), leaving 120-160 bytes for the actual creative effect.
- **Choosing the right effect** matters more than micro-optimisation: attribute-based visuals with arithmetic formulas (XOR, modular math) encode cheaply; pixel-level effects and data tables consume too many bytes at 256.
- **The LPRINT trick** (diver4d, 2015) redirects BASIC's printer output to screen memory via address 23681, producing complex visual patterns in a handful of bytes -- from pirated cassette loaders to demo art.
- **Each size tier is qualitatively different:** 256 bytes allows one effect with minimal sound; 512 adds sine tables and two-channel music; 1K enables pixel-level effects, tracker music, and multiple parts; 4K crosses the threshold into mini-demo territory with compression, full soundtracks, and multi-effect compositions.
- **4K intros** are where compression becomes viable: a ~200-byte decompressor unlocks 6-8K of working space, music players with pattern data fit comfortably, and scene tables enable 2-4 distinct effects with transitions. The optimisation target shifts from raw assembled size to compressed packed size.
- **AY bytebeat** replaces stored music data with formulas: compute tone periods and volumes from the frame counter using bitwise arithmetic. At 256 bytes, formula-driven sound (10-30 bytes) is the only option; at 4K, switch to a real pattern player. Pentatonic masking, multi-channel bit rotation, and noise percussion add musicality for minimal bytes.
- **Procedural graphics** (rendered GFX) competitions require every pixel to be computed, not loaded. The Spectrum's 1-bit pixels with 8×8 attribute colour make this a unique challenge -- Mandelbrot sets, interference patterns, distance fields, and L-systems all produce distinctive results within the attribute grid aesthetic.
- **The optimisation process** moves from structural changes (eliminating tables, merging loops) to encoding choices (RST for CALL, JR for JP, XOR A for LD A,0) to serendipitous discoveries (register states aligning with data needs).
- **Counting bytes precisely** -- via assembler DISPLAY/ASSERT, symbol file analysis, and hex dump inspection -- is essential. Intuition about code size is unreliable.
- **The ORG trick** -- choosing your load address so that address bytes double as useful data -- represents the deepest level of the puzzle.

---

## Спробуй сам

1. **Почни з великого, скороти до малого.** Напиши атрибутну плазму з лічильником кадрів. Доведи її до робочого стану будь-якого розміру. Потім оптимізуй до 512 байт, відстежуючи кожний збережений байт і як.

2. **Дослідж LPRINT.** У BASIC спробуй `POKE 23681,64 : FOR i=1 TO 500 : LPRINT CHR$(RND*96+32); : NEXT i`. Спостерігай, як транспоновані дані заповнюють екран. Поекспериментуй з різними діапазонами символів.

3. **Картуй стан регістрів.** Напиши невелику програму та анотуй, що кожний регістр містить у кожній точці. Шукай місця, де вихід однієї процедури збігається з потрібним входом іншої.

4. **Вивчи вектори RST.** Дизасемблюй ROM Spectrum за адресами $0000, $0008, $0010, $0018, $0020, $0028, $0030, $0038. Це твої "безкоштовні" підпрограми.

5. **Виклик 256 байт.** Стисни практичну вправу з цього розділу до 256 байт. Тобі доведеться приймати складні рішення про те, що залишити, а що прибрати. У цьому вся суть.

---

*Далі: Розділ 14 -- Стиснення: Більше даних у меншому просторі. Ми переходимо від програм, що вміщуються у 256 байт, до проблеми вміщення кілобайт даних у кілобайти сховища, з комплексним бенчмарком 10 пакувальників від Introspec як нашим путівником.*

> **Джерела:** UriS "NHBF Making-of" (Hype, 2025); diver4d "LPRINT Secrets" (Hype, 2015)
