import { Component, StrictMode, useEffect, useRef, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { health, listProjects, niceError, setCurrentProject } from "./api";
import { FilesPanel } from "./FilesPanel";
import { UsageBar } from "./UsageBar";
import { Chat } from "./Chat";
import { SettingsPage } from "./SettingsPage";
import { DialogHost } from "./Dialog";
import "@fontsource-variable/lexend-deca";
import "@fontsource-variable/geist-mono";
import "./style.css";

/** Bản LOCAL: một người dùng, không đăng nhập. Web + gateway + MCP chạy trên cùng máy, cạnh AutoCAD MCP Launcher. */
function App() {
  const [status, setStatus] = useState<string>("chưa kết nối");
  const [problem, setProblem] = useState("");
  const [tab, setTab] = useState<"chat" | "settings">("chat");
  const [epoch, setEpoch] = useState(0); // tăng mỗi lần kết nối lại để Chat tải lại danh sách skill
  const [project, setProject] = useState(() => { try { return localStorage.getItem("cad-project") || ""; } catch { return ""; } });
  setCurrentProject(project);   // trước khi Chat gọi API trong lần dựng này
  const [openConv, setOpenConv] = useState<string | undefined>();   // mở sẵn cuộc trò chuyện này sau khi đổi dự án
  const [filesTick, setFilesTick] = useState(0);                    // tăng sau mỗi lượt chat để cột file tải lại
  const [treeKey, setTreeKey] = useState(0);
  const pickProject = (id: string, conv?: string) => {
    setCurrentProject(id); setOpenConv(conv); setProject(id);
    try { localStorage.setItem("cad-project", id); } catch { /* bỏ qua */ }
  };
  // Chưa biết dự án (máy mới, hoặc dự án đã nhớ bị xóa): chọn dự án đầu tiên — gateway tự tạo "master" nếu chưa có.
  useEffect(() => {
    listProjects().then(l => { if (l.length && !l.some(p => p.id === project)) pickProject(l[0].id); }).catch(() => {});
  }, [project]);

  const wasOk = useRef(false);
  const connect = async () => {
    try {
      const h = await health();
      const up = h.servers.filter(x => x.ok).length;
      setStatus(h.servers.length > 1 ? `MCP OK: ${up}/${h.servers.length} server, ${h.tools} tool` : `MCP OK: ${h.tools} tool`);
      setProblem(up < h.servers.length ? `Server chưa nối được: ${h.servers.filter(x => !x.ok).map(x => x.name).join(", ")}. Mở Cài đặt để xem lỗi từng server.` : "");
      if (!wasOk.current) setEpoch(n => n + 1); // vừa nối được: tải lại danh sách skill
      wasOk.current = true;
    } catch (e) {
      wasOk.current = false;
      const m = niceError(e);
      setStatus(/Gateway đang chạy/.test(m) ? "Lỗi: chưa nối được MCP" : "Lỗi: chưa kết nối"); setProblem(m);
    }
  };
  // Không có nút Kết nối: tự kiểm tra khi mở trang, rồi thử lại mỗi 15 giây.
  useEffect(() => {
    void connect();
    const t = setInterval(() => { void connect(); }, 15000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="app">
      <DialogHost />
      <header>
        <span className="brand"><svg className="mark" viewBox="0 0 24 24" aria-hidden="true"><rect width="24" height="24" rx="6" /><path d="M7 17 12 7l5 10M9.2 13.6h5.6" /></svg>CAD Studio</span>
        <nav className="seg" aria-label="Chế độ">
          <button className={tab === "chat" ? "on" : ""} onClick={() => setTab("chat")}>Chat</button>
          <button className={tab === "settings" ? "on" : ""} onClick={() => setTab("settings")}>Cài đặt</button>
        </nav>
        <span className={`status ${status.startsWith("MCP OK") ? "ok" : status.startsWith("Lỗi") ? "bad" : ""}`} role="status">{status}</span>
      </header>
      <p className="banner" role="alert">{problem}</p>
      {tab === "settings" ? <SettingsPage reloadKey={status} onSaved={() => void connect()} onMcpChanged={() => { wasOk.current = false; void connect(); }} />
        : !project ? <div className="full" /> : <div className="full ws">
            <Chat key={`${project}:${openConv ?? ""}`} epoch={epoch} project={project} treeKey={treeKey} initialOpen={openConv}
              onSelectProject={id => pickProject(id)} onOpenOther={(id, conv) => pickProject(id, conv)} onTurnDone={() => setFilesTick(n => n + 1)} onProjectsChanged={() => setFilesTick(n => n + 1)} />
            <FilesPanel project={project} tick={filesTick} />
          </div>}
      <UsageBar tick={filesTick} />
    </div>
  );
}

/** Lỗi khi dựng giao diện hiện thành thông báo, không để trang trắng. */
class Boundary extends Component<{ children: ReactNode }, { err?: Error }> {
  state: { err?: Error } = {};
  static getDerivedStateFromError(err: Error) { return { err }; }
  render() {
    return this.state.err
      ? <div className="login"><div role="alert" style={{ maxWidth: 480 }}><h1>Giao diện gặp lỗi</h1><p className="desc">{this.state.err.message}</p><button onClick={() => location.reload()}>Tải lại trang</button></div></div>
      : this.props.children;
  }
}

createRoot(document.getElementById("root")!).render(<StrictMode><Boundary><App /></Boundary></StrictMode>);
