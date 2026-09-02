"use client";
import React, { useState, useRef, useEffect } from 'react';
import { fetchApi } from '@/lib/api';

const ROBOT_MESSAGES = [
  "أهلاً بك! 👋",
  "هل يمكنني مساعدتك؟",
  "هل تود الاستفسار عن شيء؟",
  "أنا الصيدلي الذكي، في خدمتك 🤖",
  "اسألني عن أي دواء...",
  "هل تبحث عن بدائل أرخص للأدوية؟",
  "لا تتردد في سؤالي عن الجرعات!"
];

// 3D Medical AI Robot Doctor Avatar (Asset Replacement)
const RobotAvatar = ({ isTalking, isMoving }: { isTalking: boolean; isMoving?: boolean }) => {
  return (
    <div className={`relative w-full h-full flex items-center justify-center transition-transform duration-300 ${isMoving ? 'scale-105' : ''}`}>
      {/* Dynamic Aura Glow */}
      <div 
        className="absolute inset-0 rounded-full opacity-60 mix-blend-screen"
        style={{
          background: 'radial-gradient(circle, rgba(16, 185, 129, 0.4) 0%, transparent 70%)',
          animation: 'pulse-glow 3s ease-in-out infinite',
        }}
      />

      {/* Floating Pharmacy Elements Animation (Prescription -> Medicine) */}
      <div className="absolute inset-0 pointer-events-none z-30 overflow-visible flex items-center justify-center">
        {/* Prescription Icon */}
        <div className="absolute text-3xl drop-shadow-xl animate-float-prescription opacity-0">
          📝
        </div>
        {/* Medicine Pill Icon */}
        <div className="absolute text-3xl drop-shadow-xl animate-float-medicine opacity-0">
          💊
        </div>
      </div>

      {/* The 3D Medical Robot Image */}
      <img 
        src="/selected-robot.jpg" 
        alt="AI Medical Doctor Robot" 
        draggable="false"
        className="w-full h-full object-cover rounded-full shadow-lg z-10 pointer-events-none"
        style={{
          animation: isTalking ? 'breathing 1.5s ease-in-out infinite' : 'floating 3.5s ease-in-out infinite',
          transformOrigin: 'center bottom'
        }}
      />
      <style>{`
        @keyframes floating {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-10px) rotate(2deg); }
        }
        @keyframes breathing {
          0%, 100% { transform: scale(1) translateY(0px); }
          50% { transform: scale(1.08) translateY(-4px); }
        }
        @keyframes pulse-glow {
          0%, 100% { transform: scale(1); opacity: 0.4; }
          50% { transform: scale(1.3); opacity: 0.8; }
        }
        @keyframes float-prescription {
          0% { transform: translate(0px, 10px) scale(0.5); opacity: 0; }
          15% { transform: translate(-45px, -15px) scale(1.3); opacity: 1; }
          30% { transform: translate(-60px, -60px) scale(0.8); opacity: 0; }
          100% { transform: translate(-60px, -60px) scale(0.8); opacity: 0; }
        }
        @keyframes float-medicine {
          0%, 40% { transform: translate(0px, 10px) scale(0.5); opacity: 0; }
          55% { transform: translate(45px, -15px) scale(1.3); opacity: 1; }
          70% { transform: translate(60px, -60px) scale(0.8); opacity: 0; }
          100% { transform: translate(60px, -60px) scale(0.8); opacity: 0; }
        }
        .animate-float-prescription {
          animation: float-prescription 5s ease-out infinite;
        }
        .animate-float-medicine {
          animation: float-medicine 5s ease-out infinite;
        }
      `}</style>
    </div>
  );
};

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function FloatingChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: "أهلاً بك! أنا الصيدلي الذكي الخاص بك. كيف يمكنني مساعدتك اليوم؟" }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Position & Dragging State for Chat Window (Step 1837)
  const [windowPos, setWindowPos] = useState({ x: 0, y: 0 });
  const [isDraggingWindow, setIsDraggingWindow] = useState(false);
  const dragWindowStart = useRef({ x: 0, y: 0 });

  // Floating Button Dragging State (Step 2788 / 2827)
  const [btnPos, setBtnPos] = useState({ x: 0, y: 0 });
  const [isDraggingBtn, setIsDraggingBtn] = useState(false);
  const dragBtnStart = useRef({ x: 0, y: 0 });
  const btnMoved = useRef(false);

  // Rotating Speech Bubble State (Step 2173)
  const [messageIndex, setMessageIndex] = useState(0);
  const [showSpeechBubble, setShowSpeechBubble] = useState(false);
  const [isTalking, setIsTalking] = useState(false);
  const [typedMessage, setTypedMessage] = useState("");

  useEffect(() => {
    if (isOpen) {
      setShowSpeechBubble(false);
      return;
    }

    const interval = setInterval(() => {
      setShowSpeechBubble(true);
      setIsTalking(true);

      setTimeout(() => {
        setShowSpeechBubble(false);
        setMessageIndex((prev) => (prev + 1) % ROBOT_MESSAGES.length);
        setTimeout(() => setIsTalking(false), 1500);
      }, 6000);
    }, 10000);

    return () => clearInterval(interval);
  }, [isOpen]);

  // Typewriter effect for speech bubble
  useEffect(() => {
    if (!showSpeechBubble) {
      setTypedMessage("");
      return;
    }
    const currentMsg = ROBOT_MESSAGES[messageIndex];
    let i = 0;
    setTypedMessage("");
    const typeInterval = setInterval(() => {
      if (i < currentMsg.length) {
        setTypedMessage(currentMsg.slice(0, i + 1));
        i++;
      } else {
        clearInterval(typeInterval);
      }
    }, 45);
    return () => clearInterval(typeInterval);
  }, [showSpeechBubble, messageIndex]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Window Drag Handlers (Step 1837)
  const handleWindowPointerDown = (e: React.PointerEvent) => {
    if (isExpanded) return;
    setIsDraggingWindow(true);
    dragWindowStart.current = { x: e.clientX - windowPos.x, y: e.clientY - windowPos.y };
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handleWindowPointerMove = (e: React.PointerEvent) => {
    if (!isDraggingWindow) return;
    setWindowPos({
      x: e.clientX - dragWindowStart.current.x,
      y: e.clientY - dragWindowStart.current.y
    });
  };

  const handleWindowPointerUp = (e: React.PointerEvent) => {
    setIsDraggingWindow(false);
    e.currentTarget.releasePointerCapture(e.pointerId);
  };

  // Button Drag Handlers (Step 2788 / 2827)
  const handleBtnPointerDown = (e: React.PointerEvent) => {
    setIsDraggingBtn(true);
    btnMoved.current = false;
    dragBtnStart.current = { x: e.clientX - btnPos.x, y: e.clientY - btnPos.y };
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handleBtnPointerMove = (e: React.PointerEvent) => {
    if (!isDraggingBtn) return;
    const newX = e.clientX - dragBtnStart.current.x;
    const newY = e.clientY - dragBtnStart.current.y;
    if (Math.abs(newX - btnPos.x) > 3 || Math.abs(newY - btnPos.y) > 3) {
      btnMoved.current = true;
    }
    setBtnPos({ x: newX, y: newY });
  };

  const handleBtnPointerUp = (e: React.PointerEvent) => {
    setIsDraggingBtn(false);
    e.currentTarget.releasePointerCapture(e.pointerId);
    if (!btnMoved.current) {
      setIsOpen(true);
      setWindowPos({ x: 0, y: 0 });
    }
  };

  // Send Message with History (Steps 1376, 1503)
  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetchApi<{ reply?: string; response?: string }>('/api/v1/ai/chat', {
        method: 'POST',
        body: JSON.stringify({ message: userMessage, history: messages })
      });
      const botReply = response.reply || response.response || "عذراً، لم أتمكن من معالجة ذلك حالياً.";
      setMessages(prev => [...prev, { role: 'assistant', content: botReply }]);
    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'عذراً، حدث خطأ أثناء الاتصال بالخادم. حاول مرة أخرى.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Clear Chat (Step 1506)
  const handleClearChat = () => {
    setMessages([
      { role: 'assistant', content: "أهلاً بك! تم مسح المحادثة. كيف يمكنني مساعدتك؟" }
    ]);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 font-sans" dir="rtl">
      {/* Chat Window */}
      {isOpen && (
        <div 
          style={{ 
            transform: isExpanded ? 'translate(0, 0)' : `translate(${windowPos.x}px, ${windowPos.y}px)`,
            transition: isDraggingWindow ? 'none' : 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
          }}
          className={`
            ${isExpanded 
              ? 'fixed inset-4 sm:inset-10 w-auto h-auto z-[60]' 
              : 'absolute bottom-20 right-0 w-[350px] sm:w-[400px] h-[550px]'} 
            bg-surface-container-lowest rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.3)] border border-outline-variant flex flex-col overflow-hidden
          `}
        >
          {/* Header with Draggable Handle (Step 1837) */}
          <div 
            onPointerDown={!isExpanded ? handleWindowPointerDown : undefined}
            onPointerMove={!isExpanded ? handleWindowPointerMove : undefined}
            onPointerUp={!isExpanded ? handleWindowPointerUp : undefined}
            onPointerCancel={!isExpanded ? handleWindowPointerUp : undefined}
            className={`bg-primary text-on-primary px-4 py-3 flex justify-between items-center select-none ${!isExpanded ? 'cursor-grab active:cursor-grabbing touch-none' : ''}`}
            dir="rtl"
            title={!isExpanded ? "اسحب النافذة للتحريك في أي مكان" : ""}
          >
            <div className="flex items-center gap-3 pointer-events-none">
              <div className="w-10 h-10 rounded-full bg-white/20 p-1 flex items-center justify-center shadow-inner border border-white/30">
                 <RobotAvatar isTalking={isLoading} />
              </div>
              <div>
                <h3 className="font-bold m-0 text-[16px] leading-tight text-white">المساعد الصيدلي الذكي</h3>
                <span className="text-[11px] text-white/90 flex items-center gap-1 mt-0.5">
                  <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse shadow-[0_0_6px_rgba(74,222,128,0.8)]"></span> متصل الآن
                </span>
              </div>
            </div>
            
            {/* Header Controls (Steps 1506, 1602) */}
            <div className="flex items-center gap-1" dir="ltr" onPointerDown={(e) => e.stopPropagation()}>
              {/* Fullscreen Toggle (Step 1602) */}
              <button 
                onPointerDown={(e) => { 
                  e.stopPropagation(); 
                  setIsExpanded(!isExpanded); 
                  setWindowPos({x:0, y:0}); 
                }}
                className="hover:bg-white/20 text-white p-2 rounded-full transition-colors flex items-center justify-center cursor-pointer"
                title={isExpanded ? "تصغير" : "تكبير بملء الشاشة"}
              >
                <span className="material-symbols-outlined text-[18px]">
                  {isExpanded ? 'fullscreen_exit' : 'fullscreen'}
                </span>
              </button>
              
              {/* Clear Chat (Step 1506) */}
              <button 
                onPointerDown={(e) => { 
                  e.stopPropagation(); 
                  handleClearChat();
                }}
                className="hover:bg-white/20 text-white p-2 rounded-full transition-colors flex items-center justify-center cursor-pointer"
                title="مسح المحادثة"
              >
                <span className="material-symbols-outlined text-[18px]">delete_sweep</span>
              </button>
              
              {/* Close Button */}
              <button 
                onPointerDown={(e) => { 
                  e.stopPropagation(); 
                  setIsOpen(false); 
                  setIsExpanded(false); 
                }}
                className="bg-red-500 hover:bg-red-600 text-white p-2 rounded-full transition-colors flex items-center justify-center cursor-pointer ml-2 shadow-sm"
                title="إغلاق"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>
          </div>

          {/* Warning Banner */}
          <div className="bg-red-500 text-white p-2 text-[11px] text-center shadow-sm flex items-center justify-center gap-2 font-medium tracking-wide">
            <span className="material-symbols-outlined text-[14px]">info</span>
            تنبيه: هذا المساعد يوفر معلومات إرشادية فقط ولا يغني عن استشارة الطبيب.
          </div>

          {/* Chat Messages Area (Steps 1376, 1407, 1503) */}
          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3 bg-surface/50" dir="rtl">
            {messages.map((msg, idx) => (
              <div 
                key={idx} 
                className={`max-w-[85%] p-3.5 rounded-2xl ${
                  msg.role === 'user' 
                    ? 'chat-user-bubble bg-primary text-white self-start rounded-tr-sm shadow-md' 
                    : 'chat-bot-bubble bg-surface-container-low text-on-surface self-end rounded-tl-sm shadow-sm border border-outline-variant'
                }`}
              >
                <p className="text-[14px] leading-relaxed whitespace-pre-wrap m-0">{msg.content}</p>
              </div>
            ))}
            
            {isLoading && (
              <div className="bg-surface-container-low text-on-surface self-end rounded-2xl rounded-tl-sm p-4 shadow-sm w-16 border border-outline-variant flex items-center justify-center h-[46px]">
                <div className="flex gap-1.5 justify-center">
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-3.5 bg-surface border-t border-outline-variant">
            <div className="flex gap-2 items-center bg-surface-container-lowest rounded-full px-4 py-2 border-2 border-outline-variant focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20 transition-all shadow-sm">
              <input 
                type="text" 
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                placeholder="اكتب استفسارك الطبي أو الدوائي هنا..."
                className="flex-1 bg-transparent border-none outline-none text-on-surface text-[14px] placeholder:text-on-surface-variant h-8"
                dir="rtl"
              />
              <button 
                onClick={handleSend}
                disabled={!input.trim() || isLoading}
                className="bg-primary text-on-primary disabled:opacity-40 transition-all w-9 h-9 flex items-center justify-center rounded-full hover:bg-primary/90 hover:scale-105 active:scale-95 shadow-sm cursor-pointer"
                title="إرسال"
              >
                <span className="material-symbols-outlined text-[18px]">send</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Draggable Floating Button & Speech Bubble (Steps 1913, 2173, 2788, 2827) */}
      {!isOpen && (
        <div 
          style={{ 
            transform: `translate(${btnPos.x}px, ${btnPos.y}px)`,
            transition: isDraggingBtn ? 'none' : 'transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)'
          }}
          className="flex flex-col items-end gap-3 relative select-none"
        >
          {/* Animated Rotating Speech Bubble with Glassmorphism & Typewriter */}
          <div 
            onClick={() => {
              setIsOpen(true);
              setWindowPos({ x: 0, y: 0 });
            }}
            className={`
              absolute bottom-26 -right-2 bg-white/95 backdrop-blur-md shadow-[0_18px_40px_rgba(79,70,229,0.22)] border border-indigo-200/80 rounded-2xl p-4 max-w-[290px] w-max transform transition-all duration-500 ease-out origin-bottom-right cursor-pointer hover:scale-105 group/bubble z-40
              ${showSpeechBubble ? 'opacity-100 scale-100 translate-y-0 pointer-events-auto' : 'opacity-0 scale-75 translate-y-6 pointer-events-none'}
            `}
          >
            {/* Header Badge */}
            <div className="flex items-center justify-between gap-3 mb-2 pb-1.5 border-b border-indigo-50">
              <span className="text-[12.5px] font-bold text-indigo-600 flex items-center gap-1.5">
                <span className="animate-spin text-[14px]" style={{ animationDuration: '4s' }}>✨</span> الصيدلي الذكي
              </span>
              <span className="text-[11px] bg-indigo-50 text-indigo-700 font-bold px-2.5 py-0.5 rounded-full shadow-xs">
                انقر للمحادثة 💬
              </span>
            </div>

            {/* Typewritten Message */}
            <div className="text-[16px] font-bold text-slate-800 text-center leading-relaxed min-h-[26px]" style={{ fontFamily: 'var(--font-cairo), sans-serif' }}>
              {typedMessage || ROBOT_MESSAGES[messageIndex]}
              {showSpeechBubble && typedMessage.length < ROBOT_MESSAGES[messageIndex].length && (
                <span className="inline-block w-2 h-4 bg-indigo-600 animate-pulse ml-1 align-middle rounded-xs"></span>
              )}
            </div>
            
            {/* Triangle pointer */}
            <div className="absolute -bottom-2 right-8 w-4 h-4 bg-white border-b border-r border-indigo-200/80 transform rotate-45"></div>
          </div>

          {/* Concentric Sonar Pulse Rings */}
          <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
            <span className="absolute w-24 h-24 sm:w-28 sm:h-28 rounded-full bg-gradient-to-r from-indigo-500/20 to-emerald-500/20 animate-ping opacity-60 pointer-events-none" style={{ animationDuration: '3.5s' }}></span>
            <span className="absolute w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-indigo-500/10 animate-pulse pointer-events-none"></span>
          </div>

          {/* Draggable & Clickable Floating Button with Gradient Aura */}
          <button 
            onPointerDown={handleBtnPointerDown}
            onPointerMove={handleBtnPointerMove}
            onPointerUp={handleBtnPointerUp}
            onPointerCancel={handleBtnPointerUp}
            onMouseEnter={() => setIsTalking(true)}
            onMouseLeave={() => setIsTalking(false)}
            className={`relative w-18 h-18 sm:w-22 sm:h-22 rounded-full p-[3px] bg-gradient-to-tr from-indigo-600 via-primary to-emerald-400 shadow-[0_10px_35px_rgba(79,70,229,0.4)] hover:shadow-[0_15px_45px_rgba(79,70,229,0.65)] transition-all duration-300 hover:scale-110 hover:-translate-y-1.5 group z-50 touch-none ${
              isDraggingBtn ? 'cursor-grabbing scale-105' : 'cursor-grab'
            }`}
            title="اسحب في أي مكان أو انقر للفتح"
          >
            {/* Inner White Shield */}
            <div className="w-full h-full bg-white rounded-full p-1 overflow-hidden shadow-inner flex items-center justify-center">
              <RobotAvatar isTalking={isTalking || showSpeechBubble} isMoving={isDraggingBtn} />
            </div>
            
            {/* Pulsing Notification Badge with Heartbeat */}
            <span className="absolute top-0 right-0 w-4 h-4 sm:w-5 sm:h-5 bg-rose-600 rounded-full border-2 border-white shadow-md flex items-center justify-center">
              <span className="w-2 h-2 rounded-full bg-white animate-ping"></span>
            </span>
          </button>
        </div>
      )}
    </div>
  );
}
