
"use client";

type ChatMessageProps = {
  text: string;
  sender: "user" | "assistant";
  time?: string;
};

export default function ChatMessage({
  text,
  sender,
  time,
}: ChatMessageProps) {
  const isUser = sender === "user";

  return (
    <div
      className={`flex w-full ${
        isUser ? "justify-end" : "justify-start"
      }`}
    >
      <div
        className={`flex max-w-[90%] flex-col sm:max-w-[75%] ${
          isUser ? "items-end" : "items-start"
        }`}
      >
        <span className="mb-1 px-1 text-xs font-medium text-slate-500">
          {isUser ? "You" : "SentiCare Assistant"}
        </span>

        <div
          className={`rounded-2xl px-4 py-3 shadow-sm ${
            isUser
              ? "rounded-br-sm bg-teal-700 text-white"
              : "rounded-bl-sm border border-slate-200 bg-white text-slate-800"
          }`}
        >
          <p className="whitespace-pre-wrap break-words text-sm leading-6">
            {text}
          </p>
        </div>

        {time && (
          <span className="mt-1 px-1 text-xs text-slate-400">
            {time}
          </span>
        )}
      </div>
    </div>
  );
}
