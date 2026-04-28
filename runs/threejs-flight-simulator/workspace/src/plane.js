/**
 * plane.js - Plane model and state management
 * Creates the 3D plane model and maintains flight state
 */

function createPlane(scene) {
  const planeGroup = new THREE.Group();
  const g = CONFIG.plane.geometry;

  // Fuselage (body)
  const fuselageGeometry = new THREE.BoxGeometry(...g.fuselageSize);
  const fuselageMaterial = new THREE.MeshPhongMaterial({ color: g.fuselageColor });
  const fuselage = new THREE.Mesh(fuselageGeometry, fuselageMaterial);
  fuselage.castShadow = true;
  fuselage.receiveShadow = true;
  planeGroup.add(fuselage);

  // Wings
  const wingGeometry = new THREE.BoxGeometry(...g.wingsSize);
  const wingMaterial = new THREE.MeshPhongMaterial({ color: g.wingsColor });
  const wings = new THREE.Mesh(wingGeometry, wingMaterial);
  wings.position.y = 0;
  wings.castShadow = true;
  wings.receiveShadow = true;
  planeGroup.add(wings);

  // Tail
  const tailGeometry = new THREE.BoxGeometry(...g.tailSize);
  const tailMaterial = new THREE.MeshPhongMaterial({ color: g.tailColor });
  const tail = new THREE.Mesh(tailGeometry, tailMaterial);
  tail.position.z = g.tailOffsetZ;
  tail.position.y = g.tailOffsetY;
  tail.castShadow = true;
  tail.receiveShadow = true;
  planeGroup.add(tail);

  // Nose indicator (small cone)
  const noseGeometry = new THREE.ConeGeometry(g.noseRadius, g.noseHeight, g.noseSegments);
  const noseMaterial = new THREE.MeshPhongMaterial({ color: g.noseColor });
  const nose = new THREE.Mesh(noseGeometry, noseMaterial);
  nose.position.z = g.noseOffsetZ;
  nose.castShadow = true;
  nose.receiveShadow = true;
  planeGroup.add(nose);

  // Fix plane orientation: Rotate geometry 180° around Y-axis so nose points forward
  // The plane model's nose points to local +Z, but flight direction is -Z.
  // Rotating each mesh 180° around Y embeds the correct orientation in the geometry,
  // so the nose visually points in -Z (direction of travel) while the flight state
  // remains clean (rotation = identity). This separates visual geometry from flight physics.
  fuselage.rotateY(Math.PI);
  wings.rotateY(Math.PI);
  tail.rotateY(Math.PI);
  nose.rotateY(Math.PI);

  planeGroup.position.set(...CONFIG.plane.initialPosition);
  planeGroup.castShadow = true;
  scene.add(planeGroup);

  return planeGroup;
}

/**
 * Initialize plane state
 * Manages velocity, speed, rotation, and angular velocity
 * NOTE: rotation starts at identity (0, 0, 0). Plane orientation is baked into the mesh geometry
 * via 180° rotations in createPlane(), not here. This keeps flight state clean and separate from
 * visual geometry, preventing confusion between rotational physics and visual orientation.
 */
function createPlaneState() {
  return {
    velocity: new THREE.Vector3(0, 0, 0),
    speed: 0,
    rotation: new THREE.Euler(0, 0, 0, 'YXZ'), // yaw, pitch, roll in YXZ order (prevents gimbal lock)
    angularVelocity: new THREE.Vector3(0, 0, 0), // x=pitch, y=yaw, z=roll
  };
}
