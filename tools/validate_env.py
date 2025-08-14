import re, sys, os, yaml
ENV_FILE = '.env.example'
COMPOSE_FILE = 'docker-compose.yml'

def parse_env(path):
    env = set()
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if not line or line.startswith('#') or '=' not in line: continue
            k=line.split('=',1)[0].strip()
            if k: env.add(k)
    return env

def vars_in_compose(path):
    with open(path,'r',encoding='utf-8') as f:
        data=f.read()
    return set(re.findall(r'\$\{([A-Z0-9_]+)\}', data))

def main():
    missing = set()
    env = parse_env(ENV_FILE)
    used = vars_in_compose(COMPOSE_FILE)
    missing = used - env
    if missing:
        print('Missing variables in .env.example:', ', '.join(sorted(missing)))
        sys.exit(1)
    print('All compose variables exist in .env.example.')
    sys.exit(0)

if __name__=='__main__':
    try:
        import yaml  # noqa: F401 (ensures PyYAML available if later needed)
    except Exception:
        pass
    main()
