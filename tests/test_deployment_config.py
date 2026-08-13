import re
import subprocess
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_env_block(workflow_path: Path) -> dict[str, str]:
    workflow = yaml.safe_load(workflow_path.read_text())
    return workflow["env"]


def test_k8s_deployment_name_matches_service_selector() -> None:
    deployment = yaml.safe_load((REPO_ROOT / "k8s" / "deployment.yaml").read_text())
    service = yaml.safe_load((REPO_ROOT / "k8s" / "service.yaml").read_text())

    deployment_name = deployment["metadata"]["name"]
    assert service["spec"]["selector"]["app"] == deployment["spec"]["selector"]["matchLabels"]["app"]
    assert deployment_name == "anythingintopdfbot"


def test_tencent_workflow_deployment_name_matches_k8s_manifest() -> None:
    deployment = yaml.safe_load((REPO_ROOT / "k8s" / "deployment.yaml").read_text())
    env = _load_env_block(REPO_ROOT / ".github" / "workflows" / "tencent.yml")

    assert env["DEPLOYMENT_NAME"] == deployment["metadata"]["name"]


def test_deploy_script_requires_an_image_argument() -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "scripts" / "deploy.sh")],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Usage" in result.stderr


def test_runtime_and_dockerfile_python_versions_match() -> None:
    runtime_version = (REPO_ROOT / "runtime.txt").read_text().strip()
    dockerfile = (REPO_ROOT / "Dockerfile").read_text()

    match = re.search(r"FROM python:([\d.]+)", dockerfile)
    assert match, "Dockerfile base image version not found"
    dockerfile_version = match.group(1)

    assert runtime_version == f"python-{'.'.join(dockerfile_version.split('.')[:2])}"


def test_tencent_workflow_applies_kustomize_from_k8s_directory() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "tencent.yml").read_text()

    assert "working-directory: k8s" in workflow
    assert "rollout status deployment/${DEPLOYMENT_NAME} -n anythingintopdfbot" in workflow


def test_pyproject_limits_setuptools_to_app_package() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()

    assert 'include = ["app*"]' in pyproject
