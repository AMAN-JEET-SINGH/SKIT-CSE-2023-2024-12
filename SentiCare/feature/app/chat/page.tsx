
"use client";

import { useState } from "react";

type Message = {
  id: number;
  text: string;
  sender: "user" | "assistant";
  time: string;
};

export default function ChatPage() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      text: "Hi! Welcome to SentiCare. How are you feeling today?",
      sender: "assistant",
      time: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    },
  ]);

  function handleSend() {
    const text = message.trim();
    if (!text) return;

    const newMessage: Message = {
      id: Date.now(),
      text,
      sender: "user",
      time: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };

    setMessages((previous) => [...previous, newMessage]);
    setMessage("");
  }

  return (
    <main className="min-h-screen bg-slate-100 p-4 sm:p-8">
      <section className="mx-auto flex h-[85vh] max-w-4xl flex-col overflow-hidden rounded-2xl bg-white shadow-lg">
        <header className="flex items-center justify-between bg-teal-700 p-5 text-white">
          <div>
            <h1 className="text-xl font-bold">SentiCare</h1>
            <p className="text-sm text-teal-100">
              Your Well-being Assistant
            </p>
          </div>
          <span className="rounded-full bg-white/15 px-3 py-1 text-xs">
            UI Demo
          </span>
        </header>

        <div className="flex-1 space-y-5 overflow-y-auto p-5">
          {messages.map((item) => {
            const isUser = item.sender === "user";

            return (
              <div
                key={item.id}
                className={`flex ${
                  isUser ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[85%] sm:max-w-[70%] ${
                    isUser ? "items-end" : "items-start"
                  } flex flex-col`}
                >
                  <span className="mb-1 px-1 text-xs text-slate-500">
                    {isUser ? "You" : "SentiCare Assistant"}
                  </span>

                  <div
                    className={`rounded-2xl px-4 py-3 ${
                      isUser
                        ? "rounded-br-sm bg-teal-700 text-white"
                        : "rounded-bl-sm bg-slate-100 text-slate-800"
                    }`}
                  >
                    <p className="whitespace-pre-wrap break-words text-sm leading-6">
                      {item.text}
                    </p>
                  </div>

                  <span className="mt-1 px-1 text-xs text-slate-400">
                    {item.time}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        <form
          className="flex gap-3 border-t border-slate-200 p-4"
          onSubmit={(event) => {
            event.preventDefault();
            handleSend();
          }}
        >
          <input
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Type your message..."
            aria-label="Type your message"
            className="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
          />

          <button
            type="submit"
            disabled={!message.trim()}
            className="rounded-xl bg-teal-700 px-5 py-3 font-medium text-white hover:bg-teal-800 disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </section>
    </main>
  );
}
