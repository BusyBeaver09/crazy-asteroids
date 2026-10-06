# Crazy Asteroids

Combined Asteroids labs by Eddie Liao. Written in Python with Pygame and pygame.math.Vector2.

## Controls

Click the game first to focus it. W applies thrust, A and D rotate, S brakes, Space fires, and R restarts after all asteroids are cleared or all lives are lost. Destroy the six asteroids while avoiding collisions and enemy ships.

## Included lab features

- Vector positions, velocities, thrust, rotation, and screen wrapping.
- Six differently sized asteroids with mass-based collision impulses.
- Bullets, scoring, three lives, and temporary collision invulnerability.
- Enemy patrol and attack states using distance and a dot-product field-of-view test.

## Source and browser build

`original_main.py` is the unchanged source downloaded from https://onecompiler.com/pygame/453zwqqr2. `main.py` wraps the game loop in an async function and yields with `await asyncio.sleep(0)` so the browser can render and handle input. The browser controls frame timing instead of a blocking 120 FPS limiter; elapsed time is capped at 50 ms. Game rules and vector calculations are preserved.

Run locally with `python -m pip install -r requirements.txt` and `python main.py`.

Rebuild the committed webplayer with `python build_web.py`. Vercel serves the generated static files with the Other preset and no build command. The player downloads the Pygbag Python/WebAssembly runtime from the official pygame-web CDN on first load.
