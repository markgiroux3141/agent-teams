# Critique v2

## Summary

The refactoring significantly improves code organization: **the monolithic 286-line script is now split into 5 focused modules**, **global state is properly encapsulated in a Game object**, and **all magic numbers are centralized in config.js with descriptive names**. Flight control logic is now well-commented. However, **the critical fix for the backward-facing plane is broken**: the `rotateY(Math.PI)` rotation applied in `plane.js` is immediately overwritten by the Euler angle assignment in `controls.js`, so the plane still flies backward (nose at +Z, motion in -Z). This is a regression—the fix was attempted but not executed correctly. Otherwise, the refactoring is clean and demonstrates good modularity.

## Evolution

### Fixed Since Last Round
- ✅ **Monolithic inline script (CRITICAL)**: Code is now split into 5 modules (config.js, terrain.js, plane.js, controls.js, camera.js). index.html is minimal (~150 lines with only initialization and loop).
- ✅ **Global state pollution (IMPORTANT)**: All state now encapsulated in a `Game` object (index.html:56–146) with clear ownership of scene, camera, renderer, plane, planeState.
- ✅ **Magic numbers scattered (IMPORTANT)**: Centralized in config.js with hierarchical organization (terrain, plane, flight, camera, physics, scene). All values documented and grouped by concern.
- ✅ **Missing comments on flight logic (NICE-TO-HAVE)**: Comprehensive JSDoc comments added to controls.js (lines 20–32) explaining angular velocity decay, gimbal lock prevention, YXZ rotation order, and Space/Ctrl pitch overrides.

### Still Present
- ⚠️ **Camera lerp uses fixed factor (NICE-TO-HAVE)**: camera.js line 16 still uses `lerpFactor: 0.1`. This is acceptable for a prototype but not improved.
- ⚠️ **Delta time capped at arbitrary 16ms (NICE-TO-HAVE)**: config.js line 57 still caps at `0.016`. This is acceptable for a prototype.
- ⚠️ **HUD updates DOM every frame (NICE-TO-HAVE)**: index.html lines 131–135 still update all HUD elements unconditionally. Acceptable for a prototype.

### Critical Regression
- ❌ **Plane orientation fix is broken (CRITICAL)**  
  The attempted fix for "plane flying backward" does not work. See below.

---

## Issues

### [CRITICAL] Plane orientation fix is broken—nose still points backward despite rotateY call
File: plane.js:46–48 (attempted fix), controls.js:109–112 (overwrites it)

The fix attempts to rotate the plane 180° around Y-axis when created (plane.js line 48: `planeGroup.rotateY(Math.PI);`). However, **the rotation is immediately overwritten and lost** when the plane's Euler angles are updated.

**Sequence of events:**
1. `createPlane()` creates a planeGroup and calls `rotateY(Math.PI)`. The planeGroup's rotation is now 180° around Y.
2. `createPlaneState()` initializes `planeState.rotation = new THREE.Euler(0, 0, 0, 'YXZ')` (identity).
3. On the first frame, `updatePlaneInput()` executes:
   ```javascript
   plane.rotation.y = planeState.rotation.y;  // Sets to 0, overwrites the π rotation
   plane.rotation.x = planeState.rotation.x;  // Sets to 0
   plane.rotation.z = planeState.rotation.z;  // Sets to 0
   ```
4. The plane's rotation is now identity (0, 0, 0), **losing the initial 180° rotation**.
5. The plane's nose (at local +Z) points in world +Z, but the plane travels in world -Z (direction vector at line 90).
6. The plane flies backward, nose pointing away from motion.

**Why the fix is broken**: Three.js Euler angles directly determine object rotation. Assigning to `rotation.y` overwrites the entire Y component, discarding any previous rotation applied via `rotateY()`.

**Consequence**: The plane still exhibits the original bug: backward flight, confusing visual feedback, player sees the plane's tail.

**Remedy idea**: Initialize `planeState.rotation` to `(0, Math.PI, 0, 'YXZ')` instead of `(0, 0, 0, 'YXZ')` so the 180° offset is preserved in the state. Or apply the 180° rotation to the plane geometry itself, not the group, so it's not affected by Euler assignment.

### [IMPORTANT] Euler rotation order set redundantly every frame
File: controls.js:81, 109

The rotation order is set twice per frame:
- Line 81: `planeState.rotation.order = 'YXZ';`
- Line 109: `plane.rotation.order = 'YXZ';`

And potentially a third time if the animation loop runs before input (though line 109 is in updatePlaneInput, so it happens once per frame). This is redundant—the order should be set once at initialization, not every frame.

**Why it matters**: Minor performance impact (setting an Euler order is cheap but unnecessary). More importantly, it clutters the code and suggests uncertainty about when the order is needed. If the order is set in multiple places, it's harder to track whether it's consistent.

**Remedy idea**: Set the order once in `createPlaneState()` (line 65), and remove the assignment in `updatePlaneInput()` (line 81). Keep the assignment in `plane.rotation.order = 'YXZ'` (line 109) since it's setting the 3D object's rotation (though it could also be removed if the order is managed in the state object).

### [IMPORTANT] Misleading comment about plane fix
File: plane.js:46–47

The comment claims:
```javascript
// CRITICAL FIX: Rotate plane 180° around Y-axis so nose points forward (in direction of travel)
// Without this, nose points backward while plane flies forward (direction -Z)
```

But as analyzed above, the fix doesn't actually apply (Euler assignment overwrites it). The comment is misleading because it claims the fix is applied, but it's lost on the first frame. This will confuse future developers who read the comment and assume the problem is solved.

**Remedy idea**: Either fix the underlying bug (see CRITICAL issue above), or update the comment to reflect the actual state of the code (e.g., "Attempted fix; see Issue #X—currently broken").

### [NICE-TO-HAVE] Plane geometry could be rotated instead of the group
File: plane.js:6–54

Minor architecture note: Instead of rotating the entire planeGroup (which causes issues with Euler assignment), the individual meshes (fuselage, wings, tail, nose) could be rotated 180° around Y. This would embed the orientation in the geometry and avoid conflicts with state-based Euler assignments.

**Why it matters**: Cosmetic. The current approach is reasonable; this is just an alternative that might be more robust.

---

## Stats
- **[CRITICAL: 1]** Plane orientation fix is broken—rotateY rotation overwritten by Euler assignment.
- **[IMPORTANT: 2]** Redundant Euler order assignment each frame; misleading comment.
- **[NICE-TO-HAVE: 1]** Alternative geometry rotation approach.

## Next Steps for Round 3
**Priority 1: Fix the plane orientation bug.** The backward plane is a regression from v1_redo's attempted fix. Initialize `planeState.rotation` to `(0, Math.PI, 0, 'YXZ')` to preserve the 180° offset, or apply the rotation to the geometry itself. Test by verifying the plane's nose points in the direction it moves.

**Priority 2: Simplify Euler order management.** Set the order once in `createPlaneState()`, not every frame.

**Priority 3: Update or remove the misleading comment.** Clarify whether the plane fix is intended or is a known bug.

The refactoring is otherwise excellent—modularization is clean, encapsulation is correct, and configuration is well-organized.
