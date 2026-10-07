let seq = 0

export function generateLocalId(): number {
  return -(Date.now() + seq++)
}

export function isLocalId(id: number): boolean {
  return id < 0
}
