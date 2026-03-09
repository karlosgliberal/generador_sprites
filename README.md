# generador_sprites

AI sprite generator: genera avatares con IA y extrae partes animables usando templates color-coded.

## Flujo del pipeline

```
1. PROMPT + TEMPLATE (48x48 o 64x64 stickman color-coded)
   → AI genera avatar 1024x1024 imitando la pose del stickman

2. REMOVE BACKGROUND (flood-fill desde bordes, preserva personajes oscuros)
   → Avatar 1024x1024 con fondo transparente

3. DOWNSCALE (LANCZOS)
   → Avatar 384x384

4. MASK EXTRACTION (6 partes: head, torso, front/back arm, front/back leg)
   → Template se parsea por colores → 6 máscaras booleanas
   → Cada máscara se escala x8 (384/48) y se aplica sobre el avatar
   → 6 PNGs con las partes recortadas

5. RENDER FRAME (por cada frame de una animación)
   → Se parsea el template de esa animación (distinta pose)
   → Cada parte se redimensiona (LANCZOS) al bbox del template
   → Se posiciona en canvas 96x96 usando pivots de joints

6. STRIP
   → N frames → strip horizontal PNG
```

## Quick start

```bash
# Instalar
pip install -e ".[all]"

# Configurar API keys
cp .env.example .env
# Editar .env con tus keys

# Generar personaje (4 llamadas AI, ~$0.16)
python -m generador_sprites generate \
    --character shadow_ninja \
    --description "dark ninja, purple robes, glowing green eyes" \
    --provider gemini

# Renderizar animación
python -m generador_sprites render \
    --parts parts/shadow_ninja_families \
    --animation idle

# Extraer partes de una imagen existente
python -m generador_sprites extract \
    --from-image mi_avatar.png \
    --output parts/test

# Inspeccionar un template
python -m generador_sprites parse templates/idle/frame_00.png --viz
```

## Estructura

```
generador_sprites/
├── templates/          # Stickman frames color-coded (datos, no generados)
│   ├── idle/           # 10 frames, 48x48
│   ├── punch/          # 8 frames, 64x64
│   ├── death/          # 10 frames, 48x48
│   ├── jump/           # 6 frames, 48x48
│   ├── walk/           # 8 frames, 48x48
│   ├── run/            # 8 frames, 48x48
│   └── sword_attack/   # 6 frames, 64x64
├── providers/          # Abstracción de proveedores AI
│   ├── base.py         # ImageProvider ABC
│   ├── flux.py         # Flux Kontext Pro (BFL API)
│   └── gemini.py       # Gemini Flash (Google GenAI)
├── config.py           # Paths y constantes
├── palette.py          # Colores del template → parte del cuerpo
├── parse_template.py   # Segmentación, joints, pivots, z-order
├── extract_parts.py    # Remove BG + mask extraction
├── renderer.py         # Composición de partes en frames
├── generate_parts.py   # Orquestación: avatar por familia + extracción
├── pose_families.py    # 4 familias: neutral, attack, airborne, collapsed
├── flux_client.py      # HTTP client para Flux API
├── utils.py            # assemble_strip
└── cli.py              # Entry point unificado
```

## Pose families

Cada familia genera 1 avatar con su propia pose de referencia:

| Familia | Animaciones | Template | Tamaño |
|---------|------------|----------|--------|
| neutral | idle, walk | idle/frame_00 | 48x48 |
| attack | punch, sword_attack | punch/frame_04 | 64x64 |
| airborne | jump, run | jump/frame_02 | 48x48 |
| collapsed | death | death/frame_09 | 48x48 |

## Providers

Interfaz `ImageProvider` con dos implementaciones:

- **Flux Kontext Pro**: $0.04/call, buena calidad pixel art, sin consistencia cross-pose
- **Gemini Flash**: $0.04/call, soporta `reference_images` para consistencia entre poses

Preparado para añadir: PixelLab, SDXL + LoRA, Sprite Sheet Diffusion.

## Dependencias

- **Requeridas**: Pillow, numpy, scipy, requests
- **Opcionales**: google-genai (Gemini), rembg (background removal con U2Net)

Ver `docs/` para problemas conocidos y alternativas investigadas.
