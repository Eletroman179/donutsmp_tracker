import requests
import json

def download(
    file_path: str,
    filename: str = None,
    repo: str = "Eletroman179/donutsmp_tracker",
    branch: str = "main"
):
    """
    Downloads a file from a GitHub repository's raw URL.

    :param file_path: Path to the file inside the repo (e.g., 'config/config.json')
    :param filename: Local filename to save as (defaults to the same as in file_path)
    :param repo: GitHub repo in 'username/repo' format
    :param branch: Branch name (default: 'main')
    """
    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{file_path}"
    if filename is None:
        filename = file_path.split("/")[-1]

    response = requests.get(raw_url)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded '{filename}' from '{repo}'")
    else:
        print(f"Failed to download '{file_path}' from '{repo}': {response.status_code}")

# Download necessary files
download("config.json")
download("main.py")

# Prompt for API key and update config
api_key = input("Enter API key (use /api in-game): ")
print("Now edit the usernames in the 'config.json' file.")

# Load and update config
with open("config.json", "r") as file:
    config = json.load(file)  # FIXED: used json.load, not json.loads

config["API_KEY"] = api_key

with open("config.json", "w") as file:
    json.dump(config, file, indent=4)
