# Done Criteria: Three.js Flight Simulator Demo

## Project Type
Weekend prototype / proof-of-concept. Speed and simplicity over polish. No build tools, no bundler, no npm, no tests.

## Deliverables
- `src/index.html` — Main entry point, loads Three.js from CDN
- `src/[additional JS files]` — Whatever JS modules needed (e.g. terrain.js, camera.js, controls.js, etc.)
- **No other files required.** Plain JavaScript, no build step.

## Must-Have Features (Core)
1. **Procedurally Generated Terrain** — Heightmap-based or simple hilly plane. Must be visible and flybable. At least 256×256 units or visually similar scale.
2. **Simple Plane Model** — Box with wings is acceptable. Visible indicator of nose/direction. Does not need complex geometry.
3. **Flight Controls** — WASD or arrow keys move the plane. Must be responsive and intuitive.
4. **Third-Person Chase Camera** — Follows plane from behind/above. Camera must track plane position and orientation.
5. **Sky and Fog** — Visual atmosphere (sky color, fog layer). Makes the scene feel less empty.

## Success Criteria (Hard Stops)
- [ ] Opening `src/index.html` in a browser produces a flyable 3D scene (no console errors, no blank page)
- [ ] Plane responds to input (WASD or arrows), moves through space
- [ ] Camera follows plane and shows terrain below
- [ ] Terrain is visible and procedurally generated (not a static imported model)
- [ ] No external build step, bundler, npm install, or webpack required
- [ ] Code is plain JavaScript (not TypeScript, not JSX)

## Non-Goals
- Physics engine (rough kinematic movement is fine)
- Complex plane model or cockpit view
- Terrain elevation collision detection
- Multiplayer networking
- Mobile optimization
- Audio
- Performance optimization beyond "runs at decent FPS in modern browsers"
- Production-grade error handling

## Code Review (Static)
- Critic will review code statically; do not assume runtime testing
- Prefer clarity and simplicity over fancy patterns
- Comments on non-obvious sections welcome but not required
