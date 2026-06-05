# Linux Private-Alpha Checklist

Use this for a small private test server. Keep port `4000` limited to trusted testers through a firewall allowlist, private network, or VPN.

1. Install Python, clone the repository, and enter the project directory.
2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Review `config.json`, especially `server_port`.
4. Start the server manually for the first test:
   ```bash
   .venv/bin/python veilborn_mud.py
   ```
5. Confirm the newest file under `logs/` records startup.
6. Connect from a trusted client and test login, movement, chat, disconnect, and reconnect.
7. Stop the server with `Ctrl+C` or the admin `shutdown` command.

## Optional systemd Service

Create `/etc/systemd/system/veilborn-mud.service`, replacing `/opt/veilborn-mud` with the repository path:

```ini
[Unit]
Description=Veilborn MUD private alpha
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/veilborn-mud
ExecStart=/opt/veilborn-mud/.venv/bin/python veilborn_mud.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Then enable and inspect it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now veilborn-mud
sudo systemctl status veilborn-mud
```

Runtime details continue to land in the repository's `logs/` directory.
