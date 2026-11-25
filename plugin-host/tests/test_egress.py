"""
@file
@brief Egress filter rule generation and installation sequence (iptables faked).
"""

import socket
from pathlib import Path
from typing import Any

import pytest

from host import egress
from host.supervisor import BwrapSupervisor

NEX = [("172.20.0.5", 8080)]


def lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.startswith("-A")]


def test_v4_ruleset_order_and_content() -> None:
    rules = lines(egress.ruleset(False, NEX + [("fd00::5", 8080)]))
    c = egress.CHAIN
    assert rules[0] == f"-A {c} -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT"
    dns = [
        f"-A {c} -p udp -m conntrack --ctorigdst 127.0.0.11 --ctorigdstport 53 -j ACCEPT",
        f"-A {c} -p tcp -m conntrack --ctorigdst 127.0.0.11 --ctorigdstport 53 -j ACCEPT",
    ]
    assert rules[1:3] == dns  # only DNS to the Docker resolver, never other 127.0.0.11 ports
    assert not any("-d 127.0.0.11" in r for r in rules)
    assert f"-A {c} -d 172.20.0.5/32 -p tcp --dport 8080 -j ACCEPT" in rules
    assert not any("fd00::5" in r for r in rules)
    for net in ("127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
                "100.64.0.0/10", "169.254.0.0/16", "0.0.0.0/8"):  # fmt: skip
        assert f"-A {c} -d {net} -j DROP" in rules
    accept_idx = max(i for i, r in enumerate(rules) if r.endswith("ACCEPT"))
    first_drop = min(i for i, r in enumerate(rules) if r.endswith("DROP"))
    assert accept_idx < first_drop  # allows (DNS, nexara) before the private drops
    assert rules[first_drop] == f"-A {c} -m addrtype --dst-type LOCAL -j DROP"
    assert rules[-1] == f"-A {c} -j RETURN"
    text = egress.ruleset(False, NEX)
    assert text.startswith(f"*filter\n:{c} - [0:0]\n-F {c}\n") and text.endswith("COMMIT\n")


def test_v6_ruleset() -> None:
    rules = lines(egress.ruleset(True, NEX + [("fd00::5", 8080)]))
    assert f"-A {egress.CHAIN} -d fd00::5/128 -p tcp --dport 8080 -j ACCEPT" in rules
    assert not any("127.0.0.11" in r or "172.20.0.5" in r for r in rules)
    assert f"-A {egress.CHAIN} -m addrtype --dst-type LOCAL -j DROP" in rules
    for net in ("::1/128", "fc00::/7", "fe80::/10", "::ffff:0:0/96", "64:ff9b::/96"):
        assert f"-A {egress.CHAIN} -d {net} -j DROP" in rules


def test_jump_rule_targets_plugin_uid_range() -> None:
    assert egress.jump_rule() == [
        "OUTPUT", "-m", "owner", "--uid-owner", "19999-29999", "-j", egress.CHAIN
    ]  # fmt: skip


def test_nexara_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    def gai(host: str, port: int, **kw: Any) -> list[Any]:
        assert host == "nexara"
        return [(0, 0, 0, "", ("172.20.0.5", port)), (0, 0, 0, "", ("172.20.0.5", port))]

    monkeypatch.setattr(socket, "getaddrinfo", gai)
    assert egress.nexara_targets("http://nexara:8080") == NEX
    assert egress.nexara_targets("https://nexara/x") == [("172.20.0.5", 443)]
    assert egress.nexara_targets(None) == []


def _fake(rcs: dict[str, int]) -> tuple[list[tuple[list[str], str | None]], egress.Run]:
    calls: list[tuple[list[str], str | None]] = []

    def run(argv: list[str], stdin: str | None) -> int:
        calls.append((argv, stdin))
        return rcs.get(" ".join(argv[:3]), 0)

    return calls, run


def test_apply_installs_both_families(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "if_inet6").write_text("")
    monkeypatch.setattr(egress, "IF_INET6", tmp_path / "if_inet6")
    calls, run = _fake({"iptables -w -C": 1})  # v4 jump missing, v6 present
    egress.apply("http://172.20.0.5:8080", run)
    argvs = [" ".join(a) for a, _ in calls]
    assert argvs[0] == "iptables-restore -w --noflush"
    assert "172.20.0.5/32" in (calls[0][1] or "")
    assert argvs[2].startswith("iptables -w -I OUTPUT 1 -m owner")
    assert argvs[3] == "ip6tables-restore -w --noflush"
    assert not any(a.startswith("ip6tables -w -I") for a in argvs)


def test_apply_skips_v6_without_kernel_ipv6(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(egress, "IF_INET6", tmp_path / "missing")
    calls, run = _fake({})
    egress.apply("", run)
    assert not any(a[0].startswith("ip6tables") for a, _ in calls)


def test_apply_failure_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(egress, "IF_INET6", tmp_path / "missing")
    _, run = _fake({"iptables-restore -w --noflush": 1})
    with pytest.raises(egress.EgressError):
        egress.apply("", run)


def test_supervisor_unavailable_when_filter_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(egress.ENV, "true")
    monkeypatch.setattr("host.supervisor._self_test", lambda d: True)

    def fail(**kw: Any) -> None:
        raise egress.EgressError("nope")

    monkeypatch.setattr(egress, "apply", fail)
    assert BwrapSupervisor(tmp_path).available is False
    monkeypatch.setattr(egress, "apply", lambda **kw: None)
    assert BwrapSupervisor(tmp_path).available is True
    monkeypatch.setenv(egress.ENV, "false")
    monkeypatch.setattr(egress, "apply", fail)
    assert BwrapSupervisor(tmp_path).available is True


def test_refresh_reapplies_only_when_nexara_ip_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief nexara recreated with a new IP: the next poll (≥60 s later) rebuilds rules."""
    targets = [("172.20.0.5", 8080)]
    applied: list[int] = []
    clock = [1000.0]
    monkeypatch.setattr(egress, "enabled", lambda: True)
    monkeypatch.setattr(egress, "nexara_targets", lambda url: list(targets))
    monkeypatch.setattr(egress, "apply", lambda **kw: applied.append(1))
    monkeypatch.setattr("host.supervisor.time.monotonic", lambda: clock[0])
    sup = BwrapSupervisor(tmp_path, available=True)
    assert sup._egress() and applied == [1]
    targets[0] = ("172.20.0.9", 8080)
    sup.refresh_egress()  # within the interval: not even re-resolved
    assert applied == [1]
    clock[0] += 61
    sup.refresh_egress()
    assert applied == [1, 1]
    clock[0] += 61
    sup.refresh_egress()  # unchanged: no rebuild
    assert applied == [1, 1]


def test_refresh_noop_when_sandbox_down_or_filter_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(egress, "apply", lambda **kw: pytest.fail("must not apply"))
    monkeypatch.setattr(egress, "enabled", lambda: True)
    BwrapSupervisor(tmp_path, available=False).refresh_egress()
    monkeypatch.setattr(egress, "enabled", lambda: False)
    BwrapSupervisor(tmp_path, available=True).refresh_egress()


def test_failed_refresh_is_retried_next_poll(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """@brief Targets are recorded only after apply() succeeds, and resolved once."""
    targets = [("172.20.0.5", 8080)]
    resolves: list[int] = []
    outcomes = [None, egress.EgressError("x"), None]
    got: list[object] = []
    clock = [1000.0]

    def apply(**kw: Any) -> None:
        got.append(kw["targets"])
        if (o := outcomes.pop(0)) is not None:
            raise o

    def resolve(url: object) -> list[tuple[str, int]]:
        resolves.append(1)
        return list(targets)

    monkeypatch.setattr(egress, "enabled", lambda: True)
    monkeypatch.setattr(egress, "nexara_targets", resolve)
    monkeypatch.setattr(egress, "apply", apply)
    monkeypatch.setattr("host.supervisor.time.monotonic", lambda: clock[0])
    sup = BwrapSupervisor(tmp_path, available=True)
    assert sup._egress() and len(resolves) == 1  # one resolution per apply
    targets[0] = ("172.20.0.9", 8080)
    clock[0] += 61
    sup.refresh_egress()  # apply fails: old targets stay recorded
    clock[0] += 61
    sup.refresh_egress()  # so the change is still seen and retried
    assert len(resolves) == 3  # each refresh resolves once and passes the result on
    assert got == [[("172.20.0.5", 8080)], [("172.20.0.9", 8080)], [("172.20.0.9", 8080)]]
