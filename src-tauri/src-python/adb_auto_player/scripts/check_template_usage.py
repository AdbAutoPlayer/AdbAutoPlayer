"""Script to check if templates are used or not."""

import sys
from pathlib import Path


def _get_template_paths(template_dir):
    return [
        str(path.relative_to(template_dir)).replace("\\", "/").rsplit(".", 1)[0]
        for path in template_dir.rglob("*.*")
        if path.is_file()
    ]


def _get_python_files(root_dir, templates_dir):
    return [
        path for path in root_dir.rglob("*.py") if templates_dir not in path.parents
    ]


def _template_used_in_code(template_path, code_files):
    for file in code_files:
        with file.open(encoding="utf-8") as f:
            if template_path in f.read():
                return True
    return False


def _main():
    project_root = Path(__file__).resolve().parent.parent
    games_dir = project_root / "games"

    unused_templates = []

    for game in games_dir.iterdir():
        if not game.is_dir():
            continue

        template_dir = game / "templates"
        if not template_dir.exists():
            continue

        template_paths = _get_template_paths(template_dir)
        code_files = _get_python_files(game, template_dir)

        for template_path in template_paths:
            if not _template_used_in_code(template_path, code_files):
                unused_templates.append(f"{game.name}/templates/{template_path}")

    if unused_templates:
        print("Unused templates found:")
        for template in unused_templates:
            print(f" - {template}")
        sys.exit(1)  # Fail the pre-commit
    else:
        print("All templates are used.")
        sys.exit(0)


if __name__ == "__main__":
    _main()
