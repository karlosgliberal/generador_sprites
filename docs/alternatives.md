# Alternativas investigadas para generación de sprites AI

## Tabla comparativa

| Modelo | Tipo | Viabilidad | Ventaja | Limitación | Coste | Estado |
|--------|------|:----------:|---------|------------|-------|--------|
| **Flux Kontext Pro** | API (BFL) | ALTA | Consistencia con input_image, buen pixel art | Sin cross-pose nativo, body proportion issues | $0.04/call | En uso |
| **Gemini Flash** | API (Google) | MEDIA-ALTA | Multi-image reference, barato, multimodal nativo | Calidad variable, puede rechazar prompts | $0.04/call | En uso |
| **ComfyUI + ControlNet** | Local | ALTA | Templates como seg maps, IP-Adapter para identidad | Setup complejo, requiere GPU local | Free (GPU) | Por evaluar |
| **Pipeline 3D** | Local | ALTA | Consistencia inherente (mismo modelo), animaciones gratis de Mixamo | Pipeline larga, rigging | Free | Por evaluar |
| **PixelLab** | API cloud | BAJA-MEDIA | Skeleton animation nativo, pixel art real | Ya probado: inconsistente, max 3 frames, no acepta nuestros templates | Variable | Probado |
| **Sprite Sheet Diffusion** | SD 1.5 + ControlNet | MEDIA | Pose-conditioned, ReferenceNet | Paper (arXiv:2412.03685), requiere fine-tuning, no prod-ready | Free (local) | Investigación |
| **Retro Diffusion** | Plugin Aseprite | BAJA | ControlNet + LoRA nativo, pixel art limpio | Sin animaciones, sin consistencia cross-pose, $65 | $65 una vez | Descartado |
| **Seedance 2.0** | Video → frames | MEDIA | Calidad de animación superior, acepta referencia | No respeta grid, post-proceso pesado | Variable | Investigación |
| **God Mode AI** | Servicio cloud | MEDIA | 8 direcciones, export Spine/Godot, paletas retro | Servicio cerrado sin API documentada | Variable | Investigación |
| **SDXL + pixel-art-xl LoRA** | Local | DESCARTADO | Gratis, buen pixel art base | Sin character consistency | Free | Descartado |
| **SD 1.5 + ControlNet + IP-Adapter** | Local | DESCARTADO | Pipeline completa en teoría | Resultado monstruoso: 4 componentes genéricos en conflicto | Free | Fracaso documentado |

## Detalle de cada enfoque

### Flux Kontext Pro (en uso)

Modelo DiT con buena adherencia a prompts. Se le pasa el template upscaled como `input_image` y genera el avatar imitando la pose. Sin mecanismo nativo de consistencia cross-pose — cada llamada puede variar ligeramente.

**Resultado experimental**: funciona bien para poses verticales (idle, walk). Falla en poses extremas (collapsed/death — renderizó texto literal del prompt en una prueba). El modelo `flux-sprites` en Replicate está específicamente entrenado para sprite sheets.

### Gemini Flash (en uso)

Natively multimodal. Soporta `reference_images` — se pasa el avatar neutral como referencia para las otras familias. Funciona parcialmente para cross-pose consistency. La prueba en `puppet/output/gemini_test/` demostró que generar avatares completos por pose con references funciona bien.

### ComfyUI + ControlNet (recomendado como siguiente paso)

**Idea clave**: tratar nuestras plantillas de color NO como imágenes de referencia visual, sino como **mapas de control estructural** (ControlNet seg mode). La AI solo necesita "rellenar" cada segmento de color con la textura del personaje.

Pipeline:
```
Avatar (Flux) → ControlNet (plantillas color como seg map) → Pixel Art LoRA → IP-Adapter (identidad) → Spritesheet
```

Proyectos de referencia:
- **[Animyth](https://github.com/ece1786-2023/Animyth)**: Pipeline GPT-4 + ControlNet + SD con templates de sprite sheets. Resultados: 4.5/5 consistencia, 4.3/5 suavidad.
- **[PoseCrafts](https://github.com/SupeemAFK/PoseCrafts)**: Texto → OpenPose → ControlNet → sprites.

**Nota**: OpenPose falla con pixel art 48px. Nuestros templates de color son superiores como conditioning porque incluyen segmentación semántica + oclusión + proporciones exactas.

### Pipeline 3D → Pixel Art (estilo Dead Cells)

El enfoque más robusto y predecible. La consistencia es inherente (mismo modelo 3D = mismo personaje).

```
AI genera modelo 3D → Mixamo auto-rig + animaciones → Blender pixel art shader → Spritesheet
```

Herramientas:
- [TripoSR](https://github.com/VAST-AI-Research/TripoSR): Imagen → modelo 3D
- [Mixamo](https://www.mixamo.com/): Auto-rig + biblioteca de animaciones (walk, run, attack, jump...)
- [blender-spritesheets](https://github.com/theloneplant/blender-spritesheets): Plugin para exportar a spritesheets
- Pixel Art Shader de Blender (Toshihiro Kushizaki)

Dead Cells usó exactamente este pipeline (3D → render → pixel art + normal maps).

### PixelLab (probado, resultados mediocres)

API `animate-with-skeleton` que acepta imagen de referencia + keypoints. Probado con `test_pixellab.py`:
- Máximo 3 frames por llamada (hay que hacer batches)
- Resultados no muy consistentes entre frames
- Requiere keypoints precalculados (no acepta nuestros templates)
- Artefactos y variaciones de estilo entre frames
- Tiene MCP server, soporta walk/run/idle/attack predefinidos

### Sprite Sheet Diffusion (paper académico)

Paper: [arXiv:2412.03685](https://arxiv.org/html/2412.03685v1)

Arquitectura de 3 componentes adaptada de AnimateAnyone:
1. **ReferenceNet**: codifica apariencia del personaje (SD-v1.5 modificado con spatial-attention)
2. **Pose Guider**: 4 capas conv que alinean la imagen de pose con el latent de ruido
3. **Motion Module**: modela transiciones suaves entre frames

Entrenamiento en 2 fases:
1. Pose-to-Image: entrena ReferenceNet + Pose Guider
2. Pose-to-Sprite: congela fase 1, entrena Motion Module para coherencia temporal

Resultados: SSIM 0.721 (vs 0.301 baseline), pero overfitting por dataset pequeño (463 pares, 11 personajes).

El concepto de Pose Guider es directamente aplicable a nuestras plantillas de color como conditioning.

### SD 1.5 local (fracaso documentado)

Se implementó pipeline local con `diffusers` combinando SD 1.5 + ControlNet Canny + IP-Adapter Plus + Pixel Art LoRA en M3 Max vía MPS (~16s/frame).

**Resultado**: monstruoso. Problemas:
1. SD 1.5 demasiado viejo — calidad base pobre
2. IP-Adapter genérico no transfiere identidad de pixel art (diseñado para fotos)
3. ControlNet canny necesita escala 1.2 para seguir poses → distorsiona
4. LoRA produce "estilo pixel" genérico, no pixel art limpio
5. Los componentes entran en conflicto (attention slicing rompe IP-Adapter)

**Conclusión**: juntar N componentes genéricos mediocres no supera a un modelo especializado.

### Seedance 2.0 (ByteDance)

Generación de video que acepta imagen de referencia como primer frame. Sistema multimodal con @tags para referenciar assets. Excelente en 2D animation.

Pipeline: avatar base → Seedance como @Image1 + prompt → extraer frames del video → spritesheet.

Limitación: los videos no respetan grid de pixels, la extracción requiere post-proceso pesado.

### Enfoque "Describe-then-generate" (híbrido)

Vision model (Claude/GPT-4V) extrae descripción JSON del avatar → texto como prompt para generar poses. Evita IP-Adapter completamente — transferencia de identidad vía texto.

Limitación: el texto es lossy, no codifica proporciones/píxeles exactos. Mejor combinado con Flux Kontext (texto + imagen referencia).

### Enfoque "Texture Atlas" (tipo Spine/DragonBones)

En vez de generar un avatar completo y cortarlo, pedirle al modelo que genere un **texture atlas desplegado** — todas las partes del personaje separadas en un lienzo, como texturas UV.

| Aspecto | Pipeline actual | Spine/DragonBones |
|---------|----------------|-------------------|
| Partes | Cortadas con masks genéricas | Dibujadas por separado |
| Joints | Hard-cut rectangular | Mesh weighted, transición suave |
| Poses | Mismas partes para toda animación | Mesh deformation por bone |

Requiere renderer con mesh deformation (WebGL/Canvas2D avanzado).

## Propuesta de pipeline en 3 niveles

### Nivel 1: Quick Win — ComfyUI + ControlNet
Templates como seg maps + IP-Adapter para identidad + Pixel Art LoRA. Esfuerzo medio, calidad media-alta.

### Nivel 2: Robusto — Pipeline 3D
TripoSR → Mixamo → Blender pixel shader. Esfuerzo alto, calidad alta, consistencia garantizada.

### Nivel 3: Custom Model — Sprite Sheet Diffusion
Fine-tune con nuestras plantillas como conditioning. Esfuerzo muy alto, calidad potencialmente máxima.

**Recomendación**: empezar por Nivel 1. Si no funciona, pivotar a Nivel 2.

## Herramientas para experimentar

| Herramienta | Uso | Coste | API |
|---|---|---|---|
| [ComfyUI](https://github.com/comfyanonymous/ComfyUI) | Pipeline local SD/Flux | Free (GPU local) | No |
| [Flux](https://replicate.com/miike-ai/flux-sprites) | Avatar base | ~$0.003/gen | Sí (Replicate) |
| [PixelLab](https://pixellab.ai) | Skeleton-based animation | Suscripción | Sí |
| [Gemini 2.5 Flash](https://ai.google.dev/gemini-api/docs/image-generation) | Describir/generar sprites | Free tier | Sí |
| [Seedance 2.0](https://seedance2.ai) | Video → frames | Varía | Sí (fal.ai) |
| [TripoSR](https://github.com/VAST-AI-Research/TripoSR) | Imagen → modelo 3D | Free | Sí |
| [Mixamo](https://www.mixamo.com/) | Auto-rig + animaciones | Free | No (web) |
| [Blender](https://www.blender.org/) | Render pixel art | Free | CLI scripting |
| [Retro Diffusion](https://astropulse.itch.io/retrodiffusion) | Retoques pixel art | $65 una vez | No |
| [God Mode AI](https://www.godmodeai.co/) | Sprites 8 direcciones | Variable | No |

## Fuentes

- [Sprite Sheet Diffusion](https://arxiv.org/html/2412.03685v1) — ReferenceNet + Pose Guider + Motion Module
- [Animyth](https://github.com/ece1786-2023/Animyth) — GPT-4 + ControlNet + SD
- [PoseCrafts](https://github.com/SupeemAFK/PoseCrafts) — Texto → OpenPose → ControlNet
- [Gemini + Nano Banana](https://lab.rosebud.ai/blog/how-to-create-a-sprite-sheet-with-ai-using-google-gemini-and-nano-banana-easy-guide) — Pipeline Gemini
- [ComfyUI Pixel Art Guide](https://apatero.com/blog/generate-clean-spritesheets-comfyui-guide-2025)
- [Dead Cells Animation Pipeline](https://devpost.com/software/the-dead-cells-animation-pipeline)
- [Blender Spritesheets](https://github.com/theloneplant/blender-spritesheets)
