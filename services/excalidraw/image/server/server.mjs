// StackBlaze Excalidraw server: one process, one origin.
//
//  - serves the Excalidraw web app (static build in PUBLIC_DIR)
//  - /socket.io: the live collaboration relay (same protocol as
//    excalidraw/excalidraw-room: it forwards encrypted updates between the
//    people in a room and never sees the room key)
//  - /api/v2/rooms/<id>: the latest encrypted scene of a collaboration room
//  - /api/v2/files/<prefix>/<id>: encrypted images of rooms and share links
//  - /api/v2/scenes: encrypted "Shareable link" snapshots
//  - /api/v2/health: readiness (data directory writable)
//
// Everything stored is ciphertext made in the browser; the keys live only in
// the URL fragment (#room=<id>,<key> / #json=<id>,<key>), which browsers never
// send to the server.

import { createServer } from "node:http";
import { randomBytes } from "node:crypto";
import { createReadStream } from "node:fs";
import fs from "node:fs/promises";
import path from "node:path";
import { Server as SocketIO } from "socket.io";

const PORT = Number(process.env.PORT || 8080);
const PUBLIC_DIR = process.env.PUBLIC_DIR || "/app/public";
const DATA_DIR = process.env.DATA_DIR || "/data";
const MB = 1024 * 1024;
const LIMITS = {
  room: Number(process.env.MAX_ROOM_MB || 5) * MB,
  file: Number(process.env.MAX_FILE_MB || 5) * MB,
  scene: Number(process.env.MAX_SCENE_MB || 10) * MB,
};
// Refuse writes when the volume is nearly full, so one visitor cannot fill it.
const MIN_FREE_RATIO = 0.05;

const ID = /^[A-Za-z0-9_-]{1,64}$/;
const log = (...a) => console.log(new Date().toISOString(), ...a);

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".webmanifest": "application/manifest+json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
  ".woff": "font/woff",
  ".ttf": "font/ttf",
  ".txt": "text/plain; charset=utf-8",
  ".wasm": "application/wasm",
  ".map": "application/json",
};

const SECURITY_HEADERS = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "strict-origin-when-cross-origin",
};

function send(res, status, body, headers = {}) {
  const buf = typeof body === "string" || Buffer.isBuffer(body) ? body : JSON.stringify(body);
  res.writeHead(status, {
    ...SECURITY_HEADERS,
    "Content-Type": typeof body === "object" && !Buffer.isBuffer(body) ? "application/json" : "text/plain; charset=utf-8",
    "Cache-Control": "no-store",
    ...headers,
  });
  res.end(buf);
}

function readBody(req, limit) {
  return new Promise((resolve, reject) => {
    const declared = Number(req.headers["content-length"] || 0);
    if (declared > limit) {
      reject(Object.assign(new Error("too large"), { status: 413 }));
      req.resume();
      return;
    }
    const chunks = [];
    let size = 0;
    req.on("data", (c) => {
      size += c.length;
      if (size > limit) {
        reject(Object.assign(new Error("too large"), { status: 413 }));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

async function hasSpace() {
  try {
    const s = await fs.statfs(DATA_DIR);
    return s.blocks === 0 || s.bavail / s.blocks > MIN_FREE_RATIO;
  } catch {
    return true;
  }
}

// write-then-rename so a reader never sees half a file
async function writeAtomic(file, data) {
  await fs.mkdir(path.dirname(file), { recursive: true });
  const tmp = `${file}.${randomBytes(6).toString("hex")}.tmp`;
  await fs.writeFile(tmp, data, { mode: 0o600 });
  await fs.rename(tmp, file);
}

async function readOrNull(file) {
  try {
    return await fs.readFile(file);
  } catch (e) {
    if (e.code === "ENOENT") return null;
    throw e;
  }
}

// Room saves are serialised per room inside this process (single replica).
const roomLocks = new Map();
function withRoomLock(id, fn) {
  const prev = roomLocks.get(id) || Promise.resolve();
  const next = prev.then(fn, fn);
  roomLocks.set(id, next.catch(() => {}));
  return next;
}

async function handleApi(req, res, parts) {
  const [kind, ...rest] = parts;
  const method = req.method;

  if (kind === "health" && rest.length === 0) {
    const probe = path.join(DATA_DIR, ".health");
    await fs.writeFile(probe, String(Date.now()));
    return send(res, 200, { ok: true });
  }

  if (kind === "rooms" && rest.length === 1 && ID.test(rest[0])) {
    const file = path.join(DATA_DIR, "rooms", `${rest[0]}.json`);
    if (method === "GET") {
      const buf = await readOrNull(file);
      // 204, not 404: a new room is normal, and a 404 shows as an error in
      // the browser console
      if (!buf) return send(res, 204, "");
      return send(res, 200, buf, { "Content-Type": "application/json" });
    }
    if (method === "PUT") {
      if (!(await hasSpace())) return send(res, 507, { error: "storage full" });
      const body = await readBody(req, LIMITS.room);
      let scene;
      try {
        scene = JSON.parse(body.toString("utf8"));
      } catch {
        return send(res, 400, { error: "bad json" });
      }
      if (typeof scene?.sceneVersion !== "number" || typeof scene?.iv !== "string" || typeof scene?.ciphertext !== "string") {
        return send(res, 400, { error: "bad scene" });
      }
      return withRoomLock(rest[0], async () => {
        const prevBuf = await readOrNull(file);
        const prevRev = prevBuf ? JSON.parse(prevBuf.toString("utf8")).rev : null;
        const ifMatch = req.headers["if-match"];
        const ifNone = req.headers["if-none-match"];
        if (ifNone === "*" && prevBuf) return send(res, 412, { error: "exists" });
        if (ifMatch !== undefined && String(prevRev) !== ifMatch) return send(res, 412, { error: "changed" });
        const rev = (prevRev || 0) + 1;
        await writeAtomic(file, JSON.stringify({ rev, sceneVersion: scene.sceneVersion, iv: scene.iv, ciphertext: scene.ciphertext }));
        return send(res, 200, { rev });
      });
    }
    return send(res, 405, { error: "method" });
  }

  // files/rooms/<room>/<file> and files/shareLinks/<scene>/<file>
  if (kind === "files" && rest.length === 3 && ["rooms", "shareLinks"].includes(rest[0]) && ID.test(rest[1]) && ID.test(rest[2])) {
    const file = path.join(DATA_DIR, "files", rest[0], rest[1], rest[2]);
    if (method === "GET") {
      const buf = await readOrNull(file);
      if (!buf) return send(res, 404, { error: "not found" });
      return send(res, 200, buf, {
        "Content-Type": "application/octet-stream",
        "Cache-Control": "public, max-age=31536000, immutable",
      });
    }
    if (method === "PUT") {
      if (!(await hasSpace())) return send(res, 507, { error: "storage full" });
      const body = await readBody(req, LIMITS.file);
      // Files are content-addressed by the client: never overwrite one.
      if (await readOrNull(file)) return send(res, 200, { ok: true, existed: true });
      await writeAtomic(file, body);
      return send(res, 200, { ok: true });
    }
    return send(res, 405, { error: "method" });
  }

  if (kind === "scenes") {
    if (method === "POST" && rest.length === 0) {
      if (!(await hasSpace())) return send(res, 507, { error: "storage full" });
      let body;
      try {
        body = await readBody(req, LIMITS.scene);
      } catch (e) {
        // the app shows its "too big" message for this error class
        if (e.status === 413) return send(res, 413, { error_class: "RequestTooLargeError" });
        throw e;
      }
      const id = randomBytes(12).toString("base64url");
      await writeAtomic(path.join(DATA_DIR, "scenes", id), body);
      return send(res, 200, { id });
    }
    if (method === "GET" && rest.length === 1 && ID.test(rest[0])) {
      const buf = await readOrNull(path.join(DATA_DIR, "scenes", rest[0]));
      if (!buf) return send(res, 404, { error: "not found" });
      return send(res, 200, buf, { "Content-Type": "application/octet-stream" });
    }
    return send(res, 405, { error: "method" });
  }

  return send(res, 404, { error: "not found" });
}

async function serveStatic(req, res, pathname) {
  if (req.method !== "GET" && req.method !== "HEAD") return send(res, 405, "method not allowed");
  let rel = decodeURIComponent(pathname);
  if (rel.endsWith("/")) rel += "index.html";
  let file = path.normalize(path.join(PUBLIC_DIR, rel));
  if (!file.startsWith(PUBLIC_DIR + path.sep)) return send(res, 400, "bad path");
  let stat = await fs.stat(file).catch(() => null);
  if (!stat || !stat.isFile()) {
    // Unknown paths: the app (it reads its state from the URL fragment).
    if (path.extname(rel)) return send(res, 404, "not found");
    file = path.join(PUBLIC_DIR, "index.html");
    stat = await fs.stat(file);
  }
  const ext = path.extname(file);
  const immutable = file.includes(`${path.sep}assets${path.sep}`) || file.includes(`${path.sep}fonts${path.sep}`);
  const headers = {
    ...SECURITY_HEADERS,
    "Content-Type": MIME[ext] || "application/octet-stream",
    "Cache-Control": immutable ? "public, max-age=31536000, immutable" : "no-cache",
    Vary: "Accept-Encoding",
  };
  // gzip copies are made at image build time (Dockerfile)
  let serve = file;
  if (/\bgzip\b/.test(req.headers["accept-encoding"] || "")) {
    const gz = await fs.stat(`${file}.gz`).catch(() => null);
    if (gz) {
      serve = `${file}.gz`;
      headers["Content-Encoding"] = "gzip";
      stat = gz;
    }
  }
  headers["Content-Length"] = stat.size;
  res.writeHead(200, headers);
  if (req.method === "HEAD") return res.end();
  createReadStream(serve).pipe(res);
}

const server = createServer(async (req, res) => {
  try {
    const { pathname } = new URL(req.url, "http://x");
    if (pathname.startsWith("/api/v2/")) {
      const parts = pathname.slice("/api/v2/".length).split("/").filter(Boolean);
      return await handleApi(req, res, parts);
    }
    return await serveStatic(req, res, pathname);
  } catch (e) {
    if (e.status === 413) return send(res, 413, { error: "too large" });
    log("error", req.method, req.url.split("?")[0], e.message);
    if (!res.headersSent) send(res, 500, { error: "internal" });
    else res.destroy();
  }
});

// Collaboration relay. Only this instance's own pages may connect (the
// browser sends Origin on WebSocket and polling requests), so other sites
// cannot use it as a free relay.
const io = new SocketIO(server, {
  transports: ["websocket", "polling"],
  maxHttpBufferSize: LIMITS.room,
  allowRequest: (req, cb) => {
    const origin = req.headers.origin;
    if (!origin) return cb(null, true); // non-browser clients
    try {
      const o = new URL(origin);
      const host = req.headers["x-forwarded-host"] || req.headers.host;
      cb(null, o.host === host);
    } catch {
      cb(null, false);
    }
  },
});

io.on("connection", (socket) => {
  io.to(socket.id).emit("init-room");
  socket.on("join-room", async (roomID) => {
    if (typeof roomID !== "string" || !ID.test(roomID)) return;
    await socket.join(roomID);
    const sockets = await io.in(roomID).fetchSockets();
    if (sockets.length <= 1) {
      io.to(socket.id).emit("first-in-room");
    } else {
      socket.broadcast.to(roomID).emit("new-user", socket.id);
    }
    io.in(roomID).emit("room-user-change", sockets.map((s) => s.id));
  });

  socket.on("server-broadcast", (roomID, encryptedData, iv) => {
    if (!socket.rooms.has(roomID)) return;
    socket.broadcast.to(roomID).emit("client-broadcast", encryptedData, iv);
  });

  socket.on("server-volatile-broadcast", (roomID, encryptedData, iv) => {
    if (!socket.rooms.has(roomID)) return;
    socket.volatile.broadcast.to(roomID).emit("client-broadcast", encryptedData, iv);
  });

  socket.on("user-follow", async (payload) => {
    const target = payload?.userToFollow?.socketId;
    if (typeof target !== "string") return;
    const roomID = `follow@${target}`;
    if (payload.action === "FOLLOW") await socket.join(roomID);
    else if (payload.action === "UNFOLLOW") await socket.leave(roomID);
    else return;
    const sockets = await io.in(roomID).fetchSockets();
    io.to(target).emit("user-follow-room-change", sockets.map((s) => s.id));
  });

  socket.on("disconnecting", async () => {
    for (const roomID of Array.from(socket.rooms)) {
      const others = (await io.in(roomID).fetchSockets()).filter((s) => s.id !== socket.id);
      const isFollowRoom = roomID.startsWith("follow@");
      if (!isFollowRoom && others.length > 0) {
        socket.broadcast.to(roomID).emit("room-user-change", others.map((s) => s.id));
      }
      if (isFollowRoom && others.length === 0) {
        io.to(roomID.replace("follow@", "")).emit("broadcast-unfollow");
      }
    }
  });

  socket.on("disconnect", () => {
    socket.removeAllListeners();
    socket.disconnect();
  });
});

await fs.mkdir(DATA_DIR, { recursive: true });
server.listen(PORT, "0.0.0.0", () => log(`Excalidraw listening on :${PORT}, data in ${DATA_DIR}`));
for (const sig of ["SIGTERM", "SIGINT"]) {
  process.on(sig, () => {
    log(`${sig}, shutting down`);
    io.close();
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(0), 5000).unref();
  });
}
