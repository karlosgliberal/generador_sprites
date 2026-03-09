# Problemas conocidos y mitigaciones

## 1. Mask-Avatar Mismatch (fundamental)

Las máscaras del template asumen que el AI genera un personaje que se alinea pixel a pixel
con el stickman. En la práctica:
- Cabezas más grandes/pequeñas que la máscara
- Brazos/piernas en ángulos ligeramente distintos
- Accesorios (espadas, capas) que sobresalen de cualquier máscara
- En personajes con colores similares entre partes (ej: lagarto verde con torso verde), el bleeding es peor

**Severidad**: Media. Funciona razonablemente para poses verticales (idle, walk).
Falla para poses extremas (collapsed, airborne).

**Causa raíz**: el template es un stickman delgado de 48px; el personaje generado es más ancho, con proporciones diferentes, y el AI tiende a generar vistas 3/4 o frontales en vez de side-view puro.

**Mitigaciones implementadas**:
1. `binary_dilation(iterations=2)` expande las máscaras ~2px a escala de template, capturando ~2x más píxeles del personaje
2. Extracción a alta resolución (384px) con `np.kron` para escalar máscaras, en vez de extraer a 48px
3. LANCZOS para downscale (preserva detalle), NEAREST para upscale (preserva bordes)
4. BG removal a resolución completa (1024px) antes de reducir

**Soluciones posibles**:
- Segmentación semántica del avatar (SAM) — genera masks desde la imagen misma
- ComfyUI con templates como ControlNet seg maps — el modelo rellena cada segmento de color
- Pipeline 3D (TripoSR → Mixamo → Blender) — elimina el problema por completo

## 2. Collapsed/death no funciona bien

El template death_09 tiene al stickman horizontal. El AI genera un personaje acostado,
pero la distribución de partes es muy diferente. La cabeza puede quedar donde el template
espera el torso.

**Severidad**: Alta. Las animaciones de death se ven mal.

**Causa adicional**: Flux renderizó texto literal del prompt en una prueba con collapsed template.
Gemini filtró los colores del template en el output. Ambos modelos tienen dificultades con poses extremas.

**Mitigación**: `prompt_suffix` en pose families para guiar al AI ("lying horizontal on ground, defeated, collapsed").

## 3. Inconsistencia cross-pose (Flux)

Flux Kontext no tiene mecanismo para mantener consistencia entre llamadas.
Cada familia puede generar un personaje ligeramente diferente.

**Mitigación**: Gemini soporta `reference_images` — se pasa el avatar neutral
como referencia para las otras familias. Funciona parcialmente.

**Alternativas**: FLUX.2 Multi-Reference (32B params, nov 2025) soporta hasta 9-10 imágenes de referencia. Podría combinar avatar + varios frames como referencias.

## 4. No es pixel art verdadero

Los AI generan "estilo pixel art" con gradientes suaves (~19K colores únicos).
No son sprites con paleta limitada. Esto afecta:
- El resize necesita LANCZOS en vez de NEAREST (NEAREST genera aliasing visible)
- Los bordes no son nítidos como en pixel art real
- No se puede usar reducción de paleta sin post-proceso pesado

**Pipeline de post-proceso posible**: pixelización grid-aligned + reducción de paleta + alineación a grid.

## 5. rembg roto en el entorno actual

rembg depende de numba que es incompatible con numpy actual. El import falla con
`AttributeError: module 'numpy' has no attribute 'trapz'` (numba/numpy incompatibility).
El import fallido puede dejar PIL en estado inconsistente intermitentemente.

**Mitigación**: `except Exception` en `remove_background()` (no solo `ImportError`).
El fallback flood-fill funciona bien para fondos negros puros.

**Limitación del flood-fill**: solo funciona con fondo negro puro (#000000).
Flux a veces genera fondos grises (#808080) o con gradientes — los personajes
"fantasy" y "side_fantasy" fallaron por fondo gris.

**Mejora implementada**: flood-fill desde bordes con `scipy.ndimage.label` — solo elimina
píxeles oscuros conectados al borde de la imagen. Preserva personajes oscuros (ej: gato negro)
que antes se borraban con el threshold global.

## 6. Templates con tamaños inconsistentes

punch y sword_attack son 64x64, el resto 48x48.

**Bug descubierto**: `extract_parts()` originalmente hardcodeaba `REFERENCE_FRAME` (idle/frame_00, 48x48).
La familia "attack" generaba avatar con punch template (64x64) pero extraía con idle masks (48x48) — alineación completamente errónea.

**Fix**: `extract_parts()` ahora acepta parámetro `template_img` para usar la máscara correcta
por familia. `generate_character_families()` pasa el template correspondiente.

## 7. Hard-cut joints

Las partes son imágenes rectangulares pegadas con `alpha_composite`. No hay transición
en las uniones:
- Huecos visibles entre torso y brazos
- Solapamiento donde partes se cruzan (piernas en walk)
- Bordes rectangulares antinaturales

**Mitigación descartada**: `feather_edges()` (blur gaussiano en canal alpha) añadía halo
semi-transparente difuso alrededor de las partes. Empeoró la calidad. Feather default = 0.

**Solución a largo plazo**: mesh deformation en el renderer (tipo Spine/DragonBones) con
weighted transitions entre bones.

## 8. Calidad difusa en renders

Los sprites renderizados se veían "difusos" por tres causas encadenadas:
1. `feather_edges` añadía halo semi-transparente
2. `Image.NEAREST` resize sobre imágenes no-pixel-art (19K colores) creaba aliasing
3. `extract_size=192` perdía detalle innecesariamente

**Fixes aplicados**: feather=0, LANCZOS en renderer, extract_size=384.
