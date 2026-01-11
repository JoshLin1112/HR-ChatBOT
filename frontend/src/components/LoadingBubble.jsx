import React from 'react';
import { motion } from 'framer-motion';
import { Bot } from 'lucide-react';

export function LoadingBubble() {
    return (
        <div className="flex gap-4">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center shadow-lg shadow-primary-500/20">
                <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="bg-dark-800 border border-dark-600 px-5 py-4 rounded-2xl rounded-tl-sm shadow-lg flex gap-1.5 items-center">
                {[0, 1, 2].map((i) => (
                    <motion.div
                        key={i}
                        animate={{ scale: [1, 1.3, 1], opacity: [0.4, 1, 0.4] }}
                        transition={{ repeat: Infinity, duration: 1.2, delay: i * 0.15 }}
                        className="w-2 h-2 bg-primary-400 rounded-full"
                    />
                ))}
            </div>
        </div>
    );
}
