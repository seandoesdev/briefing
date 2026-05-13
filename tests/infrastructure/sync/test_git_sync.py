from git import Repo

from briefing.infrastructure.sync.git_sync import GitVaultSync


def _setup_repos(tmp_path):
    remote = tmp_path / "remote.git"
    Repo.init(remote, bare=True)
    work = tmp_path / "work"
    repo = Repo.init(work)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "test")
        cw.set_value("user", "email", "test@example.com")
    repo.git.checkout("-b", "main")
    repo.git.commit("--allow-empty", "-m", "init")
    repo.create_remote("origin", str(remote))
    repo.git.push("--set-upstream", "origin", "main")
    return work, remote


def test_no_changes_returns_success_with_zero(tmp_path):
    work, _ = _setup_repos(tmp_path)
    sync = GitVaultSync(work, remote="origin", branch="main")
    result = sync.commit_and_push("nothing")
    assert result.ok is True
    assert result.article_count == 0


def test_commit_and_push_with_new_file(tmp_path):
    work, remote = _setup_repos(tmp_path)
    (work / "dooray").mkdir()
    (work / "dooray" / "2026-05-13.md").write_text("hello", encoding="utf-8")

    sync = GitVaultSync(work, remote="origin", branch="main")
    result = sync.commit_and_push("first")

    assert result.ok is True
    assert result.commit_sha is not None

    remote_repo = Repo(remote)
    refs = [r.name for r in remote_repo.refs]
    assert "main" in refs


def test_status_reports_last_commit(tmp_path):
    work, _ = _setup_repos(tmp_path)
    (work / "x.md").write_text("y", encoding="utf-8")
    sync = GitVaultSync(work, remote="origin", branch="main")
    sync.commit_and_push("c1")
    status = sync.status()
    assert status.last_commit_sha is not None
