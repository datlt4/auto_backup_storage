import argparse
from . import __version__, process_pair_in_pool


def backup():
    parser = argparse.ArgumentParser(
        description="Backup and sync data between directories."
    )

    # Add a version flag
    parser.add_argument(
        "--version", "-v", action="version", version=f"%(prog)s {__version__}"
    )

    parser.add_argument("source", type=str, help="Source directory")
    parser.add_argument("destination", type=str, help="Destination directory")

    args = parser.parse_args()

    source_destination_pairs = [(args.source, args.destination)]
    process_pair_in_pool(source_destination_pairs)
