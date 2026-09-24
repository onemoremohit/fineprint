import { useState, useRef, useEffect } from 'react';
import { askQuestion } from '../lib/api';
import type { QAMessage, Citation } from '../types';

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
    } catch (err) {
      const errorMsg: QAMessage = {
        id: `e-${Date.now()}`,
        role: 'assistant',
        content: 'An error occurred while processing your question. Please try again.',
        abstained: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const suggestedQuestions = [
    'What is the notice period?',
    'What happens if I break the training bond?',
    'Is there a non-compete clause?',
    'Does this include health insurance?', // Likely to abstain
    'Can I be transferred to another city?', // Likely to abstain
  ];

  return (
    <div className="glass-card flex flex-col h-[600px] animate-fade-in-up">
      {/* Header */}
      <div className="p-4 border-b border-border/50">
        <h3 className="text-sm font-semibold">Ask About Your Document</h3>
        <p className="text-xs text-text-muted mt-1">
          Questions are answered using only your document's content. The system will
          tell you when the answer isn't in the document.
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-xs text-text-muted text-center mb-4">
              Try asking a question:
            </p>
            {suggestedQuestions.map((q) => (
              <button
                key={q}
                onClick={() => setInput(q)}
                className="block w-full text-left px-4 py-2.5 rounded-lg text-sm text-text-secondary bg-surface-2/50 hover:bg-surface-3/50 transition-colors border border-border/30 hover:border-border"
              >
                {q}
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
              className={`max-w-[85%] rounded-xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-primary/20 text-text rounded-br-sm'
                  : msg.abstained
                  ? 'bg-surface-3/50 border border-warning/20 rounded-bl-sm'
                  : 'bg-surface-2 rounded-bl-sm'
              }`}
            >
              {msg.role === 'assistant' && msg.abstained && (
                <div className="flex items-center gap-1.5 mb-2">
                  <span className="text-xs px-2 py-0.5 rounded bg-warning/20 text-warning font-medium">
                    ℹ️ Not in document
                  </span>
                </div>
              )}

              <p className="text-sm leading-relaxed">{msg.content}</p>

              {/* Citation Chips */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-2 pt-2 border-t border-border/30 flex flex-wrap gap-1.5">
                  {msg.citations.map((c: Citation, idx: number) =>
                    c.kind === 'document' && c.span ? (
                      <button
                        key={idx}
                        onClick={() => onCitationClick(c.span!.start, c.span!.end)}
                        className="text-[10px] px-2 py-0.5 rounded-full bg-amber/10 text-amber-light hover:bg-amber/20 transition-colors border border-amber/20"
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
          <div className="flex justify-start">
            <div className="bg-surface-2 rounded-xl rounded-bl-sm px-4 py-3">
              <div className="flex gap-1.5">
                <div className="w-2 h-2 rounded-full bg-text-muted animate-pulse" />
                <div className="w-2 h-2 rounded-full bg-text-muted animate-pulse" style={{ animationDelay: '0.2s' }} />
                <div className="w-2 h-2 rounded-full bg-text-muted animate-pulse" style={{ animationDelay: '0.4s' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-border/50">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your document..."
            className="flex-1 px-4 py-2.5 rounded-xl bg-surface-2 border border-border text-sm text-text placeholder:text-text-muted focus:outline-none focus:border-primary transition-colors"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-dark text-white text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Ask
          </button>
        </div>
      </form>
    </div>
  );
}
