from __future__ import annotations

import json
import os

import anyio
import pytest
from kbp_conform.cli import MODES, default_protocol

from knowledge_mcp import bundled
from tests.harness import (
    CODEBASE,
    PRODUCT,
    knowledge_base,
    scope_arguments,
    session,
    texts,
    write,
)
from tests.kb_cli import kb_mcp, listed_commands, run_kb, run_kbp
from tests.test_kb_end_to_end import snapshot
from tests.test_kbp_tools import streams


def result(done):
    return done.stdout, done.stderr, done.returncode


def viewer():
    return {
        "KNOWLEDGE_BUS_EXPLORER_BUNDLE": str(bundled.EXPLORER / "explorer-viewer.js"),
        "KNOWLEDGE_BUS_EXPLORER_BUNDLE_MANIFEST": str(
            bundled.EXPLORER / "explorer-viewer.json"
        ),
    }


def sample(tmp_path, name):
    root = tmp_path / "base"
    if name == "bare":
        root.mkdir()
    else:
        knowledge_base(root, {"": [CODEBASE] if name == "one" else [CODEBASE, PRODUCT]})
    if name == "failing":
        for path in (root / ".knowledge-bus").glob("*.kbp.yaml"):
            path.write_text(
                path.read_text().replace(
                    "conforms_to: kbp/0.8", "conforms_to: knowledge-bus/0.0"
                )
            )
    if name == "unparsable":
        for path in (root / ".knowledge-bus").glob("*.kbp.yaml"):
            path.write_text("universe: [\n")
    if name == "nested":
        root = root / "docs" / "rfcs"
        root.mkdir(parents=True)
    if name == "parent":
        write(
            root, "team/.knowledge-bus/workspace.yaml", f"from_parent:\n  - {PRODUCT}\n"
        )
        root = root / "team"
    return root


PARITY = [
    ("two", ["validate"]),
    ("two", ["validate", ".knowledge-bus"]),
    ("failing", ["validate"]),
    ("bare", ["validate"]),
    ("two", ["validate", "missing.kbp.yaml"]),
    ("nested", ["validate"]),
    ("parent", ["validate"]),
    ("two", ["self-check"]),
    ("two", ["self-check", default_protocol()]),
    ("one", ["inspect"]),
    ("two", ["inspect"]),
    ("two", ["inspect", "--universe", "no-such"]),
    ("bare", ["inspect"]),
    ("one", ["card", "readme"]),
    ("one", ["card", "readme", "--format", "markdown"]),
    ("two", ["card", "readme"]),
    ("unparsable", ["card", "readme"]),
    ("one", ["kinds"]),
    ("two", ["kinds", "--universe", PRODUCT, "--format", "markdown"]),
    ("parent", ["kinds"]),
    ("bare", ["kinds"]),
    ("unparsable", ["kinds"]),
    ("two", ["--version"]),
]


@pytest.mark.parametrize(("name", "argv"), PARITY)
def test_each_mode_prints_what_kbp_prints(tmp_path, name, argv):
    root = sample(tmp_path, name)
    before = snapshot(root)
    assert result(run_kb(tmp_path, "kbp", *argv, cwd=root)) == result(
        run_kbp(tmp_path, "--" + argv[0].removeprefix("--"), *argv[1:], cwd=root)
    )
    assert snapshot(root) == before


@pytest.mark.parametrize(
    "argv",
    [
        ["mint", "elemnt"],
        ["mint", "element", "three"],
        ["card"],
        ["explore", "--universe", PRODUCT],
        ["kinds", "--format", "md"],
        ["kinds", "--universe", "a", "--universe", "b"],
        ["self-check", "a.yaml", "b.yaml"],
        ["inspect", "--output", "unused"],
        ["validate", "--version"],
        ["validate", "--", "--odd.kbp.yaml"],
        ["card", "readme", "--format=markdown"],
        ["kinds", "--univ", CODEBASE],
        ["explore", "--output", "unused", "--replace", "--replace"],
    ],
)
def test_values_after_the_mode_keep_kbps_grammar(tmp_path, argv):
    root = sample(tmp_path, "two")
    before = snapshot(root)
    assert result(run_kb(tmp_path, "kbp", *argv, cwd=root)) == result(
        run_kbp(tmp_path, "--" + argv[0], *argv[1:], cwd=root)
    )
    assert snapshot(root) == before


@pytest.mark.parametrize("argv", [["artifact", "2"], ["frame"], ["factor", "2"]])
def test_mint_matches_kbp_code_shape(tmp_path, argv):
    root = sample(tmp_path, "two")
    through = run_kb(tmp_path, "kbp", "mint", *argv, cwd=root)
    direct = run_kbp(tmp_path, "--mint", *argv, cwd=root)
    assert (through.stderr, through.returncode) == (direct.stderr, direct.returncode)
    assert [(line[0], len(line)) for line in through.stdout.splitlines()] == [
        (line[0], len(line)) for line in direct.stdout.splitlines()
    ]


def test_validate_crash_preserves_report_without_traceback(tmp_path):
    root = sample(tmp_path, "unparsable")
    through = run_kb(tmp_path, "kbp", "validate", cwd=root)
    direct = run_kbp(tmp_path, "--validate", cwd=root)
    assert through.returncode == direct.returncode == 1
    assert through.stdout == direct.stdout
    assert "Traceback" not in through.stderr
    assert through.stderr.count("Error:") == 1
    assert "Run kb doctor --verbose" in through.stderr
    assert "Traceback" in direct.stderr


@pytest.mark.parametrize("mode", [flag[2:] for flag in MODES])
def test_each_mode_has_owned_help_and_an_upstream_options_pointer(tmp_path, mode):
    done = run_kb(tmp_path, "kbp", mode, "--help")
    short = run_kb(tmp_path, "kbp", mode, "-h")
    assert done.returncode == 0 and done.stderr == ""
    assert result(short) == result(done)
    assert f"Usage: kb kbp {mode}" in done.stdout
    assert f"kbp --{mode}" in " ".join(done.stdout.split())
    assert "kb passes other flags and arguments to" in " ".join(done.stdout.split())
    assert "Exit codes:" in done.stdout


def test_group_reads_the_upstream_modes(tmp_path):
    done = run_kb(tmp_path, "kbp", "--help")
    assert listed_commands(done.stdout) == {flag[2:] for flag in MODES}
    assert "Modes:" in done.stdout
    assert "kb kbp validate" in done.stdout
    assert "kb kbp card readme" in done.stdout
    assert result(run_kb(tmp_path, "kbp")) == result(done)


@pytest.mark.parametrize(
    ("argv", "suggestion"),
    [
        (["--kinds"], "kinds"),
        (["--kind"], "kinds"),
        (["--valid", "x"], "validate"),
        (["x.kbp.yaml"], "validate x.kbp.yaml"),
        ([".knowledge-bus"], "validate .knowledge-bus"),
    ],
)
def test_old_forms_suggest_a_subcommand(tmp_path, argv, suggestion):
    done = run_kb(tmp_path, "kbp", *argv)
    assert done.returncode == 2 and done.stdout == ""
    assert "Error:" in done.stderr
    assert f"Did you mean kb kbp {suggestion}" in done.stderr


def hidden_package(tmp_path):
    shadow = tmp_path / "shadow"
    write(
        shadow,
        "kbp_conform/__init__.py",
        'raise ModuleNotFoundError(name="kbp_conform")\n',
    )
    return {"PYTHONPATH": str(shadow)}


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--help"],
        ["validate"],
        ["validate", "--help"],
        ["--version"],
        ["--kinds"],
        ["wrong"],
    ],
)
def test_every_kbp_call_reports_a_missing_package(tmp_path, argv):
    done = run_kb(tmp_path, "kbp", *argv, **hidden_package(tmp_path))
    assert result(done) == (
        "",
        "Error: kbp is missing from this kb install.\nReinstall with brew reinstall knowledge-mcp.\n",
        1,
    )


def test_root_help_works_with_the_package_missing(tmp_path):
    done = run_kb(tmp_path, "--help", **hidden_package(tmp_path))
    assert done.returncode == 0 and done.stderr == ""
    assert "kbp" in listed_commands(done.stdout)


@pytest.mark.parametrize("code", [0, 1, 7])
@pytest.mark.parametrize("as_json", [False, True])
def test_upstream_modes_and_arguments_are_read_without_starting_a_child(
    tmp_path, code, as_json
):
    shadow = tmp_path / "shadow"
    write(shadow, "kbp_conform/__init__.py")
    write(
        shadow,
        "kbp_conform/cli.py",
        """import json, os
MODES = ("--probe",)
FORMATS = ("probe-format",)
CODED = ("probe-kind",)
def main(argv):
    print(json.dumps({"argv": argv, "pid": os.getpid(), "parent": os.getppid()}))
    return RETURN_CODE
""".replace("RETURN_CODE", str(code)),
    )
    done = run_kb(tmp_path, "kbp", "--help", PYTHONPATH=str(shadow))
    assert listed_commands(done.stdout) == {"probe"}
    done = run_kb(
        tmp_path,
        "kbp",
        "probe",
        *(["--json"] if as_json else []),
        "--output=a",
        "--",
        "-odd",
        "x",
        "x",
        PYTHONPATH=str(shadow),
    )
    assert done.returncode == code, done.stderr
    if as_json:
        receipt = json.loads(done.stdout)
        assert receipt["_meta"]["exit_code"] == done.returncode
        assert receipt["isError"] is (code != 0)
        assert "Traceback" not in done.stderr
        if code:
            assert done.stderr.count("Error:") == 1
            assert (
                json.loads(done.stderr.splitlines()[-1]) == receipt["structuredContent"]
            )
        else:
            assert done.stderr == ""
        data = json.loads(receipt["content"][0]["text"])
    else:
        assert done.stderr == ""
        data = json.loads(done.stdout)
    assert data["argv"] == ["--probe", "--output=a", "--", "-odd", "x", "x"]
    assert data["parent"] == os.getpid()


def test_explore_uses_the_bundled_viewer(tmp_path):
    root = sample(tmp_path, "two")
    a, b = tmp_path / "a", tmp_path / "b"
    args = ["--universe", CODEBASE, "--output"]
    through = run_kb(tmp_path, "kbp", "explore", *args, str(a), cwd=root)
    direct = run_kbp(tmp_path, "--explore", *args, str(b), cwd=root, **viewer())
    assert through.returncode == direct.returncode == 0, through.stderr
    assert through.stdout.replace(str(a), "<out>") == direct.stdout.replace(
        str(b), "<out>"
    )
    assert (a / "index.html").is_file()
    for extra in ([], ["--replace"]):
        through = run_kb(tmp_path, "kbp", "explore", *args, str(a), *extra, cwd=root)
        direct = run_kbp(
            tmp_path, "--explore", *args, str(b), *extra, cwd=root, **viewer()
        )
        assert through.returncode == direct.returncode
        assert through.stderr.replace(str(a), "<out>").replace(
            "exists: a", "exists: <out>"
        ) == direct.stderr.replace(str(b), "<out>").replace(
            "exists: b", "exists: <out>"
        )


def test_missing_package_is_a_kbp_failed_problem_over_mcp(tmp_path):
    params = kb_mcp(tmp_path / "server")
    params.env.update(hidden_package(tmp_path))

    async def call(client):
        return await client.call_tool("kbp_version", {})

    answer = session(params, call)
    assert answer.is_error, texts(answer)
    assert answer.structured_content["type"].endswith("/kbp-failed")
    assert "kbp is missing from this kb install" in answer.structured_content["detail"]
    assert "Traceback" not in "".join(texts(answer))


def test_simultaneous_mcp_calls_keep_their_streams_and_scopes(tmp_path):
    roots = [
        knowledge_base(tmp_path / name, {"": [spec]})
        for name, spec in [("a", CODEBASE), ("b", PRODUCT)]
    ]
    calls = []
    for root, spec, kind in zip(
        roots, [CODEBASE, PRODUCT], ["readme", "design-doc"], strict=True
    ):
        arguments = {
            **scope_arguments(root, "draft.md", send_text=True),
            "location": str(root / "draft.md"),
        }
        calls.extend(
            [
                ("kbp_kinds", arguments, ["--kinds"], root),
                (
                    "kbp_card",
                    {**arguments, "kind": kind, "universe": spec},
                    ["--card", kind, "--universe", spec, "--format", "markdown"],
                    root,
                ),
            ]
        )
    calls.extend(
        [
            ("kbp_validate", calls[0][1], ["--validate"], roots[0]),
            ("kbp_version", {}, ["--version"], roots[0]),
        ]
    )

    async def together(client):
        answers = [None] * len(calls)

        async def call(index, name, args):
            answers[index] = await client.call_tool(name, args)

        async with anyio.create_task_group() as group:
            for index, (name, args, _, _) in enumerate(calls):
                group.start_soon(call, index, name, args)
        return answers

    answers = session(kb_mcp(tmp_path / "server"), together)
    for answer, (_, _, argv, root) in zip(answers, calls, strict=True):
        assert streams(answer) == result(run_kbp(tmp_path, *argv, cwd=root))
