from pathlib import Path
from html import escape
import traceback
import os
import shutil

import mymarkup


class Context(mymarkup.Context):
    def __init__(self, root_directory: Path, relative_path: Path):
        self._index = self.generate_index_html(root_directory, relative_path)
        self._breadcrumbs = self.generate_breadcrumbs_html(root_directory, relative_path)

    def index(self):
        return self._index

    def breadcrumbs(self):
        return self._breadcrumbs

    def generate_index_html(self, root_directory: Path, relative_path: Path) -> str:
        html = "<table><tr><th>Name</th><th>Description</th></tr>"
        directory = root_directory / relative_path.parent
        for path in directory.iterdir():
            if path.name == relative_path.name:
                continue
            if path.is_dir():
                href = path.name
                path = path / "index.mu"
            else:
                href = path.with_suffix(".html").name
            if not (path.exists() and path.suffix == ".mu"):
                continue
            source = path.read_text(encoding="utf-8")
            metadata = mymarkup.metadata(source)
            html += f'<tr><td><a href="{escape(href, quote=True)}">{metadata.title}</a></td><td>{metadata.description}</td></tr>'
        html += "</table>"
        return html

    def generate_breadcrumbs_html(self, root_directory: Path, relative_path: Path) -> str:
        breadcrumbs = [("Home", "/")]
        current = root_directory
        parts = relative_path.parts[:-1] if relative_path.name == "index.mu" else relative_path.parts
        href_parts = []
        for name in parts:
            current = current / name
            href_parts.append(name)
            if current.is_dir():
                source = (current / "index.mu").read_text(encoding="utf-8")
                title = mymarkup.metadata(source).title
            elif current.suffix == ".mu":
                source = current.read_text(encoding="utf-8")
                title = mymarkup.metadata(source).title
            else:
                raise Exception(f"Unknown file type when generating breadcrumbs: {current}")
            href = "/" + "/".join([escape(x) for x in href_parts]) + "/"
            breadcrumbs.append((title, href))
        html = '<div class="breadcrumbs">'
        for title, href in breadcrumbs[:-1]:
            html += f'<a href="{href}">{title}</a> / '
        html += f'{breadcrumbs[-1][0]}</div>'
        return html


def get_all_markup_paths(directory: Path) -> list[Path]:
    return [
        path.relative_to(directory)
        for path in directory.rglob("*.mu")
        if path.is_file()
    ]


def convert_markup_to_html(root_directory: Path, relative_path: Path) -> None:
    input_path = root_directory / relative_path
    output_path = root_directory / relative_path.with_suffix(".html")
    input_text = input_path.read_text(encoding="utf-8")
    input_text = f":breadcrumbs:\n\n{input_text}"
    context = Context(root_directory, relative_path)
    markup = mymarkup.render(input_text, context)
    title = mymarkup.metadata(input_text, context).title
    template = (Path(__file__).parent / "template.html").read_text(encoding="utf-8")
    html = template.replace("TITLE", title).replace("MARKUP", markup)
    output_path.write_text(html, encoding="utf-8")


def rm_html_files(root_directory: Path) -> int:
    ignore_lines = [x.strip() for x in Path(".gitignore").read_text(encoding="utf-8").split("\n") if x.strip()]
    count = 0
    for path in root_directory.rglob("*.html"):
        if any([part in ignore_lines for part in path.parts]):
            continue
        if path.is_file():
            path.unlink()
            count += 1
    return count


def build_site(root_directory: Path) -> None:
    root_directory = root_directory.resolve()
    print(f" [+] Removing all .html files from  {root_directory}")
    count = rm_html_files(root_directory)
    print(f" [+] Removed {count} .html files")
    relative_markup_paths = get_all_markup_paths(root_directory)
    print(f" [+] Detected {len(relative_markup_paths)} files to to render")
    for relative_markup_path in relative_markup_paths:
        print(f" [+] Rendering {relative_markup_path}")
        try:
            convert_markup_to_html(root_directory, relative_markup_path)
        except Exception as e:
            raise Exception(f"Error processing {relative_markup_path}: {e}")
    print(" [+] Copying styles.css")
    shutil.copy2(Path(__file__).parent / "styles.css", root_directory / "styles.css")


def main() -> int:
    try:
        build_site(Path("."))
        return 0
    except Exception as e:
        print(f" [-] {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
