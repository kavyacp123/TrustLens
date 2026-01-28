"""
Complete End-to-End Test
Tests the entire flow: Git Clone → Snippet Extraction → S3 Upload → Analysis → Report
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
load_dotenv()

from utils.logger import Logger
from storage.git_s3_workflow import GitS3Workflow
from orchestrator.orchestrator import Orchestrator
from api.controllers import CodeReviewController

logger = Logger("FullFlowTest")

def print_section(title):
    """Print a section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def test_full_flow():
    """Test complete workflow"""
    
    print_section("🚀 TRUSTLENS - FULL END-TO-END TEST")
    print(f"Started at: {datetime.now().isoformat()}")
    
    # Configuration
    repo_url = "https://github.com/kavyacp123/test-demo.git"
    analysis_id = f"test-debug-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    branch = "main"
    
    print(f"\n📋 Test Configuration:")
    print(f"   Repository: {repo_url}")
    print(f"   Analysis ID: {analysis_id}")
    print(f"   Branch: {branch}")
    
    try:
        # ============================================================================
        # STAGE 1: GIT CLONE & SNIPPET EXTRACTION
        # ============================================================================
        print_section("STAGE 1: GIT CLONE & SNIPPET EXTRACTION")
        
        git_s3_workflow = GitS3Workflow()
        
        logger.info(f"🔄 Starting Git-S3 Workflow for {analysis_id}")
        
        workflow_result = git_s3_workflow.process_git_repository(
            repo_url=repo_url,
            analysis_id=analysis_id,
            branch=branch,
            shallow=False,
            extract_snippets=True,
            metadata={}
        )
        
        print(f"\n✅ Workflow Result:")
        print(f"   Status: {workflow_result.get('status')}")
        print(f"   S3 Path: {workflow_result.get('s3_path')}")
        
        if workflow_result['status'] != 'COMPLETED':
            logger.error(f"❌ Workflow failed: {workflow_result.get('error')}")
            print(f"\n❌ Workflow failed: {workflow_result.get('error')}")
            return
        
        s3_path = workflow_result['s3_path']
        
        print(f"\n📊 Workflow Statistics:")
        stats = workflow_result.get('statistics', {})
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # ============================================================================
        # STAGE 2: ORCHESTRATOR ANALYSIS
        # ============================================================================
        print_section("STAGE 2: ORCHESTRATOR ANALYSIS")
        
        orchestrator = Orchestrator({
            "min_confidence": 0.7,
            "security_config": {"max_snippet_length": 500},
            "logic_config": {"max_snippet_length": 600},
            "quality_config": {
                "thresholds": {
                    "max_function_length": 50,
                    "max_file_length": 500,
                    "min_comment_ratio": 0.1,
                    "max_complexity": 10
                }
            },
            "decision_config": {"min_confidence": 0.7}
        })
        
        logger.info(f"🎯 Starting analysis for {repo_url}")
        
        report = orchestrator.analyze_repository(repo_url, s3_path)
        
        # ============================================================================
        # STAGE 3: DISPLAY RESULTS
        # ============================================================================
        print_section("STAGE 3: ANALYSIS RESULTS")
        
        print(f"\n📋 Report Summary:")
        print(f"   Repository: {report.repository_url}")
        print(f"   Analysis ID: {analysis_id}")
        print(f"   Timestamp: {report.timestamp}")
        print(f"   Overall Confidence: {report.overall_confidence:.2%}")
        print(f"   Overall Risk Level: {report.overall_risk_level.value}")
        print(f"   Recommendation: {report.recommendation}")
        print(f"   Action: {report.action_recommended}")
        
        if report.deferred:
            print(f"\n⚠️  DEFERRED: {report.deferral_reason}")
        
        # ============================================================================
        # AGENT OUTPUTS
        # ============================================================================
        print_section("AGENT OUTPUTS")
        
        for i, output in enumerate(report.agent_outputs, 1):
            print(f"\n{i}. {output.agent_type.value.upper()}")
            print(f"   Success: {output.success}")
            print(f"   Confidence: {output.confidence:.2%}")
            print(f"   Risk Level: {output.risk_level.value}")
            
            if output.findings:
                print(f"   Findings ({len(output.findings)}):")
                for finding in output.findings[:3]:  # Show first 3
                    severity = finding.get('severity', 'unknown')
                    desc = finding.get('description', '')[:100]
                    print(f"      - [{severity.upper()}] {desc}...")
                if len(output.findings) > 3:
                    print(f"      ... and {len(output.findings) - 3} more")
            
            # Show metadata with detailed info
            metadata = output.metadata or {}
            print(f"   Metadata Keys: {list(metadata.keys())}")
            
            # Special handling for quality metrics
            if output.agent_type.value == "code_quality":
                quality_metrics = metadata.get("quality_metrics", {})
                print(f"\n   📊 QUALITY METRICS DETAIL:")
                print(f"      Total LoC: {quality_metrics.get('total_loc', 0)}")
                print(f"      Function Count: {quality_metrics.get('function_count', 0)}")
                print(f"      Class Count: {quality_metrics.get('class_count', 0)}")
                print(f"      Max Nesting Depth: {quality_metrics.get('max_nesting_depth', 0)}")
                print(f"      Avg File Size: {quality_metrics.get('avg_file_size', 0)}")
                print(f"      All Keys: {list(quality_metrics.keys())}")
        
        # ============================================================================
        # CONFLICTS
        # ============================================================================
        if report.conflicts:
            print_section("CONFLICTS DETECTED")
            for i, conflict in enumerate(report.conflicts, 1):
                print(f"\n{i}. {' vs '.join(conflict.agents_involved)}")
                print(f"   Disagreement Level: {conflict.disagreement_level:.2%}")
                print(f"   Details: {conflict.details}")
        
        # ============================================================================
        # FULL JSON REPORT
        # ============================================================================
        print_section("FULL REPORT (JSON)")
        
        report_dict = {
            "repository_url": report.repository_url,
            "analysis_id": analysis_id,
            "timestamp": report.timestamp,
            "overall_confidence": report.overall_confidence,
            "overall_risk_level": report.overall_risk_level.value,
            "recommendation": report.recommendation,
            "action_recommended": report.action_recommended,
            "deferred": report.deferred,
            "deferral_reason": report.deferral_reason,
            "agent_outputs": []
        }
        
        for output in report.agent_outputs:
            output_dict = {
                "agent_type": output.agent_type.value,
                "success": output.success,
                "confidence": output.confidence,
                "risk_level": output.risk_level.value,
                "findings_count": len(output.findings or []),
                "metadata": output.metadata
            }
            report_dict["agent_outputs"].append(output_dict)
        
        print(json.dumps(report_dict, indent=2, default=str))
        
        # ============================================================================
        # FINAL SUMMARY
        # ============================================================================
        print_section("✅ TEST COMPLETED SUCCESSFULLY")
        
        print(f"\n📊 Final Summary:")
        print(f"   Analysis ID: {analysis_id}")
        print(f"   Status: SUCCESS")
        print(f"   Overall Confidence: {report.overall_confidence:.2%}")
        print(f"   Risk Level: {report.overall_risk_level.value}")
        print(f"   Agents Executed: {len(report.agent_outputs)}")
        print(f"   Total Findings: {sum(len(o.findings or []) for o in report.agent_outputs)}")
        
        print(f"\n⏱️  Completed at: {datetime.now().isoformat()}")
        
        return report
        
    except Exception as e:
        print_section("❌ TEST FAILED")
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        import traceback
        print(traceback.format_exc())
        return None

if __name__ == "__main__":
    report = test_full_flow()
    sys.exit(0 if report else 1)
