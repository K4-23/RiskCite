# 台账 diff
from app.store.reports import compute_diff


def _f(domain, title, severity, redlines=None):
    return {"domain": domain, "title": title, "severity": severity, "redlines": redlines or []}


def test_added_and_resolved():
    diff = compute_diff([_f("tech", "新发现", "high")], [_f("tech", "旧发现", "low")])
    assert diff["added"] == [{"domain": "tech", "title": "新发现", "severity": "high"}]
    assert diff["resolved"] == [{"domain": "tech", "title": "旧发现", "severity": "low"}]


def test_changed_severity():
    diff = compute_diff([_f("tech", "同一发现", "high")], [_f("tech", "同一发现", "low")])
    assert diff["changed"] and diff["changed"][0]["severity"] == "low → high"


def test_no_change():
    diff = compute_diff([_f("tech", "A", "low")], [_f("tech", "A", "low")])
    assert not (diff["added"] or diff["resolved"] or diff["changed"])
