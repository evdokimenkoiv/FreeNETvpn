## CI & Health Check

- GitHub Actions runs:
  - Shellcheck for bash scripts
  - YAML lint for compose/workflows
  - Docker build for the admin panel
  - `docker-compose config` validation

Add the badge at the top of README:

```
![CI](https://github.com/evdokimenkoiv/FreeNETvpn/actions/workflows/ci.yml/badge.svg)
```

### On-server health check

```
sudo bash scripts/health_check.sh
# Quiet mode:
sudo bash scripts/health_check.sh -q
```
