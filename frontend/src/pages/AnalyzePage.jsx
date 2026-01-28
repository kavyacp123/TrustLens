import React, { useState } from 'react';
import InputPanel from '../components/InputPanel';
import { useNavigate } from 'react-router-dom';
import { Shield, Zap, Info } from 'lucide-react';
import clsx from 'clsx';
import { motion } from 'framer-motion';
import { useAnalysis } from '../context/AnalysisContext';

const AnalyzePage = () => {
    const { startAnalysis } = useAnalysis();
    const navigate = useNavigate();
    const [analysisType, setAnalysisType] = useState('deep');
    const [allowSuggestions, setAllowSuggestions] = useState(false);

    const handleStart = (input) => {
        startAnalysis(input, analysisType, allowSuggestions);
        navigate('/session/new');
    };

    return (
        <div className="container mx-auto px-4 py-8">
            <div className="max-w-2xl mx-auto py-12">
                <div className="text-center mb-10">
                    <h2 className="text-3xl font-bold text-white mb-3">Begin Code Analysis</h2>
                    <p className="text-slate-400">Configure your analysis parameters.</p>
                </div>

                <InputPanel onStartAnalysis={handleStart} isAnalyzing={false} />

                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6 w-full px-4"
                >
                    
                  
                </motion.div>
            </div>
        </div>
    );
};

export default AnalyzePage;
