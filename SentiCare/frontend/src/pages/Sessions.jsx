import React, { useState, useRef, useEffect } from "react";
import { Send, Paperclip, X, FileText, Image, File, Loader2, Shield, Activity } from "lucide-react";
import axios from "axios";
import { useAuth } from "../contexts/AuthContext";

const API_BASE_URL = "http://localhost:8000";

export default function Sessions() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: "bot",
      content: "Hello! I'm here to support you. How are you feeling today?",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [piiProtection, setPiiProtection] = useState(true);
  const { user, getAuthHeaders } = useAuth();
  const [contextLoaded, setContextLoaded] = useState(false);

  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Create a new chat session on component mount
  useEffect(() => {
    createNewSession();
  }, []);

  // Fetch mental health context on mount
  useEffect(() => {
    fetchMentalHealthContext();
  }, []);

  const createNewSession = async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/chat/new-session`);
      if (response.data.success) {
        setSessionId(response.data.session_id);
        console.log("New session created:", response.data.session_id);
      }
    } catch (err) {
      console.error("Error creating session:", err);
      setError("Failed to create chat session. Please refresh the page.");
    }
  };

  const fetchMentalHealthContext = async () => {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/journals/recent-scores?days=5`,
        {
          headers: getAuthHeaders(),
        }
      );

      if (response.data.success && response.data.data.length > 0) {
        setContextLoaded(true);
        console.log("Mental health context loaded for chatbot:", response.data.data);
      }
    } catch (err) {
      console.error("Failed to load mental health context:", err);
      // Continue without context
    }
  };

  const sendMessageToAPI = async (message) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/chat/message`, {
        session_id: sessionId,
        message: message,
        temperature: 0.7,
        max_tokens: 500,
        remove_pii: piiProtection,  // Add this parameter
      });

      if (response.data.success) {
        return response.data.assistant_message;
      } else {
        throw new Error(response.data.error || "Failed to get response");
      }
    } catch (err) {
      console.error("Error sending message:", err);
      throw err;
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() && uploadedFiles.length === 0) return;

    if (!sessionId) {
      setError("No active session. Please refresh the page.");
      return;
    }

    // Add user message
    const userMessage = {
      id: Date.now(),
      type: "user",
      content: inputValue,
      files: uploadedFiles.length > 0 ? [...uploadedFiles] : null,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setUploadedFiles([]);
    setIsLoading(true);
    setError(null);

    try {
      // Send message to API
      const botResponse = await sendMessageToAPI(inputValue);

      // Add bot response
      const botMessage = {
        id: Date.now() + 1,
        type: "bot",
        content: botResponse,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      console.log(err);
      const errorMessage = {
        id: Date.now() + 1,
        type: "bot",
        content:
          "I apologize, but I'm having trouble connecting right now. Please try again in a moment. 🙏",
        timestamp: new Date(),
        isError: true,
      };

      setMessages((prev) => [...prev, errorMessage]);
      setError("Failed to send message. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files);
    const newFiles = files.map((file) => ({
      id: Date.now() + Math.random(),
      file,
      name: file.name,
      size: file.size,
      type: file.type,
    }));
    setUploadedFiles((prev) => [...prev, ...newFiles]);
  };

  const removeFile = (fileId) => {
    setUploadedFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const getFileIcon = (fileType) => {
    if (fileType.startsWith("image/")) return <Image className="w-4 h-4" />;
    if (fileType.includes("pdf") || fileType.includes("document"))
      return <FileText className="w-4 h-4" />;
    return <File className="w-4 h-4" />;
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const clearChat = async () => {
    if (!sessionId) return;

    try {
      await axios.delete(`${API_BASE_URL}/api/chat/clear/${sessionId}`);
      setMessages([
        {
          id: 1,
          type: "bot",
          content: "Chat history cleared. How can I help you today?",
          timestamp: new Date(),
        },
      ]);
    } catch (err) {
      console.error("Error clearing chat:", err);
      setError("Failed to clear chat history.");
    }
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="border-b border-gray-200 p-6">
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-[#1A3A37]">
              Chat With Maitri - Your Digital Companion
            </h1>
            <p className="text-gray-600 text-sm mt-1">
              Share your thoughts and feelings in a safe space
              {contextLoaded && (
                <span className="ml-2 text-teal-600 font-medium">
                  • Context-aware support based on your recent progress
                </span>
              )}
            </p>
            {sessionId && (
              <p className="text-xs text-gray-400 mt-1">
                Session ID: {sessionId.slice(0, 8)}...
              </p>
            )}
            
            {/* Privacy Badge */}
            <div className="mt-2 inline-flex items-center gap-2 px-3 py-1 bg-green-50 border border-green-200 rounded-full">
              <Shield className="w-3 h-3 text-green-600" />
              <span className="text-xs text-green-700 font-medium">
                PII Protection Enabled
              </span>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Privacy Toggle */}
            <button
              onClick={() => setPiiProtection(!piiProtection)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full border transition-colors ${
                piiProtection
                  ? "bg-green-50 border-green-200 text-green-700"
                  : "bg-gray-50 border-gray-200 text-gray-600"
              }`}
            >
              <Shield className="w-4 h-4" />
              <span className="text-xs font-medium">
                {piiProtection ? "Protected" : "Off"}
              </span>
            </button>
            
            <button
              onClick={clearChat}
              className="px-4 py-2 text-sm text-gray-600 hover:text-[#1A3A37] hover:bg-gray-100 rounded-lg transition-colors"
            >
              Clear Chat
            </button>
          </div>
        </div>

        {/* Context Awareness Badge */}
        {contextLoaded && (
          <div className="mt-4 p-3 bg-teal-50 border border-teal-200 rounded-lg">
            <div className="flex items-start gap-2">
              <Activity className="w-4 h-4 text-teal-600 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm text-teal-900 font-medium">
                  Personalized Support Active
                </p>
                <p className="text-xs text-teal-700 mt-1">
                  Maitri has access to your recent mental health trends and can provide context-aware support and encouragement.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Privacy Notice */}
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-start gap-2">
            <Shield className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm text-blue-900 font-medium">Privacy Protection Active</p>
              <p className="text-xs text-blue-700 mt-1">
                Personal information (names, locations, emails, phone numbers) is automatically anonymized before processing.
              </p>
            </div>
          </div>
        </div>

        {error && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.type === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[70%] rounded-2xl px-4 py-3 ${
                message.type === "user"
                  ? "bg-[#1A3A37] text-white"
                  : message.isError
                  ? "bg-red-50 text-red-800 border border-red-200"
                  : "bg-gray-100 text-gray-800"
              }`}
            >
              {message.content && (
                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                  {message.content}
                </p>
              )}

              {/* Display uploaded files */}
              {message.files && message.files.length > 0 && (
                <div className="mt-2 space-y-2">
                  {message.files.map((file) => (
                    <div
                      key={file.id}
                      className={`flex items-center space-x-2 p-2 rounded-lg ${
                        message.type === "user"
                          ? "bg-white bg-opacity-20"
                          : "bg-white"
                      }`}
                    >
                      <div
                        className={
                          message.type === "user"
                            ? "text-white"
                            : "text-gray-600"
                        }
                      >
                        {getFileIcon(file.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p
                          className={`text-xs font-medium truncate ${
                            message.type === "user"
                              ? "text-white"
                              : "text-gray-700"
                          }`}
                        >
                          {file.name}
                        </p>
                        <p
                          className={`text-xs ${
                            message.type === "user"
                              ? "text-white text-opacity-80"
                              : "text-gray-500"
                          }`}
                        >
                          {formatFileSize(file.size)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <p
                className={`text-xs mt-2 ${
                  message.type === "user"
                    ? "text-white text-opacity-70"
                    : message.isError
                    ? "text-red-600"
                    : "text-gray-500"
                }`}
              >
                {message.timestamp.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-2xl px-4 py-3">
              <div className="flex items-center space-x-2">
                <Loader2 className="w-4 h-4 animate-spin text-gray-600" />
                <p className="text-sm text-gray-600">Maitri is thinking...</p>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* File Upload Preview */}
      {uploadedFiles.length > 0 && (
        <div className="border-t border-gray-200 p-4">
          <p className="text-sm text-gray-600 mb-2">Files to send:</p>
          <div className="space-y-2">
            {uploadedFiles.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between bg-gray-50 rounded-lg p-3"
              >
                <div className="flex items-center space-x-3">
                  <div className="text-gray-500">{getFileIcon(file.type)}</div>
                  <div>
                    <p className="text-sm font-medium text-gray-700">
                      {file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(file.size)}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => removeFile(file.id)}
                  className="text-gray-400 hover:text-red-500 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="border-t border-gray-200 p-6">
        <div className="flex items-end space-x-3">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            multiple
            className="hidden"
            accept="image/*,.pdf,.doc,.docx,.txt"
          />

          

          <div className="flex-1">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
              placeholder="Type your message here..."
              className="w-full px-4 py-3 border border-gray-300 rounded-2xl resize-none focus:outline-none focus:border-[#1A3A37] focus:ring-1 focus:ring-[#1A3A37] text-sm disabled:bg-gray-50 disabled:cursor-not-allowed"
              rows="1"
              style={{
                minHeight: "48px",
                maxHeight: "120px",
                height: "auto",
              }}
            />
          </div>

          <button
            onClick={handleSendMessage}
            disabled={
              (!inputValue.trim() && uploadedFiles.length === 0) || isLoading
            }
            className="shrink-0 p-3 bg-[#1A3A37] text-white rounded-full hover:bg-[#154F4A] disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>

        <div className="flex items-center justify-between mt-2">
          <p className="text-xs text-gray-500">
            Press Enter to send • Shift + Enter for new line
          </p>
          <div className="flex items-center gap-1 text-xs text-green-600">
            <Shield className="w-3 h-3" />
            <span>Privacy Protected</span>
          </div>
        </div>
      </div>
    </div>
  );
}
