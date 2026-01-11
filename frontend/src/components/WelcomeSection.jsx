import React from 'react';
import { motion } from 'framer-motion';
import { Bot, Sparkles } from 'lucide-react';

export function WelcomeSection({ onSelectExample }) {
    const examples = ['事假可以請幾天？', '特休假計算方式', '加班費計算基準', '忘記打卡怎麼補救？'];

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center py-20 text-center"
        >
            <div className="w-20 h-20 bg-gradient-to-br from-primary-500 to-primary-600 rounded-3xl flex items-center justify-center mb-6 shadow-2xl shadow-primary-500/30">
                <Sparkles className="w-10 h-10 text-white" />
            </div>
            <h2 className="text-3xl font-extrabold text-white mb-2">您好，我是差勤助手</h2>
            <p className="text-slate-400 max-w-md mb-10 leading-relaxed">
                我可以幫您查詢公司規章、計算請假時數或解答各項勞基法相關問題。
            </p>

            <div className="grid grid-cols-2 gap-3 w-full max-w-xl">
                {examples.map((ex, i) => (
                    <button
                        key={i}
                        onClick={() => onSelectExample(ex)}
                        className="p-4 bg-dark-800 border border-dark-600 rounded-2xl text-left hover:border-primary-500/50 hover:bg-dark-700 hover:shadow-lg hover:shadow-primary-500/10 transition-all group"
                    >
                        <p className="text-sm font-semibold text-slate-200 group-hover:text-primary-400 transition-colors">{ex}</p>
                        <p className="text-[11px] text-slate-500 mt-1">點擊立即詢問</p>
                    </button>
                ))}
            </div>
        </motion.div>
    );
}
