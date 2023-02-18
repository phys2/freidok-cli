"""
Update an article on a legacy Plone 3 site, replacing its content with
html loaded from a file or stdin.
"""
import argparse
import os
import sys

import requests
from dotenv import load_dotenv
from requests.exceptions import HTTPError, ConnectionError

ENV_PREFIX = "PUSH_PLONE_"


def envname(var):
    return f"{ENV_PREFIX}{var}"


def getenv(var):
    return os.getenv(envname(var))


def arguments():
    argp = argparse.ArgumentParser(description=__doc__)

    argp.add_argument(
        "file",
        nargs="?",
        type=argparse.FileType("r", encoding="utf8"),
        default=sys.stdin,
        help="File containing html or '-' for stdin",
    )
    argp.add_argument(
        "-u",
        "--user",
        dest="username",
        metavar="USER",
        default=getenv("USER"),
        required=not getenv("USER"),
        help=f"Plone username (env: {envname('USER')})",
    )
    argp.add_argument(
        "-p",
        "--pass",
        dest="password",
        metavar="PASS",
        default=getenv("PASS"),
        required=not getenv("PASS"),
        help=f"Plone password (env: {envname('PASS')})",
    )
    argp.add_argument(
        "--base-url",
        default=getenv("BASE_URL"),
        required=not getenv("BASE_URL"),
        help=f"Plone site base URL (env: {envname('BASE_URL')})",
    )
    argp.add_argument(
        "--path",
        default=getenv("PATH"),
        required=not getenv("PATH"),
        help=f"Remote path to Plone document (env: {envname('PATH')})",
    )
    argp.add_argument(
        "--no-verify",
        dest="verify",
        action="store_false",
        help=f"Don't reject full html documents",
    )

    return argp.parse_args()


class PlonePusher:
    def __init__(self, username, password, base_url):
        self.username = username
        self.password = password
        self.base_url = base_url.rstrip("/")

        self.login_path = "login_form"
        self.logout_path = "logout"

    def login(self, s: requests.Session):
        payload = {
            "came_from": self.base_url,
            "form.submitted": "1",
            "js_enabled": "0",
            "login_name": "",
            "pwd_empty": "0",
            "submit": "Log in",
            "__ac_name": self.username,
            "__ac_password": self.password,
        }

        url = f"{self.base_url}/{self.login_path}"
        r = s.post(url, data=payload)
        r.raise_for_status()

        # Plone 3 returns 200 even if login fails, so we check
        # session cookies for signs of successful login
        if not s.cookies.get("__ac"):
            raise ValueError("cookie indicating successful login was not found")

    def logout(self, s: requests.Session):
        url = f"{self.base_url}/{self.logout_path}"
        r = s.get(url)
        r.raise_for_status()

    def _send(self, s: requests.Session, remote_path: str, data: str):
        remote_path = remote_path.strip("/")

        payload = {
            "text": data,
            "text_text_format": "text/html",
            "language": "en",
            "form.submitted": "1",
            "form.button.save": "Save",
        }

        # remove 'filename=XXX' part from form-data
        for k, v in payload.items():
            payload[k] = (None, v)

        url = f"{self.base_url}/{remote_path}/atct_edit"
        r = s.post(url, files=payload)
        r.raise_for_status()

        # Plone 3 redirects to the login page if the logged in user is not
        # authorized to edit a page. We assume insufficient privileges if we
        # detect such a redirect to the "required_login" page.
        if "require_login" in r.url:
            raise ValueError("Unauthorized")

    def push(self, remote_path: str, data: str):
        with requests.Session() as s:
            try:
                self.login(s)
                print("Login successful")
            except (HTTPError, ConnectionError, ValueError) as e:
                raise ValueError("Login failed") from e

            try:
                self._send(s, remote_path, data)
                print("Push successful")
            except (HTTPError, ConnectionError, ValueError) as e:
                raise ValueError("Push failed") from e
            finally:
                try:
                    self.logout(s)
                    print("Logout successful")
                except (HTTPError, ConnectionError):
                    print("Logout failed", file=sys.stderr)


def verify_html(html):
    if "<html" in html or "<body" in html or "<head" in html:
        raise ValueError(
            "Your input looks like a complete html document, "
            "but Plone expects your upload to contain only the article inner content, "
            "i.e. anything that could be a child of the <body> element."
        )


def main():
    load_dotenv()
    args = arguments()

    html = args.file.read()

    if len(html) == 0:
        print("Error: No data (empty file?)", file=sys.stderr)
        exit(1)

    if args.verify:
        try:
            verify_html(html)
        except ValueError as e:
            print("Error:", str(e), file=sys.stderr)
            exit(1)

    p = PlonePusher(
        username=args.username,
        password=args.password,
        base_url=args.base_url,
    )

    try:
        p.push(args.path, data=html)
    except ValueError as e:
        msg = str(e)
        if e.__context__:
            msg += f" ({e.__context__})"
        print("Error:", msg, file=sys.stderr)
        exit(1)


if __name__ == "__main__":
    main()
