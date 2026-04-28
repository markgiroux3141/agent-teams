/**
 * camera.js - Chase camera logic
 * Updates camera position to follow plane from behind/above
 */

function updateCamera(camera, plane, planeState) {
  const cfg = CONFIG.camera;

  // Camera looks from behind and above the plane
  const cameraOffset = new THREE.Vector3(0, cfg.height, cfg.distance);
  cameraOffset.applyEuler(planeState.rotation);

  // Smoothly interpolate camera position toward target
  camera.position.lerp(
    plane.position.clone().add(cameraOffset),
    cfg.lerpFactor
  );

  // Camera looks slightly ahead of plane (not directly at it)
  const targetLook = plane.position.clone().add(new THREE.Vector3(0, cfg.lookAheadHeight, 0));
  camera.lookAt(targetLook);
}
