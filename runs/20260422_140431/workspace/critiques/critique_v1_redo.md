# Critique v1 (Redo)

## Summary

The flight simulator demonstrates functional gameplay—flyable terrain, responsive controls, working camera—but is undermined by two structural failures: **(1) all 286 lines of code live in a single inline `<script>` block**, making the codebase unmaintainable and violating the DONE_CRITERIA pattern of separate JS modules, and **(2) the plane model is oriented 180° backward**, causing the nose to point away from its direction of travel, breaking visual feedback. Together, these issues prevent the code from scaling beyond a weekend demo and create a confusing user experience. The functionality works; the architecture does not.

## Issues

### [CRITICAL] Entire application hardcoded into single inline `<script>` block with zero modularization
File: src/index.html:44-330
The DONE_CRITERIA describes the expected deliverable structure as: `src/index.html` (main entry) plus `src/[additional JS files]` (e.g., terrain.js, camera.js, controls.js). Instead, all 286 lines—scene setup, terrain generation, plane geometry creation, state management, input handling, flight physics, camera logic, and animation loop—are crammed into a single `<script>` tag. This exceeds "fits on one screen" by a factor of 5–6x. Consequences:
- **No separation of concerns**: rendering, physics, and input events are inseparably intertwined.
- **Impossible to reuse or test** components: want to use the terrain generator elsewhere? Copy-paste the entire script.
- **Fragile to edit**: changing terrain parameters requires reading through unrelated flight control code.
- **Violates DONE_CRITERIA pattern**: the criteria explicitly lists separate modules as the expected structure ("src/[additional JS files] — Whatever JS modules needed").

**Remedy idea**: Extract into 4 files immediately:
- `terrain.js` (generateTerrain function, ~50 lines)
- `plane.js` (createPlane function + planeState object, ~60 lines)  
- `camera.js` (updateCamera function, ~20 lines)
- `controls.js` (input handling + updatePlaneInput, ~100 lines)
- Keep `index.html` ~50 lines: load these files, initialize scene, start loop.

### [IMPORTANT] Plane model is oriented backward relative to direction of travel
File: src/index.html:118-162 (model construction), 244 (direction vector)
The plane's nose cone is positioned at `z = 1.8` in local space and points toward local +Z. The flight direction is set to world `-Z` (line 244: `const direction = new THREE.Vector3(0, 0, -1)`). After identity rotation, the nose points in world +Z but the plane **travels in world -Z**—exactly opposite. Consequences:
- **Visual feedback is inverted**: the player sees the plane's tail (or rear fuselage), not the nose, as it flies away.
- **Breaks intuition**: in a flight simulator, the plane should point in the direction it moves. This violates fundamental UX.
- **Confusing when pitching**: pitch input rotates the tail forward and the nose backward, which looks wrong.

The camera follows from behind, so the player doesn't see the nose as a small detail—they see the entire rear profile of the plane moving away. This is disorienting. 

**Remedy idea**: Rotate the plane 180° around its Y-axis when constructing it (add `planeGroup.rotateY(Math.PI)` at line 159 before positioning), so the nose and tail swap roles and the nose points in the direction of travel.

### [IMPORTANT] All global state with zero encapsulation or namespace protection
File: src/index.html:46-64, 115, 164, 167-172, 175, 187-330
Every major object is a global variable: `scene`, `camera`, `renderer`, `terrain`, `plane`, `planeState`, `keys`, `animate`, and several nested functions. Consequences:
- **No isolation**: adding a pause feature, restart, or second scene requires careful coordination with unencapsulated globals (e.g., is the animation loop still running? Is planeState stale?).
- **Fragile**: any future developer adding a feature might accidentally mutate a global and break unrelated logic.
- **Harder to debug**: stack traces don't show which component owns which state.

**Remedy idea**: Wrap logic in a namespace or IIFE:
```javascript
const Game = {
  scene: new THREE.Scene(),
  // ... other globals
  init() { /* setup */ },
  update(deltaTime) { /* game logic */ },
  render() { /* THREE.render */ }
};
Game.init();
requestAnimationFrame(() => Game.update(...));
```

### [IMPORTANT] Magic numbers embedded in functions without documentation or centralization
File: src/index.html:70 (terrain), 86–93 (noise), 122–155 (plane geometry), 157 (plane position), 188–189 (rotation), 278–279 (camera), 314 (delta time)
Hardcoded values control the feel and scale of the entire demo:
- Terrain: `width=512, height=512, scale=5` (total terrain size: 2560 × 2560 units)
- Noise: `amplitude=50, frequency=0.01`, octaves with `amplitude *= 0.5, frequency *= 2`
- Plane: geometry dimensions (fuselage `0.4 × 0.4 × 3`), initial position `(0, 100, 0)`, minimum altitude `10`
- Flight: `rotationSpeed=2` (but unused; angular velocity is set directly)
- Camera: `distance=30, height=20`, lerp factor `0.1`
- Physics: delta time capped at `0.016` (assumed 60 FPS)

Consequences:
- **Invisible design parameters**: if terrain feels too flat or too mountainous, or the plane feels too fast, these values are scattered across unrelated code blocks.
- **Hard to tune**: tweaking the feel requires reading 286 lines of code to find each parameter.
- **No self-documentation**: future developers don't know why these specific values were chosen.

**Remedy idea**: Create a config object at the top of the script:
```javascript
const CONFIG = {
  terrain: { width: 512, height: 512, scale: 5, amplitude: 50, frequency: 0.01 },
  plane: { initialPosition: [0, 100, 0], minAltitude: 10 },
  flight: { rotationSpeed: 2 },
  camera: { distance: 30, height: 20, lerpFactor: 0.1 },
  physics: { deltaTimeCap: 0.016 }
};
```

### [NICE-TO-HAVE] Flight control logic lacks comments explaining non-obvious design choices
File: src/index.html:187–274
The flight system mixes angular velocity, decay, gimbal lock prevention, and vertical input overrides. The code is correct but opaque:
- Lines 235–238: Euler angles are applied in 'YXZ' order, which is unusual. Why not 'XYZ'? (YXZ avoids gimbal lock in pitch-heavy movement, but this isn't documented.)
- Line 241: `planeState.rotation.x = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, planeState.rotation.x))` prevents gimbal lock by clamping pitch, but there's no comment explaining why this is necessary.
- Lines 227–232: Space and Ctrl use `Math.max` and `Math.min` to constrain pitch, interacting subtly with forward/backward input (lines 200–206). This coupling isn't explained.

A 3–5 line comment above `updatePlaneInput` would clarify the model:
```javascript
// Flight controls use angular velocity with exponential decay (lines ~205, 214, 223).
// Pitch is clamped to prevent gimbal lock (line 241). YXZ rotation order avoids issues
// where pitch would affect yaw. Space/Ctrl boost the pitch beyond forward/backward's range.
```

### [NICE-TO-HAVE] Camera distance lerp uses fixed factor instead of frame-rate independent decay
File: src/index.html:285–287
`camera.position.lerp(plane.position.clone().add(cameraOffset), 0.1)` interpolates the camera 10% of the remaining distance toward the target, every frame. If the frame rate drops below 60 FPS, the camera noticeably lags behind. 

**Why it matters**: At 30 FPS, lerp runs half as often, so the camera takes twice as long to catch up. The lag is visible.

**Remedy idea**: Use a time-based lerp:
```javascript
const followSpeed = 3; // units/second
const toTarget = targetPos.clone().sub(camera.position);
camera.position.add(toTarget.multiplyScalar(Math.min(deltaTime * followSpeed, 1)));
```

### [NICE-TO-HAVE] Delta time capped at arbitrary 16ms, leading to inconsistent motion at low frame rates
File: src/index.html:314
`const deltaTime = Math.min((now - lastTime) / 1000, 0.016);` caps delta time at 16ms. Rationale: if a frame takes longer (e.g., 33ms at 30 FPS), don't let the plane jump too far.

**Problem**: The cap is arbitrary. If FPS drops to 30, each frame is 33ms, capped to 16ms. The plane moves as if time is running at half speed. This is intentional (prevent large jumps), but it causes stuttery motion at low frame rates.

**Why it matters**: Noticeable but not breaking. Minor feel issue.

**Remedy idea**: Cap at a reasonable range instead:
```javascript
const deltaTime = Math.max(0.005, Math.min((now - lastTime) / 1000, 0.05));
```
This allows 5–50ms frames, preventing both sub-frame stutter and extreme jumps.

### [NICE-TO-HAVE] HUD updates DOM every frame even when values are identical
File: src/index.html:295–299
`updateHUD()` writes to `#speed`, `#altitude`, `#position` every frame, even if the values haven't changed. Modern browsers optimize redundant writes, but it's not free: 60 writes/second per element × 3 elements = 180 DOM mutations/second.

**Why it matters**: For a tiny prototype, negligible. But it's wasteful and bad practice.

**Remedy idea**: Cache the last displayed value and only write if changed:
```javascript
if (HUD.lastSpeed !== planeState.speed) {
  document.getElementById('speed').textContent = `Speed: ${planeState.speed.toFixed(0)}`;
  HUD.lastSpeed = planeState.speed;
}
```

---

## Stats
- **[CRITICAL: 1]** Monolithic inline script blocks extensibility and violates DONE_CRITERIA structure.
- **[IMPORTANT: 3]** Plane orientation bug breaks visual feedback; global state and scattered magic numbers compromise maintainability.
- **[NICE-TO-HAVE: 4]** Missing comments on flight logic, non-frame-rate-independent camera lerp, arbitrary delta-time cap, avoidable DOM churn.

## Next Steps for Round 2
Fix the two CRITICAL/IMPORTANT issues: split code into 4 modules (`terrain.js`, `plane.js`, `camera.js`, `controls.js`), rotate the plane 180°, and gather magic numbers into a config object. These changes are prerequisites for code that can be maintained or extended.
