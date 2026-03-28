from reflective_agent.cli import _persistent_demo_artifact_dir, render_demo_report


def main() -> None:
    artifact_root = _persistent_demo_artifact_dir()
    artifact_root.mkdir(parents=True, exist_ok=True)
    print(render_demo_report(artifact_root))


if __name__ == "__main__":
    main()
