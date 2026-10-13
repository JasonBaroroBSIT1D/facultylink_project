"""Build kra_catalog.json from web rules.js (structure only, not scoring)."""
import json
import re
from pathlib import Path

rules = Path(__file__).resolve().parents[2] / "facultylink_web" / "assets" / "js" / "rules.js"
text = rules.read_text(encoding="utf-8")

mobile = {
    "kra1": "instruction",
    "kra2": "research",
    "kra3": "extension",
    "kra4": "professionalDevelopment",
}
codes = {"kra1": "KRA I", "kra2": "KRA II", "kra3": "KRA III", "kra4": "KRA IV"}

# All indicator objects: id + name (order preserved)
ind_pairs = re.findall(
    r'id:\s*"(kra[1-4]-[a-z]-[a-z0-9-]+)"\s*,\s*(?:\n\s*)?name:\s*"([^"]+)"',
    text,
)
# Criterion headers
crit_pairs = re.findall(
    r'id:\s*"(kra[1-4]-[a-z])"\s*,\s*\n\s*name:\s*"([^"]+)"',
    text,
)
kra_names = {}
for kid in mobile:
    m = re.search(rf'id:\s*"{kid}"\s*,\s*\n\s*code:\s*"([^"]+)"\s*,\s*\n\s*name:\s*"([^"]+)"', text)
    if m:
        codes[kid] = m.group(1)
        kra_names[kid] = m.group(2)
    else:
        m2 = re.search(rf'id:\s*"{kid}"[\s\S]{{0,160}}?name:\s*"([^"]+)"', text)
        kra_names[kid] = m2.group(1) if m2 else kid

catalog = []
for kid in ("kra1", "kra2", "kra3", "kra4"):
    criteria = []
    for cid, cname in crit_pairs:
        if not cid.startswith(kid + "-"):
            continue
        indicators = [
            {"id": iid, "name": iname}
            for iid, iname in ind_pairs
            if iid.startswith(cid + "-")
        ]
        # de-dupe indicators by id
        seen = set()
        uniq = []
        for ind in indicators:
            if ind["id"] in seen:
                continue
            seen.add(ind["id"])
            uniq.append(ind)
        criteria.append({"id": cid, "name": cname, "indicators": uniq})
    catalog.append(
        {
            "id": kid,
            "mobileKey": mobile[kid],
            "code": codes[kid],
            "name": kra_names[kid],
            "criteria": criteria,
        }
    )

out = Path(__file__).resolve().parent / "kra_catalog.json"
out.write_text(json.dumps({"kras": catalog}, indent=2), encoding="utf-8")
for k in catalog:
    print(
        k["id"],
        k["name"],
        "criteria",
        len(k["criteria"]),
        "indicators",
        sum(len(c["indicators"]) for c in k["criteria"]),
    )
print("wrote", out)
