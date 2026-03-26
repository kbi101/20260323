import React, { useState, useEffect, useRef } from 'react';
import { 
  Settings, History, Brain, Send, RotateCcw, Trash2, 
  Terminal, BarChart2, Shield, Search, FileText, ChevronRight,
  Database, Activity, Zap, Layers, Cpu, Maximize2, Minimize2,
  FileSearch, MessageSquare, Code, Loader2, Info, Plus, Palette,
  Menu, X, Copy, Download, Check
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_BASE = import.meta.env.VITE_API_BASE || "";

const App = () => {
    const [task, setTask] = useState("");
    const [history, setHistory] = useState([]);
    const [memories, setMemories] = useState([]);
    const [reportsList, setReportsList] = useState([]);
    const [logs, setLogs] = useState(["[SYSTEM] LINK ESTABLISHED. MINION 2.0 READY."]);
    const [sid, setSid] = useState("");
    const [phases, setPhases] = useState("");
    const [skillsList, setSkillsList] = useState({});
    const [selectedSkill, setSelectedSkill] = useState("research");
    const [model, setModel] = useState("qwen3.5:35b");
    const [activeTab, setActiveTab] = useState("history");
    const [isAdvOpen, setIsAdvOpen] = useState(false);
    const [status, setStatus] = useState("IDLE");
    const [conversation, setConversation] = useState([]);
    const [deletingId, setDeletingId] = useState(null);
    const [recallLoading, setRecallLoading] = useState(false);
    const [theme, setTheme] = useState(localStorage.getItem('minion-theme') || 'cyan');
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [copiedId, setCopiedId] = useState(null);

    useEffect(() => {
        localStorage.setItem('minion-theme', theme);
        document.body.className = `theme-${theme}`;
    }, [theme]);

    const logInterval = useRef(null);
    const logEndRef = useRef(null);
    const chatEndRef = useRef(null);

    useEffect(() => { loadHistory(); loadMemories(); loadSkills(); loadReports(); }, []);
    useEffect(() => {
        // Only auto-scroll to the neural frontier during active orchestration
        if (status === 'ORCHESTRATING') {
            chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); 
        }
    }, [conversation, status]);

    const loadHistory = async () => {
        try { const r = await fetch(`${API_BASE}/api/history`); setHistory(await r.json()); } catch(e) {}
    };
    const loadMemories = async () => {
        try { const r = await fetch(`${API_BASE}/api/memories`); setMemories(await r.json()); } catch(e) {}
    };
    const loadSkills = async () => {
        try { const r = await fetch(`${API_BASE}/api/skills`); setSkillsList(await r.json()); } catch(e) {}
    };
    const loadReports = async () => {
        try { const r = await fetch(`${API_BASE}/api/reports`); setReportsList(await r.json()); } catch(e) {}
    };

    const startMission = async () => {
        const inputTask = task.trim();
        if (!inputTask) return;
        
        // 🏛️ Neural Branching: Always deploy a NEW session for fresh directives
        const session = `session-${Date.now()}`;
        setSid(session);
        setLogs(prev => [...prev, `⚡ [MISSION] DEPLOYING CORE: ${session}`]);
        setConversation([`user: ${inputTask}`]);
        setStatus("ORCHESTRATING");
        
        try {
            const res = await fetch(`${API_BASE}/api/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ task: inputTask, sessionId: session, phases, model, skill: selectedSkill })
            });

            if (res.ok) {
                if (logInterval.current) clearInterval(logInterval.current);
                logInterval.current = setInterval(async () => {
                    const lRes = await fetch(`${API_BASE}/api/logs/${session}`);
                    if (lRes.ok) {
                        const newLogs = await lRes.json();
                        setLogs(newLogs);
                        
                        const chatLines = newLogs.filter(L => L.includes('assistant') || L.includes('user') || L.includes('PHASE') || L.includes('FINAL REPORT'));
                        if (chatLines.length > 0) setConversation(chatLines);

                        if (newLogs[newLogs.length-1].includes('COMPLETE')) {
                           clearInterval(logInterval.current);
                           setStatus("COMPLETE");
                           loadHistory(); loadMemories(); loadReports();
                        }
                    }
                }, 1500);
            }
        } catch(e) {
            setLogs(prev => [...prev, `❌ [FAULT] DEPLOYMENT FAILED: ${e.message}`]);
            setStatus("FAULT");
        }
    };

    const resetMission = () => {
        setSid("");
        setTask("");
        setConversation([]);
        setStatus("IDLE");
        setLogs(["[SYSTEM] NEURAL LINK RESET. HUB READY."]);
        if (window.innerWidth < 1024) setIsSidebarOpen(false);
    };

    const viewHistorySession = async (session_id, task_content, onlyReport = false) => {
        setRecallLoading(true);
        setStatus("RECALLING");
        setSid(session_id);
        const startLogs = [`📂 [AUDIT] RECALLING SESSION: ${session_id}`, `🎯 OBJECTIVE: ${task_content}`];
        setLogs(startLogs);
        
        try {
            const turnsRes = await fetch(`${API_BASE}/api/turns/${session_id}`);
            const turns = await turnsRes.json();
            const reportRes = await fetch(`${API_BASE}/api/report/${session_id}`);
            const report = await reportRes.json();
            
            let reconstructed = [`user: ${task_content}${onlyReport ? ' (FINAL REPORT EXTRACT)' : ''}`];
            if (!onlyReport && Array.isArray(turns)) { 
                turns.forEach(t => { reconstructed.push(`assistant: ${t.response}`); });
            }
            if (report && report.report_content) reconstructed.push(`FINAL REPORT: \n${report.report_content}`);
            
            setConversation(reconstructed);
            setStatus("AUDIT MODE");
            setLogs([...startLogs, `✅ [READY] MISSION RECONSTRUCTED.`]);
        } catch(e) {
            setLogs(prev => [...prev, `❌ [AUDIT FAULT] RECALL FAILED: ${e.message}`]);
        } finally {
            setRecallLoading(false);
        }
    };

    const copyToClipboard = (text, id) => {
        // High-Compatibility Neural Copy: Fallback for non-secure contexts
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text).then(() => {
                setCopiedId(id);
                setTimeout(() => setCopiedId(null), 2000);
            }).catch(err => {
                console.error("Clipboard Fault:", err);
                fallbackCopy(text, id);
            });
        } else {
            fallbackCopy(text, id);
        }
    };

    const fallbackCopy = (text, id) => {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            setCopiedId(id);
            setTimeout(() => setCopiedId(null), 2000);
        } catch (err) {
            console.error('Fallback Copy Fault:', err);
        }
        document.body.removeChild(textArea);
    };

    const downloadReport = (title, content) => {
        const element = document.createElement("a");
        const file = new Blob([content], {type: 'text/markdown'});
        element.href = URL.createObjectURL(file);
        element.download = `${title.replace(/\s+/g, '_').toLowerCase()}_report.md`;
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    };

    const deleteSession = async (session_id) => {
        // 🏛️ Professional Silent Purge: Removing mission records without intrusive alerts
        try {
            const res = await fetch(`${API_BASE}/api/sessions/${session_id}`, { method: 'DELETE' });
            if (res.ok) {
                // Instant UI Sync: Filter out the purged directive and refresh global lists
                setHistory(prev => prev.filter(h => h.id !== session_id));
                loadMemories();
                loadReports();
                if (sid === session_id) resetMission();
            }
        } catch(e) {
            console.error("Purge Fault:", e);
        }
    };

    const clearNeuralCache = async () => {
        // 🏛️ Neural Purge: Completely resetting the agent's long-term reasoning cache
        if (!window.confirm("Perform a full Neural Purge? This will clear all AI reasoning cache for a 100% fresh start.")) return;
        try {
            await fetch(`${API_BASE}/api/cache`, { method: 'DELETE' });
            setLogs(prev => [...prev, "🧠 [SYSTEM] NEURAL CACHE PURGED. STANDBY FOR FRESH REASONING."]);
        } catch(e) { console.error("Purge Error:", e); }
    };

    const renderMessageContent = (raw) => {
        let clean = raw.replace(/^assistant:\s*/i, '').replace(/^user:\s*/i, '');
        const fragments = [];
        const lines = clean.split('\n');
        
        lines.forEach((line, idx) => {
            if (line.trim().startsWith('TOOL:')) {
                fragments.push(
                    <div key={idx} className="my-2 bg-black/40 border-l-[2px] border-[#00f2ff] p-2.5 rounded-r-lg font-mono text-[11px] text-cyan-400 group relative">
                        <div className="text-[8px] font-black uppercase tracking-widest opacity-30 mb-0.5 flex items-center gap-2"><Cpu size={10} /> Logic Call</div>
                        <div className="whitespace-pre-wrap">{line.replace('TOOL:', '').trim()}</div>
                    </div>
                );
            } else if (line.trim().startsWith('PHASE:')) {
                 fragments.push(
                    <div key={idx} className="my-4 flex items-center gap-3 opacity-40">
                        <div className="flex-1 h-[1px] bg-white/10"></div>
                        <div className="text-[9px] font-black text-[#00f2ff] uppercase tracking-[0.5em]">{line.trim()}</div>
                        <div className="flex-1 h-[1px] bg-white/10"></div>
                    </div>
                );
            } else if (line.trim()) {
                fragments.push(<div key={idx} className="mb-1 leading-relaxed tracking-tight">{line}</div>);
            }
        });
        
        return <>{fragments}</>;
    };

    return (
        <div className={`h-[100dvh] bg-[var(--theme-bg)] text-[#ececec] font-sans selection:bg-[var(--theme-accent)]/30 antialiased overflow-hidden flex transition-theme theme-${theme}`}>
            {/* Mobile Overlay */}
            {isSidebarOpen && (
                <div 
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 lg:hidden"
                    onClick={() => setIsSidebarOpen(false)}
                />
            )}
            
            {/* PANEL 1: SIDEBAR HUB */}
            <aside className={`
                fixed lg:relative inset-y-0 left-0 w-[320px] sm:w-[360px] 
                bg-[var(--theme-sidebar)] border-r border-[#ffffff0a] 
                flex flex-col shadow-2xl z-40 lg:z-20 overflow-hidden transition-all duration-300 ease-in-out
                ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
            `}>
                <div className="px-5 pt-6 pb-4">
                    <div className="flex items-center justify-between mb-5 group">
                        <div className="flex items-center gap-3 cursor-pointer" onClick={resetMission}>
                            <div className="w-8 h-8 rounded-lg bg-[var(--theme-accent)] flex items-center justify-center shadow-[0_0_20px_var(--theme-glow)] group-hover:shadow-[0_0_40px_var(--theme-glow)] transition-all">
                                <Plus size={18} className="text-black font-black" />
                            </div>
                            <h1 className="text-xl font-bold tracking-tight text-[var(--theme-accent)]">Minion 2.0</h1>
                        </div>
                        <div className="flex items-center gap-1">
                            <button onClick={() => setIsSidebarOpen(false)} className="lg:hidden p-1.5 rounded-full hover:bg-white/5 transition-colors text-slate-500 hover:text-[var(--theme-accent)]">
                                <X size={20} />
                            </button>
                            <button onClick={() => {
                                const themes = ['cyan', 'forest', 'crimson', 'violet', 'amber'];
                                const next = themes[(themes.indexOf(theme) + 1) % themes.length];
                                setTheme(next);
                            }} className="p-1.5 rounded-full hover:bg-white/5 transition-colors text-slate-500 hover:text-[var(--theme-accent)]" title="Cycle System Theme">
                                <Palette size={16} />
                            </button>
                            <button onClick={clearNeuralCache} className="p-1.5 rounded-full hover:bg-white/5 transition-colors text-slate-500 hover:text-amber-400" title="Neural Purge: Clear Reasoning Cache">
                                <Zap size={16} />
                            </button>
                            <button onClick={resetMission} className="p-1.5 rounded-full hover:bg-white/5 transition-colors text-slate-500 hover:text-[var(--theme-accent)]" title="Reset Mission Canvas">
                                <RotateCcw size={16} />
                            </button>
                        </div>
                    </div>

                    <div className="flex bg-black/40 rounded-3xl p-1 gap-1 border border-white/5">
                        {['history', 'reports', 'console', 'memories'].map(t => (
                            <button key={t} onClick={() => setActiveTab(t)} className={`flex-1 py-1.5 text-[8px] font-black uppercase tracking-widest rounded-2xl transition-all ${activeTab === t ? 'bg-[#00f2ff] text-black shadow-lg shadow-[#00f2ff]/20' : 'text-slate-600 hover:text-slate-400 font-bold'}`}>
                                {t}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="flex-1 overflow-hidden flex flex-col">
                    {activeTab === 'console' && (
                        <div className="flex-1 bg-black/60 m-3 mt-0 rounded-xl border border-white/5 p-4 font-mono text-[11px] leading-snug overflow-y-auto space-y-1 scrollbar-none text-[#777]">
                            {logs.map((L, i) => (
                                <div key={i} className={`flex gap-3 ${L.includes('⚡') || L.includes('📂') ? 'text-[#00f2ff] font-bold' : L.includes('❌') ? 'text-red-400' : ''}`}>
                                    <span className="opacity-10 shrink-0 select-none">[{i.toString().padStart(3, '0')}]</span>
                                    <span className="break-all whitespace-pre-wrap">{L}</span>
                                </div>
                            ))}
                            <div ref={logEndRef} />
                        </div>
                    )}

                    {activeTab === 'history' && (
                        <div className="flex-1 overflow-y-auto px-4 divide-y divide-white/5">
                            {history.length === 0 && <div className="p-10 text-center text-[10px] text-slate-800 font-black uppercase tracking-[0.3em]">Neural Link Standby...</div>}
                            {history.map(h => (
                                <div key={h.id} onClick={() => viewHistorySession(h.id, h.task_content)} className={`py-3 group transition-all px-2 relative rounded-lg cursor-pointer ${sid === h.id ? 'bg-[#00f2ff]/5 border-l-2 border-[#00f2ff]' : 'border-l-2 border-transparent hover:bg-white/[0.01]'}`}>
                                    <div className={`text-[13px] font-bold leading-snug line-clamp-2 mb-1 tracking-tight ${sid === h.id ? 'text-[#00f2ff]' : 'text-slate-200 group-hover:text-[#00f2ff]'}`}>{h.task_content}</div>
                                    <div className="flex items-center justify-between text-[8px] font-black text-slate-600 uppercase tracking-widest">
                                        <span>{h.skill_name || 'RESEARCH'} • {new Date(h.timestamp).toLocaleDateString()}</span>
                                        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button onClick={(e) => { e.stopPropagation(); setTask(h.task_content); setSid(h.id); }} className="text-[#00f2ff] hover:scale-125 transition-transform"><RotateCcw size={10} /></button>
                                            
                                            {deletingId === h.id ? (
                                                <button 
                                                    onClick={(e) => { e.stopPropagation(); deleteSession(h.id); }} 
                                                    className="bg-red-500/20 text-red-400 px-2 py-0.5 rounded border border-red-500/50 hover:bg-red-500 hover:text-white transition-all animate-pulse"
                                                >
                                                    CONFIRM?
                                                </button>
                                            ) : (
                                                <button 
                                                    onClick={(e) => { e.stopPropagation(); setDeletingId(h.id); }} 
                                                    className="text-red-500 hover:scale-125 transition-transform"
                                                >
                                                    <Trash2 size={10} />
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {activeTab === 'memories' && (
                        <div className="flex-1 overflow-y-auto p-4 space-y-2">
                            {memories.length === 0 && <div className="p-10 text-center text-[10px] text-slate-800 font-black uppercase tracking-[0.3em]">No Extractions Found</div>}
                            {memories.map(m => (
                                <div key={m.id} className="p-3 bg-white/[0.01] border-l-2 border-[#00f2ff]/30 rounded-r-lg transition-all hover:bg-white/[0.04] group">
                                    <div className="text-[8px] text-[#00f2ff]/60 font-black uppercase tracking-tight mb-0.5 group-hover:text-[#00f2ff]">/{m.key}</div>
                                    <div className="text-[12px] text-slate-400 font-medium leading-relaxed group-hover:text-slate-200">{m.value}</div>
                                </div>
                            ))}
                        </div>
                    )}

                    {activeTab === 'reports' && (
                        <div className="flex-1 overflow-y-auto px-4 divide-y divide-white/5">
                            {reportsList.length === 0 && <div className="p-10 text-center text-[10px] text-slate-800 font-black uppercase tracking-[0.3em]">No Reports Found</div>}
                            {reportsList.map(r => (
                                <div key={r.session_id} onClick={() => viewHistorySession(r.session_id, r.task, true)} className={`py-3 group transition-all px-2 relative rounded-lg cursor-pointer ${sid === r.session_id ? 'bg-[var(--theme-accent)]/5 border-l-2 border-[var(--theme-accent)]' : 'border-l-2 border-transparent hover:bg-white/[0.01]'}`}>
                                    <div className={`text-[13px] font-bold leading-snug line-clamp-2 mb-1 tracking-tight ${sid === r.session_id ? 'text-[var(--theme-accent)]' : 'text-slate-200 group-hover:text-[var(--theme-accent)]'}`}>📄 {r.task}</div>
                                    <div className="flex items-center justify-between text-[8px] font-black text-slate-600 uppercase tracking-widest mt-1">
                                        <span>{new Date(r.timestamp).toLocaleDateString()}</span>
                                        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button 
                                                onClick={(e) => { e.stopPropagation(); copyToClipboard(r.report_content, r.session_id); }} 
                                                className="text-[var(--theme-accent)] hover:scale-125 transition-transform p-1"
                                                title="Quick Copy"
                                            >
                                                {copiedId === r.session_id ? <Check size={10} className="text-green-400" /> : <Copy size={10} />}
                                            </button>
                                            <button 
                                                onClick={(e) => { e.stopPropagation(); downloadReport(r.task.substring(0, 30), r.report_content); }} 
                                                className="text-[var(--theme-accent)] hover:scale-125 transition-transform p-1"
                                                title="Quick Download"
                                            >
                                                <Download size={10} />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                <div className="p-4 border-t border-white/5 bg-black/20 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className={`w-1.5 h-1.5 rounded-full ${status !== 'IDLE' ? 'bg-[var(--theme-accent)] animate-pulse' : 'bg-slate-700'}`}></div>
                        <span className="text-[8px] font-black text-slate-600 uppercase tracking-[0.3em]">{status}</span>
                    </div>
                </div>
            </aside>

            {/* PANEL 2: MAIN EXECUTION (FLEX-1) */}
            <main className="flex-1 flex flex-col relative bg-[var(--theme-bg)] shadow-[inset_0_0_100px_rgba(0,0,0,0.5)] transition-theme min-w-0">
                {/* Mobile Header */}
                <header className="lg:hidden h-14 border-b border-white/5 flex items-center justify-between px-4 sticky top-0 bg-[var(--theme-bg)]/80 backdrop-blur-md z-30">
                    <button onClick={() => setIsSidebarOpen(true)} className="p-2 text-slate-400 hover:text-[var(--theme-accent)]">
                        <Menu size={24} />
                    </button>
                    <div className="text-[var(--theme-accent)] font-bold text-sm">Minion 2.0</div>
                    <button onClick={resetMission} className="p-2 text-slate-400">
                        <RotateCcw size={18} />
                    </button>
                </header>

                {/* Conversation Canvas */}
                <div className="flex-1 overflow-y-auto p-4 sm:p-6 md:p-10 pt-6 sm:pt-8 md:pt-12 pb-24 scrollbar-none">
                    <div className="max-w-4xl mx-auto space-y-5">
                        {conversation.length === 0 && (
                            <div className="h-full flex flex-col items-center justify-center pt-24 opacity-10 grayscale space-y-4">
                                <Cpu size={80} strokeWidth={0.5} className="text-[var(--theme-accent)]" />
                                <div className="text-center">
                                    <p className="text-[10px] uppercase font-black tracking-[1.5em] text-[var(--theme-accent)]">Ready for Directive</p>
                                </div>
                            </div>
                        )}
                        {conversation.map((C, i) => {
                            const isUser = C.trim().toLowerCase().startsWith('user:');
                            // 🏛️ Neural Boundary: A message is a report if it contains the FINAL REPORT manifest and is NOT a user directive
                            const isReport = C.includes('FINAL REPORT:') && !isUser;
                            if (isReport) console.log("📑 [HUB] Mission Result Manifested in Feed:", i);
                            
                            return (
                                <div key={i} className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2 duration-500 ease-out`}>
                                    <div className={`message relative max-w-[94%] px-6 py-3.5 rounded-2xl transition-theme ${isUser ? 'bg-[var(--theme-accent)] text-black font-semibold shadow-[0_4px_20px_var(--theme-glow)]' : isReport ? 'bg-black/40 backdrop-blur-md border border-[var(--theme-accent)]/20 shadow-xl' : 'bg-white/[0.03] backdrop-blur-sm border border-white/[0.04] text-slate-200'}`}>
                                        <div className={`absolute top-[-14px] ${isUser ? 'right-6' : 'left-4 sm:left-6'} text-[8px] font-black uppercase tracking-[0.2em] ${isUser ? 'text-[var(--theme-accent)]' : 'text-slate-600'} opacity-70 flex items-center gap-4`}>
                                            {isUser ? 'Directive' : isReport ? 'Mission Result' : 'Minion Logic'}
                                            
                                            {isReport && (
                                                <div className="flex gap-2 -mt-1 ml-2">
                                                    <button 
                                                        onClick={() => {
                                                            const content = C.split('FINAL REPORT:')[1].trim();
                                                            copyToClipboard(content, i);
                                                        }}
                                                        className="hover:text-[var(--theme-accent)] transition-colors p-1"
                                                        title="Copy Markdown"
                                                    >
                                                        {copiedId === i ? <Check size={10} className="text-green-400" /> : <Copy size={10} />}
                                                    </button>
                                                    <button 
                                                        onClick={() => {
                                                            const content = C.split('FINAL REPORT:')[1].trim();
                                                            downloadReport(conversation[0].replace('user:', '').trim().substring(0, 30), content);
                                                        }}
                                                        className="hover:text-[var(--theme-accent)] transition-colors p-1"
                                                        title="Download .md"
                                                    >
                                                        <Download size={10} />
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                        <div className="text-[13px] sm:text-[14px] leading-relaxed font-normal whitespace-pre-wrap w-full overflow-hidden">
                                            {isReport ? (
                                                <div className="prose prose-invert max-w-none prose-sm sm:prose-base prose-headings:text-[var(--theme-accent)] prose-a:text-[var(--theme-accent)] prose-strong:text-white prose-p:text-gray-100 prose-li:text-gray-100 prose-td:text-gray-100 prose-th:text-[var(--theme-accent)] prose-table:border-collapse prose-th:border prose-th:border-white/20 prose-th:bg-[var(--theme-accent)]/10 prose-th:px-3 prose-th:py-2 prose-td:border prose-td:border-white/10 prose-td:px-3 prose-td:py-1.5 text-gray-100 overflow-x-auto">
                                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                        {C.split('FINAL REPORT:')[1].trim()}
                                                    </ReactMarkdown>
                                                </div>
                                            ) : (
                                                renderMessageContent(C)
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                        <div ref={chatEndRef} />
                    </div>
                </div>

                {/* Main Input Dock */}
                <div className="p-4 sm:p-6 md:p-8 bg-black border-t border-white/[0.05] shadow-[0_-20px_50px_rgba(0,0,0,1)] z-20">
                    <div className="max-w-5xl mx-auto flex flex-col sm:flex-row gap-3 sm:gap-5">
                         <div className="relative group flex-1">
                             <div className="absolute inset-x-0 -top-20 hidden sm:group-focus-within:flex flex-col items-center justify-center animate-in fade-in slide-in-from-bottom-2 duration-300">
                                <div className="bg-[var(--theme-accent)]/5 border border-[var(--theme-accent)]/20 rounded-full px-4 sm:px-6 py-1 flex sm:py-1.5 items-center gap-2 sm:gap-3">
                                    <div className="flex items-center gap-1.5"><Brain size={12} className="text-[var(--theme-accent)]" /> <span className="text-[9px] sm:text-[10px] font-bold text-slate-400">Model: {model}</span></div>
                                    <div className="w-[1px] h-3 bg-white/10"></div>
                                    <div className="flex items-center gap-1.5"><Zap size={12} className="text-yellow-400" /> <span className="text-[9px] sm:text-[10px] font-bold text-slate-400">Skill: {selectedSkill}</span></div>
                                </div>
                             </div>

                             <div className="relative">
                                <Search className="absolute left-4 sm:left-6 top-1/2 -translate-y-1/2 text-slate-700 group-focus-within:text-[var(--theme-accent)] transition-colors" size={20} />
                                <input 
                                    value={task}
                                    onChange={e => setTask(e.target.value)}
                                    onKeyPress={e => e.key === 'Enter' && startMission()}
                                    placeholder="SYNTHESIZE NEW MISSION..."
                                    className="w-full bg-white/[0.02] border border-[#ffffff1a] rounded-2xl sm:rounded-[2.5rem] pl-12 sm:pl-16 pr-6 sm:pr-8 py-3.5 sm:py-6 outline-none focus:border-[var(--theme-accent)]/50 transition-all text-sm sm:text-lg font-normal tracking-wide ring-0 focus:shadow-[0_0_30px_var(--theme-glow)] placeholder:text-slate-800 placeholder:font-black placeholder:tracking-[0.2em] placeholder:text-[9px]"
                                />
                             </div>
                         </div>
                         <button 
                            onClick={startMission}
                             className="bg-[var(--theme-accent)] text-black font-black px-6 sm:px-12 py-3.5 sm:py-6 rounded-2xl sm:rounded-[2.5rem] hover:scale-105 transition-all shadow-[0_10px_40px_var(--theme-glow)] active:scale-95 text-[11px] sm:text-[12px] uppercase tracking-widest flex items-center justify-center gap-2 sm:gap-3 shrink-0"
                         >
                            Deploy <ChevronRight size={18} />
                         </button>
                    </div>
                </div>
            </main>
        </div>
    );
};

export default App;
