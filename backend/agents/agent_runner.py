def run_agent(goal: str):
    steps = plan(goal)
    state = {}

    for step in steps:
        if step == "generate":
            state["molecules"] = generate_molecules("EGFR")
        elif step == "score":
            state["scored"] = score_molecules(state["molecules"])

    return state
