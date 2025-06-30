"""Dev specific helpers."""

import logging
import subprocess
import sys


def _is_dev():
    return not hasattr(sys, "frozen") or "__compiled__" in globals()


class DevHelper:
    """Util functions for dev."""

    @staticmethod
    def log_is_main_up_to_date():
        """Check if local main branch is up-to-date with origin/main and log the status.

        Logs different messages depending on whether local branch is:
        - Up-to-date
        - Behind remote
        - Ahead of remote
        - Diverged from remote
        """
        if not _is_dev():
            return

        try:
            # Fetch latest changes from origin
            subprocess.run(
                ["git", "fetch", "origin"],
                check=True,
                capture_output=True,
            )

            # Get commit hashes
            local_main = (
                subprocess.check_output(
                    ["git", "rev-parse", "main"], stderr=subprocess.PIPE
                )
                .strip()
                .decode()
            )
            remote_main = (
                subprocess.check_output(
                    ["git", "rev-parse", "origin/main"], stderr=subprocess.PIPE
                )
                .strip()
                .decode()
            )
            base = (
                subprocess.check_output(
                    ["git", "merge-base", "main", "origin/main"], stderr=subprocess.PIPE
                )
                .strip()
                .decode()
            )

            last_commit_msg = (
                subprocess.check_output(
                    ["git", "log", "-1", "--pretty=%B"], stderr=subprocess.PIPE
                )
                .strip()
                .decode()
            )

            if local_main == remote_main:
                logging.info(
                    "Local main is up-to-date with origin/main. Last commit: "
                    f"{local_main[:7]} - {last_commit_msg}"
                )
            elif local_main == base:
                commits_behind = (
                    subprocess.check_output(
                        ["git", "rev-list", "--count", "main..origin/main"],
                        stderr=subprocess.PIPE,
                    )
                    .strip()
                    .decode()
                )
                logging.warning(
                    f"Local main is behind origin/main by {commits_behind} commit(s). "
                    f"Last local commit: {local_main[:7]} - {last_commit_msg}\n"
                    "Run 'git pull' to update."
                )
            elif remote_main == base:
                logging.info("Local main is ahead of origin/main (no remote changes)")
            else:
                # Branches have diverged
                local_only = (
                    subprocess.check_output(
                        ["git", "rev-list", "--count", "origin/main..main"],
                        stderr=subprocess.PIPE,
                    )
                    .strip()
                    .decode()
                )
                remote_only = (
                    subprocess.check_output(
                        ["git", "rev-list", "--count", "main..origin/main"],
                        stderr=subprocess.PIPE,
                    )
                    .strip()
                    .decode()
                )
                logging.warning(
                    "Branches have diverged:\n"
                    f"- Local main has {local_only} unique commit(s)\n"
                    f"- Origin/main has {remote_only} unique commit(s)\n"
                    "Consider merging or rebasing."
                )

        except subprocess.CalledProcessError as e:
            logging.error(
                f"Git command failed: {e}\n"
                f"Command: {e.cmd}\n"
                f"Output: {e.output.decode().strip() if e.output else ''}\n"
                f"Error: {e.stderr.decode().strip() if e.stderr else ''}"
            )
        except FileNotFoundError:
            logging.error("Git command not found. Is git installed?")
        except Exception as e:
            logging.error(f"Unexpected error checking git status: {e!s}")
