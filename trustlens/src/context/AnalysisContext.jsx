import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { ANALYSIS_STEPS, APP_CONFIG } from '../utils/constants';

const AnalysisContext = createContext(null);

export const useAnalysis = () => useContext(AnalysisContext);

export const AnalysisProvider = ({ children }) => {
    const [status, setStatus] = useState('IDLE'); // IDLE, UPLOADING, ANALYZING, COMPLETE, FAILED
    const [currentStepId, setCurrentStepId] = useState(0);
    const [completedMeasurements, setCompletedMeasurements] = useState([]);
    const [results, setResults] = useState(null);
    const [analysisType, setAnalysisType] = useState('deep');
    const [allowSuggestions, setAllowSuggestions] = useState(false);
    const [analysisId, setAnalysisId] = useState(null);
    const [error, setError] = useState(null);
    const [report, setReport] = useState(null);
    const [reliability, setReliability] = useState(null);
    const [agents, setAgents] = useState([]);

    const pollingIntervalRef = useRef(null);

    const startAnalysis = async (input, type = 'deep', suggestions = false) => {
        try {
            setError(null);
            setStatus('UPLOADING');
            setResults(null);
            setCurrentStepId(0);
            setCompletedMeasurements([]);
            setAnalysisType(type);
            setAllowSuggestions(suggestions);

            let currentAnalysisId = null;

            // 1. Ingestion
            if (input.startsWith('http')) {
                const response = await fetch(`${APP_CONFIG.API_BASE_URL}/repos/from-github`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ repo_url: input, branch: 'main' })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.message || 'GitHub clone failed');
                currentAnalysisId = data.analysis_id;
            } else {
                // If not a URL, treat as direct code snippet
                const response = await fetch(`${APP_CONFIG.API_BASE_URL}/repos/snippet`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        code: input,
                        language: 'python' // In production, added language detection or a dropdown
                    })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.message || 'Snippet upload failed');
                currentAnalysisId = data.analysis_id;
            }

            setAnalysisId(currentAnalysisId);

            // 2. Start Analysis
            const startResponse = await fetch(`${APP_CONFIG.API_BASE_URL}/analysis/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    analysis_id: currentAnalysisId,
                    config: {
                        min_confidence: 0.7,
                        enable_security: true,
                        enable_logic: true,
                        enable_quality: true
                    }
                })
            });
            const startData = await startResponse.json();
            if (!startResponse.ok) throw new Error(startData.message || 'Analysis start failed');

            setStatus('ANALYZING');
            startPolling(currentAnalysisId);

        } catch (err) {
            console.error("Analysis Error:", err);
            setError(err.message);
            setStatus('FAILED');
        }
    };

    const startPolling = (id) => {
        if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);

        pollingIntervalRef.current = setInterval(async () => {
            try {
                const response = await fetch(`${APP_CONFIG.API_BASE_URL}/analysis/status/${id}`);
                const data = await response.json();

                if (data.status === 'COMPLETED') {
                    clearInterval(pollingIntervalRef.current);
                    fetchResults(id);
                } else if (data.status === 'FAILED') {
                    clearInterval(pollingIntervalRef.current);
                    setStatus('FAILED');
                    setError(data.message || 'Analysis failed');
                } else {
                    // Update progress if available
                    // data.progress could be used to set currentStepId or something
                }
            } catch (err) {
                console.error("Polling error:", err);
            }
        }, 2000);
    };

    const fetchResults = async (id) => {
        try {
            // Fetch multiple datasets in parallel
            const [reportRes, agentsRes, reliabilityRes] = await Promise.all([
                fetch(`${APP_CONFIG.API_BASE_URL}/analysis/report/${id}`),
                fetch(`${APP_CONFIG.API_BASE_URL}/analysis/agents/${id}`),
                fetch(`${APP_CONFIG.API_BASE_URL}/analysis/reliability/${id}`)
            ]);

            const reportData = await reportRes.json();
            const agentsData = await agentsRes.json();
            const reliabilityData = await reliabilityRes.json();

            setReport(reportData);
            setAgents(agentsData.agents || []);
            setReliability(reliabilityData);

            // Map agent results for the frontend components
            const mappedResults = (agentsData.agents || []).map(a => {
                const agentFindings = getDetailedFindings(a.agent, reportData);
                const prettyName = a.agent
                    .split('_')
                    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                    .join(' ');

                return {
                    name: prettyName,
                    risk: a.risk_level,
                    confidence: Math.round(a.confidence * 100),
                    findingsCount: a.findings_count,
                    summary: getAgentSummary(a.agent, reportData),
                    findings: agentFindings
                };
            });

            setResults(mappedResults);
            setStatus('COMPLETE');
        } catch (err) {
            console.error("Fetch results error:", err);
            setStatus('FAILED');
            setError("Failed to fetch analysis results");
        }
    };

    const getDetailedFindings = (agentId, report) => {
        const id = agentId.toLowerCase();
        if (id.includes('security')) return report.security_findings || [];
        if (id.includes('logic')) return report.logic_findings || [];
        if (id.includes('quality')) return report.quality_summary?.findings || [];
        if (id.includes('feature')) return report.feature_findings || []; // We'll add this to backend
        return [];
    };

    const getAgentSummary = (agentId, report) => {
        const id = agentId.toLowerCase();
        if (id.includes('security')) {
            return report.security_findings?.[0]?.description || "No major security vulnerabilities detected.";
        }
        if (id.includes('logic')) {
            return report.logic_findings?.[0]?.description || "Code logic appears consistent with defined patterns.";
        }
        if (id.includes('quality')) {
            const score = Math.round(report.quality_summary?.quality_score * 100) || 0;
            return `Code quality score: ${score}%. ${report.quality_summary?.findings?.[0]?.description || "Maintainability is within expected parameters."}`;
        }
        if (id.includes('feature')) {
            return `Identified ${report.quality_summary?.metrics?.total_loc || 'several'} lines across ${report.quality_summary?.metrics?.languages?.join(', ') || 'multiple'} files.`;
        }
        return `Detailed analysis complete for ${agentId}.`;
    };

    const resetAnalysis = () => {
        if (pollingIntervalRef.current) clearInterval(pollingIntervalRef.current);
        setStatus('IDLE');
        setResults(null);
        setCurrentStepId(0);
        setCompletedMeasurements([]);
        setAnalysisId(null);
        setError(null);
        setReport(null);
        setReliability(null);
        setAgents([]);
    };

    return (
        <AnalysisContext.Provider value={{
            status,
            currentStepId,
            completedMeasurements,
            results,
            overall: report ? {
                risk: report.overall_risk_level,
                confidence: report.overall_confidence,
                summary: report.system_reasoning
            } : null,
            analysisType,
            allowSuggestions,
            analysisId,
            error,
            report,
            reliability,
            agents,
            startAnalysis,
            resetAnalysis
        }}>
            {children}
        </AnalysisContext.Provider>
    );
};
