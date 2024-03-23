import os
import requests
from github import Github, GithubException

def get_diff(repo, pull_number=None):
    """
    Retrieves the diff of a pull request or the changes in the main branch.
    """
    if pull_number:
        try:
            pull = repo.get_pull(pull_number)
            diff = pull.diff()
            print(diff.decoded_content)  # Print the diff for pull requests
        except GithubException as e:
            print(f"Error getting pull request diff: {e}")
            return None
    else:
        try:
            main_branch = repo.get_branch("main")
            latest_commit = main_branch.commit
            parent_commit = latest_commit.parents[0]
            comparison = repo.compare(parent_commit.sha, latest_commit.sha)
            diff = comparison.diff
            print(diff.decoded_content)  # Print the diff for main branch
        except GithubException as e:
            print(f"Error getting main branch diff: {e}")
            return None
    return diff.decoded_content

def send_to_claude(diff, language):
    """
    Sends the diff to the Bedrock Claude model for code review.
    """
    aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")

    # Define the system prompt and message prompts
    system_prompt = "Act as an empathetic software engineer that's an expert in all programming languages, frameworks and software architecture."
    human_message_prompt = f"""
    Your task is to review a Pull Request. You will receive a git diff.
    Review it and suggest any improvements in code quality, maintainability, readability, performance, security, etc.
    Identify any potential bugs or security vulnerabilities. Check it adheres to coding standards and best practices.
    Suggest adding comments to the code only when you consider it a significant improvement.
    Write your reply and examples in GitHub Markdown format. The programming language in the git diff is {language}.

    git diff to review

    {diff}
    """

    # Call the Bedrock Claude API
    response = generate_message(aws_access_key_id, aws_secret_access_key, system_prompt, [{"role": "user", "content": human_message_prompt}])

    return response["choices"][0]["message"]["content"]

def generate_message(aws_access_key_id, aws_secret_access_key, system_prompt, messages):
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": aws_access_key_id,
    }
    data = {
        "anthropic_version": "bedrock-2023-05-31",
        "model_id": model_id,
        "system": system_prompt,
        "messages": messages,
    }

    response = requests.post("https://api.bedrockcai.io/v1/models/generate_message", headers=headers, json=data, auth=(aws_access_key_id, aws_secret_access_key))
    response_data = response.json()

    return response_data

def main():
    # Get the GitHub repository
    github_token = os.environ.get("GITHUB_TOKEN")
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    gh = Github(github_token)
    repo = gh.get_repo(repo_name)

    # Get the diff based on the event type
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    pull_number = os.environ.get("PULL_REQUEST_NUMBER")
    diff = get_diff(repo, pull_number if pull_number else None)

    # Check if the diff was successfully retrieved
    if diff is None:
        print("Failed to retrieve the diff.")
        return

    # Assuming you can detect the programming language from the diff or repository
    language = "python"  # Replace with the actual language detection logic

    # Send the diff to Claude for code review
    response = send_to_claude(diff, language)
    print(response)

if __name__ == "__main__":
    main()