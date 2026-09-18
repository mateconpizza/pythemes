from __future__ import annotations

import copy
from typing import TYPE_CHECKING

import pytest

from pythemes.__main__ import INIFile
from pythemes.__main__ import Theme
from pythemes.__main__ import apply_theme_priority
from tests.conftest import CONFIG

if TYPE_CHECKING:
    from pathlib import Path

    from pythemes.__main__ import App
    from pythemes.__main__ import INISection
    from pythemes.__main__ import ModeAction


def test_theme_init(theme: Theme):
    assert theme.name == CONFIG.name
    theme.load()
    theme.parse_apps()
    assert theme.inifile.filepath.exists()
    assert hasattr(theme, 'wallpaper')
    assert len(theme.cmds) == 1
    assert len(theme.apps) == 2  # noqa: PLR2004


def test_theme_register(theme: Theme, valid_app: App, valid_cmd: ModeAction):
    toappend = 5
    other_app = copy.deepcopy(valid_app)
    other_app.name = 'other_app'

    # apps
    assert len(theme.apps) == 0
    for _ in range(toappend):
        theme.register_app(valid_app)
        theme.register_app(other_app)
    # ignore duplicates
    assert len(theme.apps) == 2  # noqa: PLR2004

    # commands
    assert len(theme.cmds) == 0
    for _ in range(toappend):
        theme.register_cmd(valid_cmd)
    assert len(theme.cmds) == toappend


def test_theme_errors(theme: Theme, temp_section: INISection):
    expected_errors = 3
    assert theme.errors() == 0
    for i in range(expected_errors):
        temp_section['query'] = f'invalid_query {i}'
        theme.inifile.add(f'invalid_section_{i}', temp_section)
    theme.load()
    theme.parse_apps()
    assert theme.errors() == expected_errors


def test_theme_get(theme: Theme):
    target_app = 'xresources'
    theme.load()
    theme.parse_apps()
    app = theme.get(target_app)
    assert app is not None
    assert app.name == target_app
    nonexistent_app = 'nonexistent'
    app = theme.get(nonexistent_app)
    assert app is None


def test_theme_parse_apps(theme: Theme):
    with pytest.raises(ValueError):
        theme.parse_apps()


def test_apply_theme_priority_removes_overlapping_apps(
    theme: Theme,
    user_theme: Theme,
    valid_apps: dict[str, App],
):
    for app in valid_apps.values():
        theme.register_app(app)
        user_theme.register_app(app)

    # remove one app from the priority theme,
    removed_name = next(iter(valid_apps))
    del user_theme.apps[removed_name]

    result = apply_theme_priority(user_theme, theme)

    # priority theme (user_theme) is untouched by the call itself
    assert set(user_theme.apps) == set(valid_apps) - {removed_name}

    # target theme has every app present in the priority theme removed,
    # leaving only the one app the priority theme didn't have
    assert set(theme.apps) == {removed_name}

    # target_theme is mutated in place and returned, not replaced
    assert result is theme


def test_apply_theme_priority_no_overlap_is_noop(
    theme: Theme,
    ini_filepath: Path,
    valid_apps: dict[str, App],
):
    for app in valid_apps.values():
        theme.register_app(app)

    empty_priority = Theme('my-theme', INIFile(ini_filepath), dry_run=True)
    before = dict(theme.apps)

    result = apply_theme_priority(empty_priority, theme)

    assert result.apps == before
    assert result is theme


def test_apply_theme_priority_full_overlap_empties_target(
    theme: Theme,
    user_theme: Theme,
    valid_apps: dict[str, App],
):
    for app in valid_apps.values():
        theme.register_app(app)
        user_theme.register_app(app)

    result = apply_theme_priority(user_theme, theme)

    assert result.apps == {}
    # priority theme itself is unaffected
    assert len(user_theme.apps) == len(valid_apps)


def test_apply_theme_priority_ignores_priority_apps_not_in_target(
    theme: Theme,
    user_theme: Theme,
    valid_apps: dict[str, App],
):
    # priority_theme has an app the target never registered; .pop(app, None)
    # should silently no-op for that key rather than raising.
    for app in valid_apps.values():
        user_theme.register_app(app)

    before = dict(theme.apps)  # empty target
    result = apply_theme_priority(user_theme, theme)

    assert result.apps == before == {}
