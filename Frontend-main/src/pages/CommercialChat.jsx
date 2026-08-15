import React, { useContext, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Send, ShieldAlert, ShieldCheck, Plus, Trash2, Loader2, KeyRound } from "lucide-react";
import { ThemeContext } from "../context/ThemeContext";
import { api } from "../lib/api";

const inputClass = (theme) =>
  `w-full p-2.5 rounded-lg border text-sm ${
    theme === "dark" ? "bg-gray-900 border-gray-700 text-white" : "bg-white border-gray-300 text-gray-900"
  } focus:outline-none focus:ring-2 focus:ring-blue-500`;

const PROVIDER_LABELS = { openai: "OpenAI", anthropic: "Anthropic (Claude)", gemini: "Google Gemini" };

export const CommercialChat = ({ token }) => {
  const { theme } = useContext(ThemeContext);
  const [credentials, setCredentials] = useState([]);
  const [selectedCredential, setSelectedCredential] = useState("");
  const [showKeyForm, setShowKeyForm] = useState(false);
  const [keyForm, setKeyForm] = useState({ provider: "openai", label: "", api_key: "" });

  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef(null);

  const loadCredentials = async () => {
    const rows = await api.listCredentials(token);
    setCredentials(rows);
    if (rows.length && !selectedCredential) setSelectedCredential(rows[0].id);
  };

  useEffect(() => {
    if (token) loadCredentials();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleAddKey = async (e) => {
    e.preventDefault();
    await api.createCredential(token, keyForm);
    setKeyForm({ provider: "openai", label: "", api_key: "" });
    setShowKeyForm(false);
    loadCredentials();
  };

  const handleDeleteKey = async (id) => {
    await api.deleteCredential(token, id);
    if (selectedCredential === id) setSelectedCredential("");
    loadCredentials();
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!prompt.trim() || !selectedCredential) return;
    const userMessage = { role: "user", content: prompt };
    setMessages((m) => [...m, userMessage]);
    setPrompt("");
    setSending(true);
    setError("");
    try {
      const result = await api.chatCommercial({
        user_id: "gui_user",
        credential_id: selectedCredential,
        prompt: userMessage.content,
      });
      setMessages((m) => [...m, { role: "assistant", content: result.generation, governance: result.governance }]);
    } catch (err) {
      const blockedAt = err.body?.detail?.blocked_at;
      setMessages((m) => [
        ...m,
        {
          role: "blocked",
          content: blockedAt
            ? `Blocked at ${blockedAt === "layer1" ? "Layer 1 (input security)" : "Layer 2 (policy engine)"}`
            : "Request failed",
          detail: err.body?.detail,
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-3xl font-bold ${theme === "dark" ? "text-white" : "text-gray-900"}`}>Commercial AI Chat</h1>
          <p className={`${theme === "dark" ? "text-gray-400" : "text-gray-600"} mt-1`}>
            Every prompt is screened by Layer 1 and Layer 2 before it ever reaches the provider. A blocked prompt
            never spends a token.
          </p>
        </div>
        <button onClick={() => setShowKeyForm((s) => !s)}
          className={`px-3 py-2 rounded-lg border text-sm flex items-center gap-2 ${theme === "dark" ? "border-gray-700 text-gray-300 hover:bg-gray-800" : "border-gray-300 text-gray-700 hover:bg-gray-100"}`}>
          <KeyRound className="w-4 h-4" /> Manage Keys
        </button>
      </div>

      {showKeyForm && (
        <div className={`p-4 rounded-xl border ${theme === "dark" ? "bg-gray-900/50 border-gray-800" : "bg-white border-gray-200"} space-y-3`}>
          <form onSubmit={handleAddKey} className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Provider</label>
              <select value={keyForm.provider} onChange={(e) => setKeyForm({ ...keyForm, provider: e.target.value })} className={inputClass(theme)}>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="gemini">Gemini</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Label</label>
              <input required value={keyForm.label} onChange={(e) => setKeyForm({ ...keyForm, label: e.target.value })} placeholder="prod key" className={inputClass(theme)} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">API Key</label>
              <input required type="password" value={keyForm.api_key} onChange={(e) => setKeyForm({ ...keyForm, api_key: e.target.value })} placeholder="sk-..." className={inputClass(theme)} />
            </div>
            <button type="submit" className="px-4 py-2.5 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:opacity-90 flex items-center justify-center gap-2 text-sm">
              <Plus className="w-4 h-4" /> Add Key
            </button>
          </form>
          <div className="flex flex-wrap gap-2 pt-2">
            {credentials.map((c) => (
              <span key={c.id} className={`px-2.5 py-1 rounded-full text-xs flex items-center gap-2 ${theme === "dark" ? "bg-gray-800 text-gray-300" : "bg-gray-100 text-gray-700"}`}>
                {PROVIDER_LABELS[c.provider] || c.provider} - {c.label} ({c.masked_key})
                <button onClick={() => handleDeleteKey(c.id)}><Trash2 className="w-3 h-3 text-red-400" /></button>
              </span>
            ))}
          </div>
        </div>
      )}

      <div className={`flex-1 rounded-xl border ${theme === "dark" ? "bg-gray-900/50 border-gray-800" : "bg-white border-gray-200"} flex flex-col min-h-[420px]`}>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-center text-gray-500 text-sm mt-10">No messages yet. Pick a key below and say hello.</p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm ${
                  m.role === "user"
                    ? "bg-gradient-to-r from-blue-500 to-purple-600 text-white"
                    : m.role === "blocked"
                    ? "bg-red-500/10 border border-red-500/30 text-red-400"
                    : theme === "dark"
                    ? "bg-gray-800 text-gray-100"
                    : "bg-gray-100 text-gray-900"
                }`}
              >
                {m.role === "blocked" && <ShieldAlert className="w-4 h-4 inline mr-1.5 -mt-0.5" />}
                {m.role === "assistant" && <ShieldCheck className="w-3.5 h-3.5 inline mr-1.5 -mt-0.5 text-green-500" />}
                {m.content}
              </div>
            </div>
          ))}
          <div ref={scrollRef} />
        </div>
        <form onSubmit={handleSend} className={`p-3 border-t ${theme === "dark" ? "border-gray-800" : "border-gray-200"} flex gap-2`}>
          <select value={selectedCredential} onChange={(e) => setSelectedCredential(e.target.value)} className={inputClass(theme) + " max-w-[180px]"}>
            <option value="">Select a key...</option>
            {credentials.map((c) => (
              <option key={c.id} value={c.id}>{PROVIDER_LABELS[c.provider] || c.provider} - {c.label}</option>
            ))}
          </select>
          <input value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Type a prompt..." className={inputClass(theme) + " flex-1"} />
          <button type="submit" disabled={sending || !selectedCredential} className="px-4 py-2.5 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg hover:opacity-90 disabled:opacity-50 flex items-center gap-2">
            {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </form>
      </div>
      {error && <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">{error}</div>}
    </motion.div>
  );
};
