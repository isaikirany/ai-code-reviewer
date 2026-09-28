import os
from pathlib import Path
from dotenv import load_dotenv
from github import Auth, Github


env_path = Path(__file__).resolve().parent/".env"
load_dotenv(dotenv_path = env_path, override=True)

github_token = os.getenv("GITHUB_TOKEN")

if not github_token:
    raise ValueError("GITHUB_TOKEN must be set in the environment variables.")

with Github(auth=Auth.Token(github_token)) as github:
    repository = github.get_repo("isaikirany/ai-code-reviwer")
    pull_request = repository.get_pull(2)


    print("PR number:", pull_request.number)
    print("PR title:", pull_request.title)
    print("PR state:", pull_request.state)

    for changed_file in pull_request.get_files():
        print("\nFile:",changed_file.filename)
        print("Status:",changed_file.status)
        print("Diff:")
        print(changed_file.patch or "No Text diff available")
