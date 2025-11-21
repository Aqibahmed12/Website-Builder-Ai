# ai/deploy.py
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

        # 1. Sanitize Repo Name
        repo_name = repo_name.strip()
        # If user pasted a full URL, extract the last segment
        if "/" in repo_name:
            repo_name = repo_name.rstrip("/").split("/")[-1]
        # Replace spaces with dashes
        repo_name = repo_name.replace(" ", "-")

        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json",
        }

        # 2. Get the authenticated user's username
        user_resp = requests.get("https://api.github.com/user", headers=headers)
        if user_resp.status_code != 200:
            raise RuntimeError("Invalid Token or GitHub API error: " + user_resp.text)

        username = user_resp.json().get("login")
        if not username:
            raise RuntimeError("Could not retrieve GitHub username.")

        # 3. Create repo (or check if it exists)
        repo_resp = requests.post(
            "https://api.github.com/user/repos",
            headers=headers,
            json={"name": repo_name, "private": not make_public},
        )

        # Handle creation response
        if repo_resp.status_code == 201:
            # Successfully created, use the official name from response
            repo_name = repo_resp.json().get("name", repo_name)
        elif repo_resp.status_code == 422:
            # 422 often means "Repo already exists". We verify this.
            check_url = f"https://api.github.com/repos/{username}/{repo_name}"
            check_resp = requests.get(check_url, headers=headers)

            if check_resp.status_code == 200:
                # Repo exists! We can proceed to update it.
                pass
            else:
                # It doesn't exist, so the 422 was a real error (e.g. invalid name)
                raise RuntimeError(f"Cannot create repository '{repo_name}'. GitHub says: {repo_resp.text}")
        else:
            # Any other error
            raise RuntimeError(f"Could not create repo: {repo_resp.text}")

        # 4. Upload files
        uploaded_count = 0
        for name, content in files.items():
            # Construct URL with verified repo_name
            file_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{name}"

            # Check if file exists to get SHA (needed for updates)
            get_file = requests.get(file_url, headers=headers)
            sha = get_file.json().get("sha") if get_file.status_code == 200 else None

            data = {
                "message": f"Update {name}",
                "content": base64.b64encode(content.encode("utf-8")).decode(),
            }
            if sha:
                data["sha"] = sha

            put_resp = requests.put(file_url, headers=headers, json=data)
            if put_resp.status_code in [200, 201]:
                uploaded_count += 1
            else:
                print(f"Failed to upload {name}: {put_resp.text}")

        if uploaded_count == 0:
            raise RuntimeError("All file uploads failed. Check your permissions or repo name.")

        # 5. Enable Pages (Best effort)
        try:
            requests.post(
                f"https://api.github.com/repos/{username}/{repo_name}/pages",
                headers=headers,
                json={"source": {"branch": "main", "path": "/"}},
            )
        except:
            pass

        return {"url": f"https://{username}.github.io/{repo_name}/"}
