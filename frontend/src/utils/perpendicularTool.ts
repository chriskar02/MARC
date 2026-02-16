export function ensurePerpendicular(pose: any, delta: { dx: number; dy: number; dz: number }) {
  // Simplified helper: keep tool orientation perpendicular to XY plane by
  // forcing alpha and beta to zero and returning the same delta. In a full
  // implementation this would compute required joint changes (IK) to move
  // the tool tip while maintaining perpendicularity.
  // pose: { x, y, z, alpha, beta, gamma }
  return { ...delta, targetOrientation: { alpha: 0, beta: 0, gamma: pose?.gamma ?? 0 } };
}
