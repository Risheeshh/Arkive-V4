import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import {
  Archive, ArrowUpRight, BookOpen, Check, ChevronRight, CircleAlert, Clock3, ExternalLink,
  FileText, Hash, Library, LogOut, MessageCircle, MoreHorizontal, Plus, Search, Send,
  Settings2, Sparkles, Star, Trash2, X, Zap, Heart, BarChart3, Activity,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { api, GOOGLE_AUTH_URL, type Bookmark, type Citation, type Status, type User, type SearchResult } from "./api";

type View = "library" | "search" | "chat" | "insights";
type AuthMode = "login" | "signup";

function SpaceCanvas() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 100);
    camera.position.z = 3;
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    ref.current.appendChild(renderer.domElement);
    const points = new THREE.BufferGeometry();
    const positions = new Float32Array(180 * 3);
    for (let i = 0; i < positions.length; i += 3) {
      positions[i] = (Math.random() - 0.5) * 7;
      positions[i + 1] = (Math.random() - 0.5) * 4;
      positions[i + 2] = (Math.random() - 0.5) * 3;
    }
    points.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const stars = new THREE.Points(points, new THREE.PointsMaterial({ color: 0x7d8cff, size: 0.018, transparent: true, opacity: 0.7 }));
    scene.add(stars);
    const resize = () => {
      const { clientWidth, clientHeight } = ref.current!;
      renderer.setSize(clientWidth, clientHeight, false);
      camera.aspect = clientWidth / clientHeight;
      camera.updateProjectionMatrix();
    };
    resize();
    window.addEventListener("resize", resize);
    let frame = 0;
    const animate = () => {
      stars.rotation.y += 0.0007;
      stars.rotation.x = Math.sin(Date.now() * 0.0002) * 0.05;
      renderer.render(scene, camera);
      frame = requestAnimationFrame(animate);
    };
    animate();
    return () => { cancelAnimationFrame(frame); window.removeEventListener("resize", resize); renderer.dispose(); points.dispose(); ref.current?.removeChild(renderer.domElement); };
  }, []);
  return <div ref={ref} className="space-canvas" aria-hidden="true" />;
}

function Logo({ small = false }: { small?: boolean }) {
  return <div className={`logo ${small ? "logo-small" : ""}`}><span className="logo-mark"><span /></span><span>arkive</span></div>;
}

function LandingVisual() {
  return <div className="landing-visual" aria-hidden="true">
    <div className="visual-orbit orbit-one" />
    <div className="visual-orbit orbit-two" />
    <motion.div className="visual-image image-main" animate={{ y: [0, -12, 0], rotate: [-2, 1, -2] }} transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}>
      <img src="https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=900&q=85" alt="" />
      <span><Sparkles size={13} /> SYNTHESIZED MEMORY</span>
    </motion.div>
    <motion.div className="visual-image image-secondary" animate={{ y: [0, 14, 0], rotate: [4, 1, 4] }} transition={{ duration: 10, repeat: Infinity, ease: "easeInOut", delay: 1 }}>
      <img src="https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=600&q=85" alt="" />
      <span><Library size={13} /> VISUAL LIBRARY</span>
    </motion.div>
    <div className="visual-spark spark-a">✦</div><div className="visual-spark spark-b">✧</div>
  </div>;
}

function LibraryVisuals() {
  return <div className="library-visuals" aria-hidden="true">
    <div className="library-glow glow-purple" /><div className="library-glow glow-teal" />
    <div className="library-ring ring-large" /><div className="library-ring ring-small" />
    <div className="library-scanline" />
  </div>;
}

function AuthScreen({ onAuthenticated, initialError = "" }: { onAuthenticated: (user: User) => void; initialError?: string }) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(initialError);
  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      if (mode === "signup") await api.register(email, password);
      const token = await api.login(email, password);
      localStorage.setItem("arkive_token", token.access_token);
      onAuthenticated(await api.me());
    } catch (err) { setError(err instanceof Error ? err.message : "Something went wrong."); }
    finally { setBusy(false); }
  };
  return <main className="auth-page"><SpaceCanvas /><div className="landing-copy"><Logo small /><div className="eyebrow"><Sparkles size={14} /> YOUR PERSONAL KNOWLEDGE UNIVERSE</div><h1>Everything worth<br /><em>remembering.</em></h1><p>Arkive turns scattered links into a visual, searchable library that gets smarter every time you save.</p><div className="landing-features"><span><Sparkles size={15} /> AI-curated genres</span><span><Library size={15} /> Visual memory cards</span><span><MessageCircle size={15} /> Ask your archive</span></div><LandingVisual /></div><motion.div className="auth-panel" initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}>
    <Logo />
    <div className="eyebrow"><Sparkles size={14} /> PERSONAL KNOWLEDGE SYSTEM</div>
    <h1>Your ideas,<br /><em>in orbit.</em></h1>
    <p className="auth-copy">Save the things that matter. Ask your archive anything. Let Arkive connect the dots.</p>
    <form onSubmit={submit} className="auth-form">
      <label>Email<input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required /></label>
      <label>Password<input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters" minLength={8} required /></label>
      {error && <div className="error-message"><CircleAlert size={15} />{error}</div>}
      <button className="primary-button wide" disabled={busy}>{busy ? "Opening your archive…" : mode === "login" ? "Enter Arkive" : "Create your archive"} <ArrowUpRight size={17} /></button>
    </form>
    <div className="or-divider"><span>or continue with</span></div>
    <a className="google-button" href={GOOGLE_AUTH_URL}><span className="google-g">G</span> Continue with Google</a>
    <p className="auth-switch">{mode === "login" ? "New to Arkive?" : "Already have an archive?"} <button onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(""); }}>{mode === "login" ? "Create an account" : "Sign in"}</button></p>
  </motion.div></main>;
}

function StatusBadge({ status }: { status: Status }) {
  const labels: Record<Status, string> = { unread: "Unread", read: "Ready", archived: "Archived", failed: "Failed" };
  return <span className={`status-badge ${status}`}><span className="status-dot" />{labels[status]}</span>;
}

function BookmarkCard({ bookmark, onOpen, onDelete, onStatus, onFavorite }: { bookmark: Bookmark; onOpen: () => void; onDelete: () => void; onStatus: (status: Status) => void; onFavorite: () => void }) {
  const host = (() => { try { return new URL(bookmark.url).hostname.replace("www.", ""); } catch { return bookmark.url; } })();
  return <motion.article className="bookmark-card" style={bookmark.image_url ? { backgroundImage: `linear-gradient(180deg, #11121955 0%, #111219 58%), url("${bookmark.image_url}")` } : undefined} layout initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} whileHover={{ y: -3 }}>
    <div className="card-top"><div className="site-icon">{bookmark.logo_url ? <img src={bookmark.logo_url} alt="" /> : host[0]?.toUpperCase()}</div><div className="card-actions"><button title={bookmark.is_favorite ? "Remove favorite" : "Favorite"} onClick={onFavorite}><Heart size={15} fill={bookmark.is_favorite ? "currentColor" : "none"} /></button><button title="Open source" onClick={() => window.open(bookmark.url, "_blank", "noopener,noreferrer")}><ExternalLink size={15} /></button><button title="Delete bookmark" onClick={onDelete}><Trash2 size={15} /></button></div></div>
    <button className="card-body" onClick={onOpen}><span className="domain">{bookmark.site_name || host}</span><h3>{bookmark.title}</h3><p>{bookmark.excerpt || bookmark.description || bookmark.content?.body?.slice(0, 120) || "Arkive is reading this page…"}</p><div className="genre-row">{bookmark.genres?.map((genre) => <span className="genre-pill" key={genre}>{genre}</span>)}</div></button>
    <div className="card-footer"><div className="tag-row">{bookmark.tags?.slice(0, 2).map((tag) => <span className="tag" key={tag.id}><Hash size={11} />{tag.name}</span>)}</div><button className="status-button" onClick={() => onStatus(bookmark.status === "archived" ? "unread" : "archived")}><StatusBadge status={bookmark.status} /></button></div>
  </motion.article>;
}

function AddBookmark({ onClose, onCreated }: { onClose: () => void; onCreated: (bookmark: Bookmark) => void }) {
  const [title, setTitle] = useState(""); const [url, setUrl] = useState(""); const [description, setDescription] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const submit = async (e: React.FormEvent) => { e.preventDefault(); setBusy(true); setError(""); try { onCreated(await api.createBookmark({ title, url, description: description || undefined })); onClose(); } catch (err) { setError(err instanceof Error ? err.message : "Could not save bookmark."); } finally { setBusy(false); } };
  return <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><motion.div className="modal" initial={{ opacity: 0, scale: .96 }} animate={{ opacity: 1, scale: 1 }}><div className="modal-heading"><div><div className="eyebrow">NEW MEMORY</div><h2>Save to Arkive</h2></div><button className="icon-button" onClick={onClose}><X /></button></div><form onSubmit={submit} className="modal-form"><label>Title<input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="What are you saving?" required /></label><label>URL<input type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" required /></label><label>Description <span className="optional">optional</span><textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Add a note for future you…" rows={3} /></label>{error && <div className="error-message"><CircleAlert size={15} />{error}</div>}<button className="primary-button wide" disabled={busy}>{busy ? "Saving…" : "Save memory"} <Plus size={17} /></button></form></motion.div></div>;
}

function DetailModal({ bookmark, onClose, onChanged }: { bookmark: Bookmark; onClose: () => void; onChanged: (bookmark: Bookmark) => void }) {
  const [tag, setTag] = useState(""); const [busy, setBusy] = useState(false); const [genres, setGenres] = useState<string[]>(bookmark.genres || []);
  const addTag = async (e: React.FormEvent) => { e.preventDefault(); if (!tag.trim()) return; setBusy(true); try { onChanged(await api.addTags(bookmark.id, [...bookmark.tags.map((t) => t.name), tag.trim()])); setTag(""); } finally { setBusy(false); } };
  const toggleGenre = async (genre: string) => { const next = genres.includes(genre) ? genres.filter((item) => item !== genre) : [...genres, genre]; setGenres(next); onChanged(await api.updateBookmark(bookmark.id, { genres: next })); };
  return <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><motion.div className="modal detail-modal" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}><div className="modal-heading"><div><div className="domain">{new URL(bookmark.url).hostname}</div><h2>{bookmark.title}</h2></div><button className="icon-button" onClick={onClose}><X /></button></div><div className="detail-meta"><StatusBadge status={bookmark.status} /><span><Clock3 size={14} /> Saved {new Date(bookmark.created_at).toLocaleDateString()}</span><a href={bookmark.url} target="_blank" rel="noreferrer">Visit source <ArrowUpRight size={14} /></a></div>{bookmark.description && <p className="detail-description">{bookmark.description}</p>}<div className="detail-content">{bookmark.content?.body || bookmark.content?.raw_text ? <p>{bookmark.content.body || bookmark.content.raw_text}</p> : <div className="empty-detail"><Zap size={24} /><b>Arkive is reading this memory</b><span>Content and semantic search will be available when processing finishes.</span></div>}</div><div className="genre-editor"><span className="domain">GENRES · EDIT ANYTIME</span><div className="genre-picker">{["Artificial Intelligence", "Business", "Career", "Design", "Development", "Education", "Finance", "Health", "Lifestyle", "Marketing", "News", "Photography", "Productivity", "Science", "Security", "Travel", "Writing"].map((genre) => <button type="button" className={genres.includes(genre) ? "selected" : ""} key={genre} onClick={() => toggleGenre(genre)}>{genre}</button>)}</div></div><form className="tag-input" onSubmit={addTag}><Hash size={15} /><input value={tag} onChange={(e) => setTag(e.target.value)} placeholder="Add a tag" /><button disabled={busy}>Add</button></form><div className="tag-row detail-tags">{bookmark.tags.map((t) => <span className="tag" key={t.id}><Hash size={11} />{t.name}</span>)}</div></motion.div></div>;
}

function ChatView({ bookmarks }: { bookmarks: Bookmark[] }) {
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; text: string; citations?: Citation[] }[]>([{ role: "assistant", text: "Ask me anything about your saved knowledge. I’ll search your archive and cite the sources I used." }]);
  const [question, setQuestion] = useState(""); const [busy, setBusy] = useState(false);
  const ask = async (e: React.FormEvent) => { e.preventDefault(); if (!question.trim() || busy) return; const current = question.trim(); setQuestion(""); setMessages((items) => [...items, { role: "user", text: current }]); setBusy(true); try { const answer = await api.chat(current); setMessages((items) => [...items, { role: "assistant", text: answer.answer, citations: answer.citations }]); } catch (err) { setMessages((items) => [...items, { role: "assistant", text: err instanceof Error ? err.message : "Chat is unavailable right now." }]); } finally { setBusy(false); } };
  return <div className="chat-layout"><div className="section-heading"><div><div className="eyebrow"><Sparkles size={14} /> RAG INTELLIGENCE</div><h1>Talk to your archive</h1><p>{bookmarks.length} memories in context. Answers are grounded in your saved content.</p></div></div><div className="chat-window">{messages.map((message, index) => <motion.div key={index} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={`chat-message ${message.role}`}><div className="message-avatar">{message.role === "assistant" ? <Sparkles size={15} /> : "Y"}</div><div><p>{message.text}</p>{message.citations?.length ? <div className="citation-row">{message.citations.map((citation) => <a href={citation.url} target="_blank" rel="noreferrer" key={citation.bookmark_id}><FileText size={13} />{citation.title}</a>)}</div> : null}</div></motion.div>)}{busy && <div className="chat-message assistant"><div className="message-avatar"><Sparkles size={15} /></div><div className="typing"><i /><i /><i /></div></div>}</div><form className="chat-input" onSubmit={ask}><input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask your archive anything…" /><button className="primary-button" disabled={busy || !question.trim()}><Send size={17} /></button></form></div>;
}

function SearchView({ results, query, onQuery, onOpen, recommendations }: { results: SearchResult[]; query: string; onQuery: (query: string) => void; onOpen: (id: string) => void; recommendations: string[] }) {
  const [value, setValue] = useState(query); const submit = (e: React.FormEvent) => { e.preventDefault(); onQuery(value); };
  return <div><div className="section-heading"><div><div className="eyebrow"><Search size={14} /> SEMANTIC SEARCH</div><h1>Find the thread</h1><p>Search meaning, not just keywords, across your archive.</p></div></div><form className="big-search" onSubmit={submit}><Search size={19} /><input autoFocus value={value} onChange={(e) => setValue(e.target.value)} placeholder="Try “ideas for better focus”…" /><button className="primary-button">Search</button></form>{!query && <div className="recommendations"><div className="eyebrow"><Sparkles size={14} /> RECOMMENDED THREADS</div>{recommendations.map((item) => <button key={item} onClick={() => { setValue(item); onQuery(item); }}>{item} <ArrowUpRight size={14} /></button>)}</div>}{query && <div className="results-label">{results.length} results for <strong>“{query}”</strong></div>}<div className="search-results">{results.map((result) => <button className="search-result" key={`${result.bookmark_id}-${result.chunk}`} onClick={() => onOpen(result.bookmark_id)}><div className="result-icon"><FileText size={16} /></div><div><div className="domain">{new URL(result.url).hostname}</div><h3>{result.title}</h3><p>{result.chunk}</p></div><ChevronRight size={18} /></button>)}{query && !results.length && <div className="empty-state"><Search size={26} /><h3>No matching memories yet</h3><p>Try a broader question or save a few more sources.</p></div>}</div></div>;
}

function InsightsView({ insights }: { insights: import("./api").Insights | null }) {
  if (!insights) return <div className="empty-state"><Activity size={26} /><h3>Loading your insights…</h3></div>;
  const max = Math.max(...insights.activity.map((point) => point.count), 1);
  return <div className="insights-view"><div className="section-heading"><div><div className="eyebrow"><BarChart3 size={14} /> YOUR ARCHIVE SIGNALS</div><h1>See your knowledge evolve</h1><p>Small, useful signals from the way you save and revisit ideas.</p></div></div><div className="insights-cards"><div><strong>{insights.total}</strong><span>memories</span></div><div><strong>{insights.favorites}</strong><span>favourites</span></div><div><strong>{insights.ready}</strong><span>processed</span></div><div><strong>{insights.unread}</strong><span>to explore</span></div></div><div className="insights-grid"><section className="insight-panel"><div className="panel-title"><span>Saving rhythm</span><Activity size={16} /></div><div className="activity-chart">{insights.activity.map((point) => <div className="activity-bar" key={point.date} title={`${point.date}: ${point.count}`}><span style={{ height: `${Math.max(point.count / max * 100, point.count ? 12 : 4)}%` }} /></div>)}</div></section><section className="insight-panel"><div className="panel-title"><span>Top genres</span><Sparkles size={16} /></div>{insights.genres.slice(0, 6).map((genre) => <div className="genre-stat" key={genre.name}><span>{genre.name}</span><b>{genre.count}</b><i style={{ width: `${Math.min(100, genre.count / Math.max(insights.total, 1) * 100 * 2)}%` }} /></div>)}</section></div></div>;
}

function App() {
  const [user, setUser] = useState<User | null>(null); const [checking, setChecking] = useState(true); const [oauthError, setOauthError] = useState(""); const [view, setView] = useState<View>("library"); const [bookmarks, setBookmarks] = useState<Bookmark[]>([]); const [selected, setSelected] = useState<Bookmark | null>(null); const [showAdd, setShowAdd] = useState(false); const [query, setQuery] = useState(""); const [results, setResults] = useState<SearchResult[]>([]); const [filter, setFilter] = useState<"all" | Status>("all"); const [loading, setLoading] = useState(false); const [toast, setToast] = useState(""); const [insights, setInsights] = useState<import("./api").Insights | null>(null);
  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const oauthToken = params.get("oauth_token");
    const error = params.get("oauth_error");
    if (oauthToken) localStorage.setItem("arkive_token", oauthToken);
    if (error) setOauthError(error);
    if (oauthToken || error) window.history.replaceState(null, document.title, window.location.pathname + window.location.search);
  }, []);
  useEffect(() => { if (!localStorage.getItem("arkive_token")) { setChecking(false); return; } api.me().then(setUser).catch(() => localStorage.removeItem("arkive_token")).finally(() => setChecking(false)); }, []);
  useEffect(() => { if (!user) return; setLoading(true); Promise.all([api.bookmarks(), api.insights()]).then(([items, archiveInsights]) => { setBookmarks(items); setInsights(archiveInsights); }).catch((err) => setToast(err.message)).finally(() => setLoading(false)); }, [user]);
  const filtered = useMemo(() => filter === "all" ? bookmarks : bookmarks.filter((bookmark) => bookmark.status === filter), [bookmarks, filter]);
  const refreshSelected = (bookmark: Bookmark) => { setBookmarks((items) => items.map((item) => item.id === bookmark.id ? bookmark : item)); setSelected(bookmark); };
  const changeStatus = async (bookmark: Bookmark, status: Status) => { try { const updated = await api.updateBookmark(bookmark.id, { status }); refreshSelected(updated); } catch (err) { setToast(err instanceof Error ? err.message : "Could not update bookmark."); } };
  const remove = async (bookmark: Bookmark) => { if (!window.confirm(`Delete “${bookmark.title}”?`)) return; try { await api.deleteBookmark(bookmark.id); setBookmarks((items) => items.filter((item) => item.id !== bookmark.id)); if (selected?.id === bookmark.id) setSelected(null); } catch (err) { setToast(err instanceof Error ? err.message : "Could not delete bookmark."); } };
  const runSearch = async (value: string) => { setQuery(value); if (!value.trim()) { setResults([]); return; } try { setResults((await api.search(value)).results); } catch (err) { setToast(err instanceof Error ? err.message : "Search is unavailable."); } };
  const favorite = async (bookmark: Bookmark) => { try { refreshSelected(await api.updateBookmark(bookmark.id, { is_favorite: !bookmark.is_favorite })); } catch (err) { setToast(err instanceof Error ? err.message : "Could not update favorite."); } };
  const grouped = useMemo(() => filtered.reduce<Record<string, Bookmark[]>>((groups, bookmark) => { const genres = bookmark.genres?.length ? bookmark.genres : ["Uncategorized"]; genres.forEach((genre) => { (groups[genre] ||= []).push(bookmark); }); return groups; }, {}), [filtered]);
  if (checking) return <div className="loading-screen"><Logo /><div className="loader" /></div>;
  if (!user) return <AuthScreen onAuthenticated={setUser} initialError={oauthError} />;
  const counts = { all: bookmarks.length, unread: bookmarks.filter((b) => b.status === "unread").length, read: bookmarks.filter((b) => b.status === "read").length, archived: bookmarks.filter((b) => b.status === "archived").length };
  return <div className="app-shell"><SpaceCanvas /><LibraryVisuals /><aside className="sidebar"><Logo small /><nav><button className={view === "library" ? "active" : ""} onClick={() => setView("library")}><Library size={18} /> Library <span>{counts.all}</span></button><button className={view === "search" ? "active" : ""} onClick={() => setView("search")}><Search size={18} /> Search</button><button className={view === "insights" ? "active" : ""} onClick={() => setView("insights")}><BarChart3 size={18} /> Insights</button><button className={view === "chat" ? "active" : ""} onClick={() => setView("chat")}><MessageCircle size={18} /> Ask Arkive <span className="new-dot" /></button></nav><div className="sidebar-bottom"><button><Settings2 size={18} /> Settings</button><div className="user-chip"><div className="avatar">{user.email[0].toUpperCase()}</div><span>{user.email}</span><button aria-label="Log out" onClick={() => { localStorage.removeItem("arkive_token"); setUser(null); }}><LogOut size={15} /></button></div></div></aside><main className="main-content"><header className="topbar"><div className="mobile-logo"><Logo small /></div><div className="topbar-search" onClick={() => setView("search")}><Search size={16} /><span>Search your archive</span><kbd>⌘ K</kbd></div><button className="primary-button save-button" onClick={() => setShowAdd(true)}><Plus size={17} /> Save memory</button></header><div className="content-wrap">{view === "chat" ? <ChatView bookmarks={bookmarks} /> : view === "search" ? <SearchView results={results} query={query} onQuery={runSearch} recommendations={insights?.recommendations || []} onOpen={(id) => { const bookmark = bookmarks.find((item) => item.id === id); if (bookmark) setSelected(bookmark); }} /> : view === "insights" ? <InsightsView insights={insights} /> : <><div className="welcome-row"><div><div className="eyebrow"><span className="pulse-dot" /> YOUR KNOWLEDGE UNIVERSE</div><h1>Good morning, <em>{user.email.split("@")[0]}</em></h1><p>Keep collecting. Keep connecting. Your future self is grateful.</p></div><div className="orbit-stat"><div className="orbit-ring"><span>{counts.all}</span></div><small>memories<br />collected</small></div></div><div className="stats-row"><div className="stat-card"><span className="stat-icon purple"><BookOpen size={16} /></span><div><strong>{counts.all}</strong><small>Total memories</small></div></div><div className="stat-card"><span className="stat-icon amber"><Clock3 size={16} /></span><div><strong>{counts.unread}</strong><small>Need your attention</small></div></div><div className="stat-card"><span className="stat-icon green"><Check size={16} /></span><div><strong>{counts.read}</strong><small>Ready to explore</small></div></div><div className="stat-card"><span className="stat-icon blue"><Archive size={16} /></span><div><strong>{counts.archived}</strong><small>Archived</small></div></div></div><div className="library-heading"><div><h2>Your library</h2><p>{loading ? "Syncing with Arkive…" : "A living collection of the things you want to remember."}</p></div><div className="filter-tabs">{(["all", "unread", "read", "archived"] as const).map((tab) => <button key={tab} className={filter === tab ? "active" : ""} onClick={() => setFilter(tab)}>{tab === "all" ? "All memories" : tab[0].toUpperCase() + tab.slice(1)}</button>)}</div></div>{filtered.length ? <div className="genre-sections">{Object.entries(grouped).map(([genre, items]) => <section className="genre-section" key={genre}><div className="genre-heading"><h2>{genre}</h2><span>{items.length} {items.length === 1 ? "memory" : "memories"}</span></div><div className="bookmark-grid">{items.map((bookmark) => <BookmarkCard key={`${genre}-${bookmark.id}`} bookmark={bookmark} onOpen={() => setSelected(bookmark)} onDelete={() => remove(bookmark)} onStatus={(status) => changeStatus(bookmark, status)} onFavorite={() => favorite(bookmark)} />)}</div></section>)}</div> : <div className="empty-state library-empty"><div className="empty-orbit"><Star size={24} /></div><h3>{filter === "all" ? "Your archive starts here" : `No ${filter} memories`}</h3><p>Save an article, idea, or resource and let Arkive make it useful later.</p><button className="primary-button" onClick={() => setShowAdd(true)}><Plus size={16} /> Save your first memory</button></div>}</>}</div></main><AnimatePresence>{showAdd && <AddBookmark onClose={() => setShowAdd(false)} onCreated={(bookmark) => setBookmarks((items) => [bookmark, ...items])} />}{selected && <DetailModal bookmark={selected} onClose={() => setSelected(null)} onChanged={refreshSelected} />}{toast && <motion.div className="toast" initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} onClick={() => setToast("")}><CircleAlert size={15} />{toast}<X size={14} /></motion.div>}</AnimatePresence></div>;
}

export default App;
