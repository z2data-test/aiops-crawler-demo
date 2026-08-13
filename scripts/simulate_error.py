#!/usr/bin/env python
import argparse
import subprocess
import sys

VALID_ERRORS = [
    "mongodb_connection_error",
    "mongodb_timeout",
    "database_write_error",
    "source_connection_error",
    "source_timeout",
    "invalid_response",
    "crawler_process_error"
]


def main():
    parser = argparse.ArgumentParser(
        description="Trigger a simulated crawler failure by invoking the actual crawler engine."
    )
    parser.add_argument(
        "error_type",
        type=str,
        choices=VALID_ERRORS,
        help=f"Failure scenario to simulate. Choices: {', '.join(VALID_ERRORS)}"
    )
    args = parser.parse_args()

    print(f"[Simulate Error] Executing crawler with simulation mode: '{args.error_type}'...")

    # Execute main crawler module via subprocess to follow real application lifecycle and log output
    cmd = [sys.executable, "-m", "app.main", "--simulate-error", args.error_type]
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"[Simulate Error] Crawler execution completed with failure exit code ({result.returncode}) as expected.")
    else:
        print(f"[Simulate Error] Warning: Crawler exited with success code 0.")

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
