import requests
import json
import os
import time
import winsound
import progressbar
from datetime import datetime
from colorama import Fore, Style, init
import pytesseract
from PIL import Image
import pyautogui
from packaging import version

init(autoreset=True)

with open("config.json") as file:
    config = json.load(file)

# Map strings to actual Fore color attributes
player_colors = [getattr(Fore, color_name) for color_name in config["player_colors"]]

join_color = Fore.GREEN + Style.BRIGHT
leave_color = Fore.RED + Style.BRIGHT

API_KEY = config["API_KEY"]
USERNAMES = config["USERNAMES"]
POLL_INTERVAL = config["POLL_INTERVAL"]

widgets = [
    ' [', progressbar.Percentage(), '] ',
    progressbar.Bar(marker='█', fill=' ', left='[', right=']', width=30),
    ' ', progressbar.ETA(), ' ',
    progressbar.DynamicMessage('username')
]

HEADERS = {"Authorization": f"Bearer {API_KEY}"}
BASE_URL_STATS  = "https://api.donutsmp.net/v1/stats/{}"
BASE_URL_LOOKUP = "https://api.donutsmp.net/v1/lookup/{}"

pinging = False

# Initialize old_stats with placeholders and diff fields
old_stats = {
    user: {
        "money": None,
        "shards": None,
        "online": None,
        "last_money_diff": 0,
        "last_shards_diff": 0
    }
    for user in USERNAMES
}

session = requests.Session()
session.headers.update(HEADERS)

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def view(file_path: str, repo: str = "Eletroman179/donutsmp_tracker", branch: str = "main"):
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{file_path}"
    response = requests.get(url, headers={"Cache-Control": "no-cache"})
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to fetch file: {response.status_code}")
        return None

def download(file_path: str, filename: str = None, repo: str = "Eletroman179/donutsmp_tracker", branch: str = "main"):
    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{file_path}"
    if filename is None:
        filename = os.path.basename(file_path)

    response = requests.get(raw_url)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"Downloaded '{filename}' from '{repo}'")
    else:
        print(f"Failed to download '{file_path}' from '{repo}': {response.status_code}")

# Function to capture the screen at a specified region
def capture_screenshot(region=(0, 0, 1920, 50)):  # Example region, adjust as needed
    # Capture the region where the username is displayed (near the top of the screen)
    screenshot = pyautogui.screenshot(region=region)
    return screenshot

# Function to extract text (the player's username) from the screenshot
def extract_username_from_screenshot(image):
    # Use pytesseract to extract text
    text = pytesseract.image_to_string(image)
    return text.strip()

# Function to get the player's username based on the on-screen display
def get_player_username(region=(0, 0, 1920, 50)):
    # Capture a screenshot of the top part of the screen (where the Jade mod shows the name)
    screenshot = capture_screenshot(region)
    
    # Extract the username from the screenshot
    username = extract_username_from_screenshot(screenshot)
    
    # Return the username if it's detected
    return username

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def is_online(username):
    try:
        r = session.get(BASE_URL_LOOKUP.format(username))
        return r.status_code == 200
    except:
        return False

def find_location(username):
    try:
        r = session.get(BASE_URL_LOOKUP.format(username))
        return r.json()["result"]["location"]
    except:
        return "N/A"

def fetch_stats(username):
    r = session.get(BASE_URL_STATS.format(username))
    r.raise_for_status()
    res = r.json().get("result", {})
    return {
        "money": int(res.get("money", 0)),
        "shards": int(res.get("shards", 0))
    }

def format_diff(diff):
    if diff is None or diff == 0:
        return "(no change)"
    return f"(+{diff:,})" if diff > 0 else f"(-{abs(diff):,})"

def print_table(lines):
    clear_screen()
    print("╔════════════════════╦═════════════════════════════╦════════════════════════╦═══════════╦══════════════════════╗")
    print("║     Username       ║            Money            ║         Shards         ║  Online   ║      Location        ║")
    print("╠════════════════════╬═════════════════════════════╬════════════════════════╬═══════════╬══════════════════════╣")
    for ln in lines:
        print(ln)
    print("╚════════════════════╩═════════════════════════════╩════════════════════════╩═══════════╩══════════════════════╝")
    if pinging:
        print(f"{Fore.YELLOW}[pinging]{Fore.RESET}")

def play_notification():
    winsound.PlaySound("SystemExit", winsound.SND_ALIAS)

def update():
    # Step 1: Load local config
    try:
        with open("config.json", "r") as file:
            local_data = json.load(file)
    except FileNotFoundError:
        print("Local config.json not found")
        exit(1)

    # Step 2: Load remote config
    remote_json_text = view("config.json")
    print("Remote config contents:", remote_json_text)


    # Step 3: update the script
    if remote_json_text:
        try:
            remote_data = json.loads(remote_json_text)

            if version.parse(remote_data["ver"]) > version.parse(local_data["ver"]):
                print(f"Updating script from version {local_data['ver']} to {remote_data['ver']}")
                download("main.py")
                local_data["ver"] = remote_data["ver"]
                
                with open("config.json", "w") as file:
                    json.dump(local_data, file, indent=4)
            else:
                print("Script is up to date.")
        except json.JSONDecodeError:
            print("Remote config.json is not a valid JSON.")
    else:
        print("Could not retrieve remote config.")
        
    time.sleep(2)

def main_loop():
    first_pass = True

    while True:
        try:
            changed = False
            display = []

            if first_pass:
                print(f"{Fore.CYAN}Fetching player data...{Style.RESET_ALL}")
                bar = progressbar.ProgressBar(max_value=len(USERNAMES), widgets=widgets)

            # 1) Fetch & compute diffs
            pinging = True
            for idx, user in enumerate(USERNAMES):
                try:
                    # Ensure the user exists in old_stats
                    if user not in old_stats:
                        old_stats[user] = {
                            "money": 0,
                            "shards": 0,
                            "online": False,
                            "last_money_diff": 0,
                            "last_shards_diff": 0
                        }

                    prev_money  = old_stats[user]["money"]
                    prev_shards = old_stats[user]["shards"]

                    stats = fetch_stats(user)
                    online = is_online(user)

                    # compute diffs
                    money_diff  = 0 if prev_money is None else stats["money"] - prev_money
                    shards_diff = 0 if prev_shards is None else stats["shards"] - prev_shards

                    # store last diffs
                    old_stats[user]["last_money_diff"]  = money_diff
                    old_stats[user]["last_shards_diff"] = shards_diff

                    # detect change for notification
                    if (money_diff != 0 or shards_diff != 0
                        or (old_stats[user]["online"] is True and not online)
                        or (old_stats[user]["online"] is False and online)):
                        changed = True

                    # update stats
                    old_stats[user].update({
                        "money":  stats["money"],
                        "shards": stats["shards"],
                        "online": online
                    })

                except Exception as e:
                    # on error, zero them out
                    old_stats[user].update({"money":0, "shards":0, "online":False})
                    display.append(f"{Fore.RED}{user:<20}: Error fetching data [deleting]{Style.RESET_ALL}")
                    USERNAMES.remove(user)

                if first_pass:
                    clr = player_colors[idx % len(player_colors)]
                    bar.update(idx+1, username=f"{clr}|{user:^15}|{Style.RESET_ALL}")
            pinging = False
            # 2) Build display rows, sorting online first then by money
            for user in sorted(
                USERNAMES,
                key=lambda u: (
                    not old_stats[u]["online"],
                    -old_stats[u]["money"]
                )
            ):
                st  = old_stats[user]
                md  = st["last_money_diff"]
                sd  = st["last_shards_diff"]
                md_s = format_diff(md)
                sd_s = format_diff(sd)
                loc = find_location(user) if st["online"] else "N/A"

                online_str = "yes" if st["online"] else "no"
                clr = player_colors[USERNAMES.index(user) % len(player_colors)]

                uname_cell = f"{user:^20}"
                money_cell = f"{st['money']:>13,} {md_s:^14}"
                shards_cell= f"{st['shards']:>7,} {sd_s:^15}"
                online_cell= f"{online_str:^11}"
                loc_cell   = f"{loc:^22}"

                line = (
                    f"║{clr}{uname_cell}{Style.RESET_ALL}║"
                    f" {clr}{money_cell}{Style.RESET_ALL}║"
                    f" {clr}{shards_cell}{Style.RESET_ALL}║"
                    f"{Fore.GREEN if st['online'] else Fore.RED}{online_cell}{Style.RESET_ALL}║"
                    f"{clr}{loc_cell}{Style.RESET_ALL}║"
                )
                display.append(line)

            # 3) Print & notify
            if changed or first_pass:
                print_table(display)
                if not first_pass:
                    play_notification()

            first_pass = False
            time.sleep(POLL_INTERVAL)  # wait for the next polling cycle

        except KeyboardInterrupt:
            # Prompt the user to add a new username
            print("Do you want to do")
            do = input("[E]xit [A]dd username [P]ing \n").strip()

            if do.lower() == "e":
                print(f"\n{Fore.RED}[Exiting by user]{Style.RESET_ALL}")
                break
            elif do.lower() == "a":
                new_username = get_player_username()
                print(f"{Fore.YELLOW}Detected username: {new_username}{Style.RESET_ALL}")
                if new_username and new_username not in USERNAMES:
                    USERNAMES.append(new_username)
                    old_stats[new_username] = {
                        "money": 0,
                        "shards": 0,
                        "online": False,
                        "last_money_diff": 0,
                        "last_shards_diff": 0
                    }
                    print(f"{Fore.GREEN}Username {new_username} added.{Style.RESET_ALL}")
                    first_pass = True
                else:
                    print(f"{Fore.RED}Invalid or duplicate username.{Style.RESET_ALL}")
            elif do.lower() == "p":
                first_pass = True
                continue

if __name__ == "__main__":
    clear_screen()
    print(f"{Fore.YELLOW}[Starting DonutSMP Tracker]{Style.RESET_ALL}")
    update()
    main_loop()
