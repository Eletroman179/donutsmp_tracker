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
import base64

init(autoreset=True)

with open("config.json") as file:
    config = json.load(file)

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

def _make_github_request(api_url: str, token: str = ""):
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    return requests.get(api_url, headers=headers)

def view(file_path: str, repo: str = "Eletroman179/donutsmp_tracker", branch: str = "main"):
    token = config.get("GITHUB_TOKEN")
    api_url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={branch}"

    headers = {"Authorization": f"token {token}"} if token else {}
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        try:
            content = base64.b64decode(response.json()["content"])
            return content.decode()
        except Exception as e:
            print(f"Error decoding content: {e}")
            return None
    else:
        print(f"[GitHub API failed: {response.status_code}] Trying raw.githubusercontent fallback...")
        raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{file_path}"
        fallback = requests.get(raw_url, headers={"Cache-Control": "no-cache"})
        if fallback.status_code == 200:
            return fallback.text
        else:
            print(f"Fallback also failed: {fallback.status_code}")
            return None

def download(file_path: str, filename: str = "", repo: str = "Eletroman179/donutsmp_tracker", branch: str = "main"):
    token = config.get("GITHUB_TOKEN")
    if filename is None:
        filename = os.path.basename(file_path)

    api_url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={branch}"
    headers = {"Authorization": f"token {token}"} if token else {}
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        try:
            content = base64.b64decode(response.json()["content"])
            with open(filename, 'wb') as f:
                f.write(content)
            print(f"Downloaded '{filename}' from GitHub API")
            return
        except Exception as e:
            print(f"Error decoding or saving: {e}")

    print(f"[GitHub API failed: {response.status_code}] Trying raw.githubusercontent fallback...")
    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{file_path}"
    fallback = requests.get(raw_url, headers={"Cache-Control": "no-cache"})
    if fallback.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(fallback.content)
        print(f"Downloaded '{filename}' from fallback URL")
    else:
        print(f"Failed to download '{file_path}' via fallback: {fallback.status_code}")

def capture_screenshot(region=(0, 0, 1920, 50)):
    return pyautogui.screenshot(region=region)

def extract_username_from_screenshot(image):
    return pytesseract.image_to_string(image).strip()

def get_player_username(region=(0, 0, 1920, 50)):
    return extract_username_from_screenshot(capture_screenshot(region))

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
    try:
        with open("config.json", "r") as file:
            local_data = json.load(file)
    except FileNotFoundError:
        print("Local config.json not found")
        exit(1)

    remote_json_text = view("config.json")
    print("Remote config contents:", remote_json_text)

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
    global pinging
    first_pass = True

    while True:
        try:
            changed = False
            display = []

            if first_pass:
                print(f"{Fore.CYAN}Fetching player data...{Style.RESET_ALL}")
                bar = progressbar.ProgressBar(max_value=len(USERNAMES), widgets=widgets)

            pinging = True
            for idx, user in enumerate(USERNAMES):
                try:
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

                    money_diff  = 0 if prev_money is None else stats["money"] - prev_money
                    shards_diff = 0 if prev_shards is None else stats["shards"] - prev_shards

                    old_stats[user]["last_money_diff"]  = money_diff
                    old_stats[user]["last_shards_diff"] = shards_diff

                    if (money_diff != 0 or shards_diff != 0
                        or (old_stats[user]["online"] is True and not online)
                        or (old_stats[user]["online"] is False and online)):
                        changed = True

                    old_stats[user].update({
                        "money":  stats["money"],
                        "shards": stats["shards"],
                        "online": online
                    })

                except Exception as e:
                    old_stats[user].update({"money":0, "shards":0, "online":False})
                    display.append(f"{Fore.RED}{user:<20}: Error fetching data [deleting]{Style.RESET_ALL}")
                    USERNAMES.remove(user)

                if first_pass:
                    clr = player_colors[idx % len(player_colors)]
                    bar.update(idx+1, username=f"{clr}|{user:^15}|{Style.RESET_ALL}") # type: ignore
            pinging = False

            for user in sorted(
                USERNAMES,
                key=lambda u: (
                    not old_stats[u].get("online", False),
                    -old_stats[u].get("money") if old_stats[u].get("money") is not None else 0 # type: ignore
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

                money_val  = st["money"] if st["money"] is not None else 0
                shards_val = st["shards"] if st["shards"] is not None else 0

                uname_cell  = f"{user:^20}"
                money_cell  = f"{money_val:>13,} {md_s:^14}"
                shards_cell = f"{shards_val:>7,} {sd_s:^15}"
                online_cell = f"{online_str:^11}"
                loc_cell    = f"{loc:^22}"

                line = (
                    f"║{clr}{uname_cell}{Style.RESET_ALL}║"
                    f" {clr}{money_cell}{Style.RESET_ALL}║"
                    f" {clr}{shards_cell}{Style.RESET_ALL}║"
                    f"{Fore.GREEN if st['online'] else Fore.RED}{online_cell}{Style.RESET_ALL}║"
                    f"{clr}{loc_cell}{Style.RESET_ALL}║"
                )
                display.append(line)

            if changed or first_pass:
                print_table(display)
                if not first_pass:
                    play_notification()

            first_pass = False
            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("Do you want to do")
            do = input("[E]xit [A]dd username [P]ing [U]pdate \n").strip()

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
            elif do.lower() == "u":
                update()
                first_pass = True

if __name__ == "__main__":
    clear_screen()
    print(f"{Fore.YELLOW}[Starting DonutSMP Tracker]{Style.RESET_ALL}")
    update()
    main_loop()
