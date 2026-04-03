"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Plus,
  MessageSquare,
  Settings,
  History,
  HelpCircle,
  Menu,
  Send,
  Search,
  Trash2,
  Pencil,
  Check,
  X,
  MoreHorizontal,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import Image from "next/image";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// ─── 환경변수 기반 API 경로 ─────────────────────────────────────────────────
// next.config.ts 에서 /api/backend/* → 백엔드로 프록시됨.
// 브라우저에 백엔드 주소가 노출되지 않으며, 배포 시 .env.local 만 수정하면 됨.
const API = "/api/backend";

// ─── 타입 ──────────────────────────────────────────────────────────────────
interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Session {
  id: number;
  title: string;
  created_at: string;
}

// ─── ReactMarkdown 공통 컴포넌트 (중복 제거) ───────────────────────────────
const mdComponents: React.ComponentProps<typeof ReactMarkdown>["components"] = {
  h1: ({ ...props }) => (
    <h1
      className="text-[0.92rem] font-bold mt-5 mb-2 text-white border-b border-[#2d2e31] pb-1.5"
      {...props}
    />
  ),
  h2: ({ ...props }) => (
    <h2
      className="text-[0.88rem] font-bold mt-6 mb-1.5 text-white"
      {...props}
    />
  ),
  h3: ({ ...props }) => (
    <h3
      className="text-[0.84rem] font-semibold mt-3 mb-1.5 text-[#e3e3e3]"
      {...props}
    />
  ),
  h4: ({ ...props }) => (
    <h4 className="text-[0.82rem] font-semibold mt-2 mb-1 text-[#d0d0d0]" {...props} />
  ),
  p: ({ ...props }) => (
    <p className="mb-2.5 leading-[1.75] text-[#d0d0d0] text-[0.82rem] last:mb-0" {...props} />
  ),
  ul: ({ ...props }) => (
    <ul className="list-disc pl-5 space-y-1 my-2 text-[0.82rem] text-[#d0d0d0] marker:text-[#777]" {...props} />
  ),
  ol: ({ ...props }) => (
    <ol className="list-decimal pl-5 space-y-1 my-2 text-[0.82rem] text-[#d0d0d0]" {...props} />
  ),
  li: ({ ...props }) => (
    <li className="leading-[1.7] pl-0.5" {...props} />
  ),
  strong: ({ ...props }) => (
    <strong className="font-bold text-white" {...props} />
  ),
  em: ({ ...props }) => <em className="italic text-[#b0b0b0]" {...props} />,
  hr: () => <div className="my-2" />,
  blockquote: ({ ...props }) => (
    <blockquote
      className="border-l-2 border-[#555] pl-3 pr-2 py-1.5 my-3 text-[0.8rem] text-[#aaa] italic"
      {...props}
    />
  ),
  code: ({ ...props }) => (
    <code
      className="bg-[#252628] px-1 py-0.5 rounded text-[0.77rem] font-mono text-[#d0d0d0]"
      {...props}
    />
  ),
  pre: ({ ...props }) => (
    <pre
      className="bg-[#1c1d1f] p-3 rounded-xl overflow-x-auto my-2.5 border border-[#2d2e31] text-[0.77rem]"
      {...props}
    />
  ),
  table: ({ ...props }) => (
    <div className="overflow-x-auto my-3 rounded-lg border border-[#2d2e31]">
      <table className="border-collapse w-full text-[0.78rem]" {...props} />
    </div>
  ),
  thead: ({ ...props }) => <thead className="bg-[#212224] border-b border-[#2d2e31]" {...props} />,
  th: ({ ...props }) => (
    <th
      className="px-3 py-2 text-left font-semibold text-white text-[0.78rem]"
      {...props}
    />
  ),
  td: ({ ...props }) => (
    <td className="border-t border-[#252628] px-3 py-2 text-[#d0d0d0]" {...props} />
  ),
  a: ({ ...props }) => (
    <a className="underline text-[#d0d0d0] hover:text-white transition-colors" target="_blank" rel="noopener noreferrer" {...props} />
  ),
};

// ─── 메인 컴포넌트 ──────────────────────────────────────────────────────────
export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [isClient, setIsClient] = useState(false);
  // 세션 관리 상태
  const [menuOpenId, setMenuOpenId] = useState<number | null>(null);
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setIsClient(true);
    fetchSessions();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // textarea 자동 높이
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`;
    }
  }, [input]);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API}/sessions`);
      if (!res.ok) return;
      const data: Session[] = await res.json();
      setSessions(data);
    } catch {
      // 백엔드 미실행 시 무시
    }
  }, []);

  const loadSession = async (id: number) => {
    setIsLoading(true);
    setMenuOpenId(null);
    try {
      const res = await fetch(`${API}/sessions/${id}/messages`);
      if (!res.ok) throw new Error("load failed");
      const data: Message[] = await res.json();
      setMessages(data);
      setCurrentSessionId(id);
      if (isClient && window.innerWidth < 768) setIsSidebarOpen(false);
    } catch {
      alert("세션을 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setCurrentSessionId(null);
    setMenuOpenId(null);
    if (isClient && window.innerWidth < 768) setIsSidebarOpen(false);
  };

  const handleRenameStart = (s: Session) => {
    setRenamingId(s.id);
    setRenameValue(s.title);
    setMenuOpenId(null);
  };

  const handleRenameSubmit = async (id: number) => {
    const title = renameValue.trim();
    if (!title) return;
    try {
      const res = await fetch(`${API}/sessions/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title }),
      });
      if (!res.ok) throw new Error("rename failed");
      setSessions((prev) =>
        prev.map((s) => (s.id === id ? { ...s, title } : s))
      );
    } catch {
      alert("이름 변경에 실패했습니다.");
    } finally {
      setRenamingId(null);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("이 대화를 삭제하시겠습니까?")) return;
    try {
      const res = await fetch(`${API}/sessions/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("delete failed");
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (currentSessionId === id) {
        setMessages([]);
        setCurrentSessionId(null);
      }
    } catch {
      alert("삭제에 실패했습니다.");
    } finally {
      setMenuOpenId(null);
    }
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch(`${API}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          strategy: "recursive",
          session_id: currentSessionId,
        }),
      });

      if (!res.ok || !res.body) throw new Error("stream failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
      setIsLoading(false);

      let accumulated = "";
      let sidExtracted = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });

        if (!sidExtracted && chunk.includes("SESSION_ID:")) {
          const sidMatch = chunk.match(/SESSION_ID:(\d+)\n?/);
          if (sidMatch) {
            const sid = parseInt(sidMatch[1]);
            if (!isNaN(sid) && !currentSessionId) {
              setCurrentSessionId(sid);
              fetchSessions();
              sidExtracted = true;
            }
            // SESSION_ID 줄만 제거하고 나머지 내용은 줄바꿈 그대로 유지
            accumulated += chunk.replace(/SESSION_ID:\d+\n?/, "");
          } else {
            accumulated += chunk;
          }
        } else {
          accumulated += chunk;
        }

        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            content: accumulated,
          };
          return updated;
        });
      }
    } catch {
      setIsLoading(false);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "죄송하오. 일시적인 오류가 발생했구려. 잠시 후 다시 시도해주시오.",
        },
      ]);
    }
  };

  const handleActionChip = (prompt: string) => {
    setInput(prompt);
    textareaRef.current?.focus();
  };



  return (
    <div
      className="flex h-screen bg-[#131314] text-[#e3e3e3] overflow-hidden font-sans"
    >
      {/* ── 사이드바 ───────────────────────────────────────────────── */}
      <motion.aside
        initial={false}
        animate={{ width: isSidebarOpen ? 280 : 0 }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
        className="bg-[#1e1f20] h-full overflow-hidden flex-shrink-0 border-r border-[#2a2b2e]"
      >
        <div className="w-[280px] flex flex-col h-full">
          {/* 상단 헤더 */}
          <div className="flex items-center justify-between px-4 py-4 flex-shrink-0">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsSidebarOpen(false)}
                className="p-1.5 hover:bg-[#333537] rounded-full transition-colors"
                title="사이드바 닫기"
              >
                <Menu size={18} />
              </button>
              <span className="text-sm font-semibold text-[#e3e3e3]">전우치 명상소</span>
            </div>
            <button
              onClick={() => setIsSidebarOpen(false)}
              className="p-1.5 hover:bg-[#333537] rounded-full transition-colors"
              title="검색"
            >
              <Search size={16} className="text-[#9aa0a6]" />
            </button>
          </div>

          {/* 새 채팅 버튼 */}
          <div className="px-3 pb-3 flex-shrink-0">
            <button
              onClick={handleNewChat}
              className="flex items-center gap-2.5 w-full px-4 py-2 rounded-full border border-[#444] hover:bg-[#333537] text-sm font-medium transition-colors"
            >
              <Plus size={16} />
              <span>새 채팅</span>
            </button>
          </div>

          {/* 세션 목록 */}
          <div className="flex-1 overflow-y-auto px-2 pb-2">
            {sessions.length > 0 && (
              <p className="text-[11px] font-semibold text-[#9aa0a6] uppercase tracking-wider px-2 py-2">
                최근 항목
              </p>
            )}
            {sessions.length === 0 ? (
              <p className="text-sm text-[#9aa0a6] px-3 py-2 italic">
                대화 내역이 없습니다.
              </p>
            ) : (
              sessions.map((s) => (
                <div key={s.id} className="relative group">
                  {renamingId === s.id ? (
                    /* 이름 변경 입력 */
                    <div className="flex items-center gap-1 px-2 py-1">
                      <input
                        autoFocus
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleRenameSubmit(s.id);
                          if (e.key === "Escape") setRenamingId(null);
                        }}
                        className="flex-1 bg-[#2b2c2f] text-sm rounded px-2 py-1 outline-none border border-[#4285f4]"
                      />
                      <button
                        onClick={() => handleRenameSubmit(s.id)}
                        className="p-1 hover:text-[#4285f4] transition-colors"
                      >
                        <Check size={14} />
                      </button>
                      <button
                        onClick={() => setRenamingId(null)}
                        className="p-1 hover:text-[#d96570] transition-colors"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ) : (
                    /* 일반 세션 행 */
                    <div
                      onClick={() => loadSession(s.id)}
                      className={`flex items-center gap-2 py-2 px-3 rounded-lg cursor-pointer transition-colors text-sm ${
                        currentSessionId === s.id
                          ? "bg-[#333537] text-white"
                          : "text-[#c4c7c5] hover:bg-[#28292a]"
                      }`}
                    >
                      <MessageSquare size={15} className="flex-shrink-0 text-[#9aa0a6]" />
                      <span className="truncate flex-1">{s.title}</span>
                      {/* 옵션 버튼 — hover 시 표시 */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setMenuOpenId(menuOpenId === s.id ? null : s.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-[#444] transition-all flex-shrink-0"
                      >
                        <MoreHorizontal size={14} />
                      </button>
                    </div>
                  )}

                  {/* 컨텍스트 메뉴 */}
                  <AnimatePresence>
                    {menuOpenId === s.id && (
                      <motion.div
                        initial={{ opacity: 0, y: -4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -4 }}
                        transition={{ duration: 0.12 }}
                        className="absolute right-2 top-8 z-50 bg-[#2b2c2f] border border-[#444] rounded-lg shadow-xl py-1 w-36"
                      >
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRenameStart(s);
                          }}
                          className="flex items-center gap-2 w-full px-3 py-2 text-sm hover:bg-[#333537] transition-colors"
                        >
                          <Pencil size={13} />
                          이름 변경
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(s.id);
                          }}
                          className="flex items-center gap-2 w-full px-3 py-2 text-sm text-[#d96570] hover:bg-[#333537] transition-colors"
                        >
                          <Trash2 size={13} />
                          삭제
                        </button>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              ))
            )}
          </div>

          {/* 하단 네비게이션 */}
          <div className="border-t border-[#2a2b2e] px-2 py-2 flex-shrink-0 space-y-0.5">
            <NavItem icon={<History size={18} />} label="활동" />
            <NavItem icon={<Settings size={18} />} label="설정" />
            <NavItem icon={<HelpCircle size={18} />} label="도움말" />
          </div>
        </div>
      </motion.aside>

      {/* ── 메인 영역 ──────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col relative h-full min-w-0">
        {/* 헤더 */}
        <header className="px-4 py-3 flex items-center justify-between flex-shrink-0">
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-2 hover:bg-[#1e1f20] rounded-full transition-colors"
            title="사이드바 토글"
          >
            <Menu size={20} />
          </button>
          <div className="flex items-center gap-2">
            <span className="text-xs md:text-sm font-medium px-3 py-1 bg-[#1e1f20] rounded-lg border border-[#333] text-[#9aa0a6]">
              전우치 v1.0
            </span>
            <div className="w-8 h-8 rounded-full bg-[#3c4043] flex items-center justify-center text-[10px] font-bold text-white border border-[#444]">
              YOU
            </div>
          </div>
        </header>

        {/* 채팅 영역 */}
        <div
          className="flex-1 overflow-y-auto px-4 md:px-0 scrollbar-hide"
          onClick={() => setMenuOpenId(null)}
        >
          <div className="max-w-[820px] mx-auto py-6">
            {messages.length === 0 ? (
              /* 웰컴 화면 */
              <div className="mt-[8vh] text-center space-y-6 px-4">
                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                  className="relative w-48 h-48 mx-auto mb-4"
                >
                  <div className="absolute inset-0 bg-blue-500/20 blur-[80px] rounded-full animate-pulse" />
                  <Image
                    src="/images/jeon-woochi_b.png"
                    alt="전우치"
                    fill
                    className="object-contain drop-shadow-[0_0_20px_rgba(66,133,244,0.4)]"
                    priority
                  />
                </motion.div>

                <h1 className="text-4xl md:text-5xl font-medium tracking-tight bg-gradient-to-r from-[#4285f4] via-[#9b72cb] to-[#d96570] bg-clip-text text-transparent pb-1">
                  ✨ 무엇을 도와드릴까요?
                </h1>
                <p className="text-xl md:text-2xl font-medium text-[#444746]">
                  전우치가 도력으로 답해드리겠소.
                </p>

                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-10 max-w-[800px] mx-auto">
                  <ActionChip
                    icon="🧘"
                    label="명상 시작"
                    desc="가이드 명상을 시작합니다."
                    onClick={() => handleActionChip("명상을 시작하고 싶습니다. 가이드해 주세요.")}
                  />
                  <ActionChip
                    icon="📝"
                    label="고민 상담"
                    desc="지친 마음에 위로를 건넵니다."
                    onClick={() => handleActionChip("요즘 마음이 지쳐 있습니다. 위로의 말씀을 해주세요.")}
                  />
                  <ActionChip
                    icon="📖"
                    label="지혜 찾기"
                    desc="고전의 가르침을 전해드립니다."
                    onClick={() => handleActionChip("삶의 지혜가 담긴 고전의 가르침을 알려주세요.")}
                  />
                  <ActionChip
                    icon="✨"
                    label="무드 명상"
                    desc="기분에 맞춰 추천합니다."
                    onClick={() => handleActionChip("지금 제 기분에 맞는 명상을 추천해 주세요.")}
                  />
                </div>
              </div>
            ) : (
              /* 메시지 목록 */
              <div className="space-y-3 pb-32">
                <AnimatePresence initial={false}>
                  {messages.map((msg, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.18 }}
                      className={`flex gap-2.5 ${msg.role === "user" ? "justify-end" : "items-start"}`}
                    >
                      {msg.role === "assistant" && (
                        <div className="w-7 h-7 rounded-full bg-[#1e1f20] flex items-center justify-center flex-shrink-0 border border-[#333] overflow-hidden mt-0.5">
                          <Image
                            src="/images/jeon-woochi_b.png"
                            alt="전우치"
                            width={28}
                            height={28}
                            className="object-cover scale-150 relative top-0.5"
                          />
                        </div>
                      )}

                      <div
                        className={`max-w-[82%] ${
                          msg.role === "user"
                            ? "bg-[#2b2c2f] rounded-2xl px-3.5 py-2.5 text-[0.82rem] text-white shadow-sm"
                            : "bg-[#1a1b1c] border border-[#252628] rounded-2xl px-4 py-3 text-[#d8dbd9] shadow-sm"
                        }`}
                      >
                        {msg.role === "assistant" ? (
                          <div className="md-body">
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              components={mdComponents}
                            >
                              {msg.content}
                            </ReactMarkdown>
                          </div>
                        ) : (
                          <div className="whitespace-pre-wrap leading-[1.65]">{msg.content}</div>
                        )}
                      </div>

                      {msg.role === "user" && (
                        <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-[#3c4043] to-[#1e1f20] flex items-center justify-center flex-shrink-0 text-[8px] font-bold text-white border border-[#444] mt-0.5">
                          YOU
                        </div>
                      )}
                    </motion.div>
                  ))}
                </AnimatePresence>

                {/* 로딩 인디케이터 */}
                {isLoading && (
                  <div className="flex gap-3">
                    <div className="w-9 h-9 rounded-full bg-[#1e1f20] flex items-center justify-center flex-shrink-0 border border-[#333] overflow-hidden">
                      <Image
                        src="/images/jeon-woochi_b.png"
                        alt="응답 중"
                        width={36}
                        height={36}
                        className="object-cover scale-150 relative top-1 animate-bounce"
                      />
                    </div>
                    <div className="flex-1 pt-3">
                      <div className="h-1 w-full bg-[#2b2c2f] rounded-full overflow-hidden">
                        <motion.div
                          animate={{ x: ["-100%", "300%"] }}
                          transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                          className="w-1/3 h-full bg-gradient-to-r from-transparent via-[#8ab4f8] to-transparent"
                        />
                      </div>
                      <p className="text-xs text-[#9aa0a6] mt-2 animate-pulse">
                        도력을 모으는 중...
                      </p>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </div>

        {/* 입력 영역 */}
        <div className="px-4 pb-6 flex justify-center bg-gradient-to-t from-[#131314] via-[#131314] to-transparent pt-8 flex-shrink-0">
          <div className="max-w-[820px] w-full px-2 md:px-0">
            <div className="bg-[#1e1f20] rounded-[28px] border border-transparent focus-within:border-[#4285f4]/40 transition-all shadow-xl flex flex-col">
              <div className="flex items-end px-5 pt-3 pb-1">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="전우치에게 궁금한 것을 물어보세요..."
                  className="flex-1 bg-transparent outline-none resize-none text-[1rem] min-h-[48px] max-h-[200px] py-2 leading-relaxed"
                  rows={1}
                />
              </div>
              <div className="flex items-center justify-between px-5 pb-3">
                <div className="flex gap-1">
                  <IconBtn title="첨부">
                    <Plus size={18} />
                  </IconBtn>
                  <IconBtn title="채팅">
                    <MessageSquare size={18} />
                  </IconBtn>
                  <IconBtn title="검색">
                    <Search size={18} />
                  </IconBtn>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[#5f6368] hidden md:block">
                    {input.length}자
                  </span>
                  <button
                    onClick={handleSend}
                    disabled={!input.trim() || isLoading}
                    className={`p-2 rounded-full transition-all ${
                      input.trim() && !isLoading
                        ? "bg-white text-black hover:bg-[#e8eaed]"
                        : "bg-[#2b2c2f] text-[#5f6368] cursor-not-allowed"
                    }`}
                    title="전송 (Enter)"
                  >
                    <Send size={18} strokeWidth={2.5} />
                  </button>
                </div>
              </div>
            </div>
            <p className="text-[11px] text-[#5f6368] text-center mt-2">
              전우치 에이전트는 실수할 수 있습니다. 중요한 정보는 직접 확인하세요.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

// ─── 하위 컴포넌트 ──────────────────────────────────────────────────────────
function NavItem({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <button className="flex items-center gap-3 w-full py-2 px-3 hover:bg-[#28292a] rounded-lg transition-colors text-sm font-medium text-[#c4c7c5]">
      {icon}
      <span>{label}</span>
    </button>
  );
}

function IconBtn({
  icon,
  title,
  children,
}: {
  icon?: React.ReactNode;
  title?: string;
  children?: React.ReactNode;
}) {
  return (
    <button
      title={title}
      className="p-2 hover:bg-[#333] rounded-full text-[#9aa0a6] transition-colors"
    >
      {icon ?? children}
    </button>
  );
}

function ActionChip({
  icon,
  label,
  desc,
  onClick,
}: {
  icon: string;
  label: string;
  desc: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-start gap-2 p-4 bg-[#1e1f20] hover:bg-[#28292a] rounded-2xl border border-[#333] hover:border-[#444] transition-all text-left group"
    >
      <span className="text-xl bg-[#131314] w-9 h-9 flex items-center justify-center rounded-xl group-hover:scale-110 transition-transform">
        {icon}
      </span>
      <div>
        <p className="font-semibold text-sm group-hover:text-white transition-colors">
          {label}
        </p>
        <p className="text-[11px] text-[#9aa0a6] leading-tight mt-0.5">{desc}</p>
      </div>
    </button>
  );
}
