import { spawn } from "node:child_process";

// Popup báo ở góc dưới phải màn hình, bật thẳng từ gateway trên máy này.
// Không dùng toast của Windows: Focus assist / chế độ toàn màn hình hay nuốt mất toast (chỉ vào Action Center).
// Đây là cửa sổ nhỏ luôn nằm trên, không chiếm focus, tự tắt sau 15 giây (rê chuột lên thì giữ lại), có nút ✕ để tắt.
// Bấm vào popup: đưa cửa sổ trình duyệt đang mở CAD Studio lên trước; không thấy thì mở trang CAD Studio.
const CS = `
using System; using System.Text; using System.Drawing; using System.Windows.Forms; using System.Runtime.InteropServices;
public class CadPopup : Form {
  protected override bool ShowWithoutActivation { get { return true; } }
  protected override CreateParams CreateParams { get { var p = base.CreateParams; p.ExStyle |= 0x08000000 | 0x80 | 0x8; return p; } }
  public CadPopup(string title, string body) {
    FormBorderStyle = FormBorderStyle.None; ShowInTaskbar = false; TopMost = true; StartPosition = FormStartPosition.Manual;
    BackColor = Color.FromArgb(32, 33, 36); Width = 380; Height = 110; Padding = new Padding(16, 12, 16, 12);
    var b = new Label { Text = body, ForeColor = Color.FromArgb(200, 200, 205), Dock = DockStyle.Fill, Font = new Font("Segoe UI", 9.5f), AutoEllipsis = true };
    var t = new Label { Text = title, ForeColor = Color.White, Dock = DockStyle.Top, Height = 28, Font = new Font("Segoe UI Semibold", 11f), AutoEllipsis = true };
    var x = new Label { Text = "✕", ForeColor = Color.FromArgb(170, 170, 175), Font = new Font("Segoe UI", 10f), AutoSize = false,
      Size = new Size(28, 28), TextAlign = ContentAlignment.MiddleCenter, Location = new Point(Width - 34, 6), Cursor = Cursors.Hand };
    x.MouseEnter += (s, e) => { x.ForeColor = Color.White; x.BackColor = Color.FromArgb(60, 61, 66); };
    x.MouseLeave += (s, e) => { x.ForeColor = Color.FromArgb(170, 170, 175); x.BackColor = BackColor; };
    Controls.Add(x); Controls.Add(b); Controls.Add(t); t.Padding = new Padding(0, 0, 30, 0);
    var wa = Screen.PrimaryScreen.WorkingArea; Location = new Point(wa.Right - Width - 16, wa.Bottom - Height - 16);
    Cursor = Cursors.Hand; t.Cursor = Cursors.Hand; b.Cursor = Cursors.Hand;
    EventHandler close = (s, e) => Close(); EventHandler hit = (s, e) => { Clicked = true; Close(); };
    Click += hit; t.Click += hit; b.Click += hit; x.Click += close;   // ✕ chỉ tắt, không nhảy sang trình duyệt
    var tm = new Timer { Interval = 15000 }; tm.Tick += close; tm.Start();
    // Rê chuột lên popup thì dừng đếm giờ, rời ra thì đếm lại từ đầu.
    var hover = new Timer { Interval = 250 }; hover.Tick += (s, e) => {
      if (Bounds.Contains(Cursor.Position)) { tm.Stop(); tm.Start(); } }; hover.Start();
  }
  public bool Clicked;
  delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] static extern void keybd_event(byte k, byte s, int f, IntPtr e);
  /** Đưa cửa sổ có tab CAD Studio đang hiện lên trước. Trả false nếu không thấy (tab đang bị che bởi tab khác). */
  public static bool FocusStudio() {
    IntPtr found = IntPtr.Zero;
    EnumWindows((h, l) => {
      if (!IsWindowVisible(h)) return true;
      var sb = new StringBuilder(512); GetWindowText(h, sb, 512);
      var t = sb.ToString();
      if (t.Contains("CAD Studio") && !t.StartsWith("CAD Studio:")) { found = h; return false; }
      return true;
    }, IntPtr.Zero);
    if (found == IntPtr.Zero) return false;
    if (IsIconic(found)) ShowWindow(found, 9);
    keybd_event(0x12, 0, 0, IntPtr.Zero); keybd_event(0x12, 0, 2, IntPtr.Zero);   // Alt: Windows mới cho đổi cửa sổ trước
    SetForegroundWindow(found);
    return true;
  }
}`;
const SCRIPT = `Add-Type -ReferencedAssemblies System.Windows.Forms,System.Drawing -TypeDefinition @'
${CS}
'@
[System.Windows.Forms.Application]::EnableVisualStyles()
$u = [Text.Encoding]::UTF8; $f = New-Object CadPopup ($u.GetString([Convert]::FromBase64String($env:CAD_TOAST_TITLE))), ($u.GetString([Convert]::FromBase64String($env:CAD_TOAST_BODY)))
[System.Windows.Forms.Application]::Run($f)
if ($f.Clicked -and -not [CadPopup]::FocusStudio() -and $env:CAD_TOAST_URL) { Start-Process $u.GetString([Convert]::FromBase64String($env:CAD_TOAST_URL)) }`;
const b64 = (s: string) => Buffer.from(s, "utf8").toString("base64");  // tránh lỗi dấu tiếng Việt qua biến môi trường
const ENCODED = Buffer.from(SCRIPT, "utf16le").toString("base64");

export function toast(title: string, body: string, url = ""): { ok: boolean; error?: string } {
  if (process.platform !== "win32") return { ok: false, error: "Chỉ có trên Windows." };
  const p = spawn("powershell.exe", ["-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-EncodedCommand", ENCODED], {
    windowsHide: true, stdio: ["ignore", "ignore", "pipe"],  // KHÔNG dùng detached: PowerShell thoát ngay, popup không hiện
    env: { ...process.env, CAD_TOAST_TITLE: b64(title.slice(0, 120)), CAD_TOAST_BODY: b64(body.slice(0, 240)),
      CAD_TOAST_URL: /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?\//.test(url) ? b64(url) : "" },
  });
  let err = ""; p.stderr?.on("data", d => { if (err.length < 4000) err += d; });
  p.on("error", e => console.error("toast:", e.message));
  p.on("exit", c => { if (c) console.error("toast: popup lỗi", c, err.replace(/<[^>]+>/g, " ").replace(/_x000D__x000A_/g, "\n").slice(0, 1500)); });
  p.unref();
  return { ok: true };
}
