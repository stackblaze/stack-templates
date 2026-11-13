const test = require("node:test");
const assert = require("node:assert");

test("todos have titles", () => {
  const todos = [{ id: 1, title: "Write the API" }];
  assert.ok(todos.every((t) => t.title.length > 0));
});
