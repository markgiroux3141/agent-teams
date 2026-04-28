# Critique v1

## Summary

This is a functional weekend prototype that demonstrates all required features (terrain, plane, camera, controls, fog). However, it fails the fundamental modularity requirement: **286 lines of unstructured script in a single HTML file** when the DONE_CRITERIA anticipates separate JavaScript modules. Additionally, the plane's visual orientation is inverted relative to its direction of travel, breaking user feedback in the flight simulator. These issues prevent the code from being maintainable or extendable beyond this initial demo.

## Issues

### [CRITICAL] Entire application crammed into single inline script block
File: src/index.html:44-330
The DONE_CRITERIA explicitly describes the deliverable as `src/index.html` plus `src/[additional JS files]` for modules like terrain, camera, and controls. Instead, all 286 lines of logic—scene setup, terrain generation, plane creation, input handling, flight physics, camera logic, and animation loop—are jammed into a single `<script>` block. This is unmaintainable even for a weekend prototype. At 5-6 screens of code, this violates the "readable, single-responsibility files" requirement. The cost: if the next developer wants to swap terrain generation or tweak camera behavior, they must edit a 286-line blob with no boundaries. Split this into at minimum:
- `terrain.js` (generateTerrain function)
- `plane.js` (createPlane function + plane physics)
- `camera.js` (updateCamera function)
- `controls.js` (input handling + updatePlaneInput function)
- Keep index.html minimal: load these modules, initialize the scene, start the loop.

### [IMPORTANT] Plane model is oriented backward
File: src/index.html:118-162, 244
The plane's nose cone is positioned at `z = 1.8` (local +Z), and all other fuselage parts extend along +Z. However, the flight direction is calculated as `(0, 0, -1)` rotated by plane rotation (line 244). This means the plane **travels in world -Z** but the **nose points in world +Z**—opposite directions. The player sees the plane's tail, not its nose. This breaks the core visual feedback: a flight simulator where the plane appears to fly backward is confusing and wrong. Fix: either rotate the plane 180° around Y when creating it (e.g., add `planeGroup.rotateY(Math.PI)` at line 159), or change the initial direction to `(0, 0, 1)` and adjust the camera offset accordingly.

### [IMPORTANT] Global state pollution with no encapsulation
File: src/index.html:46-64, 115, 164, 167-172, 175, 187-274, 309-330
All major objects (`scene`, `camera`, `renderer`, `terrain`, `plane`, `planeState`, `keys`) are global variables. This makes the code fragile: any future feature (pause, restart, second scene) requires careful mutation of globals or namespace management. A minimal fix: wrap the entire logic in an IIFE or object to create local scope:
```javascript
const Game = {
  scene: new THREE.Scene(),
  camera: new THREE.PerspectiveCamera(...),
  // ...
  init() { ... },
  update(deltaTime) { ... },
  render() { ... }
};
```

### [IMPORTANT] Magic numbers scattered throughout without explanation
File: src/index.html:70, 86-93, 122-139, 157, 188-189, 278-279, 314
Terrain generation: `width=512`, `height=512`, `scale=5`, `amplitude=50`, `frequency=0.01`, `octaves=4`, amplitude decay `0.5`, frequency scale `2`.
Plane geometry: dimensions (0.4, 0.4, 3), (5, 0.2, 1.5), (2, 1, 0.3), positions (0, 0, 1.8), (0, 0, -1.2).
Plane physics: `rotationSpeed=2`, initial position `(0, 100, 0)`, minimum altitude `10`.
Camera: `distance=30`, `height=20`, lerp factor `0.1`.
Delta time cap: `0.016` (assumed 60 FPS).
These values control the feel and scale of the entire demo. They are invisible in the current structure. Centralize them at the top of each module or in a shared config object so designers can tune them without reading function bodies.

### [NICE-TO-HAVE] Missing explanatory comments on non-obvious flight logic
File: src/index.html:187-274
The flight control system mixes angular velocity decay, pitch/yaw/roll coupling, gimbal lock prevention (line 241), and vertical boost overrides (lines 227-232). The code is correct but opaque. For example:
- Line 241 clamps pitch to prevent gimbal lock, but doesn't explain why.
- Lines 227-232 apply space/ctrl as angular velocity overrides, but the interaction with forward/backward input (lines 200-206) is not intuitive.
- The YXZ rotation order (lines 170, 235, 264) is unusual and not justified.
Add a 2-3 line comment above `updatePlaneInput` explaining the input model, gimbal lock, and why YXZ is chosen.

### [NICE-TO-HAVE] Camera lerp uses fixed factor instead of frame-rate independent decay
File: src/index.html:285-287
`camera.position.lerp(..., 0.1)` interpolates the camera by 10% of the distance toward the target, every frame. If the frame rate drops (e.g., 30 FPS), the camera lags more noticeably. A better approach:
```javascript
const lerpSpeed = 5.0; // units per second
camera.position.lerp(target, Math.min(deltaTime * lerpSpeed / camera.position.distanceTo(target), 1));
```
Or use exponential decay: `camera.position.lerp(target, 1 - Math.exp(-deltaTime * lerpSpeed))`. For a prototype, the current approach is acceptable, but the lag may be jarring at lower frame rates.

### [NICE-TO-HAVE] Delta time capped at hardcoded 16ms
File: src/index.html:314
`const deltaTime = Math.min((now - lastTime) / 1000, 0.016);` caps at 16ms (60 FPS). This prevents the plane from jumping far if a frame is missed, but 16ms is arbitrary. If the frame rate drops to 30 FPS (33ms per frame), deltaTime is capped at 16ms, and the plane moves at half speed relative to wall time. A more robust approach:
```javascript
const deltaTime = Math.min((now - lastTime) / 1000, 0.05); // cap at 50ms / 20 FPS
```
This is minor—acceptable for a prototype—but may cause confusing behavior if the page lags.

### [NICE-TO-HAVE] HUD updates DOM elements every frame even if values don't change
File: src/index.html:295-299
`updateHUD()` writes to `#speed`, `#altitude`, `#position` every frame, even if the values are identical to the previous frame. Modern browsers optimize this, but it's not free. For a game running at 60 FPS, this is 60 DOM writes per second. Better:
```javascript
let lastDisplayedSpeed = -1;
if (planeState.speed.toFixed(0) !== lastDisplayedSpeed) {
  document.getElementById('speed').textContent = `Speed: ${planeState.speed.toFixed(0)}`;
  lastDisplayedSpeed = planeState.speed.toFixed(0);
}
```
This is premature optimization for a tiny prototype and not blocking.

---

## Stats
- **[CRITICAL: 1]** Monolithic structure blocks maintainability and future work.
- **[IMPORTANT: 3]** Plane orientation bug, global state, scattered magic numbers.
- **[NICE-TO-HAVE: 4]** Comments, camera lerp, delta time cap, DOM updates.
