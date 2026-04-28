/**
 * controls.js - Input handling and flight physics
 * Manages keyboard input and updates plane state with flight dynamics
 */

// Input state tracking
const keys = {};

function setupInputHandlers() {
  window.addEventListener('keydown', (e) => {
    keys[e.key.toLowerCase()] = true;
    if (e.key === ' ') e.preventDefault(); // Prevent page scroll on spacebar
  });

  window.addEventListener('keyup', (e) => {
    keys[e.key.toLowerCase()] = false;
  });
}

/**
 * updatePlaneInput - Apply player input and flight physics to plane state
 *
 * Flight controls use angular velocity with exponential decay:
 * - Pitch (nose up/down) and yaw (turn left/right) apply angular velocity from keys
 * - Angular velocity decays each frame (lines ~205, 214, 223) when keys release
 * - Pitch is clamped to [-π/2, π/2] to prevent gimbal lock (line 241)
 * - YXZ rotation order prevents gimbal lock issues where pitch affects yaw
 * - Space/Ctrl override pitch bounds to allow climbing/descending beyond forward/backward range
 *
 * @param {THREE.Group} plane - The plane 3D model
 * @param {Object} planeState - Plane flight state (velocity, rotation, angularVelocity)
 * @param {number} deltaTime - Frame time in seconds
 */
function updatePlaneInput(plane, planeState, deltaTime) {
  const cfg = CONFIG.flight;

  // Read input keys
  const forward = keys['w'] || keys['arrowup'];
  const backward = keys['s'] || keys['arrowdown'];
  const left = keys['a'] || keys['arrowleft'];
  const right = keys['d'] || keys['arrowright'];
  const up = keys[' ']; // Space to climb
  const down = keys['control']; // Ctrl to descend

  // Pitch (nose up/down) - forward pitches down, backward pitches up
  if (forward) {
    planeState.angularVelocity.x = -cfg.rotationSpeed;
  } else if (backward) {
    planeState.angularVelocity.x = cfg.rotationSpeed;
  } else {
    planeState.angularVelocity.x *= cfg.angularDecay;
  }

  // Yaw (turn left/right)
  if (left) {
    planeState.angularVelocity.y = cfg.rotationSpeed;
  } else if (right) {
    planeState.angularVelocity.y = -cfg.rotationSpeed;
  } else {
    planeState.angularVelocity.y *= cfg.angularDecay;
  }

  // Roll (banking) - half strength of yaw
  if (left) {
    planeState.angularVelocity.z = cfg.rotationSpeed * cfg.rollFactor;
  } else if (right) {
    planeState.angularVelocity.z = -cfg.rotationSpeed * cfg.rollFactor;
  } else {
    planeState.angularVelocity.z *= cfg.angularDecay;
  }

  // Vertical movement (Space/Ctrl override pitch limits to allow climb/descend)
  if (up) {
    planeState.angularVelocity.x = Math.max(planeState.angularVelocity.x, -cfg.rotationSpeed * cfg.rollFactor);
  }
  if (down) {
    planeState.angularVelocity.x = Math.min(planeState.angularVelocity.x, cfg.rotationSpeed * cfg.rollFactor);
  }

  // Apply angular velocity to rotation (order already set in createPlaneState)
  planeState.rotation.y += planeState.angularVelocity.y * deltaTime;
  planeState.rotation.x += planeState.angularVelocity.x * deltaTime;
  planeState.rotation.z += planeState.angularVelocity.z * deltaTime;

  // Clamp pitch to avoid gimbal lock
  planeState.rotation.x = Math.max(cfg.pitchClampMin, Math.min(cfg.pitchClampMax, planeState.rotation.x));

  // Calculate forward direction from rotation
  const direction = new THREE.Vector3(0, 0, -1); // Plane points forward in -Z
  direction.applyEuler(planeState.rotation);

  // Base speed in forward direction
  planeState.speed = cfg.baseSpeed;
  planeState.velocity.copy(direction).multiplyScalar(planeState.speed);

  // Apply vertical input (Space climbs, Ctrl descends)
  if (up) {
    planeState.velocity.y = Math.min(planeState.velocity.y + cfg.verticalBoostUp, cfg.maxVerticalSpeedUp);
  }
  if (down) {
    planeState.velocity.y = Math.max(planeState.velocity.y - cfg.verticalBoostDown, cfg.minVerticalSpeedDown);
  }

  // Update plane position
  plane.position.add(planeState.velocity.clone().multiplyScalar(deltaTime));

  // Update plane rotation (order set once at initialization in Game.init)
  plane.rotation.y = planeState.rotation.y;
  plane.rotation.x = planeState.rotation.x;
  plane.rotation.z = planeState.rotation.z;

  // Keep plane above minimum altitude (don't let it go too deep underground)
  if (plane.position.y < CONFIG.plane.minAltitude) {
    plane.position.y = CONFIG.plane.minAltitude;
    planeState.velocity.y = 0;
  }
}
