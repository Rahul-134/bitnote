def generate_checklist(topic: str, roadmap: list[dict]) -> list[str]:
    checklist = []

    for step in roadmap:
        checklist.append(f"Complete week {step['week']}: {step['focus']}")

    checklist.append(f"Build a final project on {topic}")
    return checklist
