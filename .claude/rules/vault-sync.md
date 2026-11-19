---
description: Sincronizacion con vault de conocimiento
globs: *
---

# Conexion al Vault de Conocimiento

Este proyecto esta conectado al vault centralizado.

## Vault
Ruta: /Users/wintermute/src/experimentos/obsidian-project-hub

## Proyecto en vault
[[generador-sprites]]

## Protocolo
- **Al inicio de sesion**: Lee `/Users/wintermute/src/experimentos/obsidian-project-hub/proyectos/generador-sprites.md` para contexto.
- **Durante el trabajo**: Si descubres conocimiento reutilizable, crealo en `/Users/wintermute/src/experimentos/obsidian-project-hub/conocimiento/`.
- **Al final de sesion**: Ejecuta `/vault-manager:vault-sync` para sincronizar.
