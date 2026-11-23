// Gateway hay được bật từ trong một phiên Orca / Claude Code (launcher kế thừa env của terminal đó).
// Các biến phiên đó không được lọt sang `claude` mà CAD Studio gọi: CLAUDECODE / CLAUDE_CODE_* làm CLI tưởng mình là
// tiến trình con của phiên khác (socket nhắn tin, entrypoint, effort…), ORCA_* là token/đường dẫn riêng của Orca.
// CLAUDE_CONFIG_DIR (hồ sơ Claude) xử lý riêng: CAD_CLAUDE_CONFIG_DIR=default -> dùng ~/.claude; =<đường dẫn> -> dùng đường dẫn đó;
// không đặt -> giữ nguyên (đổi hồ sơ làm mất đăng nhập và không --resume được các phiên cũ, nên phải là lựa chọn rõ ràng).

const DROP_PREFIX = ["ORCA_", "CLAUDE_CODE_"];
const DROP_EXACT = ["CLAUDECODE", "CLAUDE_PID", "CLAUDE_EFFORT", "CLAUDE_AGENT_SDK_VERSION"];

/** Trả bản env đã lọc và danh sách biến đã bỏ. Không sửa env truyền vào. */
export function cleanEnv(env: NodeJS.ProcessEnv): { env: NodeJS.ProcessEnv; dropped: string[] } {
  const out: NodeJS.ProcessEnv = {}; const dropped: string[] = [];
  for (const [k, v] of Object.entries(env)) {
    if (DROP_EXACT.includes(k.toUpperCase()) || DROP_PREFIX.some(p => k.toUpperCase().startsWith(p))) dropped.push(k);
    else out[k] = v;
  }
  const want = env.CAD_CLAUDE_CONFIG_DIR?.trim();
  if (want === "default") { if (out.CLAUDE_CONFIG_DIR !== undefined) dropped.push("CLAUDE_CONFIG_DIR"); delete out.CLAUDE_CONFIG_DIR; }
  else if (want) out.CLAUDE_CONFIG_DIR = want;
  return { env: out, dropped };
}

/** Lọc ngay process.env của gateway (gọi một lần lúc khởi động, trước khi spawn bất cứ gì). */
export function cleanProcessEnv() {
  const { env, dropped } = cleanEnv(process.env);
  for (const k of Object.keys(process.env)) if (!(k in env)) delete process.env[k];
  Object.assign(process.env, env);
  if (dropped.length) console.log(`env: bỏ ${dropped.length} biến của phiên Orca/Claude Code (${dropped.filter(k => !k.startsWith("ORCA_")).slice(0, 6).join(", ")}${dropped.length > 6 ? ", …" : ""})`);
  console.log(`env: hồ sơ Claude = ${process.env.CLAUDE_CONFIG_DIR || "~/.claude (mặc định)"}`);
}

