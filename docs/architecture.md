# Arquitectura del pipeline

## Diagrama de flujo

```
                    ┌─────────────────┐
                    │  PROMPT_TEMPLATE │
                    │  + description   │
                    │  + prompt_suffix │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ neutral  │  │ attack   │  │ airborne │  │collapsed │
        │ template │  │ template │  │ template │  │ template │
        │  48x48   │  │  64x64   │  │  48x48   │  │  48x48   │
        └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
             │              │              │              │
             ▼              ▼              ▼              ▼
        ┌──────────────────────────────────────────────────────┐
        │              AI Provider (Flux / Gemini)              │
        │  1 llamada por familia (4 total, ~$0.16)             │
        │  reference_images para cross-pose (Gemini lo usa)    │
        └──────────────────────┬───────────────────────────────┘
                               │ 4 avatares 1024x1024
                               ▼
        ┌──────────────────────────────────────────────────────┐
        │                 EXTRACT_PARTS (Python)                │
        │                                                      │
        │  1. remove_background() — flood-fill desde bordes    │
        │     (preserva personajes oscuros)                    │
        │  2. resize LANCZOS → 384x384 (o sf × template_w)    │
        │  3. segment_frame(template) → 6 máscaras booleanas   │
        │  4. np.kron escala máscara × sf (exact múltiplo)     │
        │  5. binary_dilation(iterations=2) expande            │
        │  6. Aplica máscara → crop → save PNG                 │
        │                                                      │
        │  CLAVE: usa el template_img de la familia, NO        │
        │  hardcoded idle/frame_00                             │
        └──────────────────────┬───────────────────────────────┘
                               │ 24 partes (6 × 4 familias)
                               ▼
        ┌──────────────────────────────────────────────────────┐
        │                  RENDER_FRAME (Python)                │
        │                                                      │
        │  Para cada frame de animación:                       │
        │  1. parse_frame(template_frame) → bbox + joints      │
        │  2. compute_pivots() → punto de anclaje por parte    │
        │  3. compute_z_order() → orden de dibujado            │
        │  4. Para cada parte:                                 │
        │     - resize(LANCZOS) al bbox×scale                  │
        │     - posicionar en canvas usando pivot alignment    │
        │  5. → frame 96x96                                   │
        └──────────────────────┬───────────────────────────────┘
                               │ N frames por animación
                               ▼
                        ┌──────────────┐
                        │  STRIP PNG   │
                        │  horizontal  │
                        └──────────────┘
```

## Templates como ventaja diferencial

Las plantillas de Zegley tienen una propiedad única: **el código de colores por parte del cuerpo funciona como mapa de segmentación semántica**. Esto es extremadamente valioso porque:

1. **Cada color = una parte del cuerpo**: extracción automática de máscaras de segmentación
2. **La oclusión está resuelta**: los ficheros Aseprite originales tienen capas con z-order
3. **Son mapas de conditioning perfectos**: en vez de usar OpenPose (que falla con 48px), pueden usarse directamente como ControlNet seg maps
4. **Información más rica que OpenPose**: incluyen oclusión, proporciones exactas y segmentación semántica completa

**Idea clave**: tratar las plantillas de color NO como imágenes de referencia visual, sino como **mapas de control estructural** que definen la pose, oclusión y proporciones. La AI solo necesita "rellenar" cada segmento de color con la textura/apariencia del personaje.

## Templates color-coded

Los templates son stickman frames donde cada color = una parte del cuerpo:

| Color | RGB | Parte | Rol |
|-------|-----|-------|-----|
| Cyan | (95,205,228) | head | Cabeza/cara |
| Verde | (153,229,80) | torso | Tronco |
| Amarillo | (251,242,54) | front_arm | Brazo delantero |
| Naranja | (223,113,38) | back_arm | Brazo trasero |
| Rojo | (206,80,80) | front_leg | Pierna delantera |
| Magenta | (175,26,178) | back_leg | Pierna trasera |

La clasificación usa nearest-neighbor en RGB con threshold de distancia 30 (`MAX_COLOR_DISTANCE`).

### Animaciones disponibles (Zegley 2D Platformer Asset Pack)

| Animación | Frames | Tamaño | Familia |
|-----------|--------|--------|---------|
| idle | 10 | 48x48 | neutral |
| walk | 8 | 48x48 | neutral |
| run | 8 | 48x48 | airborne |
| jump | 6 | 48x48 | airborne |
| punch | 8 | 64x64 | attack |
| sword_attack | 6 | 64x64 | attack |
| death | 10 | 48x48 | collapsed |

Fuente: [Zegley 2D Platformer Asset Pack](https://zegley.itch.io/2d-platformermetroidvania-asset-pack) (~35 animaciones en total, 7 implementadas).

## Pose families

Cada familia genera 1 avatar con su propia pose de referencia y prompt_suffix:

| Familia | Template | Tamaño | Animaciones | prompt_suffix |
|---------|----------|--------|-------------|---------------|
| neutral | idle/frame_00 | 48x48 | idle, walk | (ninguno) |
| attack | punch/frame_04 | 64x64 | punch, sword_attack | "arm extended forward, attacking pose" |
| airborne | jump/frame_02 | 48x48 | jump, run | "jumping mid-air, legs bent" |
| collapsed | death/frame_09 | 48x48 | death | "lying horizontal on ground, defeated" |

Las partes extraídas de cada familia se usan para renderizar las animaciones de esa familia.
El prompt_suffix guía al AI en poses difíciles (especialmente collapsed).

## Tamaños en el pipeline

| Paso | Resolución | Nota |
|------|-----------|------|
| Avatar AI | 1024×1024 | Output del provider |
| BG removal | 1024×1024 | Flood-fill a resolución completa (antes de resize) |
| Extracción | sf × template_w | sf = extract_size / template_w (entero), ej: 384 = 8 × 48 |
| Template | 48×48 o 64×64 | Fuente de las máscaras |
| Máscara escalada | sf × template | np.kron × sf → mismo tamaño que avatar escalado |
| Parte extraída | variable | Depende del bbox de la máscara |
| Frame renderizado | 96×96 | Output final configurable |

**Nota sobre extract_size**: debe ser múltiplo exacto del tamaño del template para que `np.kron` produzca una máscara del tamaño correcto. El código ajusta: `sf = int(extract_size / template_w); extract_size = sf * template_w`.

## Técnicas de alineación mask-avatar

Tres técnicas complementarias validadas para mejorar la alineación:

1. **Dilatación de masks** (`scipy.ndimage.binary_dilation`): expandir cada mask N píxeles a escala del template antes de escalar. Con `dilate=2` a 48px, las partes capturan ~2x más píxeles
2. **Extracción a alta resolución**: en vez de resize a 48×48, extraer a 384+ y escalar las masks con `np.kron`. El renderer se encarga del resize final
3. **Interpolación correcta**: LANCZOS para downscale (preserva detalle al comprimir), NEAREST para upscale (preserva bordes al ampliar pixel art real)
4. **BG removal a resolución completa**: eliminar fondo en 1024px antes de reducir, no después

## Background removal: flood-fill desde bordes

La función `remove_background_threshold()` usa componentes conectados en vez de threshold global:

```python
# 1. Calcular luminancia de cada pixel
lum = 0.299*R + 0.587*G + 0.114*B

# 2. Marcar píxeles oscuros (lum < threshold)
dark_mask = lum < threshold

# 3. Encontrar componentes conectados
labeled, _ = scipy.ndimage.label(dark_mask)

# 4. Solo los que tocan el borde son background
border_labels = labels que tocan fila 0, última fila, columna 0, última columna

# 5. Eliminar solo esos componentes
arr[bg_mask, alpha] = 0
```

**Ventaja**: un gato negro en el centro de la imagen se preserva porque sus píxeles oscuros no están conectados al borde. Con threshold global se borraría entero.

## Provider abstraction

```python
class ImageProvider(ABC):
    def generate(self, prompt, input_image, seed=None, reference_images=None) -> Image
    def name -> str
    def cost_per_call -> float
```

Implementaciones: `FluxProvider`, `GeminiProvider`.

Para añadir un nuevo provider: crear `providers/mi_provider.py`, implementar la interfaz,
registrar en `providers/factory.py`.

## Inventario de personajes generados (referencia)

De las pruebas con el pipeline puppet:

| Personaje | Resultado | Notas |
|-----------|-----------|-------|
| side_bright_s42 | **Mejor resultado** | Buenos colores, proporciones claras |
| tibetan_monk | Bueno en idle | Problemas en punch/death, joints visibles |
| lagarto_samurai | Bueno | Bleeding torso/brazo (verde sobre verde) |
| ninja_robot | Funcional | 48px legacy, pixelado |
| esqueleto_pirata | Malo | Personaje muy oscuro, BG removal fallaba |
| fantasy | Roto | Fondo gris, BG removal por threshold fallaba |
