"""Manual choices are scoped to one confirmed champion and selection generation."""


def key(state):
    return (getattr(state, "champ_select_generation", 0), getattr(state, "locked_champ_id", None))


def mark_manual(state):
    if getattr(state, "own_champion_locked", False) and getattr(state, "locked_champ_id", None):
        state.manual_skin_context = key(state)


def is_manual(state):
    return getattr(state, "manual_skin_context", None) == key(state) and key(state)[1] is not None


def release(state):
    state.manual_skin_context = None
