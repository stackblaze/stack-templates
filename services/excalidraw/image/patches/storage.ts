// StackBlaze build of Excalidraw: replaces excalidraw-app/data/firebase.ts.
//
// Upstream's app keeps collaboration rooms, room images and share-link images
// in excalidraw.com's own Firebase project. A self-hosted copy has no access
// to that, so this file keeps the same exports and the same client-side
// encryption, and stores the encrypted blobs on this instance instead
// (server.mjs, `/api/v2/rooms`, `/api/v2/files`). The server only ever sees
// ciphertext: the keys stay in the URL fragment.

import { reconcileElements } from "@excalidraw/excalidraw";
import { MIME_TYPES, toBrandedType } from "@excalidraw/common";
import { decompressData } from "@excalidraw/excalidraw/data/encode";
import {
  encryptData,
  decryptData,
} from "@excalidraw/excalidraw/data/encryption";
import { restoreElements } from "@excalidraw/excalidraw/data/restore";
import { getSceneVersion } from "@excalidraw/element";

import type { RemoteExcalidrawElement } from "@excalidraw/excalidraw/data/reconcile";
import type {
  ExcalidrawElement,
  FileId,
  OrderedExcalidrawElement,
} from "@excalidraw/element/types";
import type {
  AppState,
  BinaryFileData,
  BinaryFileMetadata,
  DataURL,
} from "@excalidraw/excalidraw/types";

import { getSyncableElements } from ".";

import type { SyncableExcalidrawElement } from ".";
import type Portal from "../collab/Portal";
import type { Socket } from "socket.io-client";

const API = "/api/v2";

// "/files/rooms/<room>" -> "/api/v2/files/rooms/<room>"
const filesUrl = (prefix: string, id: string) =>
  `${API}/${prefix.replace(/^\/+/, "")}/${encodeURIComponent(id)}`;

const toBase64 = (bytes: Uint8Array) => {
  let s = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  return btoa(s);
};

const fromBase64 = (b64: string) => {
  const s = atob(b64);
  const out = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) {
    out[i] = s.charCodeAt(i);
  }
  return out;
};

type StoredScene = {
  sceneVersion: number;
  iv: string; // base64
  ciphertext: string; // base64
};

type StoredSceneWithRev = StoredScene & { rev: number };

// Excalidraw+ import reads from excalidraw.com's storage, which this instance
// cannot write to.
export const uploadBytesToFirebase = async (
  _path: string,
  _data: Blob | Uint8Array,
  _metadata?: unknown,
) => {
  throw new Error(
    "Export to Excalidraw+ is not available on a self-hosted Excalidraw. Save to a file instead.",
  );
};

const encryptElements = async (
  key: string,
  elements: readonly ExcalidrawElement[],
): Promise<{ ciphertext: ArrayBuffer; iv: Uint8Array }> => {
  const json = JSON.stringify(elements);
  const encoded = new TextEncoder().encode(json);
  const { encryptedBuffer, iv } = await encryptData(key, encoded);

  return { ciphertext: encryptedBuffer, iv };
};

const decryptElements = async (
  data: StoredScene,
  roomKey: string,
): Promise<readonly ExcalidrawElement[]> => {
  const ciphertext = fromBase64(data.ciphertext) as Uint8Array<ArrayBuffer>;
  const iv = fromBase64(data.iv) as Uint8Array<ArrayBuffer>;

  const decrypted = await decryptData(iv, ciphertext, roomKey);
  const decodedData = new TextDecoder("utf-8").decode(
    new Uint8Array(decrypted),
  );
  return JSON.parse(decodedData);
};

class SceneVersionCache {
  private static cache = new WeakMap<Socket, number>();
  static get = (socket: Socket) => {
    return SceneVersionCache.cache.get(socket);
  };
  static set = (
    socket: Socket,
    elements: readonly SyncableExcalidrawElement[],
  ) => {
    SceneVersionCache.cache.set(socket, getSceneVersion(elements));
  };
}

export const isSavedToFirebase = (
  portal: Portal,
  elements: readonly ExcalidrawElement[],
): boolean => {
  if (portal.socket && portal.roomId && portal.roomKey) {
    const sceneVersion = getSceneVersion(elements);

    return SceneVersionCache.get(portal.socket) === sceneVersion;
  }
  // if no room exists, consider the room saved so that we don't unnecessarily
  // prevent unload (there's nothing we could do at that point anyway)
  return true;
};

export const saveFilesToFirebase = async ({
  prefix,
  files,
}: {
  prefix: string;
  files: { id: FileId; buffer: Uint8Array }[];
}) => {
  const erroredFiles: FileId[] = [];
  const savedFiles: FileId[] = [];

  await Promise.all(
    files.map(async ({ id, buffer }) => {
      try {
        const response = await fetch(filesUrl(prefix, id), {
          method: "PUT",
          headers: { "Content-Type": "application/octet-stream" },
          body: buffer as Uint8Array<ArrayBuffer>,
        });
        if (!response.ok) {
          throw new Error(`file upload failed: ${response.status}`);
        }
        savedFiles.push(id);
      } catch (error: any) {
        erroredFiles.push(id);
      }
    }),
  );

  return { savedFiles, erroredFiles };
};

const createSceneDocument = async (
  elements: readonly SyncableExcalidrawElement[],
  roomKey: string,
): Promise<StoredScene> => {
  const sceneVersion = getSceneVersion(elements);
  const { ciphertext, iv } = await encryptElements(roomKey, elements);
  return {
    sceneVersion,
    ciphertext: toBase64(new Uint8Array(ciphertext)),
    iv: toBase64(iv),
  };
};

const getRoom = async (roomId: string): Promise<StoredSceneWithRev | null> => {
  const response = await fetch(`${API}/rooms/${encodeURIComponent(roomId)}`, {
    cache: "no-store",
  });
  if (response.status === 204 || response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`room load failed: ${response.status}`);
  }
  return response.json();
};

// Like Firestore's runTransaction: write only if nobody saved in between
// (revision check on the server), otherwise reconcile again and retry.
const putRoom = async (
  roomId: string,
  scene: StoredScene,
  prevRev: number | null,
): Promise<boolean> => {
  const response = await fetch(`${API}/rooms/${encodeURIComponent(roomId)}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...(prevRev === null
        ? { "If-None-Match": "*" }
        : { "If-Match": String(prevRev) }),
    },
    body: JSON.stringify(scene),
  });
  if (response.status === 412) {
    return false;
  }
  if (response.status === 413) {
    // same wording Firestore uses, so Collab shows its "too large" message
    throw new Error("Scene is longer than the maximum allowed bytes");
  }
  if (!response.ok) {
    throw new Error(`room save failed: ${response.status}`);
  }
  return true;
};

export const saveToFirebase = async (
  portal: Portal,
  elements: readonly SyncableExcalidrawElement[],
  appState: AppState,
) => {
  const { roomId, roomKey, socket } = portal;
  if (
    // bail if no room exists as there's nothing we can do at this point
    !roomId ||
    !roomKey ||
    !socket ||
    isSavedToFirebase(portal, elements)
  ) {
    return null;
  }

  let storedScene: StoredScene | null = null;
  for (let attempt = 0; attempt < 5 && !storedScene; attempt++) {
    const prev = await getRoom(roomId);
    let next: StoredScene;
    if (!prev) {
      next = await createSceneDocument(elements, roomKey);
    } else {
      const prevStoredElements = getSyncableElements(
        restoreElements(await decryptElements(prev, roomKey), null),
      );
      const reconciledElements = getSyncableElements(
        reconcileElements(
          elements,
          prevStoredElements as OrderedExcalidrawElement[] as RemoteExcalidrawElement[],
          appState,
        ),
      );
      next = await createSceneDocument(reconciledElements, roomKey);
    }
    if (await putRoom(roomId, next, prev ? prev.rev : null)) {
      storedScene = next;
    }
  }
  if (!storedScene) {
    throw new Error("room save failed: too many concurrent saves");
  }

  const storedElements = getSyncableElements(
    restoreElements(await decryptElements(storedScene, roomKey), null),
  );

  SceneVersionCache.set(socket, storedElements);

  return toBrandedType<RemoteExcalidrawElement[]>(storedElements);
};

export const loadFromFirebase = async (
  roomId: string,
  roomKey: string,
  socket: Socket | null,
): Promise<readonly SyncableExcalidrawElement[] | null> => {
  const storedScene = await getRoom(roomId);
  if (!storedScene) {
    return null;
  }
  const elements = getSyncableElements(
    restoreElements(await decryptElements(storedScene, roomKey), null, {
      deleteInvisibleElements: true,
    }),
  );

  if (socket) {
    SceneVersionCache.set(socket, elements);
  }

  return elements;
};

export const loadFilesFromFirebase = async (
  prefix: string,
  decryptionKey: string,
  filesIds: readonly FileId[],
) => {
  const loadedFiles: BinaryFileData[] = [];
  const erroredFiles = new Map<FileId, true>();

  await Promise.all(
    [...new Set(filesIds)].map(async (id) => {
      try {
        const response = await fetch(filesUrl(prefix, id));
        if (response.status < 400) {
          const arrayBuffer = await response.arrayBuffer();

          const { data, metadata } = await decompressData<BinaryFileMetadata>(
            new Uint8Array(arrayBuffer),
            {
              decryptionKey,
            },
          );

          const dataURL = new TextDecoder().decode(data) as DataURL;

          loadedFiles.push({
            mimeType: metadata.mimeType || MIME_TYPES.binary,
            id,
            dataURL,
            created: metadata?.created || Date.now(),
            lastRetrieved: metadata?.created || Date.now(),
          });
        } else {
          erroredFiles.set(id, true);
        }
      } catch (error: any) {
        erroredFiles.set(id, true);
        console.error(error);
      }
    }),
  );

  return { loadedFiles, erroredFiles };
};
