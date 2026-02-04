import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DOMAINS_FILE = BASE_DIR / "domains.json"


def load_domains() -> list[str]:
    if not DOMAINS_FILE.exists():
        return []

    with open(DOMAINS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return sorted(set(d.lower() for d in data.get("blocked_domains", [])))


def save_domains(domains: list[str]):
    with open(DOMAINS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"blocked_domains": sorted(set(domains))},
            f,
            indent=2
        )


def add_domain(domain: str):
    domains = load_domains()
    domain = domain.lower().strip()

    if domain and domain not in domains:
        domains.append(domain)
        save_domains(domains)


def remove_domain(domain: str):
    domains = load_domains()
    domains = [d for d in domains if d != domain]
    save_domains(domains)
