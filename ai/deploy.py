import requests
import base64
import time
from typing import Dict, Optional


class GitHubDeployer:
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.timeout = 10  # seconds

    def token_available(self) -> bool:
        return bool(self.token)

    def deploy_to_github_pages(self, repo_name: str, files: Dict[str, str], make_public: bool = True) -> Dict:
        """
        Deploy website files to GitHub Pages.
        
        Args:
            repo_name: Repository name (can be a URL or simple name)
            files: Dictionary of {filename: content}
            make_public: Whether to make the repository public
            
        Returns:
            Dictionary with deployed URL
            
        Raises:
            RuntimeError: If deployment fails
        """
        if not self.token:
            raise RuntimeError("GitHub token missing. Please provide a valid GitHub token.")

        # 1. Sanitize Repo Name
        repo_name = repo_name.strip()
        if "/" in repo_name:
            repo_name = repo_name.rstrip("/").split("/")[-1]
        repo_name = repo_name.replace(" ", "-").replace("_", "-")

        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
        }

        # 2. Get the authenticated user's username
        try:
            user_resp = requests.get(
                "https://api.github.com/user",
                headers=headers,
                timeout=self.timeout
            )
            user_resp.raise_for_status()
            username = user_resp.json().get("login")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to authenticate with GitHub API: {str(e)}")
        except (KeyError, ValueError) as e:
            raise RuntimeError(f"Invalid response from GitHub API: {str(e)}")

        if not username:
            raise RuntimeError("Could not retrieve GitHub username from API response.")

        # 3. Create repo (or verify it exists)
        try:
            repo_resp = requests.post(
                "https://api.github.com/user/repos",
                headers=headers,
                json={"name": repo_name, "private": not make_public, "auto_init": True},
                timeout=self.timeout
            )

            if repo_resp.status_code == 201:
                repo_name = repo_resp.json().get("name", repo_name)
            elif repo_resp.status_code == 422:
                # Repo already exists - verify we can access it
                check_url = f"https://api.github.com/repos/{username}/{repo_name}"
                check_resp = requests.get(check_url, headers=headers, timeout=self.timeout)

                if check_resp.status_code != 200:
                    raise RuntimeError(
                        f"Cannot create or access repository '{repo_name}'. "
                        f"GitHub API error: {repo_resp.json().get('message', repo_resp.text)}"
                    )
            else:
                raise RuntimeError(
                    f"Failed to create repository: {repo_resp.status_code} - {repo_resp.text}"
                )
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error during repo creation: {str(e)}")

        # 4. Upload files
        uploaded_count = 0
        failed_files = []

        for file_path, content in files.items():
            try:
                file_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{file_path}"

                # Check if file exists
                try:
                    get_resp = requests.get(file_url, headers=headers, timeout=self.timeout)
                    sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None
                except (ValueError, KeyError):
                    sha = None

                # Encode content to base64
                encoded_content = base64.b64encode(content.encode("utf-8")).decode()

                data = {
                    "message": f"Add {file_path}",
                    "content": encoded_content,
                }
                if sha:
                    data["sha"] = sha

                put_resp = requests.put(file_url, headers=headers, json=data, timeout=self.timeout)

                if put_resp.status_code in [200, 201]:
                    uploaded_count += 1
                else:
                    failed_files.append(f"{file_path}: {put_resp.status_code}")
            except requests.exceptions.RequestException as e:
                failed_files.append(f"{file_path}: Network error - {str(e)}")
            except Exception as e:
                failed_files.append(f"{file_path}: {str(e)}")

        if uploaded_count == 0:
            raise RuntimeError(
                f"All file uploads failed. Details: {'; '.join(failed_files)}"
            )

        if failed_files:
            print(f"Warning: {len(failed_files)} files failed to upload: {failed_files}")

        # 5. Enable GitHub Pages (Best effort)
        try:
            pages_resp = requests.post(
                f"https://api.github.com/repos/{username}/{repo_name}/pages",
                headers=headers,
                json={"source": {"branch": "main", "path": "/"}},
                timeout=self.timeout
            )
            # Pages might already be enabled (409 Conflict is ok)
            if pages_resp.status_code not in [201, 204, 409]:
                print(f"Warning: Could not enable GitHub Pages: {pages_resp.status_code}")
        except Exception as e:
            print(f"Warning: Failed to enable GitHub Pages: {str(e)}")

        return {"url": f"https://{username}.github.io/{repo_name}/"}
