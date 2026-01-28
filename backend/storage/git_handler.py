"""
Git to S3 Workflow
Complete orchestration of cloning Git repos and uploading extracted snippets to S3
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime

from storage.git_handler import GitHandler
from storage.s3_uploader import S3Uploader
from storage.snippet_extractor import SnippetExtractor
from utils.logger import Logger


class GitS3Workflow:
    """
    Complete workflow:
    1. Validate repo
    2. Clone Git repo
    3. Extract snippets
    4. Upload snippets + metadata to S3
    5. Cleanup local files
    """

    def __init__(self):
        self.logger = Logger("GitS3Workflow")
        self.git_handler = GitHandler()
        self.s3_uploader = S3Uploader()
        self.snippet_extractor = SnippetExtractor()
        self.workflow_history: Dict[str, Any] = {}

    # -------------------------
    # Public API
    # -------------------------

    def process_git_repository(
        self,
        repo_url: str,
        analysis_id: str,
        branch: str = "main",
        shallow: bool = False,
        extract_snippets: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        workflow_result = {
            "analysis_id": analysis_id,
            "repo_url": repo_url,
            "branch": branch,
            "status": "INITIALIZED",
            "stages": {},
            "started_at": datetime.utcnow().isoformat(),
        }

        local_repo_path = None

        try:
            self.logger.info(f"🚀 Starting Git-S3 workflow: {analysis_id}")

            # ---- Preflight ----
            repo_url = self._inject_auth(repo_url)
            self._preflight_checks(repo_url, branch)

            # ---- Stage 1: Clone ----
            clone_result = self._stage_clone(repo_url, branch, shallow)
            workflow_result["stages"]["clone"] = clone_result

            if not clone_result["success"]:
                return self._fail(workflow_result, clone_result["error"])

            local_repo_path = clone_result["local_path"]
            repo_info = clone_result.get("repo_info", {})

            # ---- Stage 2: Extract ----
            snippets = {}
            if extract_snippets:
                extraction_result = self._stage_extract_snippets(local_repo_path)
                workflow_result["stages"]["extraction"] = extraction_result

                if not extraction_result["success"]:
                    return self._fail(workflow_result, "Snippet extraction failed")

                snippets = extraction_result["snippets"]

            # ---- Stage 3: Upload ----
            upload_result = self._stage_upload_to_s3(
                analysis_id=analysis_id,
                repo_url=repo_url,
                branch=branch,
                repo_info=repo_info,
                snippets=snippets,
                metadata=metadata,
            )
            workflow_result["stages"]["upload"] = upload_result

            if not upload_result["success"]:
                return self._fail(workflow_result, upload_result["error"])

            # ---- Stage 4: Cleanup ----
            cleanup_result = self._stage_cleanup(local_repo_path)
            workflow_result["stages"]["cleanup"] = cleanup_result

            workflow_result["status"] = "COMPLETED"
            workflow_result["s3_path"] = upload_result["s3_path"]
            workflow_result["completed_at"] = datetime.utcnow().isoformat()

            self.workflow_history[analysis_id] = workflow_result
            self.logger.info(f"✅ Workflow completed: {analysis_id}")

            return workflow_result

        except Exception as e:
            self.logger.error(f"❌ Workflow crashed: {e}")
            if local_repo_path:
                self._safe_cleanup(local_repo_path)

            workflow_result["status"] = "FAILED"
            workflow_result["error"] = str(e)
            workflow_result["completed_at"] = datetime.utcnow().isoformat()
            return workflow_result

    # -------------------------
    # Internal helpers
    # -------------------------

    def _inject_auth(self, repo_url: str) -> str:
        """
        Inject GitHub token for private repos
        """
        token = os.getenv("GITHUB_TOKEN")
        if token and repo_url.startswith("https://"):
            return repo_url.replace("https://", f"https://{token}@")
        return repo_url

    def _preflight_checks(self, repo_url: str, branch: str):
        """
        Fail fast before cloning
        """
        self.logger.info("🔍 Running preflight checks")

        if not self.git_handler.git_available():
            raise RuntimeError("git binary not available on system")

        if not self.git_handler.repo_exists(repo_url):
            raise RuntimeError("Repository not reachable or auth failed")

        if not self.git_handler.branch_exists(repo_url, branch):
            raise RuntimeError(f"Branch '{branch}' does not exist")

    # -------------------------
    # Workflow stages
    # -------------------------

    def _stage_clone(self, repo_url: str, branch: str, shallow: bool) -> Dict[str, Any]:
        self.logger.info("📥 Stage 1: Cloning repository")

        depth = 1 if shallow else None

        result = self.git_handler.clone_repository(
            repo_url=repo_url,
            branch=branch,
            depth=depth,
        )

        if result["success"]:
            self.logger.info(f"✅ Clone successful: {result['local_path']}")
        else:
            self.logger.error(f"❌ Clone failed: {result['error']}")

        return result

    def _stage_extract_snippets(self, local_repo_path: str) -> Dict[str, Any]:
        self.logger.info("📝 Stage 2: Extracting snippets")

        try:
            snippets = self.snippet_extractor.extract_from_directory(local_repo_path)

            if not snippets:
                raise ValueError("No snippets extracted")

            return {
                "success": True,
                "snippet_count": sum(len(v) for v in snippets.values()),
                "snippets": snippets,
            }

        except Exception as e:
            self.logger.error(f"❌ Extraction failed: {e}")
            return {"success": False, "error": str(e)}

    def _stage_upload_to_s3(
        self,
        analysis_id: str,
        repo_url: str,
        branch: str,
        repo_info: Dict[str, Any],
        snippets: Dict[str, Any],
        metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:

        self.logger.info("☁️ Stage 3: Uploading snippets to S3")

        try:
            project_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")

            metadata_obj = {
                "analysis_id": analysis_id,
                "project_name": project_name,
                "repo_url": repo_url,
                "branch": branch,
                "repo_info": repo_info,
                "snippet_count": sum(len(v) for v in snippets.values()),
                "custom_metadata": metadata or {},
            }

            s3_path = self.s3_uploader.upload_only_snippets(
                project_name=project_name,
                analysis_id=analysis_id,
                snippets=snippets,
                metadata=metadata_obj,
            )

            return {
                "success": True,
                "s3_path": s3_path,
            }

        except Exception as e:
            self.logger.error(f"❌ Upload failed: {e}")
            return {"success": False, "error": str(e)}

    def _stage_cleanup(self, local_repo_path: str) -> Dict[str, Any]:
        self.logger.info("🧹 Stage 4: Cleanup")

        try:
            self.git_handler.cleanup_by_path(local_repo_path)
            return {"success": True}
        except Exception as e:
            self.logger.warning(f"⚠️ Cleanup failed: {e}")
            return {"success": False, "error": str(e)}

    # -------------------------
    # Safety helpers
    # -------------------------

    def _safe_cleanup(self, path: str):
        try:
            self.git_handler.cleanup_by_path(path)
        except Exception:
            pass

    def _fail(self, workflow_result: Dict[str, Any], error: str):
        workflow_result["status"] = "FAILED"
        workflow_result["error"] = error
        workflow_result["completed_at"] = datetime.utcnow().isoformat()
        return workflow_result


# Singleton
git_s3_workflow = GitS3Workflow()
