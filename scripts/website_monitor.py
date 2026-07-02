#!/usr/bin/env python3
"""Watch an HTTP endpoint; alert by email; optionally self-heal over SSH. Lab 45.

The smallest useful monitor: poll the URL, and when it stops answering send one
email per outage (not one per check) and — with --restart — SSH to the box and
bring the stack back up. `compose up -d` is deliberately used instead of
`restart`: it also revives containers that are gone, not just stuck ones.
This is a stopgap below Prometheus+Alertmanager (labs 10/12): no history, no
silences, dies with your terminal — the lab asks you to say when each is right.

Usage:
    python scripts/website_monitor.py --url http://<ip>/ --once
    python scripts/website_monitor.py --url http://<ip>/ --interval 30
    python scripts/website_monitor.py --url http://<ip>/ --restart --host <ip> --key dojo-key.pem

Email settings come from env; unset SMTP_HOST = alerts print to stdout only:
    SMTP_HOST, SMTP_PORT (587), SMTP_USER, SMTP_PASSWORD, ALERT_FROM, ALERT_TO

Exit codes (--once): 0 = up, 1 = down. Loop mode runs until Ctrl-C.
"""

import argparse
import os
import smtplib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage

DEFAULT_RESTART_CMD = (
    "cd /opt/dojo && docker compose --env-file .env "
    "-f deploy/compose/compose.yaml -f deploy/compose/compose.prod.yaml up -d"
)


def check(url: str, timeout: int = 10) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if 200 <= resp.status < 300:
                return True, f"HTTP {resp.status}"
            return False, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:  # URLError, timeout, connection reset, DNS...
        return False, type(e).__name__ + ": " + str(e)


def send_alert(subject: str, body: str) -> None:
    host = os.environ.get("SMTP_HOST")
    if not host:
        print(f"  [alert] {subject} (SMTP_HOST unset — email skipped)")
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("ALERT_FROM", os.environ.get("SMTP_USER", ""))
    msg["To"] = os.environ.get("ALERT_TO", "")
    msg.set_content(body)
    with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587"))) as smtp:
        smtp.starttls()
        user = os.environ.get("SMTP_USER")
        if user:
            smtp.login(user, os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)
    print(f"  [alert] emailed: {subject}")


def restart_remote(host: str, user: str, key_path: str, command: str) -> None:
    try:
        import paramiko
    except ImportError:
        sys.exit("paramiko is required for --restart: pip install paramiko")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=user, key_filename=key_path, timeout=15)
    try:
        _, stdout, stderr = client.exec_command(command, timeout=300)
        rc = stdout.channel.recv_exit_status()
        print(f"  [restart] `{command}` exited {rc}")
        err = stderr.read().decode().strip()
        if rc != 0 and err:
            print(f"  [restart] stderr: {err}")
    finally:
        client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True, help="endpoint to watch, e.g. http://<ip>/")
    parser.add_argument("--interval", type=int, default=60, help="seconds between checks")
    parser.add_argument("--once", action="store_true", help="single check, exit 0/1 (cron-friendly)")
    parser.add_argument("--restart", action="store_true", help="on failure, SSH in and self-heal")
    parser.add_argument("--host", default=None, help="SSH host for --restart (default: URL's host)")
    parser.add_argument("--user", default="ubuntu", help="SSH user for --restart")
    parser.add_argument("--key", default="dojo-key.pem", help="SSH private key for --restart")
    parser.add_argument("--restart-cmd", default=DEFAULT_RESTART_CMD, help="remote heal command")
    args = parser.parse_args()

    if args.once:
        up, detail = check(args.url)
        print(f"{args.url} -> {'UP' if up else 'DOWN'} ({detail})")
        return 0 if up else 1

    was_up = True  # one alert per outage, one all-clear per recovery
    print(f"watching {args.url} every {args.interval}s — Ctrl-C to stop")
    while True:
        up, detail = check(args.url)
        stamp = time.strftime("%H:%M:%S")
        print(f"[{stamp}] {'UP' if up else 'DOWN'} ({detail})")

        if not up and was_up:
            send_alert(f"DOWN: {args.url}", f"Check failed at {stamp}: {detail}")
            if args.restart:
                host = args.host or urllib.parse.urlsplit(args.url).hostname
                restart_remote(host, args.user, args.key, args.restart_cmd)
        elif up and not was_up:
            send_alert(f"RECOVERED: {args.url}", f"Answering again at {stamp} ({detail})")

        was_up = up
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
