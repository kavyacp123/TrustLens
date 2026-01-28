import { useAnalysis } from '../context/AnalysisContext';
import { FileText, Download, Share2, Shield, CheckCircle2, AlertTriangle, Info, Brain, Activity, Code2, Globe, Layers, Cpu, ChevronDown, ChevronUp, Copy, Check, Zap, BarChart3 } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useState, useEffect } from 'react';

const ReportPageFull = () => {
    const { report, results, status, analysisId, repoMetadata } = useAnalysis();
    const [expandedSections, setExpandedSections] = useState({
        security: true,
        logic: true,
        quality: true,
        feature: true,
        conflicts: false,
        rawJSON: false
    });
    const [showRawJSON, setShowRawJSON] = useState(false);
    const [rawReport, setRawReport] = useState(null);
    const [copied, setCopied] = useState(false);
    const [fullReport, setFullReport] = useState(null);
    const [loading, setLoading] = useState(true);

    // Fetch detailed report from API on mount
    useEffect(() => {
        const fetchFullReport = async () => {
            if (!analysisId) {
                setLoading(false);
                return;
            }
            
            try {
                const response = await fetch(`http://localhost:5000/api/analysis/report/${analysisId}`);
                if (response.ok) {
                    const data = await response.json();
                    setFullReport(data);
                    setRawReport(JSON.stringify(data, null, 2));
                }
            } catch (err) {
                console.warn('Failed to fetch detailed report:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchFullReport();
    }, [analysisId]);

    const toggleSection = (section) => {
        setExpandedSections(prev => ({
            ...prev,
            [section]: !prev[section]
        }));
    };

    const copyToClipboard = () => {
        navigator.clipboard.writeText(rawReport);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const getSeverityColor = (severity) => {
        switch (severity?.toLowerCase()) {
            case 'critical':
                return 'bg-red-500/20 text-red-400 border-red-500/30';
            case 'high':
                return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
            case 'medium':
                return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
            case 'low':
                return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
            default:
                return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
        }
    };

    const getRiskColor = (risk) => {
        switch (risk?.toLowerCase()) {
            case 'critical':
                return 'text-red-500';
            case 'high':
                return 'text-orange-500';
            case 'medium':
                return 'text-yellow-500';
            case 'low':
                return 'text-emerald-500';
            default:
                return 'text-slate-400';
        }
    };

    if (status === 'IDLE') return <div className="text-center py-20 text-slate-400">No report available. Start an analysis first.</div>;
    if (status === 'ANALYZING' || status === 'UPLOADING') return <div className="text-center py-20 text-slate-400">Analysis in progress...</div>;
    if (!report && !fullReport) return <div className="text-center py-20 text-slate-400">Report data not found.</div>;

    const displayReport = fullReport || report;
    const formattedDate = displayReport?.timestamp ? new Date(displayReport.timestamp).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    }) : new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    });

    return (
        <div className="max-w-7xl mx-auto py-12 px-4">
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Security Audit Report</h1>
                    <p className="text-slate-400 text-sm">Analysis ID: {analysisId?.substring(0, 16)}</p>
                    <p className="text-slate-500 text-xs mt-1">Generated on {formattedDate} • UTC</p>
                </div>
                <div className="flex gap-3">
                    <button className="flex items-center gap-2 px-4 py-2 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 text-sm transition-colors">
                        <Share2 className="w-4 h-4" /> Share
                    </button>
                    <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm transition-colors shadow-lg shadow-blue-500/20">
                        <Download className="w-4 h-4" /> Export PDF
                    </button>
                </div>
            </div>

            {/* Main Report Container */}
            <div className="space-y-6">
                {/* Executive Summary */}
                <div className="bg-white/5 border border-white/5 rounded-2xl overflow-hidden backdrop-blur-md">
                    <div className="p-8 border-b border-white/5 bg-gradient-to-r from-white/5 to-white/2">
                        <h2 className="text-2xl font-bold text-white mb-4">Executive Summary</h2>
                        <p className="text-slate-300 mb-6">{displayReport?.system_reasoning || "Multi-agent consensus analysis completed."}</p>
                        
                        {displayReport?.deferred && (
                            <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20 mb-6">
                                <div className="flex items-start gap-3">
                                    <AlertTriangle className="w-5 h-5 text-yellow-500 mt-0.5 flex-shrink-0" />
                                    <div>
                                        <h4 className="font-semibold text-yellow-400">Deferred Analysis</h4>
                                        <p className="text-yellow-300/80 text-sm mt-1">{displayReport?.deferral_reason}</p>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="p-4 rounded-lg bg-slate-900/50 border border-white/5">
                                <div className="text-slate-500 text-xs mb-2">Final Decision</div>
                                <div className="text-white font-bold text-lg">{displayReport?.final_decision}</div>
                            </div>
                            <div className="p-4 rounded-lg bg-slate-900/50 border border-white/5">
                                <div className="text-slate-500 text-xs mb-2">Overall Risk</div>
                                <div className={`font-bold text-lg ${getRiskColor(displayReport?.overall_risk_level)}`}>
                                    {displayReport?.overall_risk_level?.toUpperCase()}
                                </div>
                            </div>
                            <div className="p-4 rounded-lg bg-slate-900/50 border border-white/5">
                                <div className="text-slate-500 text-xs mb-2">Confidence</div>
                                <div className="text-white font-bold text-lg">{Math.round((displayReport?.overall_confidence || 0) * 100)}%</div>
                            </div>
                            <div className="p-4 rounded-lg bg-slate-900/50 border border-white/5">
                                <div className="text-slate-500 text-xs mb-2">Consensus</div>
                                <div className={`font-bold text-lg ${displayReport?.disagreement_detected ? 'text-orange-400' : 'text-emerald-400'}`}>
                                    {displayReport?.disagreement_detected ? "Disputed" : "Unified"}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Code Metrics Summary */}
                {displayReport?.quality_summary?.metrics && (
                    <div className="bg-white/5 border border-white/5 rounded-2xl p-8 backdrop-blur-md">
                        <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                            <BarChart3 className="w-5 h-5 text-purple-400" />
                            Code Metrics & Analysis
                        </h2>
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                            <div className="p-4 rounded-lg bg-purple-500/10 border border-purple-500/20">
                                <div className="text-purple-300 text-xs mb-1">Total Lines</div>
                                <div className="text-2xl font-bold text-white">{displayReport.quality_summary.metrics.total_loc || 0}</div>
                                <div className="text-xs text-slate-400 mt-1">LoC</div>
                            </div>
                            <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                                <div className="text-blue-300 text-xs mb-1">Functions</div>
                                <div className="text-2xl font-bold text-white">{displayReport.quality_summary.metrics.function_count || 0}</div>
                                <div className="text-xs text-slate-400 mt-1">Count</div>
                            </div>
                            <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                                <div className="text-green-300 text-xs mb-1">Classes</div>
                                <div className="text-2xl font-bold text-white">{displayReport.quality_summary.metrics.class_count || 0}</div>
                                <div className="text-xs text-slate-400 mt-1">Count</div>
                            </div>
                            <div className="p-4 rounded-lg bg-orange-500/10 border border-orange-500/20">
                                <div className="text-orange-300 text-xs mb-1">Max Depth</div>
                                <div className="text-2xl font-bold text-white">{displayReport.quality_summary.metrics.max_nesting_depth || 0}</div>
                                <div className="text-xs text-slate-400 mt-1">Levels</div>
                            </div>
                            <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
                                <div className="text-red-300 text-xs mb-1">High Nesting</div>
                                <div className="text-2xl font-bold text-white">{displayReport.quality_summary.metrics.high_nesting_locations?.length || 0}</div>
                                <div className="text-xs text-slate-400 mt-1">Locations</div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Detailed Findings by Agent */}
                <div className="space-y-4">
                    {/* Security Findings */}
                    {displayReport?.security_findings && displayReport.security_findings.length > 0 && (
                        <div className="bg-white/5 border border-red-500/20 rounded-2xl overflow-hidden backdrop-blur-md">
                            <button
                                onClick={() => toggleSection('security')}
                                className="w-full p-6 flex items-center justify-between bg-red-500/5 hover:bg-red-500/10 transition-colors"
                            >
                                <div className="flex items-center gap-3">
                                    <Shield className="w-5 h-5 text-red-400" />
                                    <div className="text-left">
                                        <h3 className="text-lg font-bold text-white">Security Analysis</h3>
                                        <p className="text-red-300/70 text-sm">{displayReport.security_findings.length} findings</p>
                                    </div>
                                </div>
                                {expandedSections.security ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
                            </button>
                            
                            {expandedSections.security && (
                                <div className="p-6 space-y-4 border-t border-white/5">
                                    {displayReport.security_findings.map((finding, idx) => (
                                        <div key={idx} className="bg-slate-900/50 border border-red-500/20 rounded-lg p-4">
                                            <div className="flex items-start gap-3 mb-3">
                                                <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase border ${getSeverityColor(finding.severity)}`}>
                                                    {finding.severity || finding.type}
                                                </span>
                                                <div className="flex-1">
                                                    <h4 className="font-semibold text-white">{finding.title || finding.issue}</h4>
                                                    {finding.file && <p className="text-xs text-slate-400 mt-1">{finding.file}:{finding.line}</p>}
                                                </div>
                                            </div>
                                            <p className="text-sm text-slate-200 mb-3">{finding.description || finding.issue_description}</p>
                                            {finding.recommendation && <p className="text-sm text-emerald-300/80 italic">💡 {finding.recommendation}</p>}
                                            {finding.code && (
                                                <div className="mt-3 rounded-lg overflow-hidden border border-white/5">
                                                    <SyntaxHighlighter
                                                        language="python"
                                                        style={vscDarkPlus}
                                                        customStyle={{
                                                            margin: 0,
                                                            padding: '1rem',
                                                            fontSize: '0.75rem',
                                                            background: '#0a0c10'
                                                        }}
                                                        showLineNumbers={true}
                                                    >
                                                        {finding.code}
                                                    </SyntaxHighlighter>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Logic Findings */}
                    {displayReport?.logic_findings && displayReport.logic_findings.length > 0 && (
                        <div className="bg-white/5 border border-emerald-500/20 rounded-2xl overflow-hidden backdrop-blur-md">
                            <button
                                onClick={() => toggleSection('logic')}
                                className="w-full p-6 flex items-center justify-between bg-emerald-500/5 hover:bg-emerald-500/10 transition-colors"
                            >
                                <div className="flex items-center gap-3">
                                    <Brain className="w-5 h-5 text-emerald-400" />
                                    <div className="text-left">
                                        <h3 className="text-lg font-bold text-white">Logic Analysis</h3>
                                        <p className="text-emerald-300/70 text-sm">{displayReport.logic_findings.length} findings</p>
                                    </div>
                                </div>
                                {expandedSections.logic ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
                            </button>
                            
                            {expandedSections.logic && (
                                <div className="p-6 space-y-4 border-t border-white/5">
                                    {displayReport.logic_findings.map((finding, idx) => (
                                        <div key={idx} className="bg-slate-900/50 border border-emerald-500/20 rounded-lg p-4">
                                            <div className="flex items-start gap-3 mb-3">
                                                <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase border ${getSeverityColor(finding.severity)}`}>
                                                    {finding.severity || finding.type}
                                                </span>
                                                <div className="flex-1">
                                                    <h4 className="font-semibold text-white">{finding.title || finding.issue}</h4>
                                                    {finding.file && <p className="text-xs text-slate-400 mt-1">{finding.file}:{finding.line}</p>}
                                                </div>
                                            </div>
                                            <p className="text-sm text-slate-200 mb-3">{finding.description || finding.issue_description}</p>
                                            {finding.recommendation && <p className="text-sm text-emerald-300/80 italic">💡 {finding.recommendation}</p>}
                                            {finding.code && (
                                                <div className="mt-3 rounded-lg overflow-hidden border border-white/5">
                                                    <SyntaxHighlighter
                                                        language="python"
                                                        style={vscDarkPlus}
                                                        customStyle={{
                                                            margin: 0,
                                                            padding: '1rem',
                                                            fontSize: '0.75rem',
                                                            background: '#0a0c10'
                                                        }}
                                                        showLineNumbers={true}
                                                    >
                                                        {finding.code}
                                                    </SyntaxHighlighter>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Feature Findings */}
                    {displayReport?.feature_findings && displayReport.feature_findings.length > 0 && (
                        <div className="bg-white/5 border border-blue-500/20 rounded-2xl overflow-hidden backdrop-blur-md">
                            <button
                                onClick={() => toggleSection('feature')}
                                className="w-full p-6 flex items-center justify-between bg-blue-500/5 hover:bg-blue-500/10 transition-colors"
                            >
                                <div className="flex items-center gap-3">
                                    <Code2 className="w-5 h-5 text-blue-400" />
                                    <div className="text-left">
                                        <h3 className="text-lg font-bold text-white">Feature Analysis</h3>
                                        <p className="text-blue-300/70 text-sm">{displayReport.feature_findings.length} findings</p>
                                    </div>
                                </div>
                                {expandedSections.feature ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
                            </button>
                            
                            {expandedSections.feature && (
                                <div className="p-6 space-y-4 border-t border-white/5">
                                    {displayReport.feature_findings.map((finding, idx) => (
                                        <div key={idx} className="bg-slate-900/50 border border-blue-500/20 rounded-lg p-4">
                                            <div className="flex items-start gap-3 mb-3">
                                                <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase border ${getSeverityColor(finding.severity)}`}>
                                                    {finding.severity || finding.type}
                                                </span>
                                                <div className="flex-1">
                                                    <h4 className="font-semibold text-white">{finding.title || finding.feature}</h4>
                                                    {finding.file && <p className="text-xs text-slate-400 mt-1">{finding.file}</p>}
                                                </div>
                                            </div>
                                            <p className="text-sm text-slate-200">{finding.description}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Conflicts Section */}
                {displayReport?.conflicts && displayReport.conflicts.length > 0 && (
                    <div className="bg-white/5 border border-orange-500/20 rounded-2xl overflow-hidden backdrop-blur-md">
                        <button
                            onClick={() => toggleSection('conflicts')}
                            className="w-full p-6 flex items-center justify-between bg-orange-500/5 hover:bg-orange-500/10 transition-colors"
                        >
                            <div className="flex items-center gap-3">
                                <AlertTriangle className="w-5 h-5 text-orange-400" />
                                <div className="text-left">
                                    <h3 className="text-lg font-bold text-white">Agent Disagreements</h3>
                                    <p className="text-orange-300/70 text-sm">{displayReport.conflicts.length} conflicts detected</p>
                                </div>
                            </div>
                            {expandedSections.conflicts ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
                        </button>
                        
                        {expandedSections.conflicts && (
                            <div className="p-6 space-y-4 border-t border-white/5">
                                {displayReport.conflicts.map((conflict, idx) => (
                                    <div key={idx} className="bg-slate-900/50 border border-orange-500/20 rounded-lg p-4">
                                        <h4 className="font-semibold text-white mb-2">{conflict.finding_title}</h4>
                                        <div className="space-y-2 text-sm">
                                            {conflict.agents && Object.entries(conflict.agents).map(([agent, opinion], i) => (
                                                <div key={i} className="flex gap-2">
                                                    <span className="text-orange-300 font-mono">{agent}:</span>
                                                    <span className="text-slate-300">{opinion}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Raw JSON Viewer */}
                <div className="bg-white/5 border border-white/5 rounded-2xl overflow-hidden backdrop-blur-md">
                    <button
                        onClick={() => toggleSection('rawJSON')}
                        className="w-full p-6 flex items-center justify-between bg-white/5 hover:bg-white/10 transition-colors"
                    >
                        <div className="flex items-center gap-3">
                            <Code2 className="w-5 h-5 text-slate-400" />
                            <h3 className="text-lg font-bold text-white">Raw Report Data (JSON)</h3>
                        </div>
                        {expandedSections.rawJSON ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
                    </button>
                    
                    {expandedSections.rawJSON && (
                        <div className="p-6 border-t border-white/5">
                            <button
                                onClick={copyToClipboard}
                                className="mb-4 flex items-center gap-2 px-3 py-1 rounded bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm transition-colors"
                            >
                                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                                {copied ? 'Copied!' : 'Copy JSON'}
                            </button>
                            <div className="rounded-lg overflow-hidden border border-white/5 max-h-96 overflow-y-auto">
                                <SyntaxHighlighter
                                    language="json"
                                    style={vscDarkPlus}
                                    customStyle={{
                                        margin: 0,
                                        padding: '1rem',
                                        fontSize: '0.75rem',
                                        background: '#0a0c10'
                                    }}
                                    showLineNumbers={true}
                                >
                                    {rawReport || '{}'}
                                </SyntaxHighlighter>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ReportPageFull;
