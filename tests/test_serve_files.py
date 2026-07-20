import pytest

from research_bot import config
from research_bot.serve import file_content


@pytest.fixture
def project_root(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEARCH_ROOT", str(tmp_path))
    config._reset_root_cache()
    yield tmp_path
    config._reset_root_cache()


def test_serves_file_inside_root(project_root):
    (project_root / "notes.md").write_text("hello")
    got = file_content("notes.md")
    assert got["text"] == "hello"


def test_rejects_traversal_outside_root(project_root, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "secret.md"
    outside.write_text("secret")
    assert file_content(f"../{outside.parent.name}/secret.md") is None
    assert file_content("../../etc/hostname") is None


def test_rejects_disallowed_extension(project_root):
    (project_root / "keys.py").write_text("k = 1")
    assert file_content("keys.py") is None


def test_rejects_symlink_escaping_root(project_root, tmp_path_factory):
    outside = tmp_path_factory.mktemp("priv") / "keys.json"
    outside.write_text("{}")
    (project_root / "link.json").symlink_to(outside)
    assert file_content("link.json") is None
