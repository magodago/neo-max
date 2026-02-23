# Estado del sistema: CPU, RAM, disco. Uso: SKILL:estado_pc

DESCRIPTION = "Estado del PC: uso de CPU, RAM y disco. Uso: SKILL:estado_pc"


def run(task: str = "", **kwargs) -> str:
    try:
        import psutil
    except ImportError:
        return "Error: instala el paquete con pip install psutil"
    lines = []
    cpu_pct = psutil.cpu_percent(interval=1)
    lines.append(f"CPU: {cpu_pct}%")
    mem = psutil.virtual_memory()
    lines.append(f"RAM: {mem.percent}% usado ({mem.used // (1024**3)} GB / {mem.total // (1024**3)} GB)")
    for part in psutil.disk_partitions():
        if "fixed" in part.opts or getattr(part, "fstype", None):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                lines.append(f"Disco {part.mountpoint}: {usage.percent}% usado ({usage.used // (1024**3)} GB / {usage.total // (1024**3)} GB)")
            except Exception:
                pass
    procs = sorted(psutil.process_iter(attrs=["name", "cpu_percent"]), key=lambda p: (p.info.get("cpu_percent") or 0), reverse=True)[:3]
    lines.append("Procesos que más CPU usan:")
    for p in procs:
        name = (p.info.get("name") or "?")[:40]
        cpu = p.info.get("cpu_percent") or 0
        lines.append(f"  - {name}: {cpu}%")
    return "\n".join(lines)
