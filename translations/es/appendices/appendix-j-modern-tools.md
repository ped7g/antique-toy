# Apéndice J: Herramientas modernas para producción retro de demos

> *"La mejor herramienta es la que saca los datos de tu cabeza y los pone en la memoria del Z80 en la menor cantidad de pasos."*

---

## J.1 Dos mundos, una filosofía

La demoscene de PC y la demoscene de Z80 parecen planetas diferentes. En un planeta, los codificadores escriben fragment shaders en GLSL, generan mallas proceduralmente a través de grafos de nodos, y comprimen todo en ejecutables de 64K que renderizan 3D en tiempo real a 60fps en GPUs de consumo. En el otro planeta, los codificadores elaboran rutinas en ensamblador Z80 a mano que encajan catorce efectos en 128K de RAM paginada, contando T-states para asegurar que cada fotograma se renderice en exactamente 71.680 ciclos.

La brecha en capacidad de hardware es enorme. La brecha en filosofía es casi cero.

Ambos mundos adoran la restricción. Una intro de PC de 64K está restringida por el tamaño de archivo tan implacablemente como una demo de ZX Spectrum está restringida por la velocidad de CPU. Un competidor de Shader Showdown escribiendo un raymarcher en 25 minutos enfrenta la misma presión creativa que un codificador de 256 bytes optimizando la reutilización de registros. La generación procedural --- construir contenido desde algoritmos en lugar de almacenarlo como datos --- es la técnica central en ambas plataformas, porque ambas plataformas penalizan los datos y recompensan el cómputo (el PC penaliza los datos almacenados mediante límites de tamaño de archivo; el Spectrum los penaliza mediante límites de memoria).

Este apéndice examina la cadena de herramientas moderna de la demoscene: editores de sincronización, generadores de datos, sintetizadores de música, empaquetadores de ejecutables y herramientas de shaders. La mayoría de estas herramientas apuntan a plataformas x86/GPU y no pueden ejecutarse directamente en un Z80. Pero cumplen tres roles en la producción para ZX Spectrum:

1. **Generadores de datos** --- calculan trayectorias, posiciones de partículas, texturas procedurales en un PC, y luego exportan los resultados como tablas binarias comprimidas que el Z80 reproduce.
2. **Planificadores de sincronización** --- diseñan la relación temporal entre música y visuales en un editor interactivo, y luego exportan números de fotograma y curvas de parámetros a tablas `dw` del Z80.
3. **Entornos de prototipado** --- prueban algoritmos visuales a velocidad completa en una GPU moderna, y luego traducen el algoritmo funcional a ensamblador Z80 sabiendo exactamente cómo debe verse el resultado objetivo.

La filosofía es consistente: **usa cualquier herramienta para la preparación, pero el código de ejecución del Z80 es ensamblador escrito a mano.** La calidad de la demo se juzga por lo que se ejecuta en el Spectrum, no por lo que se ejecuta en el PC de desarrollo. Las herramientas son andamiaje; el edificio es Z80.

---

## J.2 Herramientas de sincronización

### The Sync Problem

La sincronización --- hacer que el evento visual correcto ocurra en el momento musical correcto --- es la parte más difícil de la producción de demos (Capítulo 20). A nivel del Z80, la sincronización es siempre una tabla de datos: números de fotograma emparejados con acciones. La pregunta es cómo determinar esos números de fotograma eficientemente e iterar sobre ellos rápidamente.

Cinco herramientas abordan este problema, cada una con un flujo de trabajo diferente.

### GNU Rocket

**Qué es.** GNU Rocket es un sync-tracker --- un editor tipo tracker donde las columnas representan parámetros con nombre (`camera:x`, `fade:alpha`, `effect:id`) y las filas representan pasos de tiempo (típicamente fotogramas o pulsos musicales). Estableces keyframes en filas específicas y eliges un modo de interpolación entre ellos: **step** (cambio instantáneo), **linear** (tasa constante), **smooth** (ease cúbico in/out), o **ramp** (exponencial). La demo se conecta al editor Rocket vía TCP durante el desarrollo. Recorres la línea de tiempo, editas valores y ves la demo actualizarse en tiempo real.

**Quién lo usa.** Rocket es la herramienta de sincronización estándar de facto en las demoscenes de PC y Amiga. Logicoma, Noice, Loonies, Adapt y docenas de otros grupos lo usan. Ha sido portado a C, C++, C#, Python, Rust y JavaScript.

**Flujo de trabajo con Z80.** Un Z80 de Spectrum no puede ejecutar un cliente TCP, pero el concepto se transfiere directamente:

1. Diseñar pistas de sincronización en Rocket en el PC, recorriendo con la música
2. Exportar datos de keyframes como binario (exportación nativa de Rocket)
3. Ejecutar un convertidor Python: cuantizar floats a punto fijo de 8 bits o 16 bits, emitir tablas `db`/`dw`
4. `INCBIN` las tablas en la demo

El código Z80 simplemente lee una tabla --- sin TCP, sin floats, sin complejidad. Obtienes la experiencia de edición interactiva de Rocket durante el desarrollo, y la sobrecarga mínima de ejecución del Spectrum en el binario final.

**Interpolación.** Los cuatro modos de interpolación de Rocket se mapean limpiamente a la reproducción Z80:
- **Step** -> simplemente usar el valor directamente (0 ciclos de sobrecarga de interpolación)
- **Linear** -> precalcular el delta por fotograma, sumarlo cada fotograma (~20 T-states)
- **Smooth/Ramp** -> hornear la curva interpolada en la tabla exportada (el Z80 lee valores precalculados, sin interpolación en tiempo de ejecución)

Para la mayoría de las demos de ZX Spectrum, hornear todas las curvas a valores por fotograma es el enfoque más simple. Una demo de 3.000 fotogramas (un minuto a 50fps) con 4 parámetros de sincronización consume 12KB de datos sin comprimir --- significativo, pero comprimible a 2--4KB con ZX0.

**Fuente:** `github.com/rocket/rocket` (licencia tipo MIT)

<!-- figure: appj_gnu_rocket -->

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    FIGURE: GNU Rocket sync editor                   │
│                                                                     │
│  Tracker-like grid with named columns:                              │
│  [camera:x]  [camera:y]  [fade:alpha]  [effect:id]                 │
│                                                                     │
│  Rows = frames/time steps. Keyframes shown as bright cells.         │
│  Between keyframes: interpolation curves (step/linear/smooth/ramp)  │
│  visualised as lines connecting values.                             │
│                                                                     │
│  Bottom: transport controls (play, pause, scrub).                   │
│  Connected to running demo via TCP — edit live.                     │
│                                                                     │
│  Screenshot needed: build GNU Rocket from source, create example    │
│  project with 4 tracks, capture at a point showing all 4            │
│  interpolation modes.                                               │
└─────────────────────────────────────────────────────────────────────┘
```

### Vortex Tracker II

**Qué es.** Vortex Tracker II es el editor estándar de ProTracker 3 para la escena del ZX Spectrum. La característica crítica para el trabajo de sincronización es el **contador de fotogramas** en la esquina inferior derecha de la ventana --- muestra el conteo absoluto de interrupciones (número de fotograma) en la posición actual de reproducción.

**Flujo de trabajo de sincronización.** Reproduce el archivo .pt3. Observa el contador de fotogramas. Cuando escuches un golpe, acento o transición de frase al que quieras sincronizar, anota el número de fotograma. Escríbelo en tu tabla de sincronización. Recompila la demo, prueba, ajusta.

Kolnogorov (Vein) describe este como su método principal: "Vortex + editor de vídeo. En Vortex el fotograma se muestra en la esquina inferior derecha --- miraba a qué fotogramas engancharme, creaba una tabla con entradas `dw fotograma, acción`, y sincronizaba a partir de eso."

**El fork VTI.** La comunidad mantiene VTI, un fork de Vortex Tracker II con características adicionales incluyendo precisión de reproducción mejorada y soporte de formato expandido. Para trabajo de sincronización, el VT2 original y VTI son equivalentes --- el contador de fotogramas funciona de la misma manera.

**Limitación.** Iterar es lento. Cada cambio de temporización requiere recompilar la demo y verla desde el principio. Para demos simples con una docena de puntos de sincronización, esto es suficiente. Para demos complejas con cientos de eventos, una herramienta más interactiva (Rocket, Blender) vale el coste de configuración.

<!-- figure: appj_vortex_tracker -->

```text
┌─────────────────────────────────────────────────────────────────────┐
│              FIGURE: Vortex Tracker II — frame counter              │
│                                                                     │
│  VT2 main window with pattern editor visible.                       │
│  Bottom-right: position display showing pattern:row and             │
│  absolute frame number.                                             │
│  Highlight/circle the frame counter.                                │
│                                                                     │
│  Caption: "The frame number in VT2's status bar maps directly to    │
│  the PT3 player's interrupt counter on the Spectrum. What you see   │
│  here is what your sync table references."                          │
│                                                                     │
│  Screenshot needed: open any .pt3 in VTI fork, play to a           │
│  mid-song position, capture with frame number visible.              │
└─────────────────────────────────────────────────────────────────────┘
```

### Blender VSE (Video Sequence Editor)

**Qué es.** El editor de vídeo no lineal integrado en Blender. Para sincronización de demos, proporciona una línea de tiempo donde puedes colocar franjas codificadas por color (una por efecto), importar la pista de música como franja de audio con forma de onda visible, y colocar marcadores en los puntos de sincronización.

**Flujo de trabajo de sincronización:**
1. Capturar cada efecto ejecutándose en el emulador como un clip de vídeo corto (o usar franjas de color sólido como placeholder)
2. Importar los clips y la música (.wav) en el VSE
3. Organizar clips en la línea de tiempo, recorrer para encontrar los puntos de corte perfectos
4. Colocar marcadores (diamantes verdes) en cada evento de sincronización
5. Leer los números de fotograma de las posiciones de los marcadores

El flujo de trabajo visual es potente: *ves* la forma de onda del audio, *ves* dónde golpea el beat, y arrastras el marcador al punto correcto. Sin cálculos, sin conversiones de BPM a fotograma.

**Exportar.** Los marcadores se pueden exportar vía la consola Python de Blender:

```python
for m in bpy.context.scene.timeline_markers:
    print(f"dw {m.frame}, 0  ; {m.name}")
```

Esto genera una tabla de sincronización lista para Z80 directamente. Renombra los marcadores para que coincidan con tus IDs de efecto (`plasma`, `flash`, `scroll`) y la exportación se convierte en una tabla de escenas completa.

**DaVinci Resolve** proporciona capacidades similares (línea de tiempo + marcadores + exportación EDL/CSV) y su versión gratuita es suficiente. Elige la que ya conozcas.

<!-- figure: appj_blender_vse -->

```text
┌─────────────────────────────────────────────────────────────────────┐
│                 FIGURE: Blender VSE — demo storyboard               │
│                                                                     │
│  Timeline with 4-5 colour-coded strips (one per effect):            │
│  [TORUS: blue] [PLASMA: green] [DOTSCROLL: yellow] [ROTOZOOM: red]  │
│                                                                     │
│  Below: audio waveform strip (music.wav)                            │
│  Vertical markers (green diamonds) at sync points.                  │
│  Playhead at a transition point between effects.                    │
│                                                                     │
│  Screenshot needed: create Blender project with dummy strips +      │
│  real AY music exported as WAV. Place ~8 markers at beat hits.      │
└─────────────────────────────────────────────────────────────────────┘
```

### Blender Graph Editor

**Qué es.** El editor de curvas de Blender para propiedades con keyframes. Para trabajo de demos, creas propiedades personalizadas en un objeto (p. ej., `scroll_speed`, `fade_alpha`, `camera_z`) y les pones keyframes para que coincidan con la energía y el fraseo de la música.

**Por qué importa.** El Graph Editor te da control visual e interactivo sobre cómo cambian los parámetros a lo largo del tiempo --- lo mismo que proporciona GNU Rocket, pero integrado en el ecosistema de Blender. Puedes ver múltiples curvas simultáneamente, ajustar la temporización de keyframes arrastrando, y cambiar modos de interpolación (constante, lineal, Bezier) por keyframe.

**Exportar vía API Python:**

```python
for fcurve in bpy.data.actions['SyncAction'].fcurves:
    name = fcurve.data_path.split('"')[1]
    print(f"; {name}")
    for kf in fcurve.keyframe_points:
        print(f"    dw {int(kf.co.x)}, {int(kf.co.y)}")
```

Esto genera datos de sincronización listos para Z80 directamente. El proyecto de Blender se convierte en tu storyboard, tu referencia de sincronización y tu pipeline de datos en un solo archivo.

<!-- figure: appj_blender_graph -->

```text
┌─────────────────────────────────────────────────────────────────────┐
│              FIGURE: Blender Graph Editor — keyframe export         │
│                                                                     │
│  Graph with X = frame number, Y = parameter value.                  │
│  3 curves: scroll_speed (smooth ease-in), fade_alpha (step at       │
│  transitions), camera_z (linear ramp).                              │
│                                                                     │
│  Annotation showing the Python export:                              │
│  for kf in fcurve.keyframe_points:                                  │
│      print(f"dw {int(kf.co.x)}, {int(kf.co.y)}")                   │
│                                                                     │
│  Arrow pointing to resulting Z80 data:                              │
│  dw 0, 0  /  dw 50, 128  /  dw 150, 255  /  ...                    │
│                                                                     │
│  Screenshot needed: same Blender project, switch to Graph Editor    │
│  view with 3 animated custom properties.                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Motion Canvas

Una mención breve: **Motion Canvas** es una herramienta emergente, con licencia MIT, basada en TypeScript para crear animaciones paramétricas programáticamente. Está diseñada para vídeos explicativos pero su enfoque de línea-de-tiempo-como-código podría servir como herramienta de planificación de sincronización para codificadores que prefieren escribir código a arrastrar keyframes. Todavía en desarrollo temprano; sigue el proyecto en `motioncanvas.io`.

### Comparison Table

| Herramienta | Licencia | Método de sincronización | Ruta de exportación Z80 | ¿Interactivo? |
|-------------|----------|-------------------------|------------------------|---------------|
| GNU Rocket | Tipo MIT | Pistas con keyframes + interpolación | Binario -> Python -> tablas `dw` | Sí (edición en vivo TCP) |
| Vortex Tracker II | Freeware | Lectura del contador de fotogramas | Manual (anotar números de fotograma) | Parcial (escuchar + anotar) |
| Blender VSE | GPL | Marcadores de línea de tiempo + forma de onda | Python -> tablas `dw` | Sí (recorrido visual) |
| Blender Graph Editor | GPL | Curvas con keyframes | API Python -> tablas `dw` | Sí (edición visual de curvas) |
| DaVinci Resolve | Gratis/Comercial | Marcadores de línea de tiempo | EDL/CSV -> Python -> tablas `dw` | Sí (recorrido visual) |
| Motion Canvas | MIT | Línea de tiempo definida por código | Exportación TypeScript (personalizada) | Programático |

---

## J.3 Pre-visualización y storyboarding

Antes de escribir una sola línea de ensamblador Z80, necesitas saber cómo se ve la demo. No en detalle --- no cada elección de paleta o velocidad de scroll --- sino la estructura general: qué efectos, en qué orden, durante cuánto tiempo, con qué transiciones. Esto es pre-visualización, y ahorra más tiempo que cualquier optimización de código.

### Blender as Storyboard Tool

El **Grease Pencil** de Blender (ahora completamente integrado como sistema de dibujo 2D) te permite esbozar representaciones aproximadas de cada efecto --- rectángulos de colores, formas simples, aproximaciones dibujadas a mano. No necesitan parecerse a los efectos finales. Necesitan comunicar: "aquí, durante estos segundos, pasa algo azul y arremolinado."

Un enfoque práctico:
1. Crear un objeto Grease Pencil por efecto (rectángulo de color con el nombre del efecto)
2. Organizarlos en la línea de tiempo del VSE con la pista de música
3. Reproducir y observar la estructura

No estás haciendo un animatic. Estás haciendo un *cronograma* --- una representación visual de qué efecto se ejecuta cuándo, y durante cuánto tiempo. Los colores te ayudan a detectar problemas estructurales: tres efectos azules lentos seguidos significa que el ritmo está mal. Un tramo de 45 segundos sin transición significa que el público se aburre.

### Video Editors for Rough-cut Assembly

Una vez que tengas efectos funcionando en un emulador, captúralos como clips de vídeo (OBS Studio, grabador de pantalla, o funciones de grabación del emulador). Importa los clips en un editor de vídeo --- DaVinci Resolve, Blender VSE, o incluso iMovie --- y organízalos en una línea de tiempo con la música.

Este corte preliminar revela problemas que son invisibles en el código:
- Un efecto que se ve impresionante aislado pero dura demasiado en contexto
- Una transición que debería ocurrir en el beat pero cae entre beats
- Dos efectos consecutivos con paletas de colores similares que se funden
- Una sección donde la energía visual cae mientras la música sube

El corte preliminar cuesta una hora de trabajo. Ahorra días de ajustes de temporización a nivel de ensamblador.

### The GABBA Workflow

El enfoque de diver4d para GABBA (2019) llevó esto más lejos: usó **Luma Fusion**, un editor de vídeo para iOS, como su herramienta principal de planificación de sincronización. El flujo de trabajo fue:

1. Codificar cada efecto individualmente, probar en emulador
2. Grabar la pantalla de cada efecto ejecutándose
3. Importar grabaciones + música en Luma Fusion en un iPad
4. Organizar en la línea de tiempo, recorrer fotograma a fotograma para encontrar puntos de sincronización
5. Anotar los números de fotograma, escribir tabla de sincronización

La idea clave: la sincronización a nivel de fotograma es un problema de *edición de vídeo*, no un problema de *programación*. Al resolverlo en una herramienta diseñada para edición de vídeo, diver4d pudo iterar sobre la temporización en segundos en lugar de minutos. El código Z80 era la capa de implementación; las decisiones creativas ocurrían en el editor de vídeo.

### Kolnogorov on Sync Planning

Kolnogorov (Vein) articula el enfoque combinado: "Exporté los clips de efectos a vídeo, los ensamblé en un editor de vídeo, adjunté la pista de música, y miré en qué orden funcionan mejor los efectos, anotando los fotogramas donde deben ocurrir los eventos."

La palabra importante es *miré*. Este es un proceso visual e intuitivo. *Ves* dónde el beat golpea la forma de onda. *Ves* dónde la transición del efecto se siente correcta. Y lees el número de fotograma. Sin cálculos, sin conversiones de BPM a fotograma.

---

## J.4 Motores de generación de datos

Una demo de ZX Spectrum reproduce datos precalculados a 50fps. La pregunta es: ¿dónde calculas esos datos? Para tablas de seno simples y coordenadas Bresenham, un script Python es suficiente. Para trayectorias 3D complejas, movimiento orgánico de partículas o gestos capturados por VR, necesitas un entorno más potente.

### Unity as a Data Generator

Unity no es excesivo para demos de ZX Spectrum --- es excesivo como *motor de demo*, pero perfecto como *generador de datos*. La distinción importa.

**Captura de movimiento VR.** El XR Toolkit de Unity captura la posición del controlador VR a 90Hz. Dibuja una trayectoria en el aire con un controlador VR --- el movimiento orgánico que obtienes de un gesto de mano es imposible de replicar con fórmulas matemáticas. Reduce la tasa de muestreo a 50fps, cuantiza a valores con signo de 8 bits, codifica por deltas, comprime. Una trayectoria de 5 segundos dibujada a mano se convierte en 250 bytes de datos empaquetados que *se sienten vivos* en el Spectrum.

**Sistemas de partículas GPU.** El VFX Graph de Unity ejecuta millones de partículas en la GPU. Prototipa una fuente de partículas, un vórtice o una simulación de bandada, y luego exporta las posiciones de partículas por fotograma como CSV. En el Spectrum, trazas esas posiciones como puntos o celdas de atributos. La simulación de física que tomaría meses implementar en Z80 se ejecuta en milisegundos en una GPU.

**Prototipado de shaders.** Escribe un plasma, túnel o rotozoomer como fragment shader en el ShaderGraph de Unity. Itera en tiempo real a resolución completa hasta que se vea bien. Luego traduce el algoritmo a Z80, sabiendo exactamente cómo debe verse el resultado visual.

### Unreal Engine as a Data Generator

Unreal ofrece capacidades equivalentes a través de diferentes herramientas:
- **OpenXR** para captura de movimiento VR
- **Niagara** para sistemas de partículas GPU
- **Material Editor** para prototipado de shaders

La elección entre Unity y Unreal para generación de datos es cuestión de familiaridad. Ambos exportan a los mismos formatos (CSV, arrays binarios). Ambos proporcionan más potencia computacional de la que jamás necesitarás para generar datos de demo Z80.

### Blender as a Data Generator

Para la mayoría de las tareas de generación de datos, Blender es suficiente y completamente de código abierto:

- **Geometry Nodes** para trayectorias procedurales --- define una ruta como spline, distribuye puntos a lo largo, anima con ruido, exporta posiciones de vértices por fotograma
- **Grease Pencil** para animación dibujada a mano --- dibuja fotogramas, exporta coordenadas de puntos
- **API Python** para exportación directa --- accede a cualquier propiedad animada desde `bpy.data`
- **Simulación de física** para partículas, tela, fluidos --- simula, hornea, exporta datos por fotograma

Blender no puede hacer captura de movimiento VR (sin addons de terceros) y su sistema de partículas funciona en CPU (más lento que los sistemas basados en GPU para millones de partículas). Para todo lo demás, iguala o supera a Unity/Unreal para propósitos de generación de datos.

### The Export Pipeline

Independientemente de qué herramienta genere los datos, el pipeline al Z80 sigue las mismas etapas:

```text
Source tool (Unity/Unreal/Blender)
  → Export: float arrays (CSV, JSON, or binary)
    → Python: float → 8-bit fixed-point (or 16-bit where needed)
      → Delta-encode: store differences between frames (smaller values)
        → Transpose: column-major layout (all X values, then all Y values)
          → packbench analyze: verify entropy, check suggested transforms
            → zx0/pletter: compress
              → sjasmplus: INCBIN into demo
```

Cada etapa reduce el tamaño de los datos:

| Etapa | Tamaño ejemplo (250 fotogramas x 4 parámetros) |
|-------|------------------------------------------------|
| CSV flotante | ~10 KB |
| Punto fijo de 8 bits | 1.000 bytes |
| Codificado por deltas | 1.000 bytes (los valores se reducen, mejor ratio de compresión) |
| Transpuesto + comprimido | 300-500 bytes |

Las etapas de codificación por deltas y transposición no reducen el tamaño bruto --- reformatean los datos para que se compriman mejor. La disposición por columnas agrupa valores similares (todos los deltas X, luego todos los deltas Y), lo que se comprime dramáticamente mejor que la disposición por filas donde los deltas X e Y se alternan.

### When to Use Which

| Necesidad | Herramienta | Por qué |
|-----------|-------------|---------|
| Tablas de seno, tablas de consulta | Script Python | Lo más simple, sin dependencias |
| Trayectorias 3D procedurales | Blender (Geometry Nodes) | Gratis, visual, exportación Python |
| Rutas de animación dibujadas a mano | Blender (Grease Pencil) | Dibujar directamente, fotograma a fotograma |
| Captura de gestos VR | Unity (XR Toolkit) o Unreal (OpenXR) | Necesita hardware VR + runtime |
| Posiciones de partículas GPU | Unity (VFX Graph) o Unreal (Niagara) | Millones de partículas, rápido |
| Prototipo de algoritmo shader | Cualquiera (ShaderToy, Unity, Unreal, Blender) | La que conozcas |

Las animaciones vectoriales precalculadas de Kolnogorov son un caso ilustrativo: la geometría 3D se calculó offline (minutos de cálculo son aceptables para una intro de 4K), las trayectorias de vértices resultantes se almacenaron como tablas comprimidas, y el Spectrum las reprodujo a 50fps. La herramienta que generó las trayectorias es irrelevante para el público. Lo que importa es que los datos existen y el Z80 los reproduce.

---

## J.5 La cadena de herramientas de la demoscene de PC: Una breve historia

La demoscene de PC ha pasado veinticinco años construyendo herramientas para la generación procedural de contenido y la compresión extrema. Estas herramientas no pueden ejecutarse en un Z80, pero su filosofía de diseño --- todo procedural, lo pequeño es bello, la restricción como creatividad --- refleja exactamente lo que los codificadores de ZX Spectrum hacen a mano. Entender la cadena de herramientas de PC te ayuda a reconocer qué problemas se han resuelto (en diferentes contextos) y qué ideas puedes adaptar.

### Farbrausch (1999--2012)

**Farbrausch** fue un grupo demoscene alemán que redefinió lo que era posible en ejecutables de 64K y 4K. Su enfoque: construir herramientas que generan todo proceduralmente, y luego empaquetar los generadores en ejecutables diminutos.

**Werkkzeug** (versiones 1 a 4) fue su herramienta principal --- un sistema procedural basado en nodos donde texturas, mallas, animaciones y composiciones se definían como grafos de operadores. No se almacenaban bitmaps; cada píxel se calculaba en tiempo de ejecución a partir de una receta de operaciones matemáticas. La herramienta era usada internamente por Farbrausch; el público solo veía los ejecutables resultantes.

Producciones notables construidas con Werkkzeug:
- **fr-08: .the .product** (2000) --- un vídeo musical 3D en tiempo real en 64KB que redefinió la categoría de intros de 64K. Ganó la compo de demos en The Party 2000.
- **.kkrieger** (2004) --- un shooter en primera persona en 97.280 bytes. Texturas, mallas, animaciones, IA y sonido, todo generado proceduralmente. El ejecutable es más pequeño que el archivo fuente de este apéndice.
- **fr-041: debris.** (2007) --- una demo cinemática de 177KB que empujó la calidad de renderizado en tiempo real más allá de lo que muchas demos de tamaño completo lograban. Ganó en Breakpoint 2007.

**kkrunchy** fue su empaquetador de ejecutables para intros de 64K --- un compresor de mezcla de contexto que lograba ratios de compresión muy por encima de empaquetadores estándar como UPX. kkrunchy todavía es usado activamente por codificadores de intros de 64K hoy, más de una década después de la disolución de Farbrausch.

**V2 Synthesizer** fue un sintetizador de software diseñado para intros --- un plugin VSTi para composición, con un reproductor runtime diminuto que cabía dentro del ejecutable empaquetado. La música se almacenaba como datos de notas y parámetros de síntesis, no como audio.

En 2012, Farbrausch liberó toda su cadena de herramientas como código abierto bajo una licencia tipo BSD: `github.com/farbrausch/fr_public`. El repositorio incluye Werkkzeug (todas las versiones), kkrunchy, V2 y varias otras herramientas. El código es una cápsula del tiempo de la ingeniería de demoscene de principios de los 2000: C++ denso, APIs Win32, Direct3D 9, y soluciones creativas a problemas que las GPUs modernas resuelven con fuerza bruta.

**Relevancia para Z80.** El equivalente en ZX Spectrum de las texturas procedurales de Werkkzeug es tu script Python de compilación que genera tablas de consulta a partir de funciones matemáticas. El equivalente de kkrunchy es ZX0 o Pletter. El equivalente de V2 es AY-beat o el reproductor AY de Shiru. Diferente escala, mismo principio: generar contenido a partir de descripciones compactas, comprimir el resultado, descomprimir en tiempo de ejecución.

### TiXL (2024--present)

**TiXL** (anteriormente Tooll3) es el sucesor espiritual de Werkkzeug, desarrollado por **Still** (pixtur/Thomas Mann) --- un demoscener que ha trabajado con miembros de Farbrausch y ha llevado adelante el enfoque procedural basado en nodos.

TiXL es un entorno de motion graphics en tiempo real construido sobre APIs GPU modernas. Como Werkkzeug, usa un grafo de nodos para definir contenido procedural, pero con 20 años de evolución GPU detrás: compute shaders, renderizado basado en física, partículas GPU y raymarching en tiempo real.

Con licencia MIT (`github.com/tixl3d/tixl`), TiXL muestra hacia dónde ha evolucionado la filosofía de Werkkzeug. El concepto de grafo de nodos --- definir contenido como una receta de operaciones en lugar de almacenarlo como datos --- es directamente aplicable al desarrollo de demos Z80, aunque las operaciones específicas sean completamente diferentes.

<!-- figure: appj_tixl_nodes -->

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    FIGURE: TiXL node graph                          │
│                                                                     │
│  Visual programming canvas with connected nodes:                    │
│  [Time] → [Sine] → [Multiply] → [SetFloat]                        │
│                                                                     │
│  A procedural texture pipeline:                                     │
│  [Noise3D] → [Remap] → [ColorGrade] → [RenderTarget]              │
│                                                                     │
│  3D scene graph:                                                    │
│  [Mesh:Torus] → [Transform] → [Material] → [DrawMesh]             │
│  [Camera] → [Render] → [PostFX:Bloom] → [Output]                  │
│                                                                     │
│  Right panel: live preview of the rendered output.                  │
│  Bottom: timeline with playback controls.                           │
│                                                                     │
│  Caption: "TiXL (MIT, 2024) carries forward the Werkkzeug           │
│  philosophy of node-based procedural content generation. The         │
│  Z80 equivalent is a Python build script that generates lookup       │
│  tables and compressed data from mathematical functions."            │
│                                                                     │
│  Screenshot needed: install TiXL, open an example project,          │
│  capture the node graph + preview in a split view.                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Bonzomatic

**Bonzomatic** (de Gargaj / Conspiracy) es la herramienta estándar para competiciones de **Shader Showdown** --- batallas de codificación de shaders en vivo en parties de demoscene. Dos codificadores comparten un escenario, cada uno escribiendo un fragment shader desde cero en 25 minutos, con el código y la salida proyectados lado a lado para el público.

Bonzomatic proporciona un editor mínimo con una ventana de previsualización en vivo. Cada pulsación de tecla recompila el shader; la salida se actualiza en tiempo real. No hay guardado, no hay historial de deshacer más allá del búfer del editor, y no hay bibliotecas. Es creatividad pura impulsada por restricciones --- el mismo espíritu que la codificación de 256 bytes en el Spectrum.

**Fuente:** `github.com/Gargaj/Bonzomatic`

### Crinkler

**Crinkler** (de Rune Stubbe y Aske Simon Christensen / Loonies) es un **enlazador compresor** para ejecutables de Windows. Donde un enlazador normal produce un .exe y lo comprimes por separado, Crinkler combina enlazado y compresión en un solo paso, logrando ratios de compresión que ningún empaquetador separado puede igualar.

Crinkler es el estándar para intros de PC de 1K, 4K y 8K. Su compresión es tan efectiva que los codificadores miden rutinariamente su trabajo en "bytes Crinkler" --- el tamaño final empaquetado, que puede ser 60--70% del código + datos sin comprimir.

El paralelo Z80: ZX0 y Pletter cumplen el mismo rol para demos de Spectrum, aunque los ratios de compresión son más modestos (el código Z80 tiene menos redundancia que x86).

**Fuente:** `github.com/runestubbe/Crinkler` (licencia zlib)

### Squishy

**Squishy** (de Logicoma) es un empaquetador de ejecutables de 64K --- el equivalente de kkrunchy para intros modernas de 64K. A diferencia de Crinkler (que maneja intros diminutas), Squishy apunta a la clase de tamaño de 64KB donde el ejecutable contiene código de shader sustancial, rutinas de generación de texturas y música.

Distribución solo binaria; no hay código fuente disponible. Se menciona aquí porque las intros de 64K de Logicoma (Happy Coding, Elysian, H - Immersion) representan el estado del arte actual en la categoría de 64K, y Squishy es parte de ese pipeline.

### Shader Minifier

**Shader Minifier** (de Ctrl-Alt-Test) es un minificador de GLSL/HLSL que renombra variables, elimina espacios en blanco y optimiza código de shader para tamaño mínimo. Se usa en intros con restricción de tamaño donde cada byte de código fuente de shader cuenta (los shaders se almacenan frecuentemente como cadenas en el ejecutable y se compilan en tiempo de ejecución).

**Fuente:** `github.com/laurentlb/shader-minifier`

### z80-optimizer

**z80-optimizer** (de oisee, 2025) es un superoptimizador Z80 de fuerza bruta escrito en Go. Enumera cada par de instrucciones Z80 (406 x 406 opcodes), prueba cada par contra todos los posibles estados de registros y banderas, e informa cuando un reemplazo más corto o más rápido produce una salida idéntica. Sin heurísticas, sin aprendizaje automático -- búsqueda exhaustiva pura con verificación completa de equivalencia de estados.

Una sola ejecución en un Apple M2 (3h 16m, 34.700 millones de comparaciones) produce **602.008 reglas de optimización demostrablemente correctas** en **83 patrones de transformación únicos**. Ejemplos: `SLA A : RR A` -> `OR A` (ahorra 3 bytes, 12T); `LD A, 0 : NEG` -> `SUB A` (ahorra 2 bytes); `SCF : RR A` -> `SCF : RRA` (ahorra 1 byte, 4T). Crucialmente, rechaza correctamente `LD A, 0` -> `XOR A` porque el comportamiento de las banderas difiere -- el tipo de distinción sutil que las tablas de peephole mantenidas manualmente a veces se equivocan.

Útil como paso de post-procesamiento para código Z80 generado por compilador, o como referencia para optimización manual. La salida es una base de datos de reglas legible por máquina que puede integrarse en cadenas de herramientas de ensamblador. Ver Capítulo 23 para discusión de enfoques de fuerza bruta vs redes neuronales para optimización Z80.

**Fuente:** `github.com/oisee/z80-optimizer` (licencia MIT, v0.1.0)

### The Common Philosophy

Todas estas herramientas comparten un principio que se traduce directamente al trabajo con Z80: **la generación procedural supera a los datos almacenados.** En el PC, esto significa generar texturas a partir de funciones de ruido en lugar de almacenar bitmaps. En el Spectrum, significa calcular una tabla de seno a partir de una aproximación parabólica en lugar de almacenar 256 bytes de valores precalculados. El hardware difiere por un factor de un millón; el enfoque es el mismo.

---

## J.6 Herramientas de música y sonido

La demoscene de PC necesita sintetizadores diminutos --- instrumentos de software que caben dentro de un ejecutable de 4K o 64K mientras producen música que suena profesional. La escena Z80 necesita trackers para AY-3-8910. Hay algo de solapamiento.

### Sointu

**Sointu** es un sintetizador para intros de 4K --- un fork de 4klang reescrito en Go para soporte multiplataforma. Proporciona una interfaz tipo VST para diseñar patches (osciladores, filtros, envolventes, efectos) y un compilador que genera un reproductor nativo mínimo.

El código del reproductor está diseñado para tamaño extremo: todo el runtime del sintetizador, incluyendo todas las definiciones de instrumentos y datos de notas, cabe en menos de 4KB de código + datos x86. Esto lo hace el equivalente PC de lo que AY-beat (Capítulo 13) logra en el Spectrum: máximo sonido con mínimos bytes.

**Fuente:** `github.com/vsariola/sointu` (licencia MIT)

### 4klang

**4klang** (de Alcatraz) es el sintetizador original para intros de 4K del que Sointu hizo fork. Proporciona un plugin VSTi para composición y un modo de salida de ensamblador que genera código fuente NASM para el reproductor --- el sintetizador está literalmente escrito en ensamblador x86, optimizado para tamaño.

4klang definió el estándar para música de intros de 4K y sigue en uso activo junto a su sucesor Sointu.

**Fuente:** `github.com/gopher-atz/4klang`

### WaveSabre

**WaveSabre** (de Logicoma) apunta a intros de 64K --- una clase de tamaño mayor donde el sintetizador puede ser más sofisticado. Proporciona instrumentos compatibles con VST con reverb, delay, chorus, distorsión y otros efectos que los sintetizadores de 4K deben omitir. El reproductor runtime es lo suficientemente compacto para 64K pero demasiado grande para 4K.

WaveSabre impulsa la música de las intros de 64K galardonadas de Logicoma (Happy Coding, Elysian).

**Fuente:** `github.com/logicomacorp/WaveSabre` (licencia MIT)

### Oidos

**Oidos** (de Blueberry / Loonies) adopta un enfoque fundamentalmente diferente: síntesis aditiva. Donde la mayoría de los sintetizadores construyen sonidos a partir de osciladores y filtros, Oidos los construye a partir de sumas de ondas senoidales con frecuencias y amplitudes controladas individualmente. El resultado es un sonido distintivo y rico que ocupa un espacio sónico único en intros de 4K.

**Fuente:** `github.com/askeksa/Oidos`

### Furnace

**Furnace** es un tracker chiptune multi-sistema que soporta más de 80 chips de sonido --- incluyendo el **AY-3-8910**. Esto lo hace directamente relevante para la producción de demos de ZX Spectrum: puedes componer música AY en Furnace usando una interfaz moderna con características que Vortex Tracker II carece (deshacer, múltiples pestañas, editor visual de envolventes, osciloscopio por canal).

Los chips adicionales soportados incluyen el SN76489 (Sega Master System, BBC Micro), YM2612 (Mega Drive), SID (C64), Pokey (Atari) y muchos otros. Si trabajas en proyectos retro multiplataforma, Furnace es el único tracker que cubre todos los objetivos.

**Formatos de exportación.** Furnace puede exportar a formato VGM (Video Game Music), que captura escrituras de registros crudas por fotograma. Para el AY-3-8910, esto significa que obtienes un flujo de volcados de registros de 14 bytes a 50/60Hz --- directamente utilizable en el Spectrum con un reproductor mínimo que escribe registros en cada interrupción. Scripts de exportación personalizados pueden convertir VGM a PT3 o a tablas de registros crudas para INCBIN.

**Limitación.** La emulación AY de Furnace es buena pero no idéntica a la reproducción PT3 de Vortex Tracker. Si tu demo usa un reproductor PT3, compón en Vortex Tracker para reproducción garantizada 1:1. Usa Furnace cuando quieras una experiencia de edición moderna y estés dispuesto a manejar conversión de formato, o cuando apuntes al AY directamente con escrituras de registros crudas.

**Fuente:** `github.com/tildearrow/furnace` (GPL-2.0)

### Comparison Table

| Herramienta | Clase de tamaño | Licencia | Relevancia Z80 |
|-------------|----------------|----------|----------------|
| Sointu | Intros de 4K | MIT | Conceptual (misma restricción que AY-beat) |
| 4klang | Intros de 4K | OSS | Conceptual |
| WaveSabre | Intros de 64K | MIT | Conceptual |
| Oidos | Intros de 4K | OSS | Conceptual |
| Furnace | Cualquiera | GPL-2.0 | **Directa** --- soporte AY-3-8910, exportación VGM |
| Vortex Tracker II | Cualquiera | Freeware | **Directa** --- PT3 nativo, estándar ZX |

---

## J.7 Recetas prácticas

Cinco flujos de trabajo paso a paso que conectan herramientas modernas con ensamblador Z80. Cada receta comienza desde un proyecto en blanco y termina con datos que puedes incluir con `INCBIN` en una demo.

### Recipe 1: GNU Rocket → Z80 Sync Table

**Objetivo:** Diseñar curvas de sincronización interpoladas en Rocket, exportar como tablas `dw` de Z80.

**Pasos:**

1. **Instalar Rocket.** Clonar `github.com/rocket/rocket`, compilar desde código fuente (CMake). Ejecutar el editor.

2. **Crear pistas.** Añadir cuatro pistas: `effect:id`, `fade:alpha`, `scroll:speed`, `flash:border`. Establecer el BPM para que coincida con tu música (p. ej., 125 BPM a 50fps = 24 fotogramas por beat).

3. **Establecer keyframes.** En la fila 0: `effect:id` = 0 (logo), `fade:alpha` = 255. En la fila 150: `effect:id` = 1 (plasma), `fade:alpha` rampa de 255 a 0 (interpolación smooth). Continuar para toda la duración de la demo.

4. **Exportar.** Usar el exportador de sincronización de Rocket (o la herramienta `sync_export`) para escribir archivos binarios por pista.

5. **Convertir con Python:**

```python
import struct

def rocket_to_z80(track_file, output_file):
    with open(track_file, 'rb') as f:
        data = f.read()
    # Rocket binary: array of (row: u32, value: float32) pairs
    pairs = []
    for i in range(0, len(data), 8):
        row, val = struct.unpack('<If', data[i:i+8])
        pairs.append((row, max(0, min(255, int(val)))))

    with open(output_file, 'w') as f:
        for row, val in pairs:
            f.write(f"    dw {row}, {val}\n")
        f.write("    dw 0  ; end marker\n")

rocket_to_z80('effect_id.track', 'sync_effect.inc')
```

6. **Incluir en la demo:**

```z80
sync_effect:
    INCLUDE "sync_effect.inc"
```

**Opción de horneado.** Para interpolación suave sin coste en tiempo de ejecución, expandir los keyframes a valores por fotograma:

```python
# Interpolate between keyframes, output one value per frame
for frame in range(total_frames):
    value = interpolate(keyframes, frame)  # linear, smooth, or ramp
    print(f"    db {max(0, min(255, int(value)))}")
```

Una pista de 3.000 fotogramas horneada a valores `db` por fotograma = 3.000 bytes sin comprimir, ~800 bytes después de ZX0.

### Recipe 2: Blender VSE → Frame Number Table

**Objetivo:** Planificar la estructura de la demo visualmente con música, exportar puntos de sincronización.

**Pasos:**

1. **Crear proyecto Blender.** Establecer la tasa de fotogramas a 50fps (Propiedades -> Salida -> Frame Rate -> 50). Establecer la longitud de la línea de tiempo para que coincida con tu música.

2. **Importar música.** Añadir -> Sonido en el VSE. Importar tu .pt3 exportado como .wav (usar "Archivo -> Exportar a WAV" de Vortex Tracker). La forma de onda aparece en la línea de tiempo.

3. **Añadir franjas de efectos.** Añadir -> franjas de Color para cada efecto. Nombrarlas (plasma, scroll, torus). Codificarlas por color. Organizar en la línea de tiempo para que cubran toda la duración de la demo.

4. **Colocar marcadores.** Recorrer la línea de tiempo. Cuando escuches un beat o punto de transición, pulsa M para añadir un marcador. Renombrar cada marcador: `plasma_start`, `flash_1`, `scroll_begin`, etc.

5. **Exportar vía consola Python:**

```python
import bpy

# Print sync table
print("; Auto-generated sync table from Blender VSE")
print("sync_table:")
for m in sorted(bpy.context.scene.timeline_markers,
                key=lambda x: x.frame):
    print(f"    dw {m.frame}  ; {m.name}")
print("    dw 0  ; end marker")
```

6. **Copiar la salida a tu archivo .inc del proyecto.** Recompilar la demo con `make`.

7. **Iterar.** Ver la demo, anotar dónde la temporización se siente mal, volver a Blender, ajustar marcadores, re-exportar. Cada iteración toma segundos.

### Recipe 3: Unity VR → Trajectory Data

**Objetivo:** Capturar una trayectoria 3D dibujada a mano usando un controlador VR, exportar como datos Z80 comprimidos.

**Pasos:**

1. **Configurar proyecto Unity.** Crear nuevo proyecto 3D, instalar XR Toolkit vía Package Manager. Configurar para tu headset (Quest, Index, etc.).

2. **Grabar ruta del controlador.** Crear un script que capture `transform.position` del controlador derecho cada fotograma:

```csharp
void Update() {
    positions.Add(new Vector3(
        controller.transform.position.x,
        controller.transform.position.y,
        controller.transform.position.z
    ));
}
```

3. **Exportar CSV.** Al finalizar la grabación, escribir las posiciones a CSV:

```csharp
File.WriteAllLines("trajectory.csv",
    positions.Select(p => $"{p.x},{p.y},{p.z}"));
```

4. **Convertir con Python:**

```python
import csv

with open('trajectory.csv') as f:
    rows = list(csv.reader(f))

# Downsample from 90Hz to 50Hz
factor = 90 / 50
resampled = [rows[int(i * factor)] for i in range(int(len(rows) / factor))]

# Quantise to signed 8-bit (-128..127)
def q8(val, scale=64.0):
    return max(-128, min(127, int(float(val) * scale)))

# Delta-encode
prev = [0, 0, 0]
deltas = []
for row in resampled:
    cur = [q8(row[0]), q8(row[1]), q8(row[2])]
    deltas.append([c - p for c, p in zip(cur, prev)])
    prev = cur

# Transpose (column-major) and output
print("; X deltas")
print("traj_dx:")
print("    db " + ", ".join(str(d[0] & 0xFF) for d in deltas))
print("; Y deltas")
print("traj_dy:")
print("    db " + ", ".join(str(d[1] & 0xFF) for d in deltas))
print("; Z deltas")
print("traj_dz:")
print("    db " + ", ".join(str(d[2] & 0xFF) for d in deltas))
```

5. **Comprimir.** Pasar cada columna por ZX0 por separado (la disposición por columnas se comprime mucho mejor que la entrelazada). Incluir los blobs comprimidos con `INCBIN`.

6. **Reproducción en Z80.** Descomprimir cada columna a un búfer. Cada fotograma, leer el siguiente delta y sumar a la posición actual. Trazar el (X, Y) resultante en pantalla (proyectar Z para profundidad si es necesario).

### Recipe 4: Furnace → AY Music

**Objetivo:** Componer música AY-3-8910 en Furnace y exportar para reproducción en ZX Spectrum.

**Pasos:**

1. **Configurar Furnace.** Crear nuevo proyecto. Añadir un sistema AY-3-8910 (Ajustes -> seleccionar "AY-3-8910" de la lista de chips). Establecer el reloj a 1,7734 MHz (estándar ZX Spectrum). Establecer la tasa de refresco a 50Hz (PAL).

2. **Componer.** Usar el editor de patrones de Furnace --- similar a Vortex Tracker pero con deshacer, osciloscopio por canal y edición visual de envolventes. Furnace soporta envolventes hardware del AY, mezcla de ruido y todas las características estándar del AY.

3. **Exportar como VGM.** Archivo -> Exportar -> VGM. Esto produce un archivo .vgm que contiene escrituras de registros AY crudas por fotograma --- un flujo de pares `(registro, valor)` a 50Hz.

4. **Convertir VGM a volcado de registros:**

```python
import struct

def vgm_to_ay_regs(vgm_file):
    with open(vgm_file, 'rb') as f:
        data = f.read()

    # Skip VGM header (find data offset at 0x34)
    data_offset = struct.unpack_from('<I', data, 0x34)[0] + 0x34

    frames = []
    current_regs = [0] * 14
    pos = data_offset

    while pos < len(data):
        cmd = data[pos]
        if cmd == 0xA0:  # AY-3-8910 register write
            reg = data[pos + 1]
            val = data[pos + 2]
            if reg < 14:
                current_regs[reg] = val
            pos += 3
        elif cmd == 0x62:  # Wait 1/50s
            frames.append(list(current_regs))
            pos += 1
        elif cmd == 0x66:  # End of data
            break
        else:
            pos += 1

    return frames

frames = vgm_to_ay_regs('music.vgm')

# Output as Z80 include
print(f"music_frames: equ {len(frames)}")
print("music_data:")
for regs in frames:
    print("    db " + ", ".join(f"${r:02X}" for r in regs))
```

5. **Reproductor Z80.** El reproductor más simple posible --- 14 instrucciones OUT por interrupción:

```z80
play_frame:
    ld hl, (music_ptr)
    ld b, 14
    xor a
.loop:
    out ($FD), a        ; select register
    ld c, (hl)
    inc hl
    push af
    ld a, c
    out ($BF), a        ; write value
    pop af
    inc a
    djnz .loop
    ld (music_ptr), hl
    ret
```

6. **Alternativa: conversión a PT3.** Si prefieres usar un reproductor PT3 estándar (más pequeño, mejor compresión), usa la herramienta `vgm2pt3` o compón directamente en Vortex Tracker. La ventaja de Furnace es la interfaz moderna; la ventaja de Vortex Tracker es la compatibilidad PT3 garantizada.

### Recipe 5: packbench → Pre-compression Analysis

**Objetivo:** Analizar datos crudos de demo antes de la compresión para identificar las transformaciones óptimas.

**Pasos:**

1. **Ensamblar sin compresión.** Compilar tu demo con datos INCBIN crudos (sin comprimir).

2. **Ejecutar packbench analyze** en cada archivo de datos:

```bash
packbench analyze sprites.bin
```

3. **Leer el informe.** packbench reporta:
   - **Entropía** (bits por byte) --- tamaño mínimo teórico comprimido
   - **Distribución de bytes** --- muestra si los valores se agrupan (bien) o se distribuyen uniformemente (malo para la compresión)
   - **Longitudes de ejecución** --- muestra patrones de repetición
   - **Transformaciones sugeridas** --- codificación por deltas, separación de planos de bits, transposición, etc.

4. **Aplicar transformaciones sugeridas.** Si packbench sugiere codificación por deltas:

```python
data = open('sprites.bin', 'rb').read()
deltas = bytes([((data[i] - data[i-1]) & 0xFF) for i in range(1, len(data))])
open('sprites_delta.bin', 'wb').write(bytes([data[0]]) + deltas)
```

5. **Re-analizar.** Ejecutar packbench sobre los datos transformados. La entropía debería ser menor.

6. **Comprimir.** Ejecutar ZX0 o Pletter sobre los datos transformados. Comparar el tamaño comprimido contra el original --- la transformación debería producir un resultado más pequeño.

7. **Actualizar la demo.** El descompresor Z80 se ejecuta primero (decodificación ZX0), luego la transformación inversa (des-delta) reconstruye los datos originales. La transformación inversa es barata: ~10 T-states por byte para decodificación de deltas.

---

## Lectura adicional

- **GNU Rocket:** `github.com/rocket/rocket` --- editor de sincronización + bibliotecas cliente
- **TiXL:** `github.com/tixl3d/tixl` --- motion graphics basado en nodos (MIT)
- **Archivo Farbrausch:** `github.com/farbrausch/fr_public` --- Werkkzeug, kkrunchy, V2 (BSD)
- **Furnace:** `github.com/tildearrow/furnace` --- tracker chiptune multi-sistema (GPL-2.0)
- **Sointu:** `github.com/vsariola/sointu` --- sintetizador para intros de 4K (MIT)
- **WaveSabre:** `github.com/logicomacorp/WaveSabre` --- sintetizador para intros de 64K (MIT)
- **Crinkler:** `github.com/runestubbe/Crinkler` --- enlazador compresor (zlib)
- **Bonzomatic:** `github.com/Gargaj/Bonzomatic` --- codificación de shaders en vivo
- **Shader Minifier:** `github.com/laurentlb/shader-minifier` --- optimizador GLSL/HLSL
- **z80-optimizer:** `github.com/oisee/z80-optimizer` --- superoptimizador Z80 de fuerza bruta (MIT)
- **Motion Canvas:** `motioncanvas.io` --- animación paramétrica (MIT)
- **Blender:** `blender.org` --- 3D, VSE, Graph Editor, Geometry Nodes, Grease Pencil (GPL)
