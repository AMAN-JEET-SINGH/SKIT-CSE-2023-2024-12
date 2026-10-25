
"use client";

import {
  FormEvent,
  KeyboardEvent,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

type Sender = "user" | "assistant";

type Message = {
  id: string;
  text: string;
  sender: Sender;
  createdAt: string;
  status?: "sent" | "delivered" | "read";
  reactions?: string[];
};

type QuickReply = {
  label: string;
  message: string;
};

const QUICK_REPLIES: QuickReply[] = [
  { label: "I'm feeling good", message: "I'm feeling good today." },
  { label: "Feeling stressed", message: "I'm feeling stressed today." },
  { label: "Need motivation", message: "I need some motivation." },
  { label: "Need a break", message: "I think I need a break." },
];

const INITIAL_MESSAGES: Message[] = [
  {
    id: "welcome-1",
    text: "Hello! Welcome to SentiCare.",
    sender: "assistant",
    createdAt: new Date().toISOString(),
  },
  {
    id: "welcome-2",
    text: "I'm here to help you reflect on your day. How are you feeling right now?",
    sender: "assistant",
    createdAt: new Date().toISOString(),
  },
];

function formatTime(date: string) {
  return new Date(date).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getDateLabel(date: string) {
  const value = new Date(date);
  const today = new Date();

  if (value.toDateString() === today.toDateString()) {
    return "Today";
  }

  return value.toLocaleDateString([], {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function createId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function Avatar({ sender }: { sender: Sender }) {
  return (
    <div
      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
        sender === "user"
          ? "bg-indigo-100 text-indigo-700"
          : "bg-teal-100 text-teal-800"
      }`}
      aria-label={sender === "user" ? "Your avatar" : "Assistant avatar"}
    >
      {sender === "user" ? "Y" : "S"}
    </div>
  );
}

function StatusDot({ online }: { online: boolean }) {
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${
        online ? "bg-emerald-500" : "bg-amber-500"
      }`}
      aria-hidden="true"
    />
  );
}

function MessageBubble({
  message,
  onCopy,
  onDelete,
  onReact,
}: {
  message: Message;
  onCopy: (text: string) => void;
  onDelete: (id: string) => void;
  onReact: (id: string, reaction: string) => void;
}) {
  const isUser = message.sender === "user";

  return (
    <article
      className={`group flex w-full items-end gap-2 ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      {!isUser && <Avatar sender="assistant" />}

      <div
        className={`flex max-w-[85%] flex-col sm:max-w-[75%] ${
          isUser ? "items-end" : "items-start"
        }`}
      >
        <div
          className={`mb-1 flex items-center gap-2 px-1 text-xs text-slate-500 ${
            isUser ? "flex-row-reverse" : ""
          }`}
        >
          <span className="font-medium">
            {isUser ? "You" : "SentiCare"}
          </span>
          <time dateTime={message.createdAt}>
            {formatTime(message.createdAt)}
          </time>
        </div>

        <div
          className={`rounded-2xl px-4 py-3 shadow-sm ${
            isUser
              ? "rounded-br-sm bg-teal-700 text-white"
              : "rounded-bl-sm border border-slate-200 bg-white text-slate-800"
          }`}
        >
          <p className="whitespace-pre-wrap break-words text-sm leading-6">
            {message.text}
          </p>
        </div>

        <div
          className={`mt-1 flex items-center gap-2 text-xs ${
            isUser ? "text-slate-500" : "text-slate-400"
          }`}
        >
          {isUser && message.status && (
            <span>
              {message.status === "read"
                ? "✓✓ Read"
                : message.status === "delivered"
                  ? "✓✓ Delivered"
                  : "✓ Sent"}
            </span>
          )}

          <button
            type="button"
            onClick={() => onCopy(message.text)}
            className="rounded px-1 py-0.5 hover:bg-slate-100 hover:text-slate-700"
            aria-label="Copy message"
            title="Copy message"
          >
            Copy
          </button>

          <button
            type="button"
            onClick={() => onReact(message.id, "❤️")}
            className="rounded px-1 py-0.5 hover:bg-slate-100 hover:text-slate-700"
            aria-label="React with heart"
            title="React with heart"
          >
            ♡
          </button>

          {isUser && (
            <button
              type="button"
              onClick={() => onDelete(message.id)}
              className="rounded px-1 py-0.5 hover:bg-rose-50 hover:text-rose-600"
              aria-label="Delete message"
              title="Delete message"
            >
              Delete
            </button>
          )}
        </div>

        {message.reactions && message.reactions.length > 0 && (
          <div className="mt-1 flex gap-1">
            {message.reactions.map((reaction, index) => (
              <span
                key={`${reaction}-${index}`}
                className="rounded-full border border-slate-200 bg-white px-2 py-1 text-xs"
              >
                {reaction}
              </span>
            ))}
          </div>
        )}
      </div>

      {isUser && <Avatar sender="user" />}
    </article>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-end gap-2" role="status" aria-live="polite">
      <Avatar sender="assistant" />
      <div className="rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3">
        <span className="text-xs text-slate-500">
          SentiCare is typing
        </span>
        <span className="ml-2 inline-flex gap-1">
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-teal-600" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-teal-600 [animation-delay:150ms]" />
          <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-teal-600 [animation-delay:300ms]" />
        </span>
      </div>
    </div>
  );
}

function EmptyState({ query }: { query: string }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 text-center">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-teal-50 text-3xl">
        💬
      </div>
      <h3 className="text-lg font-semibold text-slate-800">
        {query ? "No messages found" : "Start a conversation"}
      </h3>
      <p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">
        {query
          ? "Try a different search phrase."
          : "Share how your day is going or choose one of the suggested messages below."}
      </p>
    </div>
  );
}

export default function ChatPanel() {
  const [messages, setMessages] =
    useState<Message[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");
  const [showSearch, setShowSearch] = useState(false);
  const [showQuickReplies, setShowQuickReplies] = useState(true);
  const [isTyping, setIsTyping] = useState(false);
  const [connectionState, setConnectionState] = useState<
    "demo" | "connected" | "disconnected"
  >("demo");
  const [notice, setNotice] = useState("");

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const filteredMessages = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) return messages;

    return messages.filter((item) =>
      item.text.toLowerCase().includes(query)
    );
  }, [messages, search]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [filteredMessages.length, isTyping]);

  function addMessage(text: string) {
    const trimmed = text.trim();

    if (!trimmed) return;

    const message: Message = {
      id: createId(),
      text: trimmed,
      sender: "user",
      createdAt: new Date().toISOString(),
      status: "sent",
    };

    setMessages((previous) => [...previous, message]);
    setInput("");
    setShowQuickReplies(false);
    setNotice(
      "Demo mode: your message is displayed locally and has not been sent to an AI service."
    );
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    addMessage(input);
  }

  function handleKeyDown(
    event: KeyboardEvent<HTMLTextAreaElement>
  ) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      addMessage(input);
    }
  }

  async function copyMessage(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setNotice("Message copied.");
    } catch {
      setNotice("Could not copy the message. Please copy it manually.");
    }
  }

  function deleteMessage(id: string) {
    setMessages((previous) =>
      previous.filter((item) => item.id !== id)
    );
  }

  function reactToMessage(id: string, reaction: string) {
    setMessages((previous) =>
      previous.map((item) => {
        if (item.id !== id) return item;

        const reactions = item.reactions ?? [];
        const alreadyReacted = reactions.includes(reaction);

        return {
          ...item,
          reactions: alreadyReacted
            ? reactions.filter((value) => value !== reaction)
            : [...reactions, reaction],
        };
      })
    );
  }

  function clearConversation() {
    setMessages([]);
    setSearch("");
    setNotice("Local demo conversation cleared.");
  }

  const connectionLabel =
    connectionState === "connected"
      ? "Connected"
      : connectionState === "disconnected"
        ? "Disconnected"
        : "Frontend demo";

  return (
    <main className="min-h-screen bg-slate-100 p-3 sm:p-6">
      <section className="mx-auto flex h-[92vh] min-h-[560px] max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl">
        <header className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-teal-700 text-xl text-white">
              S
            </div>

            <div className="min-w-0">
              <h1 className="truncate text-lg font-bold text-slate-900">
                SentiCare
              </h1>
              <p className="text-xs text-slate-500 sm:text-sm">
                Well-being conversation space
              </p>
              <div className="mt-1 flex items-center gap-2">
                <StatusDot
                  online={connectionState === "connected"}
                />
                <span className="text-xs text-slate-500">
                  {connectionLabel}
                </span>
              </div>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-1">
            <button
              type="button"
              onClick={() => setShowSearch((value) => !value)}
              className="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100"
            >
              Search
            </button>
            <button
              type="button"
              onClick={clearConversation}
              className="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-rose-50 hover:text-rose-600"
            >
              Clear
            </button>
          </div>
        </header>

        {showSearch && (
          <div className="border-b border-slate-200 bg-slate-50 p-3">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search messages..."
              aria-label="Search messages"
              className="w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm outline-none focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
            />
          </div>
        )}

        <div className="flex-1 overflow-y-auto bg-slate-50/70 px-3 py-5 sm:px-6">
          {filteredMessages.length === 0 ? (
            <EmptyState query={search} />
          ) : (
            <div className="space-y-5">
              {filteredMessages.map((message, index) => {
                const currentDate = getDateLabel(message.createdAt);
                const previousDate =
                  index > 0
                    ? getDateLabel(filteredMessages[index - 1].createdAt)
                    : "";

                return (
                  <div key={message.id} className="space-y-4">
                    {currentDate !== previousDate && (
                      <div className="flex justify-center">
                        <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-500">
                          {currentDate}
                        </span>
                      </div>
                    )}

                    <MessageBubble
                      message={message}
                      onCopy={copyMessage}
                      onDelete={deleteMessage}
                      onReact={reactToMessage}
                    />
                  </div>
                );
              })}

              {isTyping && <TypingIndicator />}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {showQuickReplies && messages.length > 0 && (
          <div className="border-t border-slate-100 bg-white px-4 py-3">
            <p className="mb-2 text-xs font-medium text-slate-500">
              Quick replies
            </p>
            <div className="flex flex-wrap gap-2">
              {QUICK_REPLIES.map((reply) => (
                <button
                  key={reply.label}
                  type="button"
                  onClick={() => addMessage(reply.message)}
                  className="rounded-full border border-teal-200 bg-teal-50 px-3 py-2 text-xs text-teal-800 transition hover:bg-teal-100"
                >
                  {reply.label}
                </button>
              ))}
            </div>
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="border-t border-slate-200 bg-white p-3 sm:p-4"
        >
          <div className="flex items-end gap-2 sm:gap-3">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Write a message..."
              aria-label="Write a message"
              rows={1}
              className="max-h-32 min-h-12 min-w-0 flex-1 resize-y rounded-xl border border-slate-300 px-4 py-3 text-sm leading-5 outline-none transition focus:border-teal-600 focus:ring-2 focus:ring-teal-100"
            />

            <button
              type="submit"
              disabled={!input.trim()}
              className="rounded-xl bg-teal-700 px-4 py-3 text-sm font-semibold text-white transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-40 sm:px-6"
            >
              Send
            </button>
          </div>

          <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-slate-400">
              Enter to send · Shift + Enter for a new line
            </p>
            <span className="text-xs text-slate-400">
              {input.length} characters
            </span>
          </div>
        </form>

        <footer className="border-t border-slate-100 bg-white px-4 py-2">
          <p className="text-center text-xs leading-5 text-slate-400">
            Demo interface only. Messages are stored in local component
            state and disappear when the page reloads.
          </p>
          {notice && (
            <p
              role="status"
              className="mt-1 text-center text-xs text-teal-700"
            >
              {notice}
            </p>
          )}
        </footer>
      </section>
    </main>
  );
}
