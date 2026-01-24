"""
Multi-Agent AI System for Risk-Aware Code Review
Main entry point for the system.
"""

import json
import sys
from orchestrator.orchestrator import Orchestrator
from storage.s3_reader import S3Reader
from storage.s3_uploader import S3Uploader
from utils.logger import Logger


def verify_s3_ready() -> bool:
    """
    Verify S3 bucket is accessible before starting analysis.
    
    Returns:
        True if S3 is ready, False otherwise
    """
    logger = Logger("Main")
    try:
        logger.info("🔍 Verifying S3 connectivity...")
        
        reader = S3Reader()
        uploader = S3Uploader()
        
        # Test reader connection
        if not reader.use_mock:
            reader._test_connection()
            logger.info("✅ S3 Reader: Connected")
        else:
            logger.warning("⚠️ S3 Reader: Using MOCK mode")
        
        # Test uploader connection
        if not uploader.use_mock:
            uploader._verify_bucket()
            logger.info("✅ S3 Uploader: Connected")
        else:
            logger.warning("⚠️ S3 Uploader: Using MOCK mode")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ S3 verification failed: {e}")
        logger.error("Please check your AWS credentials and S3 configuration")
        return False


def main():
    """
    Main entry point for code review system.
    """
    logger = Logger("Main")
    logger.info("Multi-Agent Code Review System Starting")
    
    # Verify S3 is ready
    if not verify_s3_ready():
        logger.error("❌ S3 is not ready. Please configure AWS credentials in .env file")
        sys.exit(1)
    
    # Configuration
    config = {
        "min_confidence": 0.7,
        "security_config": {
            "max_snippet_length": 500
        },
        "logic_config": {
            "max_snippet_length": 600
        },
        "quality_config": {
            "thresholds": {
                "max_function_length": 50,
                "max_file_length": 500,
                "min_comment_ratio": 0.1,
                "max_complexity": 10
            }
        },
        "decision_config": {
            "min_confidence": 0.7
        }
    }
    
    # Initialize orchestrator
    orchestrator = Orchestrator(config)
    
    # Example analysis
    # In production: get repo_url and s3_path from command line or API
    repo_url = "https://github.com/example/repo"
    s3_path = "s3://code-review-bucket/repo-snapshot-2024/"
    
    logger.info(f"Analyzing repository: {repo_url}")
    logger.info(f"S3 snapshot: {s3_path}")
    
    # Run analysis
    try:
        report = orchestrator.analyze_repository(repo_url, s3_path)
        
        # Output report
        print("\n" + "="*80)
        print("CODE REVIEW REPORT")
        print("="*80)
        print(f"\nRepository: {report.repository_url}")
        print(f"S3 Path: {report.s3_snapshot_path}")
        print(f"Timestamp: {report.timestamp}")
        print(f"\nOverall Confidence: {report.overall_confidence:.2f}")
        print(f"Overall Risk Level: {report.overall_risk_level.value}")
        print(f"\nRecommendation: {report.recommendation}")
        print(f"Action: {report.action_recommended}")
        
        if report.deferred:
            print(f"\n⚠️  DEFERRED: {report.deferral_reason}")
        
        if report.conflicts:
            print(f"\n⚠️  CONFLICTS DETECTED: {len(report.conflicts)} conflicts")
            for i, conflict in enumerate(report.conflicts, 1):
                print(f"\n  Conflict {i}:")
                print(f"    Agents: {', '.join(conflict.agents_involved)}")
                print(f"    Disagreement: {conflict.disagreement_level:.2f}")
        
        print(f"\n\nAgent Outputs ({len(report.agent_outputs)}):")
        for output in report.agent_outputs:
            print(f"\n  - {output.agent_type.value}")
            print(f"    Success: {output.success}")
            print(f"    Confidence: {output.confidence:.2f}")
            print(f"    Risk Level: {output.risk_level.value}")
            print(f"    Findings: {len(output.findings)}")
            
            if output.findings:
                for finding in output.findings[:3]:  # Show first 3
                    print(f"      • {finding}")
        
        # Save report to JSON
        report_dict = report.to_dict()
        with open("code_review_report.json", "w") as f:
            json.dump(report_dict, f, indent=2, default=str)
        
        logger.info("Report saved to code_review_report.json")
        
        print("\n" + "="*80)
        print("Report saved to: code_review_report.json")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error("Analysis failed", exception=e)
        print(f"\n❌ Analysis failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
