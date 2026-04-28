# Cómo poner el logo oficial de Scuffers

La función `load_logo()` busca, **en este orden**, el primer archivo que encuentre:

1. `assets/scuffers_logo_light.png` — versión **clara/blanca** del logo, optimizada para fondo oscuro. **Recomendada.**
2. `assets/scuffers_logo.png` — versión por defecto. Si el logo es negro, la app le aplicará automáticamente `filter: invert(1) brightness(2)` por CSS para que se vea blanco sobre el fondo dark.
3. `assets/scuffers_logo.svg` — fallback SVG con `currentColor` (el wordmark "scuffers" en blanco). Es lo que ves ahora si no has subido tu archivo.

## Para usar el logo oficial

Arrastra tu archivo a esta carpeta con uno de los nombres anteriores. Si tienes la versión normal (negra), guárdala como:

```
assets/scuffers_logo.png
```

Si la guardas como `scuffers_logo_light.png` el CSS no aplicará invert (úsalo solo si ya es blanca).

Tamaños recomendados: 720×320 px o superior, fondo transparente. El logo se redimensiona automáticamente: 48px alto en hero, 32px en sidebar, 18px en footer.
