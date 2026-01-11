import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Bot, User, BookOpen, ChevronDown, Brain, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

export function ChatMessage({ msg }) {
    const isUser = msg.type === 'user';
    const [showRAG, setShowRAG] = useState(false);
    const [showThink, setShowThink] = useState(false);
    const [copied, setCopied] = useState(false);

    // 解析 <think> 標籤
    let thinkContent = '';
    let displayContent = msg.content;

    if (!isUser && msg.content) {
        const thinkMatch = msg.content.match(/<think>([\s\S]*?)<\/think>/);
        if (thinkMatch) {
            thinkContent = thinkMatch[1].trim();
            displayContent = msg.content.replace(/<think>[\s\S]*?<\/think>/, '').trim();
        }
    }

    const handleCopy = async () => {
        await navigator.clipboard.writeText(displayContent);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex gap-4 ${isUser ? 'justify-end' : 'justify-start'}`}
        >
            {!isUser && (
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center shadow-lg shadow-primary-500/20 flex-shrink-0">
                    <Bot className="w-5 h-5 text-white" />
                </div>
            )}

            <div className={`flex flex-col gap-2 max-w-[85%] ${isUser ? 'items-end' : 'items-start'}`}>
                <div className={`relative group px-4 py-3 rounded-2xl shadow-lg overflow-hidden ${isUser
                    ? 'bg-primary-600 text-white rounded-tr-sm'
                    : 'bg-dark-800 border border-dark-600 text-slate-100 rounded-tl-sm'
                    }`}>
                    <div className={`prose prose-sm max-w-none break-words ${isUser ? 'prose-invert' : 'prose-invert'}`}>
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm, remarkBreaks]}
                            components={{
                                a: ({ node, ...props }) => <a {...props} className="text-primary-400 hover:text-primary-300 break-all underline" target="_blank" rel="noopener noreferrer" />,
                                p: ({ node, ...props }) => <p {...props} className="mb-2 last:mb-0 text-slate-100" />,
                                ul: ({ node, ...props }) => <ul {...props} className="mb-2 last:mb-0 pl-4 list-disc text-slate-200" />,
                                ol: ({ node, ...props }) => <ol {...props} className="mb-2 last:mb-0 pl-4 list-decimal text-slate-200" />,
                                li: ({ node, ...props }) => <li {...props} className="mb-1 text-slate-200" />,
                                strong: ({ node, ...props }) => <strong {...props} className="text-white font-semibold" />,
                                code: ({ node, ...props }) => <code {...props} className="bg-dark-700 px-1.5 py-0.5 rounded text-primary-300 text-xs" />,
                            }}
                        >
                            {displayContent}
                        </ReactMarkdown>
                    </div>

                    {/* 複製按鈕 */}
                    {!isUser && (
                        <button
                            onClick={handleCopy}
                            className="absolute top-2 right-2 p-1.5 text-slate-500 hover:text-slate-300 hover:bg-dark-600 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                            title="複製內容"
                        >
                            {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                        </button>
                    )}

                    <div className={`text-[10px] mt-2 ${isUser ? 'text-right text-white/50' : 'text-slate-500'}`}>
                        {msg.timestamp}
                    </div>
                </div>

                {/* 思維鏈顯示區域 */}
                {!isUser && thinkContent && (
                    <div className="w-full bg-amber-500/10 rounded-xl p-3 border border-amber-500/20">
                        <button
                            onClick={() => setShowThink(!showThink)}
                            className="flex items-center justify-between w-full text-[11px] font-bold text-amber-400 hover:text-amber-300 transition-colors"
                        >
                            <span className="flex items-center gap-1.5 uppercase tracking-wider">
                                <Brain className="w-3.5 h-3.5" /> 思考過程 (Chain of Thought)
                            </span>
                            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showThink ? 'rotate-180' : ''}`} />
                        </button>

                        {showThink && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                className="mt-3 overflow-hidden"
                            >
                                <div className="p-3 bg-dark-800 rounded-lg border border-dark-600 text-xs text-slate-300 leading-relaxed whitespace-pre-wrap font-mono">
                                    {thinkContent}
                                </div>
                            </motion.div>
                        )}
                    </div>
                )}

                {/* RAG 特有資訊：重寫查詢與來源 */}
                {!isUser && (msg.rewritten_query || msg.context) && (
                    <div className="w-full bg-dark-800/50 rounded-xl p-3 border border-dark-600">
                        <button
                            onClick={() => setShowRAG(!showRAG)}
                            className="flex items-center justify-between w-full text-[11px] font-bold text-slate-400 hover:text-primary-400 transition-colors"
                        >
                            <span className="flex items-center gap-1.5 uppercase tracking-wider">
                                <BookOpen className="w-3.5 h-3.5" /> 檢索思維鏈 (RAG Insights)
                            </span>
                            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showRAG ? 'rotate-180' : ''}`} />
                        </button>

                        {showRAG && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                className="mt-3 space-y-3 overflow-hidden"
                            >
                                {msg.rewritten_query && (
                                    <div className="p-3 bg-dark-900 rounded-lg border border-dark-700">
                                        <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">優化後的查詢</p>
                                        <p className="text-xs text-primary-300 italic">"{msg.rewritten_query}"</p>
                                    </div>
                                )}
                                {msg.context && (
                                    <div className="p-3 bg-dark-900 rounded-lg border border-dark-700">
                                        <p className="text-[10px] text-slate-500 font-bold uppercase mb-1">參考依據</p>
                                        <p className="text-[11px] text-slate-300 line-clamp-none leading-relaxed whitespace-pre-wrap">
                                            {msg.context}
                                        </p>
                                    </div>
                                )}
                            </motion.div>
                        )}
                    </div>
                )}
            </div>

            {isUser && (
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-slate-600 to-slate-700 flex items-center justify-center shadow-lg flex-shrink-0">
                    <User className="w-5 h-5 text-white" />
                </div>
            )}
        </motion.div>
    );
}
