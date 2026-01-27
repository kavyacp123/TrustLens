"""
Git Repository Handler
Manages Git operations: clone, pull, branch handling
"""

import os
import shutil
import tempfile
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from utils.logger import Logger

try:
    import git
    from git import Repo
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


class GitHandler:
    """
    Handles Git operations for repository cloning and management.
    Supports GitHub, GitLab, Bitbucket, and self-hosted Git servers.
    """
    
    def __init__(self, base_temp_dir: Optional[str] = None):
        """
        Initialize Git handler.
        """
        self.logger = Logger("GitHandler")
        # Use a consistent writable path on Render/Linux
        self.base_temp_dir = base_temp_dir or '/tmp/trustlens_repos'
        
        # Ensure directory exists
        try:
            os.makedirs(self.base_temp_dir, exist_ok=True)
            self.logger.info(f"📂 Git workspace ready at: {self.base_temp_dir}")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not create custom temp dir: {e}. Falling back to system default.")
            self.base_temp_dir = tempfile.gettempdir()

        self.cloned_repos = {}  # Track cloned repositories
        
        if not GIT_AVAILABLE:
            self.logger.warning("GitPython not installed - some features will be limited")
        
        # Check Git installation on init
        self._check_git_installed()
    
    def _check_git_installed(self) -> bool:
        """
        Check if Git is installed and accessible.
        
        Returns:
            True if Git is available, False otherwise
        """
        try:
            import subprocess
            result = subprocess.run(['git', '--version'], capture_output=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.decode().strip()
                self.logger.info(f"✅ Git is installed: {version}")
                return True
            else:
                self.logger.error("❌ Git command failed - Git may not be in PATH")
                return False
        except FileNotFoundError:
            self.logger.error("❌ Git is NOT installed or not in PATH")
            self.logger.error("💡 FIX: Install Git - apt-get install -y git (Linux) or download from git-scm.com (Windows)")
            return False
        except Exception as e:
            self.logger.warning(f"⚠️ Could not verify Git installation: {e}")
            return False
    
    def validate_repo_url(self, repo_url: str) -> bool:
        """
        Validate Git repository URL format.
        
        Args:
            repo_url: Repository URL to validate
        
        Returns:
            True if valid, False otherwise
        """
        # Check if it's a valid Git URL
        valid_patterns = [
            'https://github.com/',
            'https://gitlab.com/',
            'https://bitbucket.org/',
            'git@github.com:',
            'git@gitlab.com:',
            'git@bitbucket.org:',
            'https://',
            'ssh://',
            'git://'
        ]
        
        is_valid = any(repo_url.startswith(pattern) for pattern in valid_patterns)
        
        if is_valid:
            self.logger.info(f"✅ Valid Git URL: {repo_url}")
        else:
            self.logger.error(f"❌ Invalid Git URL format: {repo_url}")
        
        return is_valid
    
    def extract_repo_name(self, repo_url: str) -> str:
        """
        Extract repository name from URL.
        
        Args:
            repo_url: Repository URL
        
        Returns:
            Repository name
        """
        # Handle both HTTPS and SSH URLs
        name = repo_url.rstrip('/').split('/')[-1]
        name = name.replace('.git', '')
        return name
    
    def clone_repository(
        self,
        repo_url: str,
        branch: str = "main",
        depth: Optional[int] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Clone a Git repository.
        
        Args:
            repo_url: Repository URL (HTTPS or SSH)
            branch: Branch to clone (default: main)
            depth: Shallow clone depth (for large repos)
            timeout: Operation timeout in seconds
        
        Returns:
            Dictionary with clone results
        """
        if not GIT_AVAILABLE:
            return {
                "success": False,
                "error": "GitPython not installed. Install with: pip install GitPython",
                "repo_url": repo_url
            }
        
        # Validate URL
        if not self.validate_repo_url(repo_url):
            return {
                "success": False,
                "error": f"Invalid repository URL: {repo_url}",
                "repo_url": repo_url
            }
        
        repo_name = self.extract_repo_name(repo_url)
        # Sanitize name and path
        safe_repo_name = "".join([c for c in repo_name if c.isalnum() or c in ('-', '_')])
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        clone_dir = os.path.join(self.base_temp_dir, f"repo-{safe_repo_name}-{timestamp}")
        
        try:
            # Handle Authentication (Use GITHUB_TOKEN if available)
            token = os.environ.get('GITHUB_TOKEN')
            if token and 'github.com' in repo_url:
                # Inject token: https://<token>@github.com/user/repo.git
                auth_url = repo_url.replace('https://', f'https://{token}@')
                self.logger.info(f"🔑 Using GITHUB_TOKEN for authentication")
            else:
                auth_url = repo_url

            self.logger.info(f"🔄 Starting clone: {repo_url}")
            
            # Prepare clone options
            clone_kwargs = {
                'to_path': clone_dir,
                'branch': branch,
                'progress': GitProgress(self.logger)
            }
            
            if depth:
                clone_kwargs['depth'] = depth
            
            # Clone repository
            repo = Repo.clone_from(auth_url, **clone_kwargs)
            
            # Verify clone
            if not os.path.exists(clone_dir):
                raise ValueError("Clone directory not created")
            
            # Get repo info
            repo_info = self._get_repo_info(repo, clone_dir)
            
            self.logger.info(f"✅ Successfully cloned: {repo_name}")
            return {
                "success": True,
                "repo_name": repo_name,
                "local_path": clone_dir,
                "repo_url": repo_url,
                "branch": branch,
                "repo_info": repo_info,
                "message": f"Successfully cloned {repo_name}"
            }
        
        except git.exc.GitCommandError as e:
            error_msg = str(e)
            self.logger.error(f"❌ Git clone failed: {error_msg}")
            
            # Mask token in error message if present
            if token:
                error_msg = error_msg.replace(token, "********")
                
            self._cleanup_dir(clone_dir)
            
            # Accurate Diagnosis
            if "authentication" in error_msg.lower() or "401" in error_msg or "403" in error_msg:
                diagnosis = "Authentication failed - Check if GITHUB_TOKEN is valid and has repo permissions"
            elif "not found" in error_msg.lower() or "404" in error_msg:
                diagnosis = "Repository not found - Verify the URL is correct"
            elif "exit code(128)" in error_msg and GIT_AVAILABLE:
                diagnosis = f"Git operation failed (Code 128). This is often a permission or network issue. Error: {error_msg.splitlines()[-1]}"
            else:
                diagnosis = "Git is not installed or not in PATH."
                
            self.logger.error(f"💡 DIAGNOSIS: {diagnosis}")
            
            return {
                "success": False,
                "error": diagnosis,
                "repo_url": repo_url,
                "details": error_msg
            }
        
        except Exception as e:
            self.logger.error(f"❌ Clone failed: {e}")
            self._cleanup_dir(clone_dir)
            
            # Diagnose common issues
            error_str = str(e).lower()
            if "no such file" in error_str or "directory" in error_str:
                self.logger.error("💡 DIAGNOSIS: Temp directory issue - cannot write to clone directory")
            elif "permission" in error_str:
                self.logger.error("💡 DIAGNOSIS: Permission denied - check folder permissions")
            
            return {
                "success": False,
                "error": str(e),
                "repo_url": repo_url
            }
    
    def _get_repo_info(self, repo: 'Repo', repo_path: str) -> Dict[str, Any]:
        """
        Get repository information.
        
        Args:
            repo: GitPython Repo object
            repo_path: Local path to repository
        
        Returns:
            Repository information dictionary
        """
        try:
            # Count commits
            commit_count = sum(1 for _ in repo.iter_commits(repo.active_branch))
            
            # Count files
            file_count = sum([len(files) for _, _, files in os.walk(repo_path)])
            
            # Get commit info
            latest_commit = repo.head.commit
            
            return {
                "commit_count": commit_count,
                "file_count": file_count,
                "latest_commit": latest_commit.hexsha[:7],
                "latest_author": latest_commit.author.name,
                "latest_message": latest_commit.message.split('\n')[0],
                "active_branch": repo.active_branch.name,
                "remote_url": repo.remote().url if repo.remote() else None
            }
        except Exception as e:
            self.logger.warning(f"Could not get full repo info: {e}")
            return {
                "commit_count": 0,
                "file_count": sum([len(files) for _, _, files in os.walk(repo_path)]),
                "latest_commit": "unknown",
                "latest_author": "unknown"
            }
    
    def get_clone_directory(self, repo_name: str) -> Optional[str]:
        """
        Get local path of cloned repository.
        
        Args:
            repo_name: Repository name
        
        Returns:
            Local path if exists, None otherwise
        """
        if repo_name in self.cloned_repos:
            return self.cloned_repos[repo_name]['local_path']
        return None
    
    def list_cloned_repos(self) -> Dict[str, Dict[str, Any]]:
        """
        List all cloned repositories.
        
        Returns:
            Dictionary of cloned repositories
        """
        return self.cloned_repos.copy()
    
    def cleanup_repository(self, repo_name: str, force: bool = False) -> bool:
        """
        Clean up cloned repository.
        
        Args:
            repo_name: Repository name to clean up
            force: Force cleanup even if errors occur
        
        Returns:
            True if successful, False otherwise
        """
        if repo_name not in self.cloned_repos:
            self.logger.warning(f"Repository not tracked: {repo_name}")
            return False
        
        repo_path = self.cloned_repos[repo_name]['local_path']
        
        if self._cleanup_dir(repo_path, force):
            del self.cloned_repos[repo_name]
            self.logger.info(f"✅ Cleaned up repository: {repo_name}")
            return True
        
        return False
    
    def _cleanup_dir(self, directory: str, force: bool = True) -> bool:
        """
        Delete a directory safely.
        
        Args:
            directory: Directory path to delete
            force: Force delete even if errors occur
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if os.path.exists(directory):
                shutil.rmtree(directory, ignore_errors=force)
                self.logger.info(f"Deleted directory: {directory}")
            return True
        except Exception as e:
            self.logger.error(f"Could not delete directory {directory}: {e}")
            return False
    
    def cleanup_all(self) -> bool:
        """
        Clean up all cloned repositories.
        
        Returns:
            True if all cleaned successfully
        """
        all_success = True
        for repo_name in list(self.cloned_repos.keys()):
            if not self.cleanup_repository(repo_name):
                all_success = False
        
        return all_success


class GitProgress(git.RemoteProgress):
    """Progress handler for Git operations"""
    
    def __init__(self, logger: Logger):
        super().__init__()
        self.logger = logger
    
    def update(self, op_code, cur_count, max_count=None, message=''):
        """Update progress"""
        if message:
            self.logger.info(f"Git: {message}")
