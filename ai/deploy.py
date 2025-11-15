# ai/deploy.py
# Simple GitHub Pages deployer (real API)

import requests
import base64

class GitHubDeployer:
    def __init__(self, token=None):
        self.token = token

    def token_available(self):
        return bool(self.token)

    def deploy_to_github_pages(self, repo_name, files, make_public=True):
        if not self.token:
            raise RuntimeError("GitHub token missing.")

        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
        }

        # create repo
        repo_resp = requests.post(
            "https://api.github.com/user/repos",
            headers=headers,
            json={"name": repo_name, "private": not make_public},
        )

        if repo_resp.status_code not in [200, 201]:
            raise RuntimeError("Could not create repo: " + repo_resp.text)

        # upload files
        for name, content in files.items():
            url = f"https://api.github.com/repos/YOUR_GITHUB_USERNAME/{repo_name}/contents/{name}"
            requests.put(
                url,
                headers=headers,
                json={
                    "message": f"Add {name}",
                    "content": base64.b64encode(content.encode("utf-8")).decode(),
                },
            )

        # enable Pages
        requests.post(
            f"https://api.github.com/repos/YOUR_GITHUB_USERNAME/{repo_name}/pages",
            headers=headers,
            json={"source": {"branch": "main", "path": "/"}},
        )

        return {"url": f"https://YOUR_GITHUB_USERNAME.github.io/{repo_name}/"}
