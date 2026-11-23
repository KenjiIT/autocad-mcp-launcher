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

/**
 * Hộp chọn KIỂU MỚI của Windows (giống Explorer: thanh địa chỉ, Quick access, ô tìm kiếm, nút "Select Folder"),
 * qua COM IFileOpenDialog (FOS_PICKFOLDERS cho thư mục). Là một chương trình Windows nhỏ dịch một lần bằng Add-Type,
 * lưu cạnh dữ liệu gateway (như openwith). Owner là cửa sổ đang ở trên cùng (trình duyệt vừa bấm) nên hộp hiện lên trên.
 * Trả đường dẫn qua stdout dạng UTF-8 (giữ dấu tiếng Việt). Mã thoát: 0 = đã chọn, 1 = Hủy, khác = lỗi.
 */
export const PICK_EXE = join(DATA_DIR, "bin", "pick-v3.exe");
export const PICK_SRC = `using System; using System.IO; using System.Text; using System.Runtime.InteropServices;
[ComImport, Guid("DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7")] class FileOpenDialogCo {}
[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] struct Spec { public string Name; public string Pattern; }
[ComImport, Guid("43826d1e-e718-42ee-bc55-a1e261c37bfe"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IShellItem { void BindToHandler(IntPtr a, ref Guid b, ref Guid c, out IntPtr d); void GetParent(out IShellItem p);
  void GetDisplayName(uint sigdn, [MarshalAs(UnmanagedType.LPWStr)] out string name); void GetAttributes(uint m, out uint a); void Compare(IShellItem o, uint h, out int r); }
[ComImport, Guid("b63ea76d-1f85-456f-a19c-48159efa858b"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IShellItemArray { void BindToHandler(IntPtr a, ref Guid b, ref Guid c, out IntPtr d); void GetPropertyStore(int f, ref Guid r, out IntPtr p);
  void GetPropertyDescriptionList(IntPtr k, ref Guid r, out IntPtr p); void GetAttributes(int f, uint m, out uint a); void GetCount(out uint n); void GetItemAt(uint i, out IShellItem it); void EnumItems(out IntPtr e); }
[ComImport, Guid("d57c7288-d4ad-4768-be02-9d969532d960"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IFileOpenDialog {
  [PreserveSig] int Show(IntPtr owner);
  void SetFileTypes(uint n, [MarshalAs(UnmanagedType.LPArray)] Spec[] specs); void SetFileTypeIndex(uint i); void GetFileTypeIndex(out uint i);
  void Advise(IntPtr e, out uint c); void Unadvise(uint c); void SetOptions(uint o); void GetOptions(out uint o);
  void SetDefaultFolder(IShellItem si); void SetFolder(IShellItem si); void GetFolder(out IShellItem si); void GetCurrentSelection(out IShellItem si);
  void SetFileName([MarshalAs(UnmanagedType.LPWStr)] string n); void GetFileName([MarshalAs(UnmanagedType.LPWStr)] out string n);
  void SetTitle([MarshalAs(UnmanagedType.LPWStr)] string t); void SetOkButtonLabel([MarshalAs(UnmanagedType.LPWStr)] string t);
  void SetFileNameLabel([MarshalAs(UnmanagedType.LPWStr)] string t); void GetResult(out IShellItem si); void AddPlace(IShellItem si, int where);
  void SetDefaultExtension([MarshalAs(UnmanagedType.LPWStr)] string e); void Close(int hr); void SetClientGuid(ref Guid g); void ClearClientData(); void SetFilter(IntPtr f);
  void GetResults(out IShellItemArray a); void GetSelectedItems(out IShellItemArray a); }
public static class Pick {
  [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
  static extern void SHCreateItemFromParsingName(string path, IntPtr bc, [MarshalAs(UnmanagedType.LPStruct)] Guid riid, out IShellItem item);
  [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
  [DllImport("user32.dll")] static extern IntPtr GetWindow(IntPtr h, uint cmd);
  [DllImport("user32.dll")] static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] static extern bool BringWindowToTop(IntPtr h);
  struct RECT { public int L, T, R, B; }
  const uint SIGDN_FILESYSPATH = 0x80058000;
  static string B64(string s) { return Encoding.UTF8.GetString(Convert.FromBase64String(s)); }
  [STAThread] public static int Main(string[] a) {
    // a[0] = folder|files, a[1] = tiêu đề (base64 UTF-8), a[2] = thư mục mở sẵn (base64, có thể rỗng), a[3] = bộ lọc "Tên|*.a;*.b" (base64)
    try {
      bool files = a.Length > 0 && a[0] == "files";
      var d = (IFileOpenDialog)new FileOpenDialogCo();
      uint o; d.GetOptions(out o);
      o |= 0x40 | 0x800;                                    // FOS_FORCEFILESYSTEM | FOS_PATHMUSTEXIST
      o |= files ? (0x200u | 0x1000u) : 0x20u;             // nhiều file + FILEMUSTEXIST  |  FOS_PICKFOLDERS
      d.SetOptions(o);
      if (a.Length > 1 && a[1].Length > 0) d.SetTitle(B64(a[1]));
      if (a.Length > 2 && a[2].Length > 0) { string start = B64(a[2]);
        if (Directory.Exists(start)) { IShellItem si; SHCreateItemFromParsingName(start, IntPtr.Zero, typeof(IShellItem).GUID, out si); d.SetFolder(si); } }
      if (files && a.Length > 3 && a[3].Length > 0) {
        var parts = B64(a[3]).Split('\\n'); var specs = new Spec[parts.Length];
        for (int i = 0; i < parts.Length; i++) { var kv = parts[i].Split('|'); specs[i] = new Spec { Name = kv[0], Pattern = kv[1] }; }
        d.SetFileTypes((uint)specs.Length, specs);
      }
      // Owner riêng: cửa sổ vô hình, luôn trên cùng, đặt giữa cửa sổ đang ở trước (trình duyệt vừa bấm) để hộp hiện lên trên và đúng màn hình.
      // Không dùng thẳng cửa sổ của trình duyệt làm owner: owner thuộc tiến trình khác có thể làm hộp bị ẩn hoặc tự hủy khi nó đổi trạng thái.
      var fg = GetForegroundWindow(); RECT r = new RECT(); bool has = fg != IntPtr.Zero && GetWindowRect(fg, out r);
      var owner = new System.Windows.Forms.Form { TopMost = true, ShowInTaskbar = false, FormBorderStyle = System.Windows.Forms.FormBorderStyle.None,
        Opacity = 0, StartPosition = System.Windows.Forms.FormStartPosition.Manual, Size = new System.Drawing.Size(1, 1) };
      if (has) owner.Location = new System.Drawing.Point((r.L + r.R) / 2 - 320, (r.T + r.B) / 2 - 220);
      owner.Show();
      keybd_event(0x12, 0, 0, UIntPtr.Zero); keybd_event(0x12, 0, 2, UIntPtr.Zero);   // nhả ALT: Windows cho phép tiến trình nền đưa cửa sổ lên trước
      SetForegroundWindow(owner.Handle); owner.Activate();
      // Hộp mở rồi thì ép nó lên trên cùng và lấy focus (Windows hay để cửa sổ của tiến trình nền nằm sau trình duyệt).
      int tries = 0; var timer = new System.Windows.Forms.Timer { Interval = 100 };
      timer.Tick += (s, e) => {
        var h = GetWindow(owner.Handle, 6);              // GW_ENABLEDPOPUP: hộp chọn đang mở của owner
        if (h != IntPtr.Zero && h != owner.Handle) {
          SetWindowPos(h, new IntPtr(-1), 0, 0, 0, 0, 0x0043);   // HWND_TOPMOST, NOSIZE|NOMOVE|SHOWWINDOW
          keybd_event(0x12, 0, 0, UIntPtr.Zero); keybd_event(0x12, 0, 2, UIntPtr.Zero);
          BringWindowToTop(h); SetForegroundWindow(h);
          if (++tries >= 3) timer.Stop();
        } else if (++tries > 50) timer.Stop();
      };
      timer.Start();
      int hr = d.Show(owner.Handle);
      timer.Stop();
      owner.Close();
      if (hr == unchecked((int)0x800704C7)) return 1;    // người dùng bấm Hủy
      if (hr != 0) return 3;
      var sb = new StringBuilder();
      IShellItemArray arr; d.GetResults(out arr); uint n; arr.GetCount(out n);
      for (uint i = 0; i < n; i++) { IShellItem it; arr.GetItemAt(i, out it); string p; it.GetDisplayName(SIGDN_FILESYSPATH, out p); sb.Append(p).Append('\\n'); }
      var bytes = Encoding.UTF8.GetBytes(sb.ToString());
      using (var so = Console.OpenStandardOutput()) so.Write(bytes, 0, bytes.Length);
      return 0;
    } catch (Exception e) { var b = Encoding.UTF8.GetBytes(e.Message); using (var se = Console.OpenStandardError()) se.Write(b, 0, b.Length); return 4; }
  }
}`;
let buildingPick: Promise<void> | null = null;
function ensurePickExe(): Promise<void> {
  if (existsSync(PICK_EXE)) return Promise.resolve();
  if (!buildingPick) {
    mkdirSync(dirname(PICK_EXE), { recursive: true });
    const src = join(dirname(PICK_EXE), "pick.cs");
    writeFileSync(src, PICK_SRC, "utf8");
    buildingPick = ps(`Add-Type -OutputType WindowsApplication -ReferencedAssemblies System.Windows.Forms,System.Drawing -OutputAssembly ${quote(PICK_EXE)} -TypeDefinition (Get-Content -Raw -Encoding UTF8 -LiteralPath ${quote(src)})`)
      .then(() => undefined).finally(() => { buildingPick = null; });
  }
  return buildingPick;
}
const b64 = (s: string) => Buffer.from(s, "utf8").toString("base64");

/** Tham số dòng lệnh cho pick-v1.exe (base64 để tiêu đề/đường dẫn có dấu tiếng Việt, dấu cách, nháy không bị vỡ). Tách riêng để kiểm thử. */
export function pickArgs(mode: "folder" | "files", title: string, start?: string, filters: [string, string][] = []): string[] {
  return [mode, b64(title), start ? b64(start) : "", filters.length ? b64(filters.map(f => f.join("|")).join("\n")) : ""];
}

/** Chạy hộp kiểu mới. null = không dùng được (lỗi) -> gọi hộp cũ; [] = người dùng Hủy. */
async function modernPick(args: string[]): Promise<string[] | null> {
  if (process.platform !== "win32") return null;
  try { await ensurePickExe(); } catch (e: any) { console.error("pick: không dịch được hộp chọn kiểu mới:", e?.message ?? e); return null; }
  return new Promise(res => {
    const p = spawn(PICK_EXE, args, { windowsHide: false, stdio: ["ignore", "pipe", "pipe"] });
    const out: Buffer[] = []; let err = "";
    p.stdout.on("data", d => out.push(d)); p.stderr.on("data", d => { err += d; });
    p.on("error", e => { console.error("pick:", e.message); res(null); });
    p.on("close", code => {
      if (code === 1) return res([]);
      if (code !== 0) { console.error(`pick: hộp kiểu mới lỗi (mã ${code}) ${err}`); return res(null); }
      res(Buffer.concat(out).toString("utf8").split("\n").filter(Boolean));
    });
  });
}

/** Trả đường dẫn thư mục người dùng chọn, hoặc null nếu bấm Hủy. Lỗi hộp kiểu mới thì lùi về hộp cũ. */
export async function pickFolder(title: string, start?: string): Promise<string | null> {
  const m = await modernPick(pickArgs("folder", title, start));
  if (m) return m[0] ?? null;
  const out = await ps(`$d = New-Object System.Windows.Forms.FolderBrowserDialog; $d.Description = ${quote(title)}; $d.ShowNewFolderButton = $true;` +
    (start ? ` $d.SelectedPath = ${quote(start)};` : "") +
    ` if ($d.ShowDialog($owner) -eq 'OK') { $d.SelectedPath }`);
  return out || null;
}

const FILE_FILTERS: [string, string][] = [["Hồ sơ dự án (DWG, DXF, PDF, Excel, Word, ảnh)", "*.dwg;*.dxf;*.pdf;*.xlsx;*.xls;*.docx;*.png;*.jpg"], ["Mọi file", "*.*"]];

/** Trả danh sách file người dùng chọn (có thể nhiều), rỗng nếu bấm Hủy. */
export async function pickFiles(title: string, start?: string): Promise<string[]> {
  const m = await modernPick(pickArgs("files", title, start, FILE_FILTERS));
  if (m) return m;
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
