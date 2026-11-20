const http = require("node:http");

const PORT = process.env.PORT || 3000;

const todos = [
  { id: 1, title: "Write the API", done: true },
  { id: 2, title: "Add a health check", done: true },
  { id: 3, title: "Ship it", done: false },
];

function send(res, status, body) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body, null, 2));
}

const server = http.createServer((req, res) => {
  if (req.url === "/health") return send(res, 200, { ok: true });
  if (req.url === "/todos") return send(res, 200, todos);
  send(res, 404, { error: "not found" });
});

server.listen(PORT, () => {
  console.log(`todo-api listening on http://localhost:${PORT}`);
});
