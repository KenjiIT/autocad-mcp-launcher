import { spawn } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

// Hộp chọn thư mục / file THẬT của Windows, mở ngay trên máy chạy gateway (bản local: cũng là máy người dùng).
// Trình duyệt không cho web biết đường dẫn đầy đủ của thư mục được chọn, nên phải hỏi qua gateway.
const DATA_DIR = process.env.CAD_DATA_DIR ?? fileURLToPath(new URL("../data/", import.meta.url));

function ps(script: string): Promise<string> {
  if (process.platform !== "win32") return Promise.reject(new Error("Hộp chọn thư mục chỉ có trên Windows; hãy dán đường dẫn."));
  const full = `[Console]::OutputEncoding=[Text.Encoding]::UTF8; Add-Type -AssemblyName System.Windows.Forms;` +
    `$owner = New-Object System.Windows.Forms.Form -Property @{ TopMost = $true; ShowInTaskbar = $false; WindowState = 'Minimized' }; ${script}`;
  return new Promise((resolve, reject) => {
    const p = spawn("powershell.exe", ["-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-Command", full], { windowsHide: true });
    let out = "", err = "";
    p.stdout.setEncoding("utf8").on("data", d => { out += d; });
    p.stderr.setEncoding("utf8").on("data", d => { err += d; });
    p.on("error", reject);
    p.on("close", code => code === 0 ? resolve(out.trim()) : reject(new Error(err.trim() || `PowerShell thoát với mã ${code}`)));
  });
}

const quote = (s: string) => `'${s.replace(/'/g, "''")}'`;

/** Trả đường dẫn thư mục người dùng chọn, hoặc null nếu bấm Hủy. */
export async function pickFolder(title: string, start?: string): Promise<string | null> {
  const out = await ps(`$d = New-Object System.Windows.Forms.FolderBrowserDialog; $d.Description = ${quote(title)}; $d.ShowNewFolderButton = $true;` +
    (start ? ` $d.SelectedPath = ${quote(start)};` : "") +
    ` if ($d.ShowDialog($owner) -eq 'OK') { $d.SelectedPath }`);
  return out || null;
}

/** Trả danh sách file người dùng chọn (có thể nhiều), rỗng nếu bấm Hủy. */
export async function pickFiles(title: string): Promise<string[]> {
  const out = await ps(`$d = New-Object System.Windows.Forms.OpenFileDialog; $d.Title = ${quote(title)}; $d.Multiselect = $true;` +
    ` $d.Filter = 'Hồ sơ dự án (*.dwg;*.dxf;*.pdf;*.xlsx;*.xls;*.docx;*.png;*.jpg)|*.dwg;*.dxf;*.pdf;*.xlsx;*.xls;*.docx;*.png;*.jpg|Mọi file (*.*)|*.*';` +
    ` if ($d.ShowDialog($owner) -eq 'OK') { $d.FileNames -join [char]10 }`);
  return out ? out.split(/\r?\n/).filter(Boolean) : [];
}

/**
 * Hộp "Mở bằng" (Open with) của Windows cho một file, qua API SHOpenWithDialog.
 * Đã thử và loại: `rundll32 shell32.dll,OpenAs_RunDLL` (im lặng khi đường dẫn có dấu cách), PowerShell gọi API
 * (gateway chạy ẩn thì hộp không hiện), động từ "openas" qua wscript (không làm gì). Cách chạy được: một chương trình
 * Windows nhỏ (không console) chỉ gọi SHOpenWithDialog — dịch một lần bằng PowerShell Add-Type, lưu cạnh dữ liệu gateway.
 */
const OW_EXE = join(DATA_DIR, "bin", "openwith-v1.exe");
const OW_SRC = `using System; using System.Runtime.InteropServices;
public static class P {
  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
  struct OPENASINFO { public string cszFile; public string cszClass; public int oaifInFlags; }
  [DllImport("shell32.dll", CharSet = CharSet.Unicode)] static extern int SHOpenWithDialog(IntPtr hwnd, ref OPENASINFO info);
  [STAThread] public static int Main(string[] a) {
    if (a.Length < 1) return 2;
    var i = new OPENASINFO { cszFile = a[0], oaifInFlags = 7 };   // cho phép đăng ký + nhớ cho loại file + mở luôn
    return SHOpenWithDialog(IntPtr.Zero, ref i);
  }
}`;
let building: Promise<void> | null = null;
function ensureOpenWithExe(): Promise<void> {
  if (existsSync(OW_EXE)) return Promise.resolve();
  if (!building) {
    mkdirSync(dirname(OW_EXE), { recursive: true });
    const src = join(dirname(OW_EXE), "openwith.cs");
    writeFileSync(src, OW_SRC, "utf8");
    building = ps(`Add-Type -OutputType WindowsApplication -OutputAssembly ${quote(OW_EXE)} -TypeDefinition (Get-Content -Raw -LiteralPath ${quote(src)})`)
      .then(() => undefined).finally(() => { building = null; });
  }
  return building;
}
export async function openWithDialog(full: string) {
  await ensureOpenWithExe();
  spawn(OW_EXE, [full], { detached: true, stdio: "ignore" }).unref();
}

/** Đưa file/thư mục vào Thùng rác của Windows (khôi phục được), không xóa hẳn. */
export async function toRecycleBin(full: string, isDir: boolean): Promise<void> {
  const fn = isDir ? "DeleteDirectory" : "DeleteFile";
  // Truyền enum rõ kiểu: DeleteDirectory có nhiều overload, chuỗi 'OnlyErrorDialogs' bị PowerShell khớp nhầm.
  await ps(`Add-Type -AssemblyName Microsoft.VisualBasic;` +
    ` [Microsoft.VisualBasic.FileIO.FileSystem]::${fn}(${quote(full)}, [Microsoft.VisualBasic.FileIO.UIOption]::OnlyErrorDialogs, [Microsoft.VisualBasic.FileIO.RecycleOption]::SendToRecycleBin)`);
}
