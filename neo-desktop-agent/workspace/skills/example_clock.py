# Skill de ejemplo: devuelve la hora actual del sistema.
DESCRIPTION = "Devuelve la fecha y hora actual del sistema."


def run(task: str = "", **kwargs) -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
