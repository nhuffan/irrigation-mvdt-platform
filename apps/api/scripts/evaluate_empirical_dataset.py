"""Stage 5B metric specification. No changes to historical Stage 5A denominators."""

import statistics
from collections import Counter

from scripts.evaluate_research_dataset import evaluate_legacy, has_value, ratio


def evaluate_empirical(s):
    scope = s["scope"]
    legacy_scope = dict(scope)
    legacy_scope["maim_required"] = ["identity"]
    result = evaluate_legacy({**s, "scope": legacy_scope})
    result["metric_spec_version"] = "STAGE-5B-v1"
    metrics = result["metrics"]
    targets = scope["target_asset_codes"]
    assets = {a["asset_code"]: a for a in s["assets"]}
    inventory = {a["target_asset_code"]: a for a in scope["target_inventory"]}
    requirements = scope["maim_required_by_asset"]
    by_source = {r["id"]: r for r in s["sources"]}
    models = {r["id"]: r for r in s["models"]}
    doc_sources = {
        d["source_id"] for d in s["documents"] if d["file_evidence"]["accessible"]
    }
    flags = {}
    current = []
    geometry = []
    technical = []
    for code in targets:
        a = assets.get(code)
        aid = a["id"] if a else None
        records = {
            kind: [r for r in rs if r["asset_id"] == aid]
            for kind, rs in s["records"].items()
        }
        links = [l for l in s["model_asset_links"] if l["asset_id"] == aid]
        shape = a.get("geometry", {}).get("type") if a and a.get("geometry") else None
        expected = inventory[code]["expected_geometry_type"]
        usable = bool(
            a and a["usable_geometry"] and shape == expected and expected != "NONE"
        )
        geometry.append(
            {
                "asset_code": code,
                "expected_geometry_type": expected,
                "actual_geometry_type": shape,
                "usable": usable,
                "issue": None
                if usable
                else "Missing, invalid, or type differs from approved inventory",
            }
        )
        technical_rules = scope["technical_requirements_by_asset"].get(code, [])
        matching = []
        for rule in technical_rules:
            available = any(
                r["attribute_key"] == rule["attribute_key"]
                and r.get("unit") == rule.get("unit")
                and r["verification_status"] == "VERIFIED"
                and has_value(r)
                for r in records["technical"]
            )
            matching.append(available)
            technical.append(
                {
                    "asset_code": code,
                    "attribute_key": rule["attribute_key"],
                    "expected_unit": rule.get("unit"),
                    "available": available,
                }
            )
        conditions = sorted(
            (
                r
                for r in records["conditions"]
                if r["verification_status"] == "VERIFIED"
            ),
            key=lambda r: (r["condition_date"], r.get("created_at", ""), r["id"]),
            reverse=True,
        )
        condition = conditions[0] if conditions else None
        current.append(
            {
                "asset_code": code,
                "record_id": condition["id"] if condition else None,
                "condition_date": condition["condition_date"] if condition else None,
                "condition_status": condition["condition_status"]
                if condition
                else None,
                "source_id": condition.get("source_id") if condition else None,
            }
        )
        linked_sources = {
            r["source_id"]
            for rs in records.values()
            for r in rs
            if r.get("source_id") in by_source
        }
        linked_sources.update(
            models[l["model_id"]]["source_id"]
            for l in links
            if models[l["model_id"]].get("source_id") in by_source
        )
        represented = False
        for link in links:
            model = models[link["model_id"]]
            e = model["file_evidence"]
            placement = all(
                model.get(k) is not None
                for k in [
                    "longitude",
                    "latitude",
                    "height",
                    "heading",
                    "pitch",
                    "roll",
                    "scale",
                ]
            ) and model.get("coordinate_mode") in ("MANUAL_PLACEMENT", "GEOREFERENCED")
            if (
                link["verification_status"] == "VERIFIED"
                and model.get("source_id") in by_source
                and by_source[model["source_id"]]["verification_status"] != "REJECTED"
                and model["verification_status"] != "REJECTED"
                and placement
                and e.get("accessible")
                and link["object_key"] in e.get("object_keys", [])
                and link["object_key"] not in e.get("ambiguous_object_keys", [])
            ):
                represented = True
        flags[code] = {
            "identity": bool(a and a["name"] and a["data_status"] == "VERIFIED"),
            "category": bool(
                a and a.get("category_code") == inventory[code]["category"]
            ),
            "spatial": usable,
            "technical": bool(matching) and all(matching),
            "condition": condition is not None,
            "inspection": any(
                r["verification_status"] != "REJECTED" for r in records["inspections"]
            ),
            "repair": any(
                r["verification_status"] != "REJECTED" for r in records["repairs"]
            ),
            "maintenance": any(
                r["verification_status"] != "REJECTED" for r in records["maintenance"]
            ),
            "source": bool(linked_sources),
            "document": bool(linked_sources & doc_sources),
            "three_d": represented,
        }
    metrics["asset_identification"] = ratio(
        sum(f["identity"] for f in flags.values()), len(targets)
    )
    metrics["gis_mapping"] = ratio(
        sum(f["spatial"] for f in flags.values()), len(targets)
    )
    metrics["conditions_coverage"] = ratio(
        sum(f["condition"] for f in flags.values()), len(targets)
    )
    eligible_technical = [
        c
        for c in scope["technical_requirements_by_asset"]
        if "technical" not in scope.get("not_applicable", {}).get(c, {})
    ]
    metrics["technical_coverage"] = ratio(
        sum(flags[c]["technical"] for c in eligible_technical), len(eligible_technical)
    )
    for kind, field in [
        ("inspections", "inspection"),
        ("repairs", "repair"),
        ("maintenance", "maintenance"),
    ]:
        eligible = [
            c
            for c in targets
            if field in requirements[c]
            and field not in scope.get("not_applicable", {}).get(c, {})
        ]
        metrics[kind + "_coverage"] = ratio(
            sum(flags[c][field] for c in eligible), len(eligible)
        )
    metrics["three_d_coverage"] = ratio(
        sum(flags[c]["three_d"] for c in scope["three_d_asset_codes"]),
        len(scope["three_d_asset_codes"]),
    )
    metrics["repair_record_count"] = {
        "numerator": len(s["records"]["repairs"]),
        "denominator": None,
        "value": None,
        "status": "COUNT_ONLY_NOT_A_QUALITY_SCORE",
    }
    completeness = []
    missing = []
    for code in targets:
        required = [
            f
            for f in requirements[code]
            if f not in scope.get("not_applicable", {}).get(code, {})
        ]
        available = sum(flags[code][f] for f in required)
        completeness.append(
            {
                "asset_code": code,
                "available": available,
                "required": len(required),
                "value": available / len(required) if required else None,
            }
        )
        missing.extend(
            {"asset_code": code, "field": f} for f in required if not flags[code][f]
        )
    values = [r["value"] for r in completeness if r["value"] is not None]
    result.update(
        completeness=completeness,
        missing_fields=missing,
        current_conditions=current,
        geometry_review=geometry,
        technical_requirements=technical,
        completeness_summary={
            "mean": statistics.mean(values) if values else None,
            "median": statistics.median(values) if values else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        },
    )
    reviews = {
        (r["asset_code"], r["attribute_key"]): r
        for r in scope.get("conflict_reviews", [])
    }
    if len(reviews) != len(scope.get("conflict_reviews", [])):
        raise ValueError("Duplicate conflict review")
    used = set()
    for conflict in result["conflicts"]:
        key = (conflict["asset_code"], conflict["attribute_key"])
        review = reviews.get(key)
        if review:
            if (
                review["status"] not in ("RESOLVED", "UNRESOLVED", "RETAIN_BOTH")
                or not all(
                    review.get(k)
                    for k in ["reviewer", "evidence_reference", "rationale"]
                )
                or set(review.get("record_ids", []))
                != set(conflict["record_ids"].split("|"))
            ):
                raise ValueError("Conflict review lacks matching evidence/record IDs")
            conflict["resolution"] = review["status"]
            used.add(key)
    if set(reviews) != used:
        raise ValueError("Conflict review does not match a frozen candidate conflict")
    counts = Counter(r["resolution"] for r in result["conflicts"])
    result["conflict_review_summary"] = [
        {"status": status, "groups": counts[status]}
        for status in ("RESOLVED", "UNRESOLVED", "RETAIN_BOTH", "UNREVIEWED")
    ]
    result["limitations"].append(
        "GIS validity/type matching is not survey accuracy; source-based geometry review remains human evidence."
    )
    return result
