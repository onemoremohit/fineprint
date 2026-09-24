import { useState, useRef, useEffect } from 'react';
import { askQuestion } from '../lib/api';
import type { QAMessage } from '../types';

interface Props {
  documentId: string;
  onCitationClick: (start: number, end: number) => void;
}

export default function QaPanel({ documentId, onCitationClick }: Props) {
  const [messages, setMessages] = useState<QAMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput('');

    // Add user message
    const userMsg: QAMessage = {
      id: `q-${Date.now()}`,
      role: 'user',
      content: question,
    };
    setMessages((prev) => [...prev, userMsg]);

    setLoading(true);
    try {
      const response = await askQuestion(documentId, question);

      const assistantMsg: QAMessage = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        citations: response.citations,
        abstained: response.abstained,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: QAMessage = {
        id: `e-${Date.now()}`,
        role: 'assistant',
        content: 'An error occurred while analyzing the document for your question. Please try again.',
        abstained: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const suggestedQuestions = [
    'What is the notice period required for resignation?',
    'What happens if I break the training bond?',
    'Is there a non-compete clause?',
    'Does this include health insurance coverage?', // Intentionally triggers grounded abstention
    'Can I be transferred to another city?',        // Intentionally triggers grounded abstention
  ];

  return (
    <section aria-label="Grounded Q&A Section" className="glass-card flex flex-col h-[600px] animate-fade-in-up">
      {/* Header */}
      <div className="p-4 border-b border-border/50">
        <h3 className="text-sm font-semibold text-text">Ask About Your Document</h3>
        <p className="text-xs text-text-muted mt-1 leading-relaxed">
          Questions are answered strictly using your document's text. When details are absent, the system responsibly abstains to prevent hallucinations.
        </p>
      </div>

      {/* Messages Log Landmark */}
      <div
        role="log"
        aria-live="polite"
        aria-label="Document Q&A dialogue history"
        className="flex-1 overflow-y-auto p-4 space-y-4"
      >
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-xs text-text-muted text-center mb-4 font-medium">
              Suggested questions to explore:
            </p>
            {suggestedQuestions.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => setInput(q)}
                aria-label={`Use suggested question: ${q}`}
                className="w-full text-left p-3 rounded-xl bg-surface-2/60 hover:bg-surface-2 border border-border/50 text-xs text-text-secondary hover:text-text transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-400"
              >
                💡 {q}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-sm shadow-md shadow-indigo-600/20'
                  : msg.abstained
                  ? 'bg-amber/10 border border-amber/30 text-amber-light rounded-bl-sm'
                  : 'bg-surface-2 rounded-bl-sm border border-border/50 text-text'
              }`}
            >
              {msg.role === 'assistant' && msg.abstained && (
                <div className="flex items-center gap-1.5 text-xs text-amber font-semibold mb-1">
                  <span aria-hidden="true">⚠️</span> Document Silent / Abstained
                </div>
              )}

              <p className="whitespace-pre-wrap">{msg.content}</p>

              {/* Citations */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-2.5 pt-2 border-t border-border/40 flex flex-wrap gap-1.5">
                  <span className="text-[10px] text-text-muted self-center mr-1">Source:</span>
                  {msg.citations.map((c, idx) =>
                    c.kind === 'document' && c.span ? (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => onCitationClick(c.span!.start, c.span!.end)}
                        aria-label={`Jump to citation in document from character ${c.span.start} to ${c.span.end}`}
                        className="text-[10px] px-2 py-0.5 rounded-full bg-amber/10 text-amber-light hover:bg-amber/20 transition-colors border border-amber/30 cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-400"
                      >
                        📄 Source [{c.span.start}–{c.span.end}]
                      </button>
                    ) : c.kind === 'statute' ? (
                      <span
                        key={idx}
                        className="text-[10px] px-2 py-0.5 rounded-full bg-indigo/10 text-indigo-light border border-indigo/20"
                      >
                        📜 {c.statute_id}
                      </span>
                    ) : null
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start" role="status" aria-label="Analyzing document to answer your question...">
            <div className="bg-surface-2 rounded-xl rounded-bl-sm px-4 py-3 border border-border/40 flex items-center gap-2">
              <span className="text-xs text-text-secondary">Reviewing text...</span>
              <div aria-hidden="true" className="flex gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" style={{ animationDelay: '0.2s' }} />
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" style={{ animationDelay: '0.4s' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-border/50">
        <div className="flex gap-2">
          <label htmlFor="qa-question-input" className="sr-only">
            Ask a question about your document
          </label>
          <input
            id="qa-question-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about notice periods, bonds, benefits..."
            aria-label="Ask a question about your document"
            className="flex-1 px-4 py-2.5 rounded-xl bg-surface-2 border border-border text-sm text-text placeholder:text-text-muted focus:outline-none focus:border-indigo-400 transition-colors"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            aria-label="Submit question"
            aria-busy={loading}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-400"
          >
            Ask
          </button>
        </div>
      </form>
    </section>
  );
}
