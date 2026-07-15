"""
CLI argument parsing and main entry point for ShellMind.
"""

import argparse
import os
import sys
from typing import Optional

from shellmind import __version__
from shellmind.agent import CodeAgent
from shellmind.memory import Memory


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="A local-first, cross-platform AI coding assistant.",
        epilog=(
            "Examples:\n"
            "  shellmind\n"
            "  shellmind --model qwen2.5-coder:7b\n"
            "  shellmind --cwd ~/project -p 'find TODO comments'\n"
            "  shellmind 'list the files'\n"
            "  python -m shellmind --help"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "task", nargs="*",
        help="Optional one-shot task to run.",
    )
    parser.add_argument(
        "-p", "--prompt", metavar="TEXT",
        help="Run TEXT once, then exit.",
    )
    parser.add_argument(
        "-m", "--model", metavar="NAME",
        help="LLM model to use for this session.",
    )
    parser.add_argument(
        "-C", "--cwd", metavar="DIR",
        help="Start in DIR instead of the current directory.",
    )
    parser.add_argument(
        "--manual", action="store_true",
        help="Ask before running each tool call.",
    )
    parser.add_argument(
        "--no-clear", action="store_true",
        help="Do not clear the terminal before the REPL starts.",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"ShellMind v{__version__}",
    )
    return parser.parse_args(argv)


def entry_point() -> int:
    """Console script entry point (setuptools)."""
    return main()


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for ShellMind."""
    args = parse_args(argv)

    if args.prompt and args.task:
        print("error: use either a positional task or --prompt, not both.",
              file=sys.stderr)
        return 2

    if args.cwd:
        target = os.path.abspath(os.path.expanduser(args.cwd))
        if not os.path.isdir(target):
            print(f"error: directory not found: {args.cwd}", file=sys.stderr)
            return 2
        os.chdir(target)

    task = args.prompt or " ".join(args.task).strip()
    memory = Memory()

    agent = CodeAgent(
        model=args.model,
        mode="manual" if args.manual else "auto",
        clear_screen=not args.no_clear,
        memory=memory,
    )

    if task:
        return 0 if agent.run_once(task) else 1

    agent.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
