# C4 failure-classifier probe

Three failing tests engineered to land in three different C4 categories,
plus one passing control. Used to verify `classify_failure` in
`components/c4_test_eval/execute_tests.py`.

| test | actual error | expected category |
|---|---|---|
| `test_real_defect` | `AssertionError` | Real Defect |
| `test_invalid_ai_test` | `AttributeError` | Invalid AI Test |
| `test_environment_failure` | `ModuleNotFoundError` | Environment Failure |
| `test_passes` | — | passes (control) |

## Run it

```bash
W=$(mktemp -d)
mkdir -p "$W/reports"
cp components/c4_test_eval/execute_tests.py "$W/"
cp -r tools/c4_probe/src tools/c4_probe/tests "$W/"
cd "$W" && PYTHONPATH="$W/src" python execute_tests.py
```

As of this writing `test_invalid_ai_test` is misclassified as "Real Defect".
See issue 9b in PIPELINE_NOTES.md.
