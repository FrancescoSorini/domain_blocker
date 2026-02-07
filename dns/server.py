import json
import socket
import threading
from pathlib import Path

from dnslib import DNSRecord, QTYPE, RR, A, AAAA
from dnslib.server import DNSServer, BaseResolver

from system.network import load_dns_state


# =========================
# CONFIGURAZIONE
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "domains.json"

DNS_TIMEOUT = 3

LOCAL_SUFFIXES = [
    "homenet.telecomitalia.it",
    "home",
    "lan",
]


# =========================
# UTILS DOMINI BLOCCATI
# =========================

def load_blocked_domains() -> set[str]:
    if not CONFIG_PATH.exists():
        return set()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {d.lower().rstrip(".") for d in data.get("blocked_domains", [])}


def normalize_domain(qname: str) -> str:
    domain = qname.rstrip(".").lower()
    for suffix in LOCAL_SUFFIXES:
        if domain.endswith("." + suffix):
            domain = domain[: -(len(suffix) + 1)]
            break
    return domain


def is_blocked(domain: str, blocked_domains: set[str]) -> bool:
    for blocked in blocked_domains:
        if domain == blocked or domain.endswith("." + blocked):
            return True
    return False


# =========================
# DNS RESOLVER
# =========================

class BlockResolver(BaseResolver):
    def __init__(self):
        # Legge dinamicamente DNS upstream dalla rete attiva
        state = load_dns_state()
        dns_v4 = None
        if state:
            dns_v4 = state.get("dns_ipv4") or state.get("dns")
        if dns_v4:
            self.upstream_dns_list = [(ip, 53) for ip in dns_v4]
        else:
            self.upstream_dns_list = [("8.8.8.8", 53)]  # fallback

    def resolve(self, request: DNSRecord, handler):
        qname_raw = str(request.q.qname)
        qtype = QTYPE[request.q.qtype]

        domain = normalize_domain(qname_raw)
        blocked_domains = load_blocked_domains()

        reply = request.reply()

        # BLOCCO DOMINIO
        if is_blocked(domain, blocked_domains):
            print(f"[BLOCCATO] {domain}")
            if qtype == "A":
                reply.add_answer(
                    RR(rname=request.q.qname, rtype=QTYPE.A, rclass=1, ttl=60, rdata=A("0.0.0.0"))
                )
            elif qtype == "AAAA":
                reply.add_answer(
                    RR(rname=request.q.qname, rtype=QTYPE.AAAA, rclass=1, ttl=60, rdata=AAAA("::"))
                )
            return reply

        # FORWARD DINAMICO
        return self.forward_request(request)

    def forward_request(self, request: DNSRecord) -> DNSRecord:
        for upstream in self.upstream_dns_list:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(DNS_TIMEOUT)
            try:
                sock.sendto(request.pack(), upstream)
                data, _ = sock.recvfrom(4096)
                return DNSRecord.parse(data)
            except socket.timeout:
                print(f"[TIMEOUT] DNS upstream {upstream[0]} non risponde")
            finally:
                sock.close()
        # fallback: risposta vuota
        return request.reply()


def start_dns_server(address="0.0.0.0", port=53):
    resolver = BlockResolver()
    server = DNSServer(resolver, port=port, address=address, tcp=False)
    print(f"[DNS] Blocker attivo su {address}:{port}")
    t = threading.Thread(target=server.start_thread)
    t.daemon = True
    t.start()
    return server
