import argparse
import sys
import uuid
from app.crawler import Crawler


def parse_args():
    parser = argparse.ArgumentParser(description="Simple Crawler Application for AIOps Demo")
    parser.add_argument(
        "--simulate-error",
        type=str,
        default=None,
        choices=[
            "mongodb_connection_error",
            "mongodb_timeout",
            "database_write_error",
            "source_connection_error",
            "source_timeout",
            "invalid_response",
            "crawler_process_error"
        ],
        help="Intentionally simulate a specific failure mode in the crawler lifecycle."
    )
    return parser.parse_args()


def main():
    args = parse_args()
    # Generate mandatory unique run_id for this execution context
    run_id = str(uuid.uuid4())

    crawler = Crawler(run_id=run_id, simulated_error=args.simulate_error)
    success = crawler.run()

    if not success:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
