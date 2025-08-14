import re, sys, pathlib

root = pathlib.Path(".")
compose = (root / "docker-compose.yml").read_text(encoding="utf-8", errors="ignore")
vars_in_compose = sorted(set(re.findall(r"\$\{([A-Z0-9_]+)\}", compose)))

env_example = (root / ".env.example").read_text(encoding="utf-8", errors="ignore")
env_vars = set()
for line in env_example.splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    if "=" in line:
        env_vars.add(line.split("=", 1)[0].strip())

missing = [v for v in vars_in_compose if v not in env_vars]
if missing:
    print("ERROR: Missing variables in .env.example:", ", ".join(missing))
    sys.exit(1)

print("OK: .env.example contains all variables used by docker-compose.yml")
