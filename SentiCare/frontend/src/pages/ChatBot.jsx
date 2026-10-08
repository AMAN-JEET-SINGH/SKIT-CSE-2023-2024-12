import { useState, useEffect, useRef } from "react";
import { Send, Loader2, MessageCircle } from "lucide-react";

export default function ChatBot() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hello! I'm here to support you. How are you feeling today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Create new session on mount
  useEffect(() => {
    const createSession = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/chat/new-session", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (response.ok) {
          const data = await response.json();
          setSessionId(data.session_id);
          console.log("New chat session created:", data.session_id);
        } else {
          console.error("Failed to create session:", response.status);
        }
      } catch (error) {
        console.error("Error creating session:", error);
      }
    };

    createSession();
  }, []);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      console.log("Sending message with session:", sessionId);
      
      const response = await fetch("http://localhost:8000/api/chat/message", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          message: input,
          session_id: sessionId,
          remove_pii: true // Enable PII removal by default
        }),
      });

      console.log("Response status:", response.status);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.success) {
        const botMessage = { role: "assistant", content: data.assistant_message };
        setMessages((prev) => [...prev, botMessage]);
        
        // Update session_id if it was created
        if (data.session_id && !sessionId) {
          setSessionId(data.session_id);
        }
      } else {
        throw new Error(data.error || "Failed to get response");
      }
    } catch (error) {
      console.error("Error sending message:", error);
      const errorMessage = {
        role: "assistant",
        content: error.message || "Sorry, I encountered an error. Please try again.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-linear-to-br from-blue-50 to-indigo-50 p-4">
      <div className="max-w-4xl mx-auto h-[calc(100vh-2rem)] flex flex-col bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="bg-linear-to-r from-[#61BDD3] to-[#4a9db8] p-6 text-white">
          <div className="flex items-center gap-3">
            <MessageCircle className="w-8 h-8" />
            <div>
              <h1 className="text-2xl font-bold">Mental Health Support</h1>
              <p className="text-sm text-white/80">
                Your confidential AI companion
              </p>
            </div>
          </div>
        </div>

        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  message.role === "user"
                    ? "bg-[#61BDD3] text-white"
                    : "bg-gray-100 text-gray-800"
                }`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-2xl px-4 py-3">
                <Loader2 className="w-5 h-5 animate-spin text-[#61BDD3]" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <div className="flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-[#61BDD3] focus:border-transparent"
              rows="2"
              disabled={isLoading}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              className="bg-[#61BDD3] hover:bg-[#4a9db8] text-white rounded-xl px-6 py-3 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 font-semibold"
            >
              <Send className="w-5 h-5" />
              Send
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2 text-center">
            Your messages are private and PII is automatically removed
          </p>
        </div>
      </div>
    </div>
  );
}