import requests
import json
import time

def download(file_path: str, filename: str = None, repo: str = "Eletroman179/donutsmp_tracker", branch: str = "main"):
    timestamp = int(time.time())  # Cache-busting timestamp
    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{file_path}?{timestamp}"
    
    if filename is None:
        filename = os.path.basename(file_path)

    response = requests.get(raw_url, headers={"Cache-Control": "no-cache"})
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded '{filename}' from '{repo}' at {time.ctime(timestamp)}")
    else:
        print(f"Failed to download '{file_path}' from '{repo}': {response.status_code}")

# Download necessary files
download("config.json")
download("main.py")

# Prompt for API key and update config
api_key = input("Enter API key (use /api in-game): ")
github_token = input("Enter github token if none leave empty: ")
print("Now edit the usernames in the 'config.json' file.")

# Load and update config
with open("config.json", "r") as file:
    config = json.load(file)  # FIXED: used json.load, not json.loads

config["API_KEY"] = api_key
config["GITHUB_TOKEN"] = github_token

with open("config.json", "w") as file:
    json.dump(config, file, indent=4)
