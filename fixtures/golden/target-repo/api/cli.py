# Authored-by: Perplexity (AI assistant by Perplexity AI), model family: Perplexity
"""`python3 -m api.cli profile <id>` prints {"status": int, "body": {...}} and exits 0."""
import json
import sys

from api.profile import render_profile


def main(argv):
    if len(argv) != 2 or argv[0] != "profile":
        sys.stderr.write("usage: python3 -m api.cli profile <id>\n")
        return 2
    status, body = render_profile(int(argv[1]))
    print(json.dumps({"status": status, "body": body}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
