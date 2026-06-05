"""Repeatable private-alpha soak harness.

Writes all runtime artifacts under .local/soak/ so repository state stays clean.
"""

import argparse
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import admin_commands
import veilborn_mud
import utils
from migrations import apply_migrations


ROOT = Path(__file__).resolve().parent


class TranscriptClient:
    def __init__(self, host, port, name):
        self.name = name
        self.socket = socket.create_connection((host, port), timeout=5)
        self.socket.setblocking(False)
        self.chunks = []
        self.drain(1.0)

    def drain(self, duration=0.4):
        end = time.time() + duration
        while time.time() < end:
            try:
                data = self.socket.recv(8192)
            except BlockingIOError:
                time.sleep(0.03)
                continue
            if not data:
                break
            self.chunks.append(data.decode("utf-8", errors="replace"))

    def send(self, line, duration=0.5):
        self.socket.sendall((line + "\n").encode("utf-8"))
        self.drain(duration)

    def transcript(self):
        return "".join(self.chunks)

    def close(self):
        self.socket.close()


class BuilderProtocol:
    def __init__(self, cursor):
        self.cursor = cursor
        self.username = "SoakBuilder"
        self.is_admin = True
        self.x = 1
        self.y = 1
        self.messages = []

    def sendLine(self, message):
        self.messages.append(message.decode("utf-8"))

    def display_room(self):
        pass

    def track_player(self):
        pass

    def untrack_player(self):
        pass


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def write_artifact(run_dir, name, content):
    path = run_dir / name
    path.write_text(content, encoding="utf-8")
    return path


def run_player_soak(run_dir):
    port = free_port()
    config_path = run_dir / "config.json"
    db_path = run_dir / "soak.db"
    log_path = run_dir / "server.log"
    config = {
        "db_file": str(db_path),
        "motd_file": "motd.txt",
        "help_file": "helpfiles/commands.json",
        "command_categories_file": "helpfiles/command_categories.json",
        "server_port": port,
        "zone_directory": "zones",
        "show_nearby_players": True,
        "nearby_player_radius": 20,
        "default_color_enabled": False,
        "log_file": str(log_path),
    }
    config_path.write_text(json.dumps(config, indent=4), encoding="utf-8")
    server_code = "import veilborn_mud; veilborn_mud.run_server(%r)" % str(config_path)
    server = subprocess.Popen(
        [sys.executable, "-c", server_code],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    clients = []
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            if server.poll() is not None:
                raise RuntimeError(f"server exited early with code {server.returncode}")
            try:
                alpha = TranscriptClient("127.0.0.1", port, "alpha")
                break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError("server did not accept connections")
        clients.append(alpha)
        suffix = int(time.time())
        alpha_user = f"SoakAlpha{suffix}"
        beta_user = f"SoakBeta{suffix}"
        for line in [alpha_user, "soak-pass", "soak-pass"]:
            alpha.send(line, 0.7)
        beta = TranscriptClient("127.0.0.1", port, "beta")
        clients.append(beta)
        for line in [beta_user, "soak-pass", "soak-pass"]:
            beta.send(line, 0.7)
        for line in ["say player soak begins", "north", "body", "rest", "prac throw", "train substitution", "attack practice", "combat"]:
            alpha.send(line, 0.7)
        beta.send("north", 0.7)
        beta.send("say second client present", 0.7)
        alpha.close()
        clients.remove(alpha)
        takeover = TranscriptClient("127.0.0.1", port, "takeover")
        clients.append(takeover)
        for line in [alpha_user, "soak-pass", "look", "body", "rest"]:
            takeover.send(line, 0.7)

        transcripts = {
            "alpha.txt": alpha.transcript(),
            "beta.txt": beta.transcript(),
            "takeover.txt": takeover.transcript(),
        }
        for name, text in transcripts.items():
            write_artifact(run_dir, name, text)
        combined = "\n".join(transcripts.values())
        required = [
            "You practice Throw.",
            "Throw: Untrained",
            "You train Substitution Expression.",
            "Substitution Expression: Untrained",
            "Body",
            "You rest and recover",
            "You engage Practice Construct.",
        ]
        missing = [text for text in required if text not in combined]
        if missing:
            raise AssertionError(f"player soak missing expected output: {missing}")
        if "Throw: Untrained (" in combined or "Substitution Expression: Untrained (" in combined:
            raise AssertionError("player soak exposed backend progression percentages")
        return {"port": port, "alpha": alpha_user, "beta": beta_user}
    finally:
        for client in list(clients):
            try:
                client.close()
            except OSError:
                pass
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


def run_builder_soak(run_dir):
    original_cwd = Path.cwd()
    original_overlays = dict(veilborn_mud.WORLD_OVERLAYS)
    original_config = veilborn_mud.ACTIVE_CONFIG.copy()
    original_admin_config = admin_commands.ACTIVE_CONFIG.copy()
    with tempfile.TemporaryDirectory() as temporary_directory:
        work = Path(temporary_directory)
        (work / "zones").mkdir()
        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        veilborn_mud.conn = db
        veilborn_mud.cursor = db.cursor()
        veilborn_mud.ensure_tables_exist(db)
        apply_migrations(db)
        protocol = BuilderProtocol(db.cursor())
        try:
            veilborn_mud.WORLD_OVERLAYS.clear()
            veilborn_mud.ACTIVE_CONFIG["zone_directory"] = "zones"
            admin_commands.ACTIVE_CONFIG["zone_directory"] = "zones"
            help_file = work / "commands.json"
            category_file = work / "categories.json"
            help_file.write_text(json.dumps({"look": {"summary": "Look.", "details": [], "published": False}}), encoding="utf-8")
            category_file.write_text(json.dumps({"Other": ["look"]}), encoding="utf-8")
            veilborn_mud.ACTIVE_CONFIG["help_file"] = str(help_file)
            veilborn_mud.ACTIVE_CONFIG["command_categories_file"] = str(category_file)
            admin_commands.ACTIVE_CONFIG["help_file"] = str(help_file)
            admin_commands.ACTIVE_CONFIG["command_categories_file"] = str(category_file)
            os.chdir(work)

            admin_commands.buildzone(protocol, "soak-zone", "8000", "8010", "1", "1", "Soak Yard")
            admin_commands.iedit(protocol, "create", "", "soak-ration Soak Ration")
            admin_commands.spawnitem(protocol, "soak-ration")
            admin_commands.zstat(protocol, "soak-zone")
            admin_commands.rlist(protocol, "soak-zone")
            admin_commands.bfind(protocol, "soak")
            admin_commands.contentcheck(protocol, "soak-zone")
            admin_commands.cloneitem(protocol, "soak-ration", "soak-ration-copy")
            admin_commands.cloneroom(protocol, "8000", "8001")
            admin_commands.spawnlist(protocol, "soak-zone")
            admin_commands.despawnitem(protocol, "builder-soak-ration-8000")
            admin_commands.hedit(protocol, "look", "publish")
            admin_commands.zpublish(protocol, "soak-zone")
            admin_commands.bundo(protocol)
            transcript = "\n".join(protocol.messages)
            write_artifact(run_dir, "builder.txt", transcript)
            required = [
                "Built Soak Yard [8000]",
                "Zone Soak Yard",
                "Rooms in Soak Yard",
                "Builder Search: soak",
                "Content Check",
                "Cloned item soak-ration to soak-ration-copy.",
                "Cloned room [8000] to [8001].",
                "Spawns in Soak Yard",
                "Removed item spawn builder-soak-ration-8000.",
                "Updated help for look.",
                "Published zone Soak Yard.",
                "Undid builder action:",
            ]
            missing = [text for text in required if text not in transcript]
            if missing:
                raise AssertionError(f"builder soak missing expected output: {missing}")
            return {"messages": len(protocol.messages)}
        finally:
            db.close()
            os.chdir(original_cwd)
            veilborn_mud.WORLD_OVERLAYS.clear()
            veilborn_mud.WORLD_OVERLAYS.update(original_overlays)
            veilborn_mud.ACTIVE_CONFIG.clear()
            veilborn_mud.ACTIVE_CONFIG.update(original_config)
            admin_commands.ACTIVE_CONFIG.clear()
            admin_commands.ACTIVE_CONFIG.update(original_admin_config)


def main():
    parser = argparse.ArgumentParser(description="Run local private-alpha soak checks.")
    parser.add_argument("--players-only", action="store_true", help="Skip builder smoke.")
    parser.add_argument("--builder-only", action="store_true", help="Skip two-client player smoke.")
    args = parser.parse_args()

    run_dir = ROOT / ".local" / "soak" / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = {"artifact_dir": str(run_dir)}
    if not args.builder_only:
        summary["players"] = run_player_soak(run_dir)
    if not args.players_only:
        summary["builder"] = run_builder_soak(run_dir)
    write_artifact(run_dir, "summary.json", json.dumps(summary, indent=4))
    print(json.dumps(summary, indent=4))


if __name__ == "__main__":
    main()
