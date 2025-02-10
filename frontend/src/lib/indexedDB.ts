import { openDB } from "idb";

const DB_NAME: string = "KeyValueDB";
const STORE_NAME: string = "KeyValueStore";

const dbPromise = openDB(DB_NAME, 1, {
  upgrade(db) {
    if (!db.objectStoreNames.contains(STORE_NAME)) {
      db.createObjectStore(STORE_NAME);
    }
  },
});

export async function setItem<T>(key: string, value: T): Promise<void> {
  const db = await dbPromise;
  await db.put(STORE_NAME, value, key);
}

export async function getItem<T>(key: string): Promise<T | undefined> {
  const db = await dbPromise;
  return db.get(STORE_NAME, key);
}

export async function removeItem(key: string): Promise<void> {
  const db = await dbPromise;
  await db.delete(STORE_NAME, key);
}
