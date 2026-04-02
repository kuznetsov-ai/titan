"""CLI entry point for TITAN — Testing Interfaces, Transactions And Networks."""

import argparse
import asyncio
import sys
from pathlib import Path

from config.loader import load_system_config


def main():
    parser = argparse.ArgumentParser(
        description="TITAN — Testing Interfaces, Transactions And Networks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Crawl all pages and save baselines
  titan run --system config/systems/backoffice.yaml --save-baselines

  # Regression run — compare with baselines
  titan run --system config/systems/backoffice.yaml

  # E2E interactive tests for Case Manager
  titan test --system config/systems/backoffice.yaml --scenario case-manager

  # E2E with visible browser
  titan test --system config/systems/backoffice.yaml --scenario case-manager --headed
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command (crawl + visual regression)
    run_parser = subparsers.add_parser("run", help="Crawl pages and run visual regression")
    run_parser.add_argument("--system", "-s", required=True, help="Path to system YAML config")
    run_parser.add_argument("--save-baselines", action="store_true", help="Save screenshots as baselines")
    run_parser.add_argument("--headed", action="store_true", help="Visible browser")
    run_parser.add_argument("--env", choices=["test", "prod"], help="Override environment")

    # Test command (E2E scenarios)
    test_parser = subparsers.add_parser("test", help="Run E2E interactive test scenarios")
    test_parser.add_argument("--system", "-s", required=True, help="Path to system YAML config")
    test_parser.add_argument("--scenario", required=True, help="Scenario: case-manager | lthvc-check | exd")
    test_parser.add_argument("--only", nargs="+", help="Run only these test names (e.g. --only S21 S13)")
    test_parser.add_argument("--headed", action="store_true", help="Visible browser")
    test_parser.add_argument("--env", choices=["test", "prod"], help="Override environment")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config_path = Path(args.system)
    if not config_path.exists():
        print(f"Error: config file not found: {config_path}")
        sys.exit(1)

    config = load_system_config(config_path)

    if args.headed:
        config.browser.headless = False
    if args.env:
        config.environment = args.env

    # Configure AI provider from system config
    from ai.client import configure as configure_ai
    configure_ai(config.ai)

    if args.command == "run":
        from core.runner import run_session
        report_path = asyncio.run(run_session(config, update_baselines=args.save_baselines))
        print(f"\nDone! Report saved to: {report_path}")

    elif args.command == "test":
        from scenarios.runner import run_scenario
        only = getattr(args, 'only', None)
        report_path = asyncio.run(run_scenario(config, scenario_name=args.scenario, only=only))
        print(f"\nDone! Report saved to: {report_path}")


if __name__ == "__main__":
    main()
