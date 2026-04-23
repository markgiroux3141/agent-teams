/**
 * CONFIG - Centralized configuration for the flight simulator
 * Contains all magic numbers and tunable parameters
 */
const CONFIG = {
  terrain: {
    width: 512,
    height: 512,
    scale: 5,
    amplitude: 50,
    frequency: 0.01,
    octaves: 4,
    color: 0x2d7d2d
  },
  plane: {
    initialPosition: [0, 100, 0],
    minAltitude: 10,
    geometry: {
      fuselageSize: [0.4, 0.4, 3],
      fuselageColor: 0xff0000,
      wingsSize: [5, 0.2, 1.5],
      wingsColor: 0xff4444,
      tailSize: [2, 1, 0.3],
      tailColor: 0xffaa00,
      noseRadius: 0.3,
      noseHeight: 1,
      noseSegments: 8,
      noseColor: 0xffff00,
      tailOffsetZ: -1.2,
      tailOffsetY: 0.2,
      noseOffsetZ: 1.8
    }
  },
  flight: {
    acceleration: 50,
    rotationSpeed: 2,
    baseSpeed: 150,
    verticalBoostUp: 100,
    verticalBoostDown: 100,
    maxVerticalSpeedUp: 150,
    minVerticalSpeedDown: -100,
    angularDecay: 0.9,
    rollFactor: 0.5,
    pitchClampMin: -Math.PI / 2,
    pitchClampMax: Math.PI / 2
  },
  camera: {
    fov: 75,
    near: 0.1,
    far: 10000,
    distance: 30,
    height: 20,
    lerpFactor: 0.1,
    lookAheadHeight: 5
  },
  physics: {
    deltaTimeCap: 0.016  // 60 FPS cap
  },
  scene: {
    skyColor: 0x87ceeb,
    fogColor: 0x87ceeb,
    fogNear: 1000,
    fogFar: 5000,
    ambientLightColor: 0xffffff,
    ambientLightIntensity: 0.6,
    directionalLightColor: 0xffffff,
    directionalLightIntensity: 0.8,
    directionalLightPosition: [5, 10, 5],
    shadowMapSize: 2048
  }
};
