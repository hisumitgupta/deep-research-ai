from github import Github
import os

github = Github(os.getenv("GITHUB_TOKEN"))

def search_github(query: str, max_results: int = 3) -> list:
    """Search GitHub repos and READMEs for technical topics."""
    results = []
    try:
        repos = github.search_repositories(
            query=f"{query} stars:>100",
            sort="stars"
        )
        for repo in list(repos)[:max_results]:
            try:
                readme = repo.get_readme().decoded_content.decode("utf-8")
                results.append({
                    "title": repo.full_name,
                    "url": repo.html_url,
                    "content": readme[:1000],   # first 1000 chars of README
                    "source_type": "github",
                    "relevance": 0.8
                })
            except Exception:
                continue
    except Exception:
        pass
    return results