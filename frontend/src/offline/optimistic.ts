import { generateLocalId } from './id'
import { enqueue } from './queue'

export interface FakeEntity {
  id: number
}

export type CreateFakeFn<T extends FakeEntity, D> = (data: D, localId: number) => T

export async function enqueueOptimistic<T extends FakeEntity, D>(
  data: D,
  createFake: CreateFakeFn<T, D>,
  saveFn: (entities: T[]) => Promise<void>,
  path: string,
): Promise<T> {
  const localId = generateLocalId()
  const bodyStr = JSON.stringify(data)
  const fake = createFake(data, localId)

  await saveFn([fake])
  await enqueue('POST', path, bodyStr, localId)

  return fake
}
