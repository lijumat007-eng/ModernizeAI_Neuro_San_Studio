"""Validate the Mistral API key configured for this project.

Run from the repository root with:
    python build_scripts/test_mistral_key.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import dotenv_values


API_URL = "https://api.mistral.ai/v1/chat/completions"
DEFAULT_MODEL = "mistral-small-latest"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test a Mistral API key with one minimal request.")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Mistral model to test (default: {DEFAULT_MODEL})",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout in seconds (default: 30).")
    return parser.parse_args()


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_error_message(error: HTTPError) -> str:
    try:
        payload = json.loads(error.read().decode("utf-8"))
        return str(payload.get("message") or payload.get("error") or "No error message returned")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "The API returned an unreadable error response"


def main() -> int:
    args = parse_args()
    env_path = get_project_root() / ".env"
    api_key = dotenv_values(env_path).get("MISTRAL_API_KEY") if env_path.is_file() else None

    if not api_key:
        print(f"FAIL: MISTRAL_API_KEY was not found in {env_path}")
        return 1

    request_body = json.dumps(
        {
            "model": args.model,
            "messages": [{"role": "user", "content": "Reply with OK."}],
            "max_tokens": 2,
        }
    ).encode("utf-8")
    request = Request(
        API_URL,
        data=request_body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    print(f"Testing Mistral model: {args.model}")
    try:
        with urlopen(request, timeout=args.timeout) as response:
            if 200 <= response.status < 300:
                print("PASS: Mistral API key authenticated and the model responded.")
                return 0
            print(f"FAIL: Mistral returned HTTP {response.status}.")
            return 1
    except HTTPError as error:
        message = get_error_message(error)
        if error.code == 401:
            print(f"FAIL: Mistral rejected the API key (HTTP 401): {message}")
        elif error.code == 429:
            print(f"KEY ACCEPTED, BUT RATE LIMITED (HTTP 429): {message}")
        elif error.code == 404:
            print(f"KEY ACCEPTED, BUT MODEL OR ENDPOINT WAS NOT FOUND (HTTP 404): {message}")
        else:
            print(f"FAIL: Mistral returned HTTP {error.code}: {message}")
        return 2 if error.code == 429 else 1
    except URLError as error:
        print(f"FAIL: Could not reach Mistral: {error.reason}")
        return 1
    except TimeoutError:
        print(f"FAIL: Mistral request timed out after {args.timeout:g} seconds.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
