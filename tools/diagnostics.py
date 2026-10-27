"""Read-only, bounded installation diagnostics. No credentials or raw command output."""
import argparse
import ipaddress
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys


def tr(en, ru):
    language = os.environ.get("FREENET_LANG", os.environ.get("LANG", "en"))
    return ru if language.lower().startswith("ru") else en


class ConfigurationIssue(ValueError):
    pass


def validate_hostname(value, key="DOMAIN", primary=None):
    pattern = r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}"
    if not re.fullmatch(pattern, value):
        raise ConfigurationIssue(tr(
            f"[CONFIG_DOMAIN] {key}: enter a DNS hostname such as vpn.example.com, without https://, port or path. This is an input error; DNS has not been checked.",
            f"[CONFIG_DOMAIN] {key}: укажите доменное имя, например vpn.example.com, без https://, порта и пути. Это ошибка ввода; DNS ещё не проверялся."))
    if primary == value:
        example = "wg." + primary if len(primary) <= 249 else "wg.example.com"
        raise ConfigurationIssue(tr(
            f"[CONFIG_HOSTS_EQUAL] DOMAIN and WG_DOMAIN are both {value}. The VPN portal and WireGuard UI require different hostnames. Use e.g. {example} for WG_DOMAIN; both A records may point to the same server IPv4. This is not a DNS propagation error; DNS has not been checked.",
            f"[CONFIG_HOSTS_EQUAL] DOMAIN и WG_DOMAIN совпадают: {value}. Кабинету VPN и интерфейсу WireGuard нужны разные доменные имена. Например, WG_DOMAIN={example}; обе A-записи могут указывать на один IPv4 сервера. Это не ошибка распространения DNS: DNS ещё не проверялся."))
    return value


def resume(root, no_firewall=False):
    saved = (root / ".env").exists()
    command = "sudo bash install.sh" + (" --existing" if saved else "") + (" --no-firewall" if no_firewall else "")
    print(tr("\nAfter fixing the cause:", "\nПосле исправления причины:"), file=sys.stderr)
    print("  cd -- " + shlex.quote(str(root)), file=sys.stderr)
    if saved:
        print("  sudo python3 tools/manage.py validate", file=sys.stderr)
    print("  " + command, file=sys.stderr)
    print(tr("Existing configuration detected: keep .env, data and keys. --existing reapplies settings; it does not download new code.",
             "Настройки уже сохранены: не удаляйте .env, data и ключи. --existing повторно применяет настройки, но не скачивает новый код.") if saved else
          tr("Configuration has not been saved. Repeat the setup prompts; no reset or directory deletion is needed.",
             "Настройки ещё не сохранены. Повторите ввод; сброс и удаление каталога не нужны."), file=sys.stderr)


def report(code, summary, fix, root, verify=None, no_firewall=False):
    print(f"\nERROR [{code}]: {summary}", file=sys.stderr)
    print(tr("Fix: ", "Исправление: ") + fix, file=sys.stderr)
    if verify:
        print(tr("Check: ", "Проверка: ") + verify, file=sys.stderr)
    resume(root, no_firewall)
    return 1


def lookup(host, family):
    result = subprocess.run(["getent", "ahostsv4" if family == 4 else "ahostsv6", host],
                            text=True, capture_output=True, timeout=6, check=False)
    if result.returncode not in (0, 2):
        raise OSError("resolver command failed")
    addresses = set()
    for line in result.stdout.splitlines():
        if not line.split():
            continue
        address = ipaddress.ip_address(line.split()[0])
        if address.version == family and not (family == 6 and address.ipv4_mapped):
            addresses.add(str(address))
    return sorted(addresses)


def dns(config, root, no_firewall=False):
    hosts = [config["DOMAIN"]]
    if "wireguard" in config["COMPOSE_PROFILES"].split(","):
        hosts.append(config["WG_DOMAIN"])
    failures = False
    for host in hosts:
        try:
            addresses = lookup(host, 4)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            report("DNS_LOOKUP_FAILED", tr(f"The server resolver could not check {host} within the time limit.",
                   f"Резолвер сервера не смог проверить {host} за отведённое время."),
                   tr("Check the server's DNS resolver and network. This does not prove that the domain is absent or still propagating.",
                      "Проверьте DNS-резолвер и сеть сервера. Это не доказывает, что домен отсутствует или зона ещё распространяется."), root,
                   f"getent ahostsv4 {host}", no_firewall)
            failures = True
            continue
        if not addresses:
            report("DNS_NO_IPV4", tr(f"The server resolver returned no IPv4 address for {host}.",
                   f"Резолвер сервера не вернул IPv4 для {host}."),
                   tr("Create/check its A record at your DNS provider, using this machine's public IPv4. Check hostname and zone delegation; a missing record, cache propagation or resolver failure can cause this. Wait for the corrected record to resolve, then retry. Do not reinstall the OS.",
                      "Создайте/проверьте A-запись у DNS-провайдера: она должна указывать на публичный IPv4 этой машины. Проверьте имя и делегирование зоны. Возможны отсутствие записи, задержка обновления кэша или сбой резолвера. Дождитесь правильного ответа и повторите проверку. Переустанавливать ОС не нужно."),
                   root, f"getent ahostsv4 {host}", no_firewall)
            failures = True
        else:
            print(tr("DNS observed on this server: ", "DNS на этом сервере: ") + host + " -> " + ", ".join(addresses))
        try:
            ipv6 = lookup(host, 6)
            if ipv6:
                print(tr("WARNING: IPv6 addresses also resolve: ", "ВНИМАНИЕ: также определяются IPv6-адреса: ") + host + " -> " + ", ".join(ipv6))
                print(tr("Check any AAAA record: it must reach this server on TCP 80/443; correct/remove an unusable AAAA record.",
                         "Проверьте AAAA-запись: IPv6 должен вести на этот сервер с доступными TCP 80/443; исправьте/уберите неработающую AAAA-запись."))
        except (OSError, ValueError, subprocess.TimeoutExpired):
            print(tr("WARNING: IPv6 lookup unavailable; check AAAA records at your DNS provider.",
                     "ВНИМАНИЕ: IPv6 проверить не удалось; проверьте AAAA-записи у DNS-провайдера."))
    if not failures:
        print(tr("Compare every returned address with your VPS provider's public IP. This check does not prove global DNS propagation, correct routing or open inbound ports. TCP 80/443 must reach this server.",
                 "Сравните каждый адрес с публичным IP в панели VPS. Эта проверка не подтверждает распространение DNS по всему миру, правильность маршрутизации или доступность входящих портов. TCP 80/443 должны вести на этот сервер."))
    return int(failures)


def https_failure(root, config, curl_code, status, target="portal", auth=False, no_firewall=False):
    host = config["WG_DOMAIN"] if target == "wireguard" else config["DOMAIN"]
    evidence = f"{host}: curl={curl_code}, HTTP={status}. "
    verify = "sudo python3 tools/diagnostics.py dns"
    if curl_code == 6:
        code, cause = "HTTPS_DNS", tr("Hostname resolution failed.", "Не удалось определить IP домена.")
        fix = tr("Check the A record and server resolver; compare the returned IP with your VPS IP. Allow for DNS cache updates.", "Проверьте A-запись и резолвер сервера, сравните ответ с IP VPS; учитывайте обновление DNS-кэша.")
    elif curl_code in (7, 28):
        code = "HTTPS_CONNECT" if curl_code == 7 else "HTTPS_TIMEOUT"
        cause = tr("Connection failed or timed out; this alone does not identify DNS propagation.", "Соединение не установлено или истекло время ожидания; само по себе это не доказывает задержку DNS.")
        fix = tr("Check the resolved IP, inbound TCP 80/443 in provider and host firewalls, and whether Caddy is running. Check from another network too; NAT loopback may affect the server's own probe.", "Проверьте IP домена, входящие TCP 80/443 у провайдера и на сервере, запуск Caddy. Проверьте из другой сети: серверной проверке может мешать NAT loopback.")
    elif curl_code in (35, 51, 58, 60, 77, 83, 90, 91):
        code, cause = "HTTPS_TLS", tr("TLS handshake or certificate verification failed.", "Ошибка TLS или проверки сертификата.")
        fix = tr("Check A/AAAA, port 80/443 reachability and server time. Inspect Caddy certificate issuance errors locally; fix the reported cause and allow issuance to finish. Do not disable TLS verification.", "Проверьте A/AAAA, доступность 80/443 и время сервера. Локально изучите ошибки выдачи сертификата Caddy, устраните причину и дождитесь выпуска. Не отключайте проверку TLS.")
    elif curl_code == 0 and status in (502, 503, 504):
        code, cause = "HTTPS_BACKEND", tr("The HTTPS endpoint answered, but its backend is unavailable.", "HTTPS отвечает, но внутренний сервис недоступен.")
        fix = tr("Inspect admin/Caddy container health and logs locally; for the WireGuard host also inspect wg-easy. A DNS-only diagnosis would be misleading.", "Проверьте состояние и логи admin/Caddy, а для домена WireGuard также wg-easy. Объяснять эту ошибку только DNS неправильно.")
    elif curl_code == 0 and auth:
        code, cause = "HTTPS_AUTH", tr("Expected HTTP 401 without credentials; access protection is not confirmed.", "Без пароля ожидался HTTP 401; защита входа не подтверждена.")
        fix = tr("Check that DNS reaches this installation and inspect Caddy routing/forward_auth and admin health. Do not share the portal as ready until the check passes.", "Проверьте, что домен ведёт на эту установку, маршруты/forward_auth Caddy и состояние admin. Не выдавайте кабинет за готовый до успешной проверки.")
    else:
        code, cause = "HTTPS_RESPONSE", tr("Unexpected HTTPS response or health payload.", "Неожиданный ответ HTTPS или содержимое health-check.")
        fix = tr("Check DNS against the VPS IP, Caddy routing and admin health. HTTP 200 with the wrong body may be another site. Inspect logs locally.", "Сравните DNS с IP VPS, проверьте маршруты Caddy и состояние admin. HTTP 200 с неверным телом может принадлежать другому сайту. Изучите логи локально.")
    print(tr("Local checks (logs may contain private data; do not publish full output):", "Локальные проверки (логи могут содержать личные данные; не публикуйте полный вывод):"), file=sys.stderr)
    print("  sudo python3 tools/manage.py compose ps\n  sudo python3 tools/manage.py compose logs --tail 60 caddy admin" + (" wg-easy" if target == "wireguard" else ""), file=sys.stderr)
    return report(code, evidence + cause, fix, root, verify, no_firewall)


STAGES = {
    "packages": ("System packages", "Системные пакеты", "Check APT errors above, repository connectivity, free disk space and package-manager locks. Do not remove locks while APT is running.", "Проверьте ошибки APT выше, доступ к репозиториям, место на диске и занятость менеджера пакетов. Не удаляйте блокировки работающего APT."),
    "configuration": ("Configuration", "Настройки", "Correct the named field above. Two hostnames must differ; both may use one IP. If .env exists, edit only the named fields; preserve keys and passwords.", "Исправьте поле из сообщения выше. Нужны два разных имени; IP может совпадать. Если .env существует, изменяйте только указанные поля, сохраняя ключи и пароли."),
    "docker": ("Docker installation", "Установка Docker", "Check Docker repository connectivity and systemctl status docker. Preserve existing data.", "Проверьте доступ к репозиторию Docker и systemctl status docker. Сохраните существующие данные."),
    "kernel": ("VPN kernel support", "Модули ядра VPN", "Check the failed module above and VPS support for WireGuard, IPsec, PPP and TUN; restricted containers may need provider support.", "Проверьте указанный выше модуль и поддержку WireGuard, IPsec, PPP, TUN у VPS; для ограниченных контейнеров нужна помощь провайдера."),
    "images": ("Container download/build", "Загрузка/сборка контейнеров", "Check registry/network errors and disk space. Retry after fixing the cause; do not delete volumes or VPN state.", "Проверьте ошибки реестра образов/сети и место на диске. После исправления повторите запуск; не удаляйте тома и состояние VPN."),
    "runtime": ("Service configuration", "Конфигурация сервисов", "Inspect the validation error above and the named service. Preserve .env/data before deliberate changes.", "Изучите ошибку проверки выше и указанный сервис. Перед изменениями сохраните .env/data."),
    "firewall": ("Host firewall", "Firewall сервера", "Inspect the firewall error above. Keep SSH access; --no-firewall is only for operators managing firewall rules themselves.", "Изучите ошибку firewall выше. Сохраните доступ SSH; --no-firewall предназначен только для самостоятельного управления правилами."),
    "startup": ("Service startup", "Запуск сервисов", "Run sudo python3 tools/manage.py compose ps and sudo python3 tools/manage.py compose logs --tail 60 locally. For address already in use, inspect sudo ss -lntup; identify the owner before changing ports or stopping services. For health failures inspect the named container.", "Локально выполните sudo python3 tools/manage.py compose ps и sudo python3 tools/manage.py compose logs --tail 60. При address already in use проверьте sudo ss -lntup: определите владельца порта до остановки сервисов или смены портов. При health-ошибке проверьте названный контейнер."),
    "health": ("HTTPS and protocol verification", "Проверка HTTPS и протоколов", "Follow the specific diagnostic above; inspect container status and protocol check errors locally.", "Следуйте конкретной подсказке выше; локально проверьте контейнеры и ошибки проверки протоколов."),
}


def image_pull_failure(output, root):
    """Classify Docker's message without including arbitrary log text in guidance."""
    text = output.lower()
    rules = [
        (("no space left", "disk quota exceeded"), "IMAGE_DISK", "Docker/containerd could not allocate disk space or inodes. Check df -h, df -i and docker system df. Clean package cache with sudo apt-get clean or enlarge the disk. Do not delete /var/lib/containerd manually or prune VPN volumes. Then retry --existing.", "Docker/containerd не смог выделить место или inode. Проверьте df -h, df -i и docker system df. Очистите кэш пакетов командой sudo apt-get clean либо увеличьте диск. Не удаляйте /var/lib/containerd вручную и не очищайте тома VPN. Затем повторите --existing."),
        (("no such host", "temporary failure in name resolution"), "IMAGE_DNS", "The server cannot resolve an image registry. Check the server/Docker resolver, not only the VPN website's A record.", "Сервер не разрешает имя реестра образов. Проверьте DNS сервера/Docker; A-запись сайта VPN к этому не относится."),
        (("x509", "certificate", "tls handshake"), "IMAGE_TLS", "Check system time, CA certificates and HTTPS inspection between Docker and the registry. Do not enable insecure registries.", "Проверьте время, корневые сертификаты и HTTPS-инспекцию на пути к реестру. Не включайте insecure registries."),
        (("toomanyrequests", "too many requests", "rate limit", "429"), "IMAGE_LIMIT", "The registry rate limit was reached. Wait for its reset or authenticate to that registry with your account, then retry.", "Достигнут лимит реестра. Дождитесь сброса лимита либо авторизуйтесь в этом реестре своей учётной записью, затем повторите."),
        (("manifest unknown", "manifest not found", "not found", "no matching manifest"), "IMAGE_NOT_FOUND", "The requested image/tag or CPU architecture is unavailable. Identify the image in Docker's error above; check the project's pinned version and supported architecture, then update to a verified fix. Do not substitute an arbitrary image.", "Запрошенный образ/тег или архитектура CPU недоступны. Найдите имя образа в ошибке Docker выше, проверьте закреплённую версию и архитектуру, затем обновитесь до проверенного исправления. Не подставляйте случайный образ."),
        (("unauthorized", "denied", "forbidden"), "IMAGE_AUTH", "Registry access was denied. Check the named registry, image visibility and any configured Docker login/proxy credentials locally.", "Реестр отказал в доступе. Проверьте указанный реестр, доступность образа и локальные учётные данные Docker/proxy."),
        (("unknown flag", "unknown shorthand flag"), "COMPOSE_VERSION", "Check docker compose version and install the supported Docker Compose plugin; --ignore-buildable requires a compatible version.", "Проверьте docker compose version и обновите плагин Docker Compose: --ignore-buildable требует совместимой версии."),
        (("timeout", "deadline exceeded", "connection refused", "network is unreachable"), "IMAGE_NETWORK", "Check outbound HTTPS to the named registry, host/provider network restrictions and Docker proxy settings; then retry.", "Проверьте исходящий HTTPS к указанному реестру, ограничения сети провайдера/машины и proxy Docker, затем повторите."),
    ]
    code, fix = "IMAGE_PULL", tr("Read the Docker error above for the failing image and cause. Check docker compose version, registry connectivity and free disk space. A nonzero exit alone does not identify the cause.", "Найдите выше исходную ошибку Docker с именем образа. Проверьте docker compose version, доступ к реестру и свободное место. Один ненулевой код выхода не объясняет причину.")
    for needles, candidate, en, ru in rules:
        if any(needle in text for needle in needles):
            code, fix = candidate, tr(en, ru)
            break
    return report(code, tr("Docker could not download the selected images.", "Docker не смог скачать выбранные образы."), fix, root,
                  "sudo python3 tools/manage.py compose pull --ignore-buildable", os.environ.get("FREENET_NO_FIREWALL") == "1")


def storage(root, no_firewall=False):
    paths = [root, Path("/var/lib/containerd")]
    try:
        result = subprocess.run(["docker", "info", "--format", "{{.DockerRootDir}}"], capture_output=True, text=True, timeout=10, check=True)
        directory = Path(result.stdout.strip())
        if directory.is_absolute():
            paths.append(directory)
    except (OSError, subprocess.SubprocessError):
        paths.append(Path("/var/lib/docker"))
    checked, failed = set(), False
    for path in paths:
        if not path.exists():
            continue
        device = path.stat().st_dev
        if device in checked:
            continue
        checked.add(device)
        info = os.statvfs(path)
        free = info.f_bavail * info.f_frsize
        print(f"STORAGE {path}: {free / 1024**3:.1f} GiB, {info.f_favail} free inodes", flush=True)
        if free < 2 * 1024**3 or (info.f_files > 0 and info.f_favail < 10000):
            failed = True
            report("IMAGE_DISK", tr(f"Insufficient free space/inodes on {path} before image download.", f"Недостаточно места/inode на {path} перед загрузкой образов."),
                   tr("Minimum preflight reserve: 2 GiB and 10,000 inodes; a full deployment may need substantially more. Check df -h and df -i. Use sudo apt-get clean or enlarge the disk; preserve VPN data and Docker volumes.", "Минимальный запас для начала: 2 GiB и 10 000 inode; полный набор может потребовать значительно больше. Проверьте df -h и df -i. Выполните sudo apt-get clean либо увеличьте диск, сохранив данные VPN и тома Docker."),
                   root, "df -h; df -i; sudo docker system df", no_firewall)
    return int(failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["dns", "https", "stage", "storage"])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--no-firewall", action="store_true")
    parser.add_argument("--phase", choices=list(STAGES), default="health")
    parser.add_argument("--curl-code", type=int, default=0)
    parser.add_argument("--http-status", type=int, default=0)
    parser.add_argument("--target", choices=["portal", "wireguard"], default="portal")
    parser.add_argument("--auth", action="store_true")
    args = parser.parse_args()
    if args.kind == "storage":
        return storage(args.root, args.no_firewall)
    if args.kind == "stage":
        en, ru, fix_en, fix_ru = STAGES[args.phase]
        return report("INSTALL_STAGE", tr(en, ru), tr(fix_en, fix_ru), args.root, no_firewall=args.no_firewall)
    import manage
    try:
        config = manage.read_config(args.root)
    except (ValueError, OSError):
        return report("CONFIG_READ", tr("Cannot read a valid saved configuration.", "Не удалось прочитать корректные сохранённые настройки."),
                      tr("Run manage.py validate to identify the field. Keep existing .env/data; do not reset the installation.", "Запустите manage.py validate для указания поля. Сохраните .env/data; не сбрасывайте установку."), args.root, no_firewall=args.no_firewall)
    if args.kind == "dns":
        return dns(config, args.root, args.no_firewall)
    return https_failure(args.root, config, args.curl_code, args.http_status, args.target, args.auth, args.no_firewall)


if __name__ == "__main__":
    sys.exit(main())
