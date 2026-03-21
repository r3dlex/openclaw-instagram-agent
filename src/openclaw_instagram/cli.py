"""CLI entry point for the Instagram agent."""

from __future__ import annotations

import argparse
import json
import sys

from openclaw_instagram.agent import InstagramAgent
from openclaw_instagram.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenClaw Instagram Agent")
    sub = parser.add_subparsers(dest="command")

    # engage command
    engage_cmd = sub.add_parser("engage", help="Run engagement cycle on target accounts")
    engage_cmd.add_argument(
        "--list",
        choices=["a", "b", "c"],
        default="a",
        help="Which target list to engage (default: a)",
    )

    # dms command
    dms_cmd = sub.add_parser("dms", help="Check DMs from target accounts")
    dms_cmd.add_argument(
        "--list",
        choices=["a", "b", "c"],
        default="a",
        help="Filter DMs by target list (default: a)",
    )

    # status command
    sub.add_parser("status", help="Show current agent status")

    # agents command (IAMQ peer discovery)
    sub.add_parser("agents", help="List agents registered with the message queue")

    # inbox command (IAMQ messages)
    sub.add_parser("inbox", help="Check unread messages from the message queue")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    settings = get_settings()
    agent = InstagramAgent(settings)

    try:
        if args.command == "engage":
            accounts = getattr(settings, f"accounts_{args.list}")
            if not accounts:
                print(f"No accounts configured for list {args.list.upper()}")
                sys.exit(1)
            results = agent.engage_accounts(accounts)
            print(json.dumps(results, indent=2, default=str))

        elif args.command == "dms":
            accounts = getattr(settings, f"accounts_{args.list}")
            dms = agent.check_dms(filter_usernames=accounts or None)
            print(json.dumps(dms, indent=2, default=str))

        elif args.command == "status":
            print(f"API available: {agent.api.api_available}")
            print(f"Actions this hour: {agent.api.rate_limiter.count_this_hour}")
            print(f"Max per hour: {settings.max_actions_per_hour}")
            print("Target lists:")
            print(f"  A: {settings.accounts_a}")
            print(f"  B: {settings.accounts_b}")
            print(f"  C: {settings.accounts_c}")
            print(f"IAMQ: {'enabled' if agent.iamq.enabled else 'disabled'}")
            if agent.iamq.enabled:
                print(f"  Agent ID: {agent.iamq.agent_id}")
                peers = agent.get_peer_agents()
                print(f"  Peer agents: {len(peers)}")
                for p in peers:
                    print(f"    - {p.get('id', p)}")

        elif args.command == "agents":
            if not agent.iamq.enabled:
                print("IAMQ is not enabled. Set IAMQ_ENABLED=true in .env")
                sys.exit(1)
            peers = agent.get_peer_agents()
            print(json.dumps(peers, indent=2, default=str))

        elif args.command == "inbox":
            if not agent.iamq.enabled:
                print("IAMQ is not enabled. Set IAMQ_ENABLED=true in .env")
                sys.exit(1)
            messages = agent.poll_iamq()
            print(json.dumps(messages, indent=2, default=str))
    finally:
        agent.close()


if __name__ == "__main__":
    main()
