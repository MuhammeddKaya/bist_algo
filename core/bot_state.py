from storage import repositories as repo


def get_status() -> str:
    state = repo.get_bot_state()
    return state.status if state else "STOPPED"


def set_status(status: str):
    repo.set_bot_status(status)


def is_running() -> bool:
    return get_status() == "RUNNING"


def is_paused() -> bool:
    return get_status() == "PAUSED"
