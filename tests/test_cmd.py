from __future__ import annotations

from typing import NamedTuple

import pytest

from pythemes.__main__ import Cmd
from pythemes.__main__ import ModeAction
from pythemes.__main__ import Operation
from pythemes.__main__ import OpType
from pythemes.__main__ import SysOps
from tests.conftest import CONFIG


@pytest.fixture()
def tmp_modeaction() -> ModeAction:
    return ModeAction.new(
        {
            'name': 'dunst-reload',
            'light': CONFIG.light,
            'dark': CONFIG.dark,
            'cmd': CONFIG.cmd,
        },
        dry_run=True,
    )


def test_modeaction_get_mode(tmp_modeaction: ModeAction):
    cmd = tmp_modeaction
    dark_mode = cmd.get_mode('dark')
    assert dark_mode == CONFIG.dark, f'dark mode: want: {CONFIG.dark!r}, got: {dark_mode!r}'
    assert dark_mode == tmp_modeaction.dark, (
        f'dark mode: want: {tmp_modeaction.dark!r}, got: {dark_mode!r}'
    )
    light_mode = cmd.get_mode('light')
    assert light_mode == tmp_modeaction.light, (
        f'light mode: want: {tmp_modeaction.light!r}, got: {light_mode!r}'
    )
    assert light_mode == CONFIG.light, f'light mode: want: {CONFIG.light!r}, got: {light_mode!r}'

    nonexistentmode = 'nonexistentmode'
    with pytest.raises(ValueError, match=rf'invalid mode {nonexistentmode!r}'):
        cmd.get_mode(nonexistentmode)


def test_run_no_command_does_nothing(monkeypatch, capsys):
    cmd = Cmd(name='noop', cmd='')

    run_called = False
    debug_called = False

    def fake_run(_):
        nonlocal run_called
        run_called = True
        return 0

    monkeypatch.setattr(SysOps, 'run', fake_run)

    cmd.run()

    captured = capsys.readouterr()
    assert captured.out == ''
    assert run_called is False
    assert debug_called is False


def test_run_dry_run_logs_and_does_not_execute(monkeypatch, capsys, caplog):
    name = 'xresources'
    command = 'xrdb -load ~/.config/X11/xresources'
    c = Cmd(name, command)

    monkeypatch.setattr(SysOps, 'dry_run', True)
    monkeypatch.setattr(SysOps, 'run', lambda _: 0)
    monkeypatch.setattr('pythemes.__main__.colorize', lambda text, *styles: text)  # noqa: ARG005

    with caplog.at_level('DEBUG'):
        c.run()

    assert f'dry run for command={command}' in caplog.text

    captured = capsys.readouterr()
    assert f'[cmd] {name} {Operation.DRY_RUN.value}' in captured.out


def test_run_executes_when_not_dry_run(monkeypatch, capsys, caplog):
    name = 'echo'
    command = 'echo {}'
    c = Cmd(name, command)

    monkeypatch.setattr(SysOps, 'dry_run', False)
    monkeypatch.setattr(SysOps, 'run', lambda _: 0)
    monkeypatch.setattr('pythemes.__main__.colorize', lambda text, *styles: text)  # noqa: ARG005

    with caplog.at_level('DEBUG'):
        c.run()

    assert f'running command={command}' in caplog.text

    captured = capsys.readouterr()
    assert f'{OpType.CMD} {name} {Operation.EXECUTED.value}' in captured.out


class CmdTestCase(NamedTuple):
    name: str
    cmd: str
    dry_run: bool
    expected_output: str
    expected_log: str
    should_execute: bool


@pytest.mark.parametrize(
    ('name', 'cmd', 'dry_run', 'expected_output', 'expected_log', 'should_execute'),
    (
        CmdTestCase(
            name='xresources',
            cmd='xrdb -load ~/.config/X11/xresources',
            dry_run=True,
            expected_output=f'{OpType.CMD} xresources {Operation.DRY_RUN.value}',
            expected_log='dry run for command=xrdb -load ~/.config/X11/xresources',
            should_execute=False,
        ),
        CmdTestCase(
            name='xresources',
            cmd='xrdb -load ~/.config/X11/xresources',
            dry_run=False,
            expected_output=f'{OpType.CMD} xresources {Operation.EXECUTED.value}',
            expected_log='running command=xrdb -load ~/.config/X11/xresources',
            should_execute=True,
        ),
        CmdTestCase(
            name='polybar',
            cmd='polybar-msg cmd restart',
            dry_run=True,
            expected_output=f'{OpType.CMD} polybar {Operation.DRY_RUN.value}',
            expected_log='dry run for command=polybar-msg cmd restart',
            should_execute=False,
        ),
        CmdTestCase(
            name='polybar',
            cmd='polybar-msg cmd restart',
            dry_run=False,
            expected_output=f'{OpType.CMD} polybar {Operation.EXECUTED.value}',
            expected_log='running command=polybar-msg cmd restart',
            should_execute=True,
        ),
        CmdTestCase(
            name='empty_cmd',
            cmd='',
            dry_run=False,
            expected_output='',
            expected_log='',
            should_execute=False,
        ),
        CmdTestCase(
            name='empty_cmd',
            cmd='',
            dry_run=True,
            expected_output='',
            expected_log='',
            should_execute=False,
        ),
    ),
)
def test_cmd_run(  # noqa: PLR0913, PLR0917
    monkeypatch,
    capsys,
    caplog,
    name,
    cmd,
    dry_run,
    expected_output,
    expected_log,
    should_execute,
):
    """Test Cmd.run() with various scenarios including dry-run and execution modes."""
    c = Cmd(name, cmd)
    monkeypatch.setattr(SysOps, 'dry_run', dry_run)

    # track if SysOps.run was called
    run_called = False

    def mock_run(command):  # noqa: ARG001
        nonlocal run_called
        run_called = True
        return 0

    monkeypatch.setattr(SysOps, 'run', mock_run)
    monkeypatch.setattr('pythemes.__main__.colorize', lambda text, *styles: text)  # noqa: ARG005

    with caplog.at_level('DEBUG'):
        c.run()

    # verify execution behavior
    assert run_called == should_execute

    # verify output
    captured = capsys.readouterr()
    assert expected_output in captured.out or expected_output == ''

    # verify logging
    if expected_log:
        assert expected_log in caplog.text
