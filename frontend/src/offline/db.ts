import { openDB, type IDBPDatabase } from 'idb'

const DB_NAME = 'bizibox-offline'
const DB_VERSION = 8
const MUTATIONS_STORE = 'mutations'
const MESSAGES_STORE = 'messages'
const CONTACTS_STORE = 'contacts'
const TASKS_STORE = 'tasks'
const ORDERS_STORE = 'orders'
const PRODUCTS_STORE = 'products'
const SUPPLIERS_STORE = 'suppliers'
const DRAFTS_STORE = 'drafts'
const MAX_MESSAGES = 500
const MAX_CONTACTS = 500
const MAX_TASKS = 200
const MAX_ORDERS = 200
const MAX_PRODUCTS = 200
const MAX_SUPPLIERS = 200

export interface DraftAttachment {
  name: string
  type: string
  size: number
  data: Blob
}

export interface Draft {
  contactId: number
  text: string
  attachments: DraftAttachment[]
  updatedAt: number
}

export interface PersistedFile {
  fileName: string
  mimeType: string
  data: ArrayBuffer
}

export interface OfflineMutation {
  id?: number
  method: string
  path: string
  body: string | null
  createdAt: number
  status: 'pending' | 'failed' | 'paused'
  error?: string
  localId?: number
  entityId?: number
  retry_count: number
  next_retry_at: number | null
  files?: PersistedFile[]
  formFields?: Record<string, string>
}

let dbPromise: Promise<IDBPDatabase> | null = null

function getDb(): Promise<IDBPDatabase> {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, DB_VERSION, {
      upgrade(db, _oldVersion, _newVersion, transaction) {
        if (!db.objectStoreNames.contains(MUTATIONS_STORE)) {
          const store = db.createObjectStore(MUTATIONS_STORE, {
            keyPath: 'id',
            autoIncrement: true,
          })
          store.createIndex('status', 'status')
        }
        if (_oldVersion < 4) {
          const store = transaction.objectStore(MUTATIONS_STORE)
          if (!store.indexNames.contains('status')) {
            store.createIndex('status', 'status')
          }
        }
        if (!db.objectStoreNames.contains(MESSAGES_STORE)) {
          const store = db.createObjectStore(MESSAGES_STORE, {
            keyPath: 'id',
          })
          store.createIndex('contact_id', 'contact_id')
          store.createIndex('created_at', 'created_at')
        } else if (_oldVersion < 2) {
          const store = transaction.objectStore(MESSAGES_STORE)
          if (!store.indexNames.contains('contact_id')) {
            store.createIndex('contact_id', 'contact_id')
          }
          if (!store.indexNames.contains('created_at')) {
            store.createIndex('created_at', 'created_at')
          }
        }
        if (!db.objectStoreNames.contains(CONTACTS_STORE)) {
          db.createObjectStore(CONTACTS_STORE, { keyPath: 'id' })
        }
        if (!db.objectStoreNames.contains(TASKS_STORE)) {
          db.createObjectStore(TASKS_STORE, { keyPath: 'id' })
        }
        if (!db.objectStoreNames.contains(ORDERS_STORE)) {
          db.createObjectStore(ORDERS_STORE, { keyPath: 'id' })
        }
        if (!db.objectStoreNames.contains(PRODUCTS_STORE)) {
          db.createObjectStore(PRODUCTS_STORE, { keyPath: 'id' })
        }
        if (!db.objectStoreNames.contains(SUPPLIERS_STORE)) {
          db.createObjectStore(SUPPLIERS_STORE, { keyPath: 'id' })
        }
        if (!db.objectStoreNames.contains(DRAFTS_STORE)) {
          db.createObjectStore(DRAFTS_STORE, { keyPath: 'contactId' })
        }
      },
    })
  }
  return dbPromise
}

/* === Drafts === */

export async function saveDraft(draft: Omit<Draft, 'updatedAt'>): Promise<void> {
  const db = await getDb()
  await db.put(DRAFTS_STORE, { ...draft, updatedAt: Date.now() })
}

export async function getDraft(contactId: number): Promise<Draft | null> {
  const db = await getDb()
  return (await db.get(DRAFTS_STORE, contactId)) ?? null
}

export async function clearDraft(contactId: number): Promise<void> {
  const db = await getDb()
  await db.delete(DRAFTS_STORE, contactId)
}

/* === Mutations === */

export async function addMutation(mutation: Omit<OfflineMutation, 'id' | 'createdAt'> & Partial<Pick<OfflineMutation, 'retry_count' | 'next_retry_at'>>): Promise<IDBValidKey> {
  const db = await getDb()
  return db.add(MUTATIONS_STORE, {
    ...mutation,
    retry_count: mutation.retry_count ?? 0,
    next_retry_at: mutation.next_retry_at ?? null,
    createdAt: Date.now(),
  })
}

export async function addFileMutation(mutation: {
  method: string
  path: string
  formFields: Record<string, string>
  files: PersistedFile[]
  localId?: number
}): Promise<IDBValidKey> {
  const db = await getDb()
  return db.add(MUTATIONS_STORE, {
    ...mutation,
    body: null,
    status: 'pending',
    retry_count: 0,
    next_retry_at: null,
    createdAt: Date.now(),
  })
}

export async function getPendingMutations(): Promise<OfflineMutation[]> {
  const db = await getDb()
  const all = await db.getAll(MUTATIONS_STORE)
  return all.filter(m => m.status === 'pending' || (m.status === 'failed' && m.retry_count < 999))
}

export async function getPendingOnly(): Promise<OfflineMutation[]> {
  const db = await getDb()
  const all = await db.getAll(MUTATIONS_STORE)
  return all.filter(m => m.status === 'pending')
}

export async function getPendingCount(): Promise<number> {
  const db = await getDb()
  const all = await db.getAll(MUTATIONS_STORE)
  return all.filter(m => m.status === 'pending').length
}

export async function markMutationDone(id: number, localId?: number, entityStore?: string): Promise<void> {
  const db = await getDb()
  const tx = db.transaction(MUTATIONS_STORE, 'readwrite')
  await tx.store.delete(id)
  await tx.done
  if (localId !== undefined) {
    const store = entityStore || MESSAGES_STORE
    await db.delete(store, localId)
  }
}

export async function markMutationFailed(id: number, error: string): Promise<void> {
  const db = await getDb()
  const tx = db.transaction(MUTATIONS_STORE, 'readwrite')
  const mutation = await tx.store.get(id)
  if (mutation) {
    mutation.status = 'failed'
    mutation.error = error
    mutation.retry_count = (mutation.retry_count ?? 0) + 1
    mutation.next_retry_at = Date.now() + Math.min(30_000, 1_000 * 2 ** mutation.retry_count)
    await tx.store.put(mutation)
  }
  await tx.done
}

export async function markMutationPaused(id: number, error: string): Promise<void> {
  const db = await getDb()
  const tx = db.transaction(MUTATIONS_STORE, 'readwrite')
  const mutation = await tx.store.get(id)
  if (mutation) {
    mutation.status = 'paused'
    mutation.error = error
    mutation.retry_count = (mutation.retry_count ?? 0) + 1
    mutation.next_retry_at = null
    await tx.store.put(mutation)
  }
  await tx.done
}

export async function getPausedMutations(): Promise<OfflineMutation[]> {
  const db = await getDb()
  const index = db.transaction(MUTATIONS_STORE, 'readonly').store.index('status')
  return index.getAll('paused')
}

export async function markMutationPermanentFailed(id: number, error: string): Promise<void> {
  const db = await getDb()
  const tx = db.transaction(MUTATIONS_STORE, 'readwrite')
  const mutation = await tx.store.get(id)
  if (mutation) {
    mutation.status = 'failed'
    mutation.error = error
    mutation.retry_count = 999
    mutation.next_retry_at = null
    await tx.store.put(mutation)
  }
  await tx.done
}

export async function getFailedMutations(): Promise<OfflineMutation[]> {
  const db = await getDb()
  const index = db.transaction(MUTATIONS_STORE, 'readonly').store.index('status')
  return index.getAll('failed')
}

export async function retryFailedMutation(id: number): Promise<void> {
  const db = await getDb()
  const tx = db.transaction(MUTATIONS_STORE, 'readwrite')
  const mutation = await tx.store.get(id)
  if (mutation) {
    mutation.status = 'pending'
    mutation.error = undefined
    mutation.retry_count = (mutation.retry_count ?? 0) + 1
    mutation.next_retry_at = null
    await tx.store.put(mutation)
  }
  await tx.done
}

export async function discardFailedMutation(id: number): Promise<void> {
  const db = await getDb()
  const tx = db.transaction(MUTATIONS_STORE, 'readwrite')
  await tx.store.delete(id)
  await tx.done
}

export async function discardMutation(id: number): Promise<void> {
  const db = await getDb()
  const tx = db.transaction(MUTATIONS_STORE, 'readwrite')
  await tx.store.delete(id)
  await tx.done
}

export async function updateMutationBody(id: number, body: string): Promise<void> {
  const db = await getDb()
  const tx = db.transaction(MUTATIONS_STORE, 'readwrite')
  const mutation = await tx.store.get(id)
  if (mutation) {
    mutation.body = body
    await tx.store.put(mutation)
  }
  await tx.done
}

export async function updateMessageContentInCache(id: number, content: string): Promise<void> {
  const db = await getDb()
  const msg = await db.get(MESSAGES_STORE, id)
  if (msg) {
    await db.put(MESSAGES_STORE, { ...msg, content })
  }
}

export async function clearFailedMutations(): Promise<void> {
  const db = await getDb()
  const index = db.transaction(MUTATIONS_STORE, 'readonly').store.index('status')
  const failed = await index.getAllKeys('failed')
  const tx = db.transaction(MUTATIONS_STORE, 'readwrite')
  for (const key of failed) {
    await tx.store.delete(key)
  }
  await tx.done
}

export async function resetMutationsForRetry(): Promise<void> {
  const db = await getDb()
  const index = db.transaction(MUTATIONS_STORE, 'readonly').store.index('status')
  const keys = new Set([...(await index.getAllKeys('failed')), ...(await index.getAllKeys('paused'))])
  const tx = db.transaction(MUTATIONS_STORE, 'readwrite')
  for (const key of keys) {
    const mutation = await tx.store.get(key)
    if (!mutation) continue
    mutation.status = 'pending'
    mutation.error = undefined
    mutation.retry_count = 0
    mutation.next_retry_at = null
    await tx.store.put(mutation)
  }
  await tx.done
}

export async function clearMutations(): Promise<void> {
  const db = await getDb()
  const index = db.transaction(MUTATIONS_STORE, 'readonly').store.index('status')
  const keys = new Set([...(await index.getAllKeys('failed')), ...(await index.getAllKeys('paused'))])
  const tx = db.transaction(MUTATIONS_STORE, 'readwrite')
  for (const key of keys) {
    await tx.store.delete(key)
  }
  await tx.done
}

/* === Messages === */

async function saveWithPrune(
  storeName: string,
  entities: unknown[],
  max: number,
  indexName?: string,
): Promise<void> {
  const db = await getDb()
  const tx = db.transaction(storeName, 'readwrite')
  const store = tx.store
  for (const entity of entities) {
    await store.put(entity)
  }
  const count = await store.count()
  if (count > max) {
    const keys = indexName
      ? await store.index(indexName).getAllKeys()
      : await store.getAllKeys()
    for (let i = 0; i < count - max && i < keys.length; i++) {
      await store.delete(keys[i])
    }
  }
  await tx.done
}

export async function saveMessages(messages: unknown[]): Promise<void> {
  return saveWithPrune(MESSAGES_STORE, messages, MAX_MESSAGES, 'created_at')
}

export async function getMessagesFromCache(): Promise<unknown[]> {
  const db = await getDb()
  const all = await db.getAll(MESSAGES_STORE)
  return all.sort((a, b) => {
    const da = new Date((a.created_at as string) || 0).getTime()
    const db = new Date((b.created_at as string) || 0).getTime()
    return db - da
  }).slice(0, MAX_MESSAGES)
}

export async function getMessageFromCache(id: number): Promise<unknown> {
  const db = await getDb()
  return db.get(MESSAGES_STORE, id)
}

export async function deleteMessageFromCache(id: number): Promise<void> {
  const db = await getDb()
  await db.delete(MESSAGES_STORE, id)
}

export async function getMaxMessageId(): Promise<number | null> {
  const db = await getDb()
  const keys = await db.getAllKeys(MESSAGES_STORE)
  let max: number | null = null
  for (const key of keys) {
    const id = typeof key === 'number' ? key : Number(key)
    if (max === null || id > max) max = id
  }
  return max
}

/* === Contacts === */

export async function saveContacts(contacts: unknown[]): Promise<void> {
  return saveWithPrune(CONTACTS_STORE, contacts, MAX_CONTACTS)
}

export async function getContactsFromCache(): Promise<unknown[]> {
  const db = await getDb()
  return db.getAll(CONTACTS_STORE)
}

export async function getContactFromCache(id: number): Promise<unknown> {
  const db = await getDb()
  return db.get(CONTACTS_STORE, id)
}

/* === Tasks === */

export async function saveTasks(tasks: unknown[]): Promise<void> {
  return saveWithPrune(TASKS_STORE, tasks, MAX_TASKS)
}

export async function getTasksFromCache(): Promise<unknown[]> {
  const db = await getDb()
  return db.getAll(TASKS_STORE)
}

export async function getTaskFromCache(id: number): Promise<unknown> {
  const db = await getDb()
  return db.get(TASKS_STORE, id)
}

/* === Orders === */

export async function saveOrders(orders: unknown[]): Promise<void> {
  return saveWithPrune(ORDERS_STORE, orders, MAX_ORDERS)
}

export async function getOrdersFromCache(): Promise<unknown[]> {
  const db = await getDb()
  return db.getAll(ORDERS_STORE)
}

export async function getOrderFromCache(id: number): Promise<unknown> {
  const db = await getDb()
  return db.get(ORDERS_STORE, id)
}

/* === Products === */

export async function saveProducts(products: unknown[]): Promise<void> {
  return saveWithPrune(PRODUCTS_STORE, products, MAX_PRODUCTS)
}

export async function getProductsFromCache(): Promise<unknown[]> {
  const db = await getDb()
  return db.getAll(PRODUCTS_STORE)
}

export async function getProductFromCache(id: number): Promise<unknown> {
  const db = await getDb()
  return db.get(PRODUCTS_STORE, id)
}

/* === Suppliers === */

export async function saveSuppliers(suppliers: unknown[]): Promise<void> {
  return saveWithPrune(SUPPLIERS_STORE, suppliers, MAX_SUPPLIERS)
}

export async function getSuppliersFromCache(): Promise<unknown[]> {
  const db = await getDb()
  return db.getAll(SUPPLIERS_STORE)
}

/* === Generic store helpers === */

const SAVE_FNS: Record<string, (entities: unknown[]) => Promise<void>> = {
  messages: saveMessages,
  contacts: saveContacts,
  tasks: saveTasks,
  orders: saveOrders,
  products: saveProducts,
  suppliers: saveSuppliers,
}

export function saveToStore(store: string, entity: unknown): Promise<void> {
  const fn = SAVE_FNS[store]
  if (!fn) return Promise.resolve()
  return fn([entity]).catch(() => {})
}

export async function deleteFromStore(store: string, id: number): Promise<void> {
  const db = await getDb()
  if (!db.objectStoreNames.contains(store)) return
  await db.delete(store, id)
}
