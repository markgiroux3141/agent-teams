/**
 * terrain.js - Procedural terrain generation
 * Uses multi-octave sine/cosine wave simulation for heightmap-based terrain
 */

function generateTerrain(scene) {
  const cfg = CONFIG.terrain;

  const geometry = new THREE.PlaneGeometry(cfg.width * cfg.scale, cfg.height * cfg.scale, cfg.width, cfg.height);
  geometry.rotateX(-Math.PI / 2); // Rotate to be horizontal

  const positionAttribute = geometry.getAttribute('position');
  const positions = positionAttribute.array;

  // Multi-octave noise simulation using sine/cosine waves
  for (let i = 0; i < positions.length; i += 3) {
    const x = positions[i];
    const z = positions[i + 2];

    let height = 0;
    let amplitude = cfg.amplitude;
    let frequency = cfg.frequency;

    for (let octave = 0; octave < cfg.octaves; octave++) {
      height += amplitude * Math.sin(x * frequency) * Math.cos(z * frequency);
      amplitude *= 0.5;
      frequency *= 2;
    }

    positions[i + 1] = height; // y = height
  }

  positionAttribute.needsUpdate = true;
  geometry.computeVertexNormals();

  const material = new THREE.MeshPhongMaterial({
    color: cfg.color,
    wireframe: false,
    side: THREE.DoubleSide
  });

  const terrain = new THREE.Mesh(geometry, material);
  terrain.receiveShadow = true;
  scene.add(terrain);

  return terrain;
}
