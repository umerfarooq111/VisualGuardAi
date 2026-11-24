import { useEffect, useRef, useState, type ChangeEvent, type ReactNode } from "react";
import {
  type MediaItem,
  type MediaUploadResponse,
  listVideos,
  uploadVideo,
  validateVideoFile,
  ALLOWED_VIDEO_EXTENSIONS,
  MAX_UPLOAD_SIZE_MB,
} from "./services/videoService";
import {
  type ProcessingTaskResponse,
  createProcessingTask,
  listProcessingTasks,
} from "./services/processingService";
import {
  type ProcessedMediaItem,
  listAllOutputs,
  getOutputPreviewUrl,
  getOutputDownloadUrl,
} from "./services/outputsService";

type Screen =
  | "landing"
  | "dashboard"
  | "upload"
  | "detectionType"
  | "detecting"
  | "detect"
  | "settings"
  | "processing"
  | "preview"
  | "history"
  | "saved";

type IconName =
  | "shield"
  | "arrow"
  | "scan"
  | "cursor"
  | "video"
  | "sliders"
  | "grid"
  | "upload"
  | "history"
  | "folder"
  | "help"
  | "settings"
  | "logout"
  | "image"
  | "film"
  | "clock"
  | "check"
  | "chevron"
  | "eye"
  | "eyeOff"
  | "download"
  | "play"
  | "back"
  | "sparkle"
  | "lock"
  | "plus"
  | "user"
  | "menu"
  | "close"
  | "alert"
  | "refresh";

type DetectionType = "faces" | "number_plates" | "both";
type SelectionMode = "all" | "specific" | "except";

export interface DetectedEntityItem {
  id: number;
  label: string;
  confidence?: number;
  x?: string;
  y?: string;
  w?: string;
  h?: string;
}

function Icon({ name, size = 20, className = "" }: { name: IconName; size?: number; className?: string }) {
  const paths: Record<IconName, ReactNode> = {
    shield: <><path d="M12 3 5 6v5c0 4.7 2.9 8.8 7 10 4.1-1.2 7-5.3 7-10V6l-7-3Z" /><path d="m9 12 2 2 4-4" /></>,
    arrow: <><path d="M5 12h14" /><path d="m14 7 5 5-5 5" /></>,
    scan: <><path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3" /><circle cx="12" cy="11" r="3" /><path d="M7.5 17c1.1-1.3 2.6-2 4.5-2s3.4.7 4.5 2" /></>,
    cursor: <><path d="m5 3 14 9-6.5 1.2L9 19 5 3Z" /><path d="m13 13 5 5" /></>,
    video: <><rect x="3" y="5" width="13" height="14" rx="2" /><path d="m16 10 5-3v10l-5-3" /></>,
    sliders: <><path d="M4 7h10M18 7h2M4 17h2M10 17h10" /><circle cx="16" cy="7" r="2" /><circle cx="8" cy="17" r="2" /></>,
    grid: <><rect x="4" y="4" width="6" height="6" rx="1" /><rect x="14" y="4" width="6" height="6" rx="1" /><rect x="4" y="14" width="6" height="6" rx="1" /><rect x="14" y="14" width="6" height="6" rx="1" /></>,
    upload: <><path d="M12 16V4m0 0L7 9m5-5 5 5" /><path d="M5 14v5h14v-5" /></>,
    history: <><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5M12 7v5l3 2" /></>,
    folder: <><path d="M3 6h7l2 2h9v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6Z" /></>,
    help: <><circle cx="12" cy="12" r="9" /><path d="M9.8 9a2.3 2.3 0 1 1 3.4 2c-.8.5-1.2 1-1.2 2M12 17h.01" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3v-.2h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z" /></>,
    logout: <><path d="M10 5H5v14h5M14 8l4 4-4 4M18 12H9" /></>,
    image: <><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="9" cy="10" r="2" /><path d="m21 15-5-5L5 20" /></>,
    film: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M7 4v16M17 4v16M3 9h4M17 9h4M3 15h4M17 15h4" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    chevron: <path d="m9 18 6-6-6-6" />,
    eye: <><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" /><circle cx="12" cy="12" r="2.5" /></>,
    eyeOff: <><path d="m3 3 18 18M10.6 6.2c.5-.1.9-.2 1.4-.2 6 0 9.5 6 9.5 6a16 16 0 0 1-2.1 2.8M6.5 6.6C4 8.2 2.5 12 2.5 12s3.5 6 9.5 6c1.3 0 2.5-.3 3.5-.7" /></>,
    download: <><path d="M12 4v12m0 0 5-5m-5 5-5-5" /><path d="M5 20h14" /></>,
    play: <path d="m9 7 8 5-8 5V7Z" />,
    back: <><path d="M19 12H5" /><path d="m10 7-5 5 5 5" /></>,
    sparkle: <><path d="m12 3 1.2 4.3L17 9l-3.8 1.7L12 15l-1.2-4.3L7 9l3.8-1.7L12 3Z" /><path d="m19 15 .6 2.4L22 18.5l-2.4 1.1L19 22l-.6-2.4-2.4-1.1 2.4-1.1L19 15Z" /></>,
    lock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></>,
    plus: <><path d="M12 5v14M5 12h14" /></>,
    user: <><circle cx="12" cy="8" r="4" /><path d="M4 21c.8-4 3.5-6 8-6s7.2 2 8 6" /></>,
    menu: <><path d="M4 7h16M4 12h16M4 17h16" /></>,
    close: <><path d="m6 6 12 12M18 6 6 18" /></>,
    alert: <><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></>,
    refresh: <><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /><path d="M3 3v5h5" /><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" /><path d="M16 21h5v-5" /></>,
  };
  return <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

function Logo({ light = false }: { light?: boolean }) {
  return (
    <button className="flex items-center gap-2.5" onClick={() => window.location.reload()} aria-label="VisualGuard AI home">
      <span className="grid h-9 w-9 place-items-center rounded-xl bg-teal-500 text-white shadow-lg shadow-teal-500/20"><Icon name="shield" size={21} /></span>
      <span className={`text-[17px] font-bold tracking-tight ${light ? "text-white" : "text-slate-950"}`}>VisualGuard <span className="text-teal-500">AI</span></span>
    </button>
  );
}

function Button({ children, onClick, variant = "primary", className = "", disabled = false, type = "button" }: { children: ReactNode; onClick?: () => void; variant?: "primary" | "secondary" | "ghost"; className?: string; disabled?: boolean; type?: "button" | "submit" }) {
  const variants = {
    primary: "bg-[#0d9488] text-white shadow-lg shadow-teal-600/20 hover:bg-[#0f766e]",
    secondary: "border border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50",
    ghost: "text-slate-600 hover:bg-slate-100",
  };
  return <button type={type} disabled={disabled} onClick={onClick} className={`inline-flex h-11 items-center justify-center gap-2 rounded-xl px-5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${className}`}>{children}</button>;
}

function Landing({ navigate }: { navigate: (screen: Screen) => void }) {
  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900">
      <header className="fixed inset-x-0 top-0 z-50 border-b border-slate-200/70 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex h-18 max-w-7xl items-center justify-between px-5 lg:px-8">
          <Logo />
          <nav className="hidden items-center gap-8 text-sm font-medium text-slate-600 md:flex">
            <a href="#features" className="hover:text-slate-950">Features</a>
            <a href="#how" className="hover:text-slate-950">How it works</a>
            <a href="#security" className="hover:text-slate-950">Security</a>
          </nav>
          <div className="flex items-center gap-2">
            <Button onClick={() => navigate("dashboard")}>Get started <Icon name="arrow" size={17} /></Button>
          </div>
        </div>
      </header>

      <main className="overflow-hidden pt-18">
        <section className="relative">
          <div className="hero-grid absolute inset-0 opacity-50" />
          <div className="mx-auto grid max-w-7xl items-center gap-14 px-5 py-20 lg:grid-cols-[.9fr_1.1fr] lg:px-8 lg:py-28">
            <div className="relative z-10">
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-teal-200 bg-teal-50 px-3 py-1.5 text-xs font-bold uppercase tracking-[.12em] text-teal-700">
                <Icon name="sparkle" size={14} /> AI-powered privacy protection
              </div>
              <h1 className="max-w-2xl text-5xl font-bold leading-[1.06] tracking-[-.045em] text-slate-950 md:text-6xl">
                Protect privacy with <span className="text-teal-600">intelligent</span> visual detection.
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-8 text-slate-600">Automatically detect faces and license plates. Choose exactly what to conceal, and let AI track it across every frame.</p>
              <div className="mt-9 flex flex-wrap gap-3">
                <Button onClick={() => navigate("dashboard")} className="h-13 px-7 text-base">Protect your media <Icon name="arrow" size={18} /></Button>
                <Button variant="secondary" onClick={() => navigate("dashboard")} className="h-13 px-7 text-base"><Icon name="play" size={18} /> See how it works</Button>
              </div>
              <div className="mt-8 flex flex-wrap gap-5 text-sm text-slate-500">
                <span className="flex items-center gap-2"><Icon name="check" size={17} className="text-teal-600" /> No technical skills needed</span>
                <span className="flex items-center gap-2"><Icon name="lock" size={17} className="text-teal-600" /> Your media stays private</span>
              </div>
            </div>

            <div className="relative mx-auto w-full max-w-2xl">
              <div className="absolute -inset-10 rounded-full bg-teal-300/20 blur-3xl" />
              <div className="relative overflow-hidden rounded-[28px] border border-white/70 bg-white p-3 shadow-[0_30px_80px_-20px_rgba(15,23,42,.25)]">
                <div className="mb-3 flex items-center justify-between px-2 py-1">
                  <div className="flex gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-slate-200" /><span className="h-2.5 w-2.5 rounded-full bg-slate-200" /><span className="h-2.5 w-2.5 rounded-full bg-slate-200" /></div>
                  <span className="flex items-center gap-1.5 text-xs font-semibold text-teal-700"><span className="h-2 w-2 animate-pulse rounded-full bg-teal-500" /> AI detection active</span>
                </div>
                <div className="relative aspect-[4/3] overflow-hidden rounded-2xl bg-gradient-to-br from-slate-950 via-[#0b1726] to-slate-900 flex flex-col items-center justify-center p-8 text-white">
                  <div className="relative grid h-20 w-20 place-items-center rounded-3xl bg-teal-500/10 border border-teal-500/30 text-teal-400 shadow-2xl">
                    <Icon name="shield" size={40} />
                  </div>
                  <h3 className="mt-5 text-lg font-bold tracking-tight">AI Privacy Engine</h3>
                  <p className="mt-2 text-center text-xs text-slate-400 max-w-sm">
                    Automated face and license plate detection, persistent entity tracking, and blur protection.
                  </p>
                  <div className="mt-6 flex flex-wrap justify-center gap-2">
                    <span className="rounded-full bg-white/10 px-3 py-1 text-[11px] font-semibold text-teal-300">Face Protection</span>
                    <span className="rounded-full bg-white/10 px-3 py-1 text-[11px] font-semibold text-amber-300">Number Plate Protection</span>
                    <span className="rounded-full bg-white/10 px-3 py-1 text-[11px] font-semibold text-emerald-300">Automated Tracking</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="border-y border-slate-200 bg-white py-20">
          <div className="mx-auto max-w-7xl px-5 lg:px-8">
            <div className="mx-auto max-w-2xl text-center">
              <span className="text-sm font-bold uppercase tracking-[.18em] text-teal-600">Privacy, precisely controlled</span>
              <h2 className="mt-3 text-3xl font-bold tracking-tight md:text-4xl">Powerful protection. Effortlessly simple.</h2>
              <p className="mt-4 text-slate-600">From a single image to a full-length video, VisualGuard does the complex work for you.</p>
            </div>
            <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
              {[
                ["scan", "AI Detection", "Find faces and license plates automatically with high accuracy."],
                ["cursor", "Selective Protection", "Choose individual objects while leaving everything else visible."],
                ["video", "Smart Video Tracking", "Track and re-identify selected objects across every frame."],
                ["sliders", "Flexible Controls", "Apply blur, pixelation, or masking at your chosen intensity."],
              ].map(([icon, title, copy]) => (
                <div key={title} className="group rounded-2xl border border-slate-200 bg-white p-6 transition hover:-translate-y-1 hover:border-teal-200 hover:shadow-xl hover:shadow-slate-200/60">
                  <span className="grid h-11 w-11 place-items-center rounded-xl bg-slate-100 text-slate-700 transition group-hover:bg-teal-50 group-hover:text-teal-600"><Icon name={icon as IconName} /></span>
                  <h3 className="mt-5 font-bold">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-500">{copy}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
      <footer className="bg-[#081a2c] px-5 py-8 text-white"><div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 sm:flex-row"><Logo light /><p className="text-sm text-slate-400">Privacy is a right, not a privilege. © 2025 VisualGuard AI</p></div></footer>
    </div>
  );
}

const navItems: { screen: Screen; icon: IconName; label: string }[] = [
  { screen: "dashboard", icon: "grid", label: "Overview" },
  { screen: "upload", icon: "upload", label: "Upload media" },
  { screen: "history", icon: "history", label: "Processing history" },
  { screen: "saved", icon: "folder", label: "Saved media" },
];

function AppShell({ screen, navigate, children }: { screen: Screen; navigate: (s: Screen) => void; children: ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className="min-h-screen bg-[#f5f7fa] text-slate-900">
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-[#0a1d31] px-4 py-6 text-white transition-transform lg:translate-x-0 ${menuOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="px-2"><Logo light /></div>
        <button onClick={() => setMenuOpen(false)} className="absolute right-4 top-7 lg:hidden"><Icon name="close" /></button>
        <nav className="mt-10 space-y-1">
          {navItems.map((item, i) => <button key={`${item.label}-${i}`} onClick={() => { navigate(item.screen); setMenuOpen(false); }} className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-medium transition ${screen === item.screen ? "bg-teal-500 text-white shadow-lg shadow-teal-950/30" : "text-slate-400 hover:bg-white/5 hover:text-white"}`}><Icon name={item.icon} size={19} />{item.label}</button>)}
        </nav>
        <div className="mt-auto space-y-1 border-t border-white/10 pt-4">
          <button className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium text-slate-400 hover:bg-white/5 hover:text-white"><Icon name="help" size={19} />Help center</button>
          <button className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium text-slate-400 hover:bg-white/5 hover:text-white"><Icon name="settings" size={19} />Settings</button>
          <div className="mt-3 flex items-center gap-3 rounded-xl bg-white/5 p-3">
            <div className="grid h-9 w-9 place-items-center rounded-full bg-teal-500/20 text-sm font-bold text-teal-400">VG</div>
            <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold">VisualGuard User</p><p className="truncate text-xs text-slate-400">user@visualguard.ai</p></div>
            <button onClick={() => navigate("landing")} className="text-slate-500 hover:text-white" aria-label="Log out"><Icon name="logout" size={18} /></button>
          </div>
        </div>
      </aside>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex h-18 items-center justify-between border-b border-slate-200 bg-white/90 px-5 backdrop-blur-xl md:px-8">
          <button className="text-slate-700 lg:hidden" onClick={() => setMenuOpen(true)}><Icon name="menu" /></button>
          <div className="hidden items-center gap-2 text-sm text-slate-400 lg:flex"><Icon name="shield" size={17} className="text-teal-500" /> Secure workspace</div>
          <div className="flex items-center gap-3">
            <div className="hidden rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 sm:block">System Connected</div>
            <button className="grid h-9 w-9 place-items-center rounded-full bg-slate-100 text-slate-600"><Icon name="user" size={17} /></button>
          </div>
        </header>
        <main className="p-5 md:p-8 lg:p-10">{children}</main>
      </div>
    </div>
  );
}

function Dashboard({ navigate }: { navigate: (s: Screen) => void }) {
  const [mediaItems, setMediaItems] = useState<MediaItem[]>([]);
  const [totalMedia, setTotalMedia] = useState<number>(0);
  const [totalTasks, setTotalTasks] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;
    Promise.all([
      listVideos(0, 5).catch(() => ({ total: 0, items: [] })),
      listProcessingTasks(0, 5).catch(() => ({ total: 0, items: [] })),
    ]).then(([videosRes, tasksRes]) => {
      if (mounted) {
        setMediaItems(videosRes.items);
        setTotalMedia(videosRes.total);
        setTotalTasks(tasksRes.total);
        setLoading(false);
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  const now = new Date();
  const formattedDate = now.toLocaleDateString(undefined, {
    weekday: "long",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  const hour = now.getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <AppShell screen="dashboard" navigate={navigate}>
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div>
            <span className="text-sm font-semibold text-teal-600">{formattedDate}</span>
            <h1 className="mt-1 text-3xl font-bold tracking-tight">{greeting}.</h1>
            <p className="mt-2 text-slate-500">Welcome to your VisualGuard AI workspace.</p>
          </div>
          <Button onClick={() => navigate("upload")} className="h-12">
            <Icon name="upload" size={18} /> Upload media
          </Button>
        </div>

        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {[
            ["image", `${totalMedia}`, "Uploaded videos", "Stored in database"],
            ["sliders", `${totalTasks}`, "Processing tasks", "Initiated workflows"],
            ["shield", "3", "Protection types", "Faces · Plates · Both"],
          ].map(([icon, n, l, s]) => (
            <div key={l} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-start justify-between">
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-teal-50 text-teal-600">
                  <Icon name={icon as IconName} size={19} />
                </span>
                <span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-700">
                  ONLINE
                </span>
              </div>
              <div className="mt-5 text-3xl font-bold">{loading ? "..." : n}</div>
              <div className="mt-1 text-sm font-semibold text-slate-700">{l}</div>
              <div className="mt-2 text-xs text-slate-400">{s}</div>
            </div>
          ))}
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5">
              <div>
                <h2 className="font-bold">Recent media</h2>
                <p className="mt-1 text-xs text-slate-400">Your latest uploaded videos</p>
              </div>
              <button
                onClick={() => navigate("history")}
                className="flex items-center gap-1 text-sm font-semibold text-teal-600"
              >
                View all <Icon name="chevron" size={15} />
              </button>
            </div>
            {mediaItems.length === 0 ? (
              <div className="p-8 text-center">
                <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-slate-400">
                  <Icon name="film" size={24} />
                </span>
                <h3 className="mt-4 font-bold text-slate-700">No media uploaded yet</h3>
                <p className="mt-1 text-xs text-slate-400">
                  Upload a video to start detecting and protecting sensitive objects.
                </p>
                <Button onClick={() => navigate("upload")} className="mt-4 h-9 px-4 text-xs">
                  Upload media
                </Button>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {mediaItems.slice(0, 3).map((item) => (
                  <div key={item.media_id} className="flex w-full items-center gap-4 px-6 py-4 text-left">
                    <div className="grid h-12 w-12 place-items-center rounded-lg bg-teal-50 text-teal-600 shrink-0">
                      <Icon name="video" size={22} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-slate-800">
                        {item.file_name || `Media #${item.media_id}`}
                      </p>
                      <p className="mt-1 text-xs text-slate-400">
                        Media #{item.media_id}
                        {item.duration_seconds ? ` · ${item.duration_seconds.toFixed(1)}s` : ""}
                        {item.fps ? ` · ${item.fps.toFixed(0)} fps` : ""}
                      </p>
                    </div>
                    <span className="hidden items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-bold text-emerald-700 sm:flex">
                      <Icon name="check" size={12} /> Stored
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={() => navigate("upload")}
            className="group flex min-h-64 flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-white p-8 text-center transition hover:border-teal-400 hover:bg-teal-50/30"
          >
            <span className="grid h-14 w-14 place-items-center rounded-2xl bg-teal-50 text-teal-600 transition group-hover:scale-105">
              <Icon name="plus" size={25} />
            </span>
            <h3 className="mt-5 font-bold">Start a new project</h3>
            <p className="mt-2 max-w-xs text-sm leading-6 text-slate-500">
              Upload a video and let our AI detect faces and number plates.
            </p>
            <span className="mt-5 text-sm font-bold text-teal-600">Choose media →</span>
          </button>
        </div>
      </div>
    </AppShell>
  );
}

function Upload({
  navigate,
  uploadedMedia,
  setUploadedMedia,
}: {
  navigate: (s: Screen) => void;
  uploadedMedia: MediaUploadResponse | null;
  setUploadedMedia: (media: MediaUploadResponse | null) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Clean up object URL when component unmounts or previewUrl changes
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const handleFileProcess = async (selectedFile: File) => {
    setErrorMessage(null);

    // 1. Client-side validation
    const validation = validateVideoFile(selectedFile);
    if (!validation.valid) {
      setErrorMessage(validation.error || "Invalid file format or size.");
      return;
    }

    // 2. Setup local preview
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    const newPreviewUrl = URL.createObjectURL(selectedFile);
    setFile(selectedFile);
    setPreviewUrl(newPreviewUrl);
    setUploadedMedia(null);
    setUploading(true);
    setUploadProgress(0);

    // 3. Upload to backend
    try {
      const response = await uploadVideo(selectedFile, 1, (percent) => {
        setUploadProgress(percent);
      });
      setUploadedMedia(response);
      setUploading(false);
      setUploadProgress(100);
    } catch (err: any) {
      setUploading(false);
      setErrorMessage(err.message || "Failed to upload video to the backend.");
    }
  };

  const select = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0];
    if (selected) {
      handleFileProcess(selected);
    }
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    const dropped = event.dataTransfer.files?.[0];
    if (dropped) {
      handleFileProcess(dropped);
    }
  };

  const handleRemove = () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    setFile(null);
    setPreviewUrl(null);
    setUploadedMedia(null);
    setErrorMessage(null);
    setUploadProgress(0);
    setUploading(false);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  const handleRetry = () => {
    if (file) {
      handleFileProcess(file);
    }
  };

  return (
    <AppShell screen="upload" navigate={navigate}>
      <div className="mx-auto max-w-4xl">
        <StepHeader step={1} title="Upload your media" copy="Choose an image or video to begin privacy detection." />

        {/* Error Alert */}
        {errorMessage && (
          <div className="mt-6 flex items-start justify-between gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
            <div className="flex items-start gap-3">
              <Icon name="alert" size={19} className="mt-0.5 shrink-0 text-rose-600" />
              <div>
                <p className="font-semibold">Upload issue</p>
                <p className="mt-1 text-xs text-rose-700">{errorMessage}</p>
              </div>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-rose-500 hover:text-rose-800 transition"
              aria-label="Dismiss message"
            >
              <Icon name="close" size={16} />
            </button>
          </div>
        )}

        {!file ? (
          <div
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={(e) => {
              e.preventDefault();
              setIsDragging(false);
            }}
            onDrop={handleDrop}
            className={`mt-9 flex min-h-96 cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed bg-white px-6 text-center transition ${isDragging ? "border-teal-500 bg-teal-50/40" : "border-slate-300 hover:border-teal-400 hover:bg-teal-50/20"
              }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept={ALLOWED_VIDEO_EXTENSIONS.join(",")}
              className="hidden"
              onChange={select}
            />
            <span className="grid h-16 w-16 place-items-center rounded-2xl bg-teal-50 text-teal-600">
              <Icon name="upload" size={28} />
            </span>
            <h2 className="mt-6 text-xl font-bold">Drop your media here</h2>
            <p className="mt-2 text-sm text-slate-500">or click to browse from your device</p>
            <Button variant="secondary" className="mt-6">
              Choose a file
            </Button>
            <p className="mt-6 text-xs text-slate-400">
              Videos: MP4, AVI, MOV, MKV, WEBM · Up to {MAX_UPLOAD_SIZE_MB} MB
            </p>
          </div>
        ) : (
          <div className="mt-9 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
            <div className="grid gap-6 p-6 md:grid-cols-[240px_1fr]">
              <div className="aspect-video overflow-hidden rounded-xl bg-slate-900 flex items-center justify-center relative">
                {previewUrl ? (
                  <video
                    src={previewUrl}
                    className="h-full w-full object-cover"
                    controls
                    playsInline
                    muted
                  />
                ) : (
                  <div className="h-full w-full flex items-center justify-center bg-slate-800">
                    <Icon name="film" size={36} className="text-slate-500" />
                  </div>
                )}
              </div>
              <div className="flex flex-col justify-center">
                <div className="flex items-center gap-3">
                  <span className="grid h-10 w-10 place-items-center rounded-xl bg-teal-50 text-teal-600">
                    <Icon name={file.type.startsWith("video") ? "film" : "image"} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <h3 className="font-bold truncate">{uploadedMedia ? uploadedMedia.file_name : file.name}</h3>
                    <p className="mt-1 text-xs text-slate-400">
                      {(file.size / 1024 / 1024).toFixed(1)} MB · {file.type || "video"}
                      {uploadedMedia?.metadata.width && uploadedMedia?.metadata.height && (
                        <span> · {uploadedMedia.metadata.width} × {uploadedMedia.metadata.height}</span>
                      )}
                      {uploadedMedia?.metadata.duration_seconds && (
                        <span> · {uploadedMedia.metadata.duration_seconds}s</span>
                      )}
                      {uploadedMedia?.metadata.fps && (
                        <span> · {uploadedMedia.metadata.fps} fps</span>
                      )}
                    </p>
                    {uploadedMedia && (
                      <p className="mt-0.5 text-[11px] font-semibold text-teal-700">
                        Media ID: #{uploadedMedia.media_id} · Saved in backend/uploads/
                      </p>
                    )}
                  </div>
                </div>

                <div className="mt-6 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${errorMessage ? "bg-rose-500" : "bg-teal-500"
                      }`}
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>

                <div className="mt-2 flex justify-between text-xs">
                  {uploading ? (
                    <>
                      <span className="font-semibold text-teal-600 flex items-center gap-1.5">
                        <span className="h-2 w-2 animate-pulse rounded-full bg-teal-500" />
                        Uploading to backend...
                      </span>
                      <span className="text-slate-400 font-medium">{uploadProgress}%</span>
                    </>
                  ) : uploadedMedia ? (
                    <>
                      <span className="font-semibold text-emerald-600 flex items-center gap-1">
                        <Icon name="check" size={13} /> Upload complete
                      </span>
                      <span className="text-slate-400 font-medium">100%</span>
                    </>
                  ) : errorMessage ? (
                    <>
                      <span className="font-semibold text-rose-600 flex items-center gap-1">
                        <Icon name="alert" size={13} /> Upload failed
                      </span>
                      <span className="text-slate-400 font-medium">{uploadProgress}%</span>
                    </>
                  ) : (
                    <>
                      <span className="font-semibold text-slate-500">Ready to upload</span>
                      <span className="text-slate-400 font-medium">0%</span>
                    </>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50 px-6 py-4">
              <div className="flex items-center gap-4">
                <button
                  onClick={handleRemove}
                  className="text-sm font-semibold text-slate-500 hover:text-rose-600 transition"
                >
                  Remove file
                </button>
                {errorMessage && (
                  <button
                    onClick={handleRetry}
                    className="text-sm font-semibold text-teal-600 hover:text-teal-700 transition"
                  >
                    Try again
                  </button>
                )}
              </div>
              <Button
                disabled={!uploadedMedia || uploading}
                onClick={() => navigate("detectionType")}
              >
                Continue <Icon name="arrow" size={17} />
              </Button>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

function StepHeader({ step, title, copy }: { step: number; title: string; copy: string }) {
  return <><div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[.12em] text-teal-600"><span className="grid h-6 w-6 place-items-center rounded-full bg-teal-100">{step}</span> Step {step} of 4</div><h1 className="mt-4 text-3xl font-bold tracking-tight">{title}</h1><p className="mt-2 text-slate-500">{copy}</p></>;
}

function DetectionTypeSelection({
  navigate,
  detectionType,
  setDetectionType,
  uploadedMedia,
  currentTask,
  setCurrentTask,
}: {
  navigate: (s: Screen) => void;
  detectionType: DetectionType;
  setDetectionType: (type: DetectionType) => void;
  uploadedMedia: MediaUploadResponse | null;
  currentTask: ProcessingTaskResponse | null;
  setCurrentTask: (task: ProcessingTaskResponse | null) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const options: {
    id: DetectionType;
    icon: IconName;
    title: string;
    description: string;
    detail: string;
    accent: string;
  }[] = [
      {
        id: "faces",
        icon: "scan",
        title: "Detect Faces",
        description: "Find human faces only.",
        detail: "Face detection model",
        accent: "bg-blue-50 text-blue-600",
      },
      {
        id: "number_plates",
        icon: "grid",
        title: "Detect Number Plates",
        description: "Find vehicle license plates only.",
        detail: "Plate detection model",
        accent: "bg-amber-50 text-amber-600",
      },
      {
        id: "both",
        icon: "sparkle",
        title: "Detect Both",
        description: "Find faces and license plates.",
        detail: "Both AI models",
        accent: "bg-teal-50 text-teal-600",
      },
    ];

  const handleStartDetection = async () => {
    // Prevent duplicate task creation from repeated clicks
    if (loading) return;

    if (!uploadedMedia || !uploadedMedia.media_id) {
      setErrorMessage("No uploaded media found. Please upload a video first.");
      return;
    }

    setLoading(true);
    setErrorMessage(null);

    try {
      const task = await createProcessingTask({
        media_id: uploadedMedia.media_id,
        protection_type: detectionType,
        blur_intensity: null,
      });

      // Store the returned task_id in frontend state
      setCurrentTask(task);

      // Navigate to the processing/detecting screen only after successful task creation
      navigate("detecting");
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to create processing task. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell screen="upload" navigate={navigate}>
      <div className="mx-auto max-w-5xl">
        <StepHeader
          step={2}
          title="What would you like to detect?"
          copy="Choose which AI detection model to run on your uploaded media."
        />

        {uploadedMedia && (
          <div className="mt-4 flex items-center gap-2 text-xs font-medium text-slate-500">
            <Icon name="video" size={14} className="text-teal-600" />
            <span>
              Target media: <strong className="text-slate-700">{uploadedMedia.file_name}</strong> (Media ID: #{uploadedMedia.media_id})
            </span>
          </div>
        )}

        {!uploadedMedia && (
          <div className="mt-6 flex items-start justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            <div className="flex items-start gap-3">
              <Icon name="alert" size={18} className="mt-0.5 shrink-0 text-amber-600" />
              <p>
                <strong>No media selected.</strong> Please upload a video file first to enable detection.
              </p>
            </div>
            <button
              onClick={() => navigate("upload")}
              className="shrink-0 font-semibold text-amber-800 underline hover:text-amber-900"
            >
              Go to Upload
            </button>
          </div>
        )}

        {errorMessage && (
          <div className="mt-6 flex items-start justify-between gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
            <div className="flex items-start gap-3">
              <Icon name="alert" size={18} className="mt-0.5 shrink-0 text-rose-600" />
              <div>
                <p className="font-semibold text-rose-900">Task Creation Failed</p>
                <p className="mt-1 text-rose-700">{errorMessage}</p>
              </div>
            </div>
            <button
              onClick={handleStartDetection}
              className="shrink-0 font-semibold text-rose-700 underline hover:text-rose-900"
            >
              Try again
            </button>
          </div>
        )}

        <div className="mt-9 grid gap-5 md:grid-cols-3">
          {options.map((option) => {
            const active = detectionType === option.id;
            return (
              <button
                key={option.id}
                type="button"
                disabled={loading}
                onClick={() => {
                  setDetectionType(option.id);
                  if (errorMessage) setErrorMessage(null);
                }}
                className={`relative flex min-h-72 flex-col rounded-3xl border-2 bg-white p-6 text-left transition duration-200 hover:-translate-y-1 hover:shadow-xl disabled:cursor-not-allowed disabled:opacity-70 ${active
                  ? "border-teal-500 shadow-xl shadow-teal-600/10"
                  : "border-slate-200 hover:border-slate-300"
                  }`}
              >
                {active && (
                  <span className="absolute right-5 top-5 grid h-7 w-7 place-items-center rounded-full bg-teal-500 text-white">
                    <Icon name="check" size={15} />
                  </span>
                )}
                <span className={`grid h-14 w-14 place-items-center rounded-2xl ${option.accent}`}>
                  <Icon name={option.icon} size={27} />
                </span>
                <h2 className="mt-7 text-lg font-bold">{option.title}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-500">{option.description}</p>
                <div className="mt-auto flex items-center gap-2 border-t border-slate-100 pt-5 text-xs font-semibold text-slate-400">
                  <Icon name="sparkle" size={15} /> {option.detail}
                </div>
              </button>
            );
          })}
        </div>

        <div className="mt-7 flex flex-col-reverse justify-between gap-3 sm:flex-row">
          <Button
            variant="secondary"
            disabled={loading}
            onClick={() => navigate("upload")}
          >
            <Icon name="back" size={17} /> Back to upload
          </Button>
          <Button
            onClick={handleStartDetection}
            disabled={loading || !uploadedMedia}
            className="h-12 px-7"
          >
            {loading ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                <span>Starting Detection...</span>
              </>
            ) : (
              <>
                <Icon name="scan" size={18} />
                <span>Start Detection</span>
              </>
            )}
          </Button>
        </div>

        <div className="mt-6 flex items-start gap-3 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-800">
          <Icon name="lock" size={18} className="mt-0.5 shrink-0" />
          <p>
            Only the selected detection model{detectionType === "both" ? "s" : ""} will run.
            Changing this option clears previous detections and selections.
          </p>
        </div>
      </div>
    </AppShell>
  );
}

function DetectionProgress({ navigate, detectionType }: { navigate: (s: Screen) => void; detectionType: DetectionType }) {
  const [progress, setProgress] = useState(8);
  useEffect(() => { const timer = window.setInterval(() => setProgress((p) => Math.min(100, p + 3)), 80); return () => window.clearInterval(timer); }, []);
  useEffect(() => { if (progress === 100) { const timer = window.setTimeout(() => navigate("detect"), 450); return () => window.clearTimeout(timer); } }, [progress, navigate]);
  const models = detectionType === "both" ? ["Face detection model", "Number plate model", "Entity tracking"] : [detectionType === "faces" ? "Face detection model" : "Number plate model", "Entity tracking"];
  return <AppShell screen="upload" navigate={navigate}><div className="mx-auto flex min-h-[70vh] max-w-2xl flex-col items-center justify-center text-center">
    <div className="relative grid h-28 w-28 place-items-center rounded-full bg-white shadow-xl shadow-slate-200"><div className="absolute inset-2 animate-spin rounded-full border-2 border-slate-100 border-t-teal-500" /><Icon name="scan" size={38} className="text-teal-600" /></div>
    <span className="mt-8 text-sm font-bold uppercase tracking-[.15em] text-teal-600">AI detection in progress</span><h1 className="mt-3 text-3xl font-bold tracking-tight">Finding {detectionType === "faces" ? "faces" : detectionType === "number_plates" ? "number plates" : "faces and number plates"}</h1><p className="mt-3 text-slate-500">Analyzing the media and associating unique entities across frames.</p>
    <div className="mt-9 w-full rounded-2xl border border-slate-200 bg-white p-6 text-left shadow-sm"><div className="mb-3 flex justify-between"><span className="text-sm font-semibold">{progress < 65 ? "Running detection models" : "Associating tracked entities"}</span><span className="text-sm font-bold text-teal-600">{progress}%</span></div><div className="h-2.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-teal-500 transition-all duration-300" style={{ width: `${progress}%` }} /></div><div className="mt-5 flex flex-wrap gap-2">{models.map((model) => <span key={model} className="flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-teal-500" />{model}</span>)}</div></div>
  </div></AppShell>;
}

function DetectionBox({ style, label, selected = false, protectedBox = false }: { style: React.CSSProperties; label: string; selected?: boolean; protectedBox?: boolean }) {
  return <div style={style} className={`absolute border-2 ${selected ? "border-teal-400 bg-teal-400/10" : "border-white/80 bg-white/5"} ${protectedBox ? "overflow-hidden backdrop-blur-md" : ""}`}>
    {protectedBox && <div className="absolute inset-0 privacy-pixels opacity-90" />}
    <span className={`absolute -top-6 left-[-2px] whitespace-nowrap rounded-t px-2 py-1 text-[10px] font-bold text-white ${selected ? "bg-teal-500" : "bg-slate-950/75"}`}>{selected && "✓ "}{label}</span>
  </div>;
}

function CategorySelection({ title, objects, mode, setMode, selected, setSelected }: { title: string; objects: DetectedEntityItem[]; mode: SelectionMode; setMode: (mode: SelectionMode) => void; selected: number[]; setSelected: (ids: number[]) => void }) {
  const modes: { id: SelectionMode; label: string; description: string }[] = [
    { id: "all", label: "Select All", description: "Protect every detected object" },
    { id: "specific", label: "Select Specific", description: "Choose only objects to protect" },
    { id: "except", label: "Select All Except", description: "Mark objects to keep visible" },
  ];
  const toggle = (id: number) => setSelected(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  return <section className="rounded-2xl border border-slate-200 bg-white shadow-sm">
    <div className="flex items-center justify-between border-b border-slate-100 p-5"><div><h2 className="font-bold">{title}</h2><p className="mt-1 text-xs text-slate-400">{objects.length} unique {title.toLowerCase().replace(" protection", "")} detected</p></div><span className="rounded-full bg-teal-50 px-2.5 py-1 text-xs font-bold text-teal-700">{objects.length}</span></div>
    <div className="grid gap-2 p-3 sm:grid-cols-3 xl:grid-cols-1">{modes.map((item) => <button key={item.id} onClick={() => { setMode(item.id); setSelected(item.id === "all" ? objects.map((x) => x.id) : []); }} className={`rounded-xl border p-3 text-left transition ${mode === item.id ? "border-teal-300 bg-teal-50" : "border-slate-100 hover:border-slate-200"}`}><div className="flex items-center gap-2"><span className={`grid h-4 w-4 place-items-center rounded-full border ${mode === item.id ? "border-teal-500" : "border-slate-300"}`}>{mode === item.id && <span className="h-2 w-2 rounded-full bg-teal-500" />}</span><span className="text-xs font-bold">{item.label}</span></div><p className="ml-6 mt-1 text-[11px] text-slate-400">{item.description}</p></button>)}</div>
    {mode !== "all" && <div className="border-t border-slate-100 p-3"><p className="mb-2 px-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">{mode === "except" ? "Mark as Keep Visible" : "Choose to protect"}</p><div className="space-y-2">{objects.map((object, i) => {
      const active = selected.includes(object.id);
      return <button key={object.id} onClick={() => toggle(object.id)} className={`flex w-full items-center gap-3 rounded-xl border p-2.5 text-left ${active ? mode === "except" ? "border-amber-300 bg-amber-50" : "border-teal-300 bg-teal-50" : "border-transparent bg-slate-50"}`}><div className="h-10 w-12 overflow-hidden rounded-lg bg-slate-200 flex items-center justify-center text-slate-400"><Icon name="scan" size={18} /></div><div className="flex-1"><div className="text-xs font-bold">{object.label}</div><div className="mt-0.5 text-[10px] text-slate-400">{object.confidence !== undefined ? `${object.confidence}% confidence` : "Detected entity"}</div></div><span className={`grid h-5 w-5 place-items-center rounded-md border ${active ? mode === "except" ? "border-amber-500 bg-amber-500 text-white" : "border-teal-500 bg-teal-500 text-white" : "border-slate-300 bg-white"}`}>{active && <Icon name={mode === "except" ? "eye" : "check"} size={12} />}</span></button>;
    })}</div></div>}
  </section>;
}

function Detect({ navigate, detectionType }: { navigate: (s: Screen) => void; detectionType: DetectionType }) {
  return <AppShell screen="upload" navigate={navigate}><div className="mx-auto max-w-7xl">
    <StepHeader step={3} title="Choose what to protect" copy="Set an independent selection mode for each detected category." />
    <div className="mt-10 flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-white py-20 text-center">
      <span className="grid h-16 w-16 place-items-center rounded-2xl bg-teal-50 text-teal-600">
        <Icon name="scan" size={30} />
      </span>
      <h2 className="mt-5 text-xl font-bold">Detection results will appear here</h2>
      <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">
        After AI processing is complete, detected entities will be listed here and you can choose which ones to protect.
      </p>
      <p className="mt-3 text-xs font-semibold text-teal-600 uppercase tracking-wider">Coming in a future phase</p>
    </div>
    <div className="mt-6 flex flex-col-reverse justify-between gap-3 sm:flex-row"><Button variant="secondary" onClick={() => navigate("detectionType")}><Icon name="back" size={17} /> Change detection type</Button></div>
  </div></AppShell>;
}

function StylePanel({ title, method, setMethod, intensity, setIntensity }: { title: string; method: string; setMethod: (method: string) => void; intensity: number; setIntensity: (value: number) => void }) {
  return <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><div className="flex items-center justify-between"><h2 className="font-bold">{title}</h2><span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">Independent</span></div><div className="mt-5 grid gap-3 sm:grid-cols-3">{["Blur", "Pixelation", "Masking"].map((item) => <button key={item} onClick={() => setMethod(item)} className={`rounded-xl border-2 p-3 text-left transition ${method === item ? "border-teal-500 bg-teal-50" : "border-slate-200 hover:border-slate-300"}`}><div className="flex items-center justify-between"><span className="text-sm font-bold">{item}</span>{method === item && <Icon name="check" size={15} className="text-teal-600" />}</div><div className={`mt-3 h-10 rounded-lg ${item === "Blur" ? "bg-teal-300 blur-sm" : item === "Pixelation" ? "privacy-pixels" : "bg-slate-900"}`} /></button>)}</div><div className="mt-6 border-t border-slate-100 pt-5"><div className="flex items-center justify-between"><span className="text-sm font-bold">Intensity</span><span className="rounded-lg bg-teal-50 px-2.5 py-1 text-xs font-bold text-teal-700">{intensity}%</span></div><input className="mt-4 w-full accent-teal-600" type="range" min="20" max="100" value={intensity} onChange={(e) => setIntensity(Number(e.target.value))} /></div></div>;
}

function ProtectionSettings({ navigate, detectionType }: { navigate: (s: Screen) => void; detectionType: DetectionType }) {
  const [faceMethod, setFaceMethod] = useState("Blur");
  const [faceIntensity, setFaceIntensity] = useState(72);
  const [plateMethod, setPlateMethod] = useState("Pixelation");
  const [plateIntensity, setPlateIntensity] = useState(84);
  return <AppShell screen="upload" navigate={navigate}><div className="mx-auto max-w-6xl">
    <StepHeader step={4} title="Choose protection styles" copy={detectionType === "both" ? "Configure faces and number plates independently." : "Set how selected objects will appear in the final media."} />
    <div className={`mt-8 grid gap-6 ${detectionType === "both" ? "lg:grid-cols-2" : "mx-auto max-w-2xl"}`}>
      {detectionType !== "number_plates" && <StylePanel title="Face Protection" method={faceMethod} setMethod={setFaceMethod} intensity={faceIntensity} setIntensity={setFaceIntensity} />}
      {detectionType !== "faces" && <StylePanel title="Number Plate Protection" method={plateMethod} setMethod={setPlateMethod} intensity={plateIntensity} setIntensity={setPlateIntensity} />}
    </div>
    <div className="mt-6 flex items-start gap-3 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-800"><Icon name="video" size={18} className="mt-0.5 shrink-0" /><p><strong>Video tracking is automatic.</strong> Your selected protection styles follow each tracked entity across frames, including when it disappears and reappears.</p></div>
    <div className="mt-6 flex justify-between"><Button variant="secondary" onClick={() => navigate("detect")}><Icon name="back" size={17} /> Back to selection</Button><Button onClick={() => navigate("processing")}><Icon name="sparkle" size={17} /> Apply privacy protection</Button></div>
  </div></AppShell>;
}

function Processing({ navigate }: { navigate: (s: Screen) => void }) {
  const [progress, setProgress] = useState(16);
  useEffect(() => { const timer = window.setInterval(() => setProgress((p) => p >= 100 ? 100 : p + 2), 90); return () => window.clearInterval(timer); }, []);
  useEffect(() => { if (progress === 100) { const timer = window.setTimeout(() => navigate("preview"), 650); return () => window.clearTimeout(timer); } }, [progress, navigate]);
  const current = progress < 28 ? 0 : progress < 58 ? 1 : progress < 88 ? 2 : 3;
  const stages = ["Analyzing media", "Tracking selected objects", "Applying privacy protection", "Generating protected media"];
  return <AppShell screen="upload" navigate={navigate}><div className="mx-auto flex min-h-[70vh] max-w-2xl flex-col items-center justify-center text-center">
    <div className="relative grid h-28 w-28 place-items-center rounded-full bg-white shadow-xl shadow-slate-200"><div className="absolute inset-2 animate-spin rounded-full border-2 border-slate-100 border-t-teal-500" /><Icon name="shield" size={38} className="text-teal-600" /></div>
    <span className="mt-8 text-sm font-bold uppercase tracking-[.15em] text-teal-600">AI processing</span><h1 className="mt-3 text-3xl font-bold tracking-tight">Protecting your media</h1><p className="mt-3 text-slate-500">Keep this window open. This usually takes less than a minute.</p>
    <div className="mt-10 w-full rounded-2xl border border-slate-200 bg-white p-6 text-left shadow-sm"><div className="mb-3 flex justify-between"><span className="text-sm font-semibold">{stages[current]}</span><span className="text-sm font-bold text-teal-600">{progress}%</span></div><div className="h-2.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-teal-500 transition-all duration-300" style={{ width: `${progress}%` }} /></div><div className="mt-6 space-y-4">{stages.map((stage, i) => <div key={stage} className={`flex items-center gap-3 text-sm ${i <= current ? "text-slate-800" : "text-slate-300"}`}><span className={`grid h-6 w-6 place-items-center rounded-full ${i < current ? "bg-teal-500 text-white" : i === current ? "border-2 border-teal-500 bg-teal-50 text-teal-600" : "border border-slate-200"}`}>{i < current ? <Icon name="check" size={13} /> : <span className="text-[10px] font-bold">{i + 1}</span>}</span>{stage}</div>)}</div></div>
    <p className="mt-5 text-xs text-slate-400">Estimated time remaining: {Math.max(1, Math.ceil((100 - progress) / 12))} seconds</p>
  </div></AppShell>;
}

function Preview({ navigate }: { navigate: (s: Screen) => void }) {
  return (
    <AppShell screen="history" navigate={navigate}>
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div>
            <div className="flex items-center gap-2 text-sm font-bold text-emerald-600">
              <span className="grid h-5 w-5 place-items-center rounded-full bg-emerald-100">
                <Icon name="check" size={13} />
              </span>
              Processing complete
            </div>
            <h1 className="mt-3 text-3xl font-bold tracking-tight">Your media is protected</h1>
            <p className="mt-2 text-slate-500">Your processed output has been generated by the AI engine.</p>
          </div>
        </div>
        <div className="mt-10 flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-white py-20 text-center">
          <span className="grid h-16 w-16 place-items-center rounded-2xl bg-teal-50 text-teal-600">
            <Icon name="shield" size={30} />
          </span>
          <h2 className="mt-5 text-xl font-bold">Outputs available in Saved Media</h2>
          <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">
            You can view, preview streaming video, and download all protected output videos in the Saved Media section.
          </p>
          <Button onClick={() => navigate("saved")} className="mt-6">
            View saved media <Icon name="arrow" size={17} />
          </Button>
        </div>
        <div className="mt-6 flex flex-wrap justify-between gap-3">
          <Button variant="secondary" onClick={() => navigate("upload")}>
            <Icon name="plus" size={17} /> Protect another file
          </Button>
        </div>
      </div>
    </AppShell>
  );
}

function HistoryPage({
  navigate,
  initialTab = "all",
}: {
  navigate: (s: Screen) => void;
  initialTab?: "all" | "tasks" | "videos" | "saved";
}) {
  const [activeTab, setActiveTab] = useState<"all" | "tasks" | "videos" | "saved">(initialTab);
  const [videos, setVideos] = useState<MediaItem[]>([]);
  const [tasks, setTasks] = useState<ProcessingTaskResponse[]>([]);
  const [outputs, setOutputs] = useState<ProcessedMediaItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewOutput, setPreviewOutput] = useState<ProcessedMediaItem | null>(null);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  const loadData = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      listVideos(0, 100).catch(() => ({ total: 0, items: [] as MediaItem[] })),
      listProcessingTasks(0, 100).catch(() => ({ total: 0, items: [] as ProcessingTaskResponse[] })),
      listAllOutputs(0, 100).catch(() => ({ total: 0, items: [] as ProcessedMediaItem[] })),
    ])
      .then(([vRes, tRes, oRes]) => {
        setVideos(vRes?.items || []);
        setTasks(tRes?.items || []);
        setOutputs(oRes?.items || []);
        setLoading(false);
      })
      .catch(() => {
        setError("Unable to connect to the backend server. Please verify the backend is running.");
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, []);

  const formatDate = (dateStr?: string | null): string => {
    if (!dateStr) return "";
    try {
      const d = new Date(dateStr);
      return isNaN(d.getTime()) ? "" : d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
    } catch {
      return "";
    }
  };

  const getStatusBadge = (s?: string | null) => {
    const norm = (s || "uploaded").toLowerCase();
    const styles: Record<string, string> = {
      pending: "bg-amber-50 text-amber-700 border border-amber-200",
      processing: "bg-blue-50 text-blue-700 border border-blue-200",
      completed: "bg-emerald-50 text-emerald-700 border border-emerald-200",
      failed: "bg-rose-50 text-rose-700 border border-rose-200",
      uploaded: "bg-slate-100 text-slate-600 border border-slate-200",
      saved: "bg-teal-50 text-teal-700 border border-teal-200",
    };
    return styles[norm] || "bg-slate-100 text-slate-600 border border-slate-200";
  };

  return (
    <AppShell screen={activeTab === "saved" ? "saved" : "history"} navigate={navigate}>
      <div className="mx-auto max-w-6xl">
        {/* Header */}
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              {activeTab === "saved" ? "Saved media" : "Processing history"}
            </h1>
            <p className="mt-2 text-slate-500">
              {activeTab === "saved"
                ? "Browse, preview, and download your protected output videos."
                : "Track AI detection tasks, uploaded media, and generated outputs."}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={loadData}
              className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50 transition"
              title="Refresh records"
            >
              <Icon name="refresh" size={16} /> Refresh
            </button>
            <Button onClick={() => navigate("upload")}>
              <Icon name="upload" size={18} /> Upload new media
            </Button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="mt-8 flex flex-wrap gap-2 border-b border-slate-200 pb-3">
          <button
            onClick={() => setActiveTab("all")}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              activeTab === "all" ? "bg-teal-600 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            All Activity
          </button>
          <button
            onClick={() => setActiveTab("saved")}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition ${
              activeTab === "saved" ? "bg-teal-600 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <span>Saved Media</span>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-bold ${
                activeTab === "saved" ? "bg-white/20 text-white" : "bg-slate-200 text-slate-700"
              }`}
            >
              {outputs.length}
            </span>
          </button>
          <button
            onClick={() => setActiveTab("tasks")}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition ${
              activeTab === "tasks" ? "bg-teal-600 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <span>Processing Tasks</span>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-bold ${
                activeTab === "tasks" ? "bg-white/20 text-white" : "bg-slate-200 text-slate-700"
              }`}
            >
              {tasks.length}
            </span>
          </button>
          <button
            onClick={() => setActiveTab("videos")}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition ${
              activeTab === "videos" ? "bg-teal-600 text-white shadow-sm" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <span>Uploaded Videos</span>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-bold ${
                activeTab === "videos" ? "bg-white/20 text-white" : "bg-slate-200 text-slate-700"
              }`}
            >
              {videos.length}
            </span>
          </button>
        </div>

        {/* Error notification */}
        {error && (
          <div className="mt-6 flex items-center justify-between rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
            <div className="flex items-center gap-3">
              <Icon name="alert" size={18} className="shrink-0 text-rose-600" />
              <span>{error}</span>
            </div>
            <button
              onClick={loadData}
              className="text-xs font-bold text-rose-800 underline hover:text-rose-950"
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading indicator */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-20 text-slate-400">
            <span className="h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-teal-600" />
            <p className="mt-4 text-sm font-medium">Loading history records...</p>
          </div>
        )}

        {!loading && (
          <div className="mt-6 space-y-8">
            {/* 1. Saved Media (Outputs) */}
            {(activeTab === "all" || activeTab === "saved") && (
              <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5">
                  <div>
                    <h2 className="text-base font-bold text-slate-900">Protected Outputs (Saved Media)</h2>
                    <p className="mt-0.5 text-xs text-slate-400">
                      Processed video files generated by the AI privacy engine
                    </p>
                  </div>
                  <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-bold text-teal-700">
                    {outputs.length} outputs
                  </span>
                </div>

                {outputs.length === 0 ? (
                  <div className="flex flex-col items-center py-14 text-center">
                    <span className="grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-slate-400">
                      <Icon name="shield" size={24} />
                    </span>
                    <h3 className="mt-3 text-sm font-bold text-slate-700">No protected outputs found</h3>
                    <p className="mt-1 text-xs text-slate-400 max-w-sm">
                      Completed video outputs will appear here with instant streaming preview and download links.
                    </p>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {outputs.map((out) => (
                      <div
                        key={out.processed_id}
                        className="flex flex-col gap-4 px-6 py-4 transition hover:bg-slate-50 sm:flex-row sm:items-center sm:justify-between"
                      >
                        <div className="flex items-center gap-4">
                          <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-teal-50 text-teal-600">
                            <Icon name="shield" size={22} />
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="truncate text-sm font-bold text-slate-800">
                                Protected Video #{out.processed_id}
                              </p>
                              <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
                                READY
                              </span>
                            </div>
                            <p className="mt-0.5 text-xs text-slate-400">
                              Source Media #{out.media_id} · Type:{" "}
                              <strong className="text-slate-600">
                                {(out.output_type || "protected_video").replace(/_/g, " ")}
                              </strong>
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 sm:self-center">
                          <button
                            onClick={() => setPreviewOutput(out)}
                            className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:border-slate-300 hover:bg-slate-50 transition"
                          >
                            <Icon name="eye" size={15} /> Preview
                          </button>
                          <a
                            href={getOutputDownloadUrl(out.processed_id)}
                            download
                            className="flex items-center gap-1.5 rounded-xl bg-teal-600 px-3.5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-teal-700 transition"
                          >
                            <Icon name="download" size={15} /> Download
                          </a>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 2. Processing Tasks */}
            {(activeTab === "all" || activeTab === "tasks") && (
              <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5">
                  <div>
                    <h2 className="text-base font-bold text-slate-900">Processing Tasks</h2>
                    <p className="mt-0.5 text-xs text-slate-400">
                      Lifecycle tracking for background AI protection pipelines
                    </p>
                  </div>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">
                    {tasks.length} tasks
                  </span>
                </div>

                {tasks.length === 0 ? (
                  <div className="flex flex-col items-center py-14 text-center">
                    <span className="grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-slate-400">
                      <Icon name="sliders" size={24} />
                    </span>
                    <h3 className="mt-3 text-sm font-bold text-slate-700">No processing tasks recorded</h3>
                    <p className="mt-1 text-xs text-slate-400">
                      Start an AI detection run from the Upload Media workflow.
                    </p>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {tasks.map((t) => (
                      <div
                        key={t.task_id}
                        className="flex flex-col gap-3 px-6 py-4 transition hover:bg-slate-50 sm:flex-row sm:items-center sm:justify-between"
                      >
                        <div className="flex items-center gap-4">
                          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-600">
                            <Icon name="sliders" size={19} />
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-semibold text-slate-800">
                                Task #{t.task_id} — {(t.protection_type || "both").replace(/_/g, " ")}
                              </p>
                              <span
                                className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${getStatusBadge(
                                  t.status
                                )}`}
                              >
                                {(t.status || "pending").toUpperCase()}
                              </span>
                            </div>
                            <p className="mt-0.5 text-xs text-slate-400">
                              Target Media #{t.media_id}
                              {t.progress != null ? ` · ${t.progress}% complete` : ""}
                              {t.created_at ? ` · ${formatDate(t.created_at)}` : ""}
                              {t.error_message ? ` · Error: ${t.error_message}` : ""}
                            </p>
                          </div>
                        </div>

                        {t.status === "completed" && (
                          <button
                            onClick={() => setActiveTab("saved")}
                            className="self-start text-xs font-semibold text-teal-600 hover:text-teal-700 sm:self-center"
                          >
                            View output →
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 3. Uploaded Videos */}
            {(activeTab === "all" || activeTab === "videos") && (
              <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="flex items-center justify-between border-b border-slate-100 px-6 py-5">
                  <div>
                    <h2 className="text-base font-bold text-slate-900">Uploaded Videos</h2>
                    <p className="mt-0.5 text-xs text-slate-400">
                      Original source videos stored in backend/uploads/
                    </p>
                  </div>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600">
                    {videos.length} videos
                  </span>
                </div>

                {videos.length === 0 ? (
                  <div className="flex flex-col items-center py-14 text-center">
                    <span className="grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-slate-400">
                      <Icon name="video" size={24} />
                    </span>
                    <h3 className="mt-3 text-sm font-bold text-slate-700">No videos uploaded yet</h3>
                    <p className="mt-1 text-xs text-slate-400">
                      Upload your first video to start detecting faces and number plates.
                    </p>
                    <Button onClick={() => navigate("upload")} className="mt-4 h-9 px-4 text-xs">
                      Upload media
                    </Button>
                  </div>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {videos.map((vid) => (
                      <div
                        key={vid.media_id}
                        className="flex flex-col gap-3 px-6 py-4 transition hover:bg-slate-50 sm:flex-row sm:items-center sm:justify-between"
                      >
                        <div className="flex items-center gap-4">
                          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-teal-50 text-teal-600">
                            <Icon name="video" size={20} />
                          </div>
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-slate-800">
                              {vid.file_name || `Media #${vid.media_id}`}
                            </p>
                            <p className="mt-0.5 text-xs text-slate-400">
                              Media #{vid.media_id}
                              {vid.duration_seconds != null ? ` · ${vid.duration_seconds.toFixed(1)}s` : ""}
                              {vid.fps != null ? ` · ${vid.fps.toFixed(0)} fps` : ""}
                              {vid.file_size ? ` · ${(vid.file_size / 1024 / 1024).toFixed(1)} MB` : ""}
                              {vid.created_at ? ` · ${formatDate(vid.created_at)}` : ""}
                            </p>
                          </div>
                        </div>

                        <span className="self-start rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-bold text-emerald-700 sm:self-center">
                          STORED
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Video Preview Modal */}
        {previewOutput && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 p-4 backdrop-blur-sm">
            <div className="relative w-full max-w-4xl overflow-hidden rounded-3xl bg-slate-900 text-white shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
                <div>
                  <h3 className="font-bold text-white">
                    Preview: Protected Video #{previewOutput.processed_id}
                  </h3>
                  <p className="text-xs text-slate-400">
                    Source Media #{previewOutput.media_id} ·{" "}
                    {(previewOutput.output_type || "protected_video").replace(/_/g, " ")}
                  </p>
                </div>
                <button
                  onClick={() => setPreviewOutput(null)}
                  className="grid h-9 w-9 place-items-center rounded-xl bg-white/10 text-slate-300 hover:bg-white/20 hover:text-white transition"
                  aria-label="Close preview"
                >
                  <Icon name="close" size={18} />
                </button>
              </div>

              <div className="p-4">
                <video
                  src={getOutputPreviewUrl(previewOutput.processed_id)}
                  controls
                  autoPlay
                  className="aspect-video w-full rounded-2xl bg-black"
                />
              </div>

              <div className="flex items-center justify-between border-t border-slate-800 bg-slate-900/50 px-6 py-4">
                <span className="text-xs text-slate-400">
                  Streaming directly from backend outputs storage
                </span>
                <div className="flex items-center gap-3">
                  <a
                    href={getOutputDownloadUrl(previewOutput.processed_id)}
                    download
                    className="inline-flex h-9 items-center gap-2 rounded-xl bg-teal-500 px-4 text-xs font-semibold text-white hover:bg-teal-600 transition"
                  >
                    <Icon name="download" size={14} /> Download File
                  </a>
                  <button
                    onClick={() => setPreviewOutput(null)}
                    className="inline-flex h-9 items-center rounded-xl border border-slate-700 px-4 text-xs font-semibold text-slate-300 hover:bg-white/10 transition"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("landing");
  const [detectionType, setDetectionType] = useState<DetectionType>("both");
  const [uploadedMedia, setUploadedMedia] = useState<MediaUploadResponse | null>(null);
  const [currentTask, setCurrentTask] = useState<ProcessingTaskResponse | null>(null);

  const navigate = (next: Screen) => {
    setScreen(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (screen === "landing") return <Landing navigate={navigate} />;
  if (screen === "dashboard") return <Dashboard navigate={navigate} />;
  if (screen === "upload") return <Upload navigate={navigate} uploadedMedia={uploadedMedia} setUploadedMedia={setUploadedMedia} />;
  if (screen === "detectionType") {
    return (
      <DetectionTypeSelection
        navigate={navigate}
        detectionType={detectionType}
        setDetectionType={setDetectionType}
        uploadedMedia={uploadedMedia}
        currentTask={currentTask}
        setCurrentTask={setCurrentTask}
      />
    );
  }
  if (screen === "detecting") return <DetectionProgress navigate={navigate} detectionType={detectionType} />;
  if (screen === "detect") return <Detect navigate={navigate} detectionType={detectionType} />;
  if (screen === "settings") return <ProtectionSettings navigate={navigate} detectionType={detectionType} />;
  if (screen === "processing") return <Processing navigate={navigate} />;
  if (screen === "preview") return <Preview navigate={navigate} />;
  if (screen === "saved") return <HistoryPage navigate={navigate} initialTab="saved" />;
  return <HistoryPage navigate={navigate} initialTab="all" />;
}

