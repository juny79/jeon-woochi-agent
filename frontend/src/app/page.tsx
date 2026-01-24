"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  Plus, 
  MessageSquare, 
  Settings, 
  History, 
  HelpCircle, 
  Menu, 
  Send,
  Sparkles,
  User,
  MoreVertical,
  Search
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import Image from 'next/image';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Session {
  id: number;
  title: string;
  created_at: string;
}

export default function Home() {
  const [mounted, setMounted] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [input, setInput] = useState("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      const response = await fetch("http://localhost:8000/sessions");
      const data = await response.json();
      setSessions(data);
    } catch (error) {
      console.error("Error fetching sessions:", error);
    }
  };

  const loadSession = async (id: number) => {
    setIsLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/sessions/${id}/messages`);
      const data = await response.json();
      setMessages(data);
      setCurrentSessionId(id);
      if (window.innerWidth < 768) setIsSidebarOpen(false);
    } catch (error) {
      console.error("Error loading session:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setCurrentSessionId(null);
    if (window.innerWidth < 768) setIsSidebarOpen(false);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (mounted) {
      scrollToBottom();
    }
  }, [messages, mounted]);

  if (!mounted) {
    return <div className="h-screen bg-[#131314]" />;
  }

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages(prev => [...prev, userMessage]);
    
    const currentInput = input;
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          message: currentInput, 
          strategy: "recursive",
          session_id: currentSessionId 
        }),
      });

      if (!response.ok) throw new Error("Network response was not ok");
      if (!response.body) throw new Error("No body in response");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      // 어시스턴트 메시지 자리 미리 확보
      setMessages(prev => [...prev, { role: "assistant", content: "" }]);
      setIsLoading(false); // 스트리밍이 시작되면 로딩 바는 끕니다.

      let accumulatedContent = "";
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        
        // 세션 ID 체크 (첫 줄에 있을 수 있음)
        if (chunk.startsWith("SESSION_ID:")) {
          const firstNewline = chunk.indexOf("\n");
          if (firstNewline !== -1) {
            const sid = chunk.substring(11, firstNewline);
            const contentPart = chunk.substring(firstNewline + 1);
            
            if (!currentSessionId) {
              setCurrentSessionId(parseInt(sid));
              fetchSessions();
            }
            
            if (contentPart) {
              accumulatedContent += contentPart;
              setMessages(prev => {
                const updated = [...prev];
                updated[updated.length - 1].content = accumulatedContent;
                return updated;
              });
            }
          }
        } else {
          accumulatedContent += chunk;
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1].content = accumulatedContent;
            return updated;
          });
        }
      }
    } catch (error) {
      console.error("Error fetching chat:", error);
      setIsLoading(false);
      setMessages(prev => [...prev, { role: "assistant", content: "죄송하오. 일시적인 오류가 발생했구려. 잠시 후 다시 시도해주시오." }]);
    }
  };

  return (
    <div className="flex h-screen bg-[#131314] text-[#e3e3e3] overflow-hidden font-sans" suppressHydrationWarning>
      {/* Sidebar */}
      <motion.aside 
        initial={false}
        animate={{ width: isSidebarOpen ? 280 : 0 }}
        className="bg-[#1e1f20] h-full overflow-hidden flex-shrink-0 relative border-r border-[#333]"
      >
        <div className="w-[280px] p-4 flex flex-col h-full">
          <button 
            className="flex items-center gap-3 bg-[#333537] hover:bg-[#3d3f42] py-2.5 px-4 rounded-full text-sm font-medium mb-8 transition-colors"
            onClick={handleNewChat}
          >
            <Plus size={18} />
            {isSidebarOpen && <span>새 채팅</span>}
          </button>

          <div className="flex-1 overflow-y-auto space-y-2 custom-scrollbar">
            <p className="text-xs font-semibold text-[#9aa0a6] uppercase tracking-wider px-2 mb-2">최근 항목</p>
            {sessions.length === 0 ? (
                <p className="text-sm text-[#9aa0a6] px-2 italic">대화 내역이 없습니다.</p>
            ) : (
                sessions.map((session) => (
                  <div 
                    key={session.id}
                    onClick={() => loadSession(session.id)}
                    className={`flex items-center gap-3 py-2 px-3 rounded-lg cursor-pointer transition-colors text-sm ${currentSessionId === session.id ? 'bg-[#333537] text-white' : 'text-[#c4c7c5] hover:bg-[#202122]'}`}
                  >
                    <MessageSquare size={16} className="flex-shrink-0" />
                    <span className="truncate flex-1">{session.title}</span>
                  </div>
                ))
            )}
          </div>

          <div className="mt-auto space-y-1">
            <NavItem icon={<History size={20} />} label="활동" />
            <NavItem icon={<Settings size={20} />} label="설정" />
            <NavItem icon={<HelpCircle size={20} />} label="도움말" />
          </div>
        </div>
      </motion.aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative h-full">
        {/* Header */}
        <header className="p-4 flex items-center justify-between z-10">
          <button 
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-2 hover:bg-[#1e1f20] rounded-full transition-colors"
          >
            <Menu size={20} />
          </button>
          <div className="flex items-center gap-2">
            <span className="text-xs md:text-sm font-medium px-3 py-1 bg-[#1e1f20] rounded-lg border border-[#333] text-[#9aa0a6]">Gemini 3 Pro (전우치 Ver)</span>
            <div className="w-8 h-8 rounded-full bg-[#3c4043] flex items-center justify-center text-[10px] font-bold text-white border border-[#444]">
              USER
            </div>
          </div>
        </header>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto px-4 md:px-0 scrollbar-hide">
          <div className="max-w-[820px] mx-auto py-8">
            {messages.length === 0 ? (
              <div className="mt-[8vh] text-center space-y-6 px-4">
                <motion.div 
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                  className="relative w-56 h-56 mx-auto mb-4"
                >
                  <div className="absolute inset-0 bg-blue-500/20 blur-[80px] rounded-full animate-pulse" />
                  <Image 
                    src="/images/jeon-woochi_b.png" 
                    alt="Jeon Woo-chi" 
                    fill 
                    className="object-contain drop-shadow-[0_0_20px_rgba(66,133,244,0.4)]"
                    priority
                  />
                </motion.div>
                
                <h1 className="text-4xl md:text-5xl font-medium tracking-tight bg-gradient-to-r from-[#4285f4] via-[#9b72cb] to-[#d96570] bg-clip-text text-transparent pb-1">
                  ✨ 무엇을 도와드릴까요?
                </h1>
                <p className="text-2xl md:text-3xl font-medium text-[#444746]">
                  전우치가 도력으로 답해드리겠소.
                </p>
                
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-12 max-w-[800px] mx-auto">
                    <ActionButton icon="🧘" label="명상 시작" desc="가이드 명상을 시작합니다." />
                    <ActionButton icon="📝" label="고민 상담" desc="지친 마음에 위로를 건넵니다." />
                    <ActionButton icon="📖" label="지혜 찾기" desc="고전의 가르침을 전해드립니다." />
                    <ActionButton icon="✨" label="무드 명상" desc="기분에 맞춰 추천합니다." />
                </div>
              </div>
            ) : (
              <div className="space-y-8 pb-32">
                <AnimatePresence>
                {messages.map((msg, i) => (
                  <motion.div 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    key={i} 
                    className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : ''}`}
                  >
                    {msg.role === 'assistant' && (
                      <div className="w-10 h-10 rounded-full bg-[#1e1f20] flex items-center justify-center flex-shrink-0 border border-[#333] overflow-hidden">
                        <Image 
                          src="/images/jeon-woochi_b.png" 
                          alt="Woochi" 
                          width={40} 
                          height={40} 
                          className="object-cover scale-150 relative top-1"
                        />
                      </div>
                    )}
                    <div className={`max-w-[85%] ${msg.role === 'user' ? 'bg-[#2b2c2f] rounded-2xl p-4 shadow-sm' : 'pt-1'}`}>
                      <div className={`text-[1.05rem] leading-relaxed ${msg.role === 'assistant' ? 'text-[#e3e3e3]' : 'text-white'}`}>
                        {msg.role === 'assistant' ? (
                          <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                            components={{
                              h1: ({node, ...props}) => <h1 className="text-2xl font-bold mt-6 mb-4 text-white border-b border-[#333] pb-2" {...props} />,
                              h2: ({node, ...props}) => <h2 className="text-xl font-bold mt-5 mb-3 text-[#d1d1d1]" {...props} />,
                              h3: ({node, ...props}) => <h3 className="text-lg font-bold mt-4 mb-2 text-[#c4c7c5]" {...props} />,
                              ul: ({node, ...props}) => <ul className="list-disc ml-6 mb-4 space-y-2" {...props} />,
                              ol: ({node, ...props}) => <ol className="list-decimal ml-6 mb-4 space-y-2" {...props} />,
                              li: ({node, ...props}) => <li className="pl-1" {...props} />,
                              strong: ({node, ...props}) => <strong className="font-bold text-[#8ab4f8] bg-[#8ab4f8]/10 px-1 rounded" {...props} />,
                              blockquote: ({node, ...props}) => (
                                <blockquote className="border-l-4 border-[#4285f4] pl-4 py-2 my-4 bg-[#1e1f20] rounded-r-lg italic text-[#9aa0a6]" {...props} />
                              ),
                              p: ({node, ...props}) => <p className="mb-4 last:mb-0" {...props} />,
                              code: ({node, ...props}) => (
                                <code className="bg-[#2b2c2f] px-1.5 py-0.5 rounded text-sm font-mono text-[#d96570]" {...props} />
                              ),
                            }}
                          >
                            {msg.content}
                          </ReactMarkdown>
                        ) : (
                          <div className="whitespace-pre-wrap">{msg.content}</div>
                        )}
                      </div>
                    </div>
                    {msg.role === 'user' && (
                       <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-[#3c4043] to-[#1e1f20] flex items-center justify-center flex-shrink-0 text-[10px] font-bold text-white shadow-lg border border-[#333]">
                        USER
                      </div>
                    )}
                  </motion.div>
                ))}
                </AnimatePresence>
                {isLoading && (
                  <div className="flex gap-4">
                    <div className="w-10 h-10 rounded-full bg-[#1e1f20] flex items-center justify-center flex-shrink-0 border border-[#333] overflow-hidden">
                        <Image 
                          src="/images/jeon-woochi_b.png" 
                          alt="Woochi Thinking" 
                          width={40} 
                          height={40} 
                          className="object-cover scale-150 relative top-1 animate-bounce"
                        />
                    </div>
                    <div className="w-full">
                        <div className="h-1.5 w-full bg-[#1e1f20] rounded-full overflow-hidden mt-6">
                            <motion.div 
                                animate={{ x: ["-100%", "300%"] }}
                                transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                                className="w-1/3 h-full bg-gradient-to-r from-transparent via-[#8ab4f8] to-transparent"
                            />
                        </div>
                        <p className="text-xs text-[#9aa0a6] mt-2 animate-pulse">도력을 모으는 중...</p>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </div>

        {/* Input Area */}
        <div className="p-4 pb-8 flex justify-center bg-gradient-to-t from-[#131314] via-[#131314] to-transparent pt-10">
          <div className="max-w-[820px] w-full relative group px-2 md:px-0">
            <div className="bg-[#1e1f20] group-focus-within:bg-[#202124] rounded-[32px] border border-transparent focus-within:ring-1 focus-within:ring-[#4285f4]/30 transition-all shadow-xl overflow-hidden flex flex-col">
              <div className="flex items-center px-6 py-2">
                <textarea 
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="전우치에게 궁금한 것을 물어보세요..."
                  className="flex-1 bg-transparent py-4 outline-none resize-none text-[1.1rem] min-h-[56px] max-h-[200px]"
                  style={{ height: 'auto' }}
                  rows={1}
                />
              </div>
              <div className="flex items-center justify-between px-6 pb-4">
                <div className="flex gap-1 md:gap-2">
                    <IconButton icon={<Plus size={20} />} />
                    <IconButton icon={<MessageSquare size={20} />} />
                    <IconButton icon={<Search size={20} />} />
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-[#5f6368] hidden md:block">{input.length} 자</span>
                  <button 
                    onClick={handleSend}
                    disabled={!input.trim() || isLoading}
                    className={`p-2.5 rounded-full transition-all ${input.trim() ? 'bg-white text-black' : 'text-[#5f6368] bg-[#131314]'}`}
                  >
                    <Send size={20} strokeWidth={2.5} />
                  </button>
                </div>
              </div>
            </div>
            <p className="text-[11px] text-[#9aa0a6] text-center mt-3">
              전우치 에이전트는 환각이나 실수를 할 수 있습니다. 중요한 정보는 도력으로 직접 확인하십시오.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

function NavItem({ icon, label }: { icon: React.ReactNode, label: string }) {
  return (
    <div className="flex items-center gap-3 py-2.5 px-3 hover:bg-[#333537] rounded-lg cursor-pointer transition-colors text-sm font-medium text-[#c4c7c5]">
      {icon}
      <span>{label}</span>
    </div>
  );
}

function IconButton({ icon }: { icon: React.ReactNode }) {
  return (
    <button className="p-2.5 hover:bg-[#333] rounded-full text-[#9aa0a6] transition-colors">
      {icon}
    </button>
  );
}

function ActionButton({ icon, label, desc }: { icon: string, label: string, desc: string }) {
  return (
    <button className="flex flex-col items-start gap-2 p-4 bg-[#1e1f20] hover:bg-[#28292a] rounded-2xl border border-[#333] transition-all text-left group">
      <span className="text-xl bg-[#131314] w-10 h-10 flex items-center justify-center rounded-xl group-hover:scale-110 transition-transform">{icon}</span>
      <div className="mt-1">
        <p className="font-semibold text-sm group-hover:text-white transition-colors">{label}</p>
        <p className="text-[11px] text-[#9aa0a6] leading-tight mt-1">{desc}</p>
      </div>
    </button>
  );
}
