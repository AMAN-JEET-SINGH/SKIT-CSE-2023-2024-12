
"use client";

import { useState } from "react";

export default function ChatPage() {
  const [message, setMessage] = useState("");

  const [messages, setMessages] = useState([
    {
      id: 1,
      text: "Hi! Welcome to SentiCare. How are you feeling today?",
      sender: "bot",
    },
  ]);

  function handleSend() {
    const text = message.trim();

    if (!text) return;

    setMessages((previous) => [
      ...previous,
      {
        id: Date.now(),
        text,
        sender: "user",
      },
    ]);

    setMessage("");
  }

  return (
    <main className="min-h-screen bg-slate-100 p-4 sm:p-8">
      <section className="mx-auto flex h-[85vh] max-w-4xl flex-col overflow-hidden rounded-2xl bg-white shadow-lg">
        {/* Chat Header */}
        <header className="flex items-center justify-between bg-teal-700 px-5 py-4 text-white">
          <div>
            <h1 className="text-xl font-bold">SentiCare</h1>
            <p className="text-sm text-teal-100">
              Your Well-being Assistant
            </p>
          </div>

          <span className="rounded-full bg-white/15 px-3 py-1 text-sm">
            UI Demo
          </span>
        </header>

        {/* Messages */}
        <div className="flex-1 space-y-4 overflow-y-auto p-5">
          {messages.map((item) => (
            <div
              key={item.id}
              className={`flex ${
                item.sender === "user"
                  ? "justify-end"
                  : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  item.sender === "user"
                    ? "rounded-br-sm bg-teal-700 text-white"
                    : "rounded-bl-sm bg-slate-100 text-slate-800"
                }`}
              >
                <p className="break-words text-sm">{item.text}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Message Input */}
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
            className="rounded-xl bg-teal-700 px-5 py-3 font-medium text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </section>
    </main>
  );
}
