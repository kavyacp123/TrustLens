import requests
import json
import time
import sys

BASE_URL = "http://localhost:5000"

# List of repositories to test representing different languages/types
TEST_REPOS = [
    {
        "name": "Hello World (Basic Mix)",
        "url": "https://github.com/octocat/Hello-World",
        "branch": "master"
    },
    {
        "name": "Flask (Python)",
        "url": "https://github.com/pallets/flask",
        "branch": "main"
    },
    {
        "name": "Redux (TypeScript/JS)",
        "url": "https://github.com/reduxjs/redux",
        "branch": "master"
    }
]

def check_server_health():
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Server is reachable.")
            return True
    except requests.exceptions.ConnectionError:
        print("❌ Server is NOT reachable. Please make sure 'python run_api.py' is running.")
        return False
    return False

def run_test_for_repo(repo):
    print(f"\n{'='*60}")
    print(f"🧪 Testing Repo: {repo['name']}")
    print(f"🔗 URL: {repo['url']}")
    print(f"{'='*60}")

    # 1. Upload/Clone Repo
    print("➡️ 1. Submitting Repo for Ingestion...")
    try:
        resp = requests.post(f"{BASE_URL}/api/repos/from-github", json={
            "repo_url": repo['url'],
            "branch": repo['branch']
        })
        
        if resp.status_code != 201:
            print(f"❌ Failed to ingest repo. Status: {resp.status_code}")
            print(resp.text)
            return
        
        data = resp.json()
        analysis_id = data.get("analysis_id")
        print(f"✅ Repo Accepted. Analysis ID: {analysis_id}")
        
    except Exception as e:
        print(f"❌ Error during ingestion request: {e}")
        return

    # 2. Start Analysis
    print("➡️ 2. Starting Analysis...")
    try:
        resp = requests.post(f"{BASE_URL}/api/analysis/start", json={
            "analysis_id": analysis_id,
            "config": {"min_confidence": 0.6}
        })
        
        if resp.status_code != 202:
            print(f"❌ Failed to start analysis. Status: {resp.status_code}")
            print(resp.text)
            return
            
        print("✅ Analysis Started.")
    except Exception as e:
        print(f"❌ Error starting analysis: {e}")
        return

    # 3. Poll for Completion
    print("➡️ 3. Waiting for Results...")
    max_retries = 20
    for i in range(max_retries):
        try:
            resp = requests.get(f"{BASE_URL}/api/analysis/status/{analysis_id}")
            status_data = resp.json()
            status = status_data.get("status")
            
            sys.stdout.write(f"\r   ⏳ Status: {status} ({i+1}/{max_retries})")
            sys.stdout.flush()
            
            if status in ["COMPLETED", "FAILED", "DEFERRED"]:
                print(f"\n   🔄 Final Status: {status}")
                break
            
            time.sleep(2)
        except Exception as e:
            print(f"\n❌ Error polling status: {e}")
            break
    else:
        print("\n❌ Timed out waiting for analysis.")
        return

    # 4. Get Report
    print("➡️ 4. Fetching Report...")
    try:
        resp = requests.get(f"{BASE_URL}/api/analysis/report/{analysis_id}")
        if resp.status_code == 200:
            report = resp.json()
            print("\n📊 REPORT SUMMARY")
            print(f"   - Final Decision: {report.get('final_decision')}")
            print(f"   - Risk Level: {report.get('overall_risk_level')}")
            print(f"   - Confidence: {report.get('overall_confidence')}")
            print(f"   - Recommendation: {report.get('recommendation')}")
        else:
            print(f"❌ Failed to get report. Status: {resp.status_code}")
    except Exception as e:
        print(f"❌ Error fetching report: {e}")

def main():
    print("🚀 STARTING MULTI-REPO BACKEND TEST")
    if not check_server_health():
        return

    for repo in TEST_REPOS:
        run_test_for_repo(repo)
        time.sleep(2) # Brief pause between repos

    print(f"\n{'='*60}")
    print("✅ All Tests Finished")

if __name__ == "__main__":
    main()
