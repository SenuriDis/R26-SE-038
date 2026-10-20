from pipeline.stages import stage4_test_eval


def test_stage_workdir_skips_artifact_dir_inside_target(tmp_path):
    # The GitHub Action's default: analyse the repository root, with the
    # artifact directory inside it. Copying the root must not copy the
    # artifact directory into itself.
    repo = tmp_path / "repo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "module.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    artifacts = repo / ".ai-test-artifacts"
    generated = artifacts / "c3_output" / "run_1" / "generated_tests"
    generated.mkdir(parents=True)
    test_file = generated / "test_f.py"
    test_file.write_text("def test_f():\n    assert True\n", encoding="utf-8")

    workdir = stage4_test_eval.stage_workdir(artifacts, repo, repo, [test_file])

    assert (workdir / "src" / "pkg" / "module.py").exists()
    assert not (workdir / "src" / ".ai-test-artifacts").exists()
    assert (workdir / "tests" / "test_f.py").exists()
