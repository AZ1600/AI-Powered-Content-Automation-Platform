from pathlib import Path


def test_expected_files_exist():
    root = Path(__file__).resolve().parents[1]
    expected = [
        root / "lambdas" / "common.py",
        root / "lambdas" / "x_oauth_start.py",
        root / "lambdas" / "x_oauth_callback.py",
        root / "lambdas" / "x_publisher.py",
        root / "lambdas" / "x_queue_list.py",
        root / "lambdas" / "x_plan_save.py",
        root / "lambdas" / "x_plan_generate.py",
        root / "lambdas" / "x_plan_list.py",
        root / "lambdas" / "x_plan_queue.py",
        root / "lambdas" / "x_queue_remove.py",
        root / "lambdas" / "x_account_summary.py",
        root / "lambdas" / "x_queue_publish.py",
        root / "lambdas" / "x_activity_list.py",
        root / "lambdas" / "x_queue_scheduler.py",
        root / "lambdas" / "x_dashboard.py",
        root / "templates" / "template.yaml",
        root / "samconfig.toml",
    ]
    for path in expected:
        assert path.exists(), f"Missing expected file: {path}"


def test_template_defines_posts_table():
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates" / "template.yaml").read_text()
    assert "XPostsTable" in template
    assert "X_POSTS_TABLE_NAME" in template


def test_template_defines_plans_and_queue_endpoints():
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates" / "template.yaml").read_text()
    assert "XPlansTable" in template
    assert "Path: /x/queue" in template
    assert "Path: /x/plan" in template
    assert "Path: /x/plan/generate" in template
    assert "Path: /x/plans" in template
    assert "Path: /x/plan/queue" in template
    assert "Path: /x/queue/remove" in template
    assert "Path: /x/summary" in template
    assert "Path: /x/queue/publish" in template
    assert "Path: /x/activity" in template
    assert "rate(15 minutes)" in template
    assert "Path: /dashboard" in template
