import { test } from "node:test";
import assert from "node:assert/strict";
import { join } from "node:path";
import { homedir } from "node:os";
import { claudeConfigDir, cliPermissions, cliProjectSlug, parseRefs, refPrompt } from "../src/cli.js";

const CWD = "C:\\Users\\u\\AppData\\Local\\Temp\\cad-web-cli";
const SLUG = "C--Users-u-AppData-Local-Temp-cad-web-cli";
const RES = `C:/cfg/projects/${SLUG}`;
const TR = `Read(${RES}/**/tool-results/**)`;

test("claudeConfigDir: theo CLAUDE_CONFIG_DIR, mặc định ~/.claude", () => {
  assert.equal(claudeConfigDir({ CLAUDE_CONFIG_DIR: "C:\\Users\\x\\orca\\home\\" }), "C:/Users/x/orca/home");
  assert.equal(claudeConfigDir({}, "C:\\Users\\u"), "C:/Users/u/.claude");
  assert.equal(claudeConfigDir({ CLAUDE_CONFIG_DIR: "  " }, "/home/u"), "/home/u/.claude");
  assert.equal(claudeConfigDir({}), join(homedir(), ".claude").replace(/\\/g, "/"));
});

test("cliProjectSlug khớp cách CLI đặt tên thư mục", () => {
  assert.equal(cliProjectSlug(CWD), SLUG);
  assert.equal(cliProjectSlug("D:\\Dự án\\A_1"), "D--D---n-A-1");
});

test("không dự án, không ảnh/đính kèm: vẫn có Read cho tool-results", () => {
  const r = cliPermissions({ servers: [{ id: "litebim" }], allowed: [], imageRoots: [], cwd: CWD, configDir: "C:\\cfg" });
  assert.equal(r.tools, "Read");
  assert.deepEqual(r.allow, ["mcp__litebim", TR]);
  assert.deepEqual(r.addDirs, [RES]);   // chỉ thư mục của cwd này, không cả projects/ hay cả thư mục cấu hình
});

test("tool-results chỉ được Read; transcript .jsonl bị chặn", () => {
  const r = cliPermissions({ servers: [], allowed: [], imageRoots: [], cwd: "D:\\p", configDir: "C:/cfg", project: { dir: "D:\\p", shell: true } });
  const res = "C:/cfg/projects/D--p";
  assert.deepEqual(r.allow.filter(x => x.includes("/cfg")), [`Read(${res}/**/tool-results/**)`]);
  assert.deepEqual(r.addDirs, [res]);
  for (const t of ["Read", "Glob", "Grep"]) assert.ok(r.deny.includes(`${t}(${res}/*.jsonl)`) && r.deny.includes(`${t}(${res}/**/*.jsonl)`));
  assert.equal(r.tools, "Read,Glob,Grep,Write,Edit,Bash");
  assert.ok(r.allow.includes("Write(D:/p/**)") && r.allow.includes("Bash"));
});

test("slug quá dài: lùi về projects/ nhưng rule vẫn chỉ tool-results", () => {
  const r = cliPermissions({ servers: [], allowed: [], imageRoots: [], cwd: "C:\\" + "a".repeat(250), configDir: "C:/cfg" });
  assert.deepEqual(r.addDirs, ["C:/cfg/projects"]);
  assert.ok(r.allow.includes("Read(C:/cfg/projects/**/tool-results/**)"));
});

test("đủ thành phần: MCP theo tên, ask, ảnh, đính kèm", () => {
  const r = cliPermissions({ servers: [{ id: "a" }], allowed: ["x", "y"], ask: true, imageRoots: ["E:\\img"], attDir: "F:\\att", cwd: CWD, configDir: "C:/cfg/" });
  assert.deepEqual(r.allow, ["mcp__a__x", "mcp__a__y", "mcp__ask__ask_user", "Read(E:/img/**)", "Read(F:/att/**)", TR]);
  assert.equal(r.tools, "Read");
});

test("dự án tên tiếng Việt, thư mục có dấu cách: slug giống CLI, rule và --add-dir đúng thư mục tool-results", () => {
  const dir = "C:\\Users\\minhk\\CAD Studio\\projects\\vẽ nhà";
  assert.equal(cliProjectSlug(dir), "C--Users-minhk-CAD-Studio-projects-v--nh-");
  const r = cliPermissions({ servers: [], allowed: [], imageRoots: [], cwd: dir, configDir: "C:\\Users\\minhk\\.claude", project: { dir } });
  const res = "C:/Users/minhk/.claude/projects/C--Users-minhk-CAD-Studio-projects-v--nh-";
  assert.deepEqual(r.addDirs, [res]);
  assert.ok(r.allow.includes(`Read(${res}/**/tool-results/**)`));
  assert.ok(r.allow.includes("Read(C:/Users/minhk/CAD Studio/projects/vẽ nhà/**)"));
  assert.ok(r.deny.includes(`Read(${res}/*.jsonl)`));
});

test("tài liệu LiteBIM launcher đã lưu: lấy từ /status, cho Read/Grep/Glob + --add-dir đúng thư mục, prompt nêu đường dẫn", () => {
  const dir = "C:\\repo\\mcp\\launcher\\state\\litebim\\reference";
  const refs = parseRefs({ reference: {
    litebim: { available: true, path: dir + "\\litebim-reference.md", dir, version: "27.4.19", fetched_at: "2026-11-21T12:00:00" },
    litecad: { available: false, path: "x" } } });
  assert.equal(refs.length, 1);
  assert.equal(refs[0].title, "LiteBIM");
  assert.deepEqual(parseRefs({}), []);
  assert.deepEqual(parseRefs(null), []);
  const r = cliPermissions({ servers: [], allowed: [], imageRoots: [], cwd: CWD, configDir: "C:/cfg", refDirs: [dir] });
  assert.equal(r.tools, "Read,Glob,Grep");
  for (const t of ["Read", "Grep", "Glob"]) assert.ok(r.allow.includes(`${t}(C:/repo/mcp/launcher/state/litebim/reference/**)`));
  assert.ok(!r.allow.some(x => x.startsWith("Write(") || x.startsWith("Edit(")), "chỉ đọc");
  assert.deepEqual(r.addDirs, [RES, "C:/repo/mcp/launcher/state/litebim/reference"]);
  const p = refPrompt(refs);
  assert.match(p, /litebim-reference\.md/); assert.match(p, /offset\/limit/); assert.match(p, /thay vì gọi tool get_reference/); assert.match(p, /27\.4\.19/);
});
