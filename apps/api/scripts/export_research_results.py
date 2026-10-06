"""Descriptive paired retrieval and custom questionnaire summaries; no invented observations."""

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from scripts.research_common import write_csv


def read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def number(value, minimum=0):
    n = float(value)
    if not math.isfinite(n) or n < minimum:
        raise ValueError("Invalid observation number")
    return n


def summarize_retrieval(rows):
    paired = defaultdict(dict)
    groups = defaultdict(list)
    for r in rows:
        if (
            r["workflow"] not in ("BASELINE", "MVDT")
            or r["success"] not in ("0", "1")
            or not all(
                r.get(k)
                for k in [
                    "participant_id",
                    "task_id",
                    "dataset_version",
                    "task_version",
                    "participant_group",
                    "start_time",
                    "end_time",
                    "evidence_reference",
                ]
            )
        ):
            raise ValueError("Incomplete retrieval observation")
        if r["workflow"] == "BASELINE" and not r.get("baseline_method"):
            raise ValueError("Actual baseline method is required")
        elapsed = number(r["completion_time_seconds"])
        if r["participant_group"] not in ("DOMAIN_STAFF", "RESEARCH_TEAM"):
            raise ValueError(
                "Declare DOMAIN_STAFF or RESEARCH_TEAM; controlled trials are not domain-user evidence"
            )
        started, ended = (
            datetime.fromisoformat(r["start_time"]),
            datetime.fromisoformat(r["end_time"]),
        )
        if (
            started.tzinfo is None
            or ended.tzinfo is None
            or ended < started
            or abs((ended - started).total_seconds() - elapsed) > 1
        ):
            raise ValueError(
                "Elapsed time must match timezone-aware start/end timestamps (within 1 second)"
            )
        key = (
            r["dataset_version"],
            r["task_version"],
            r["participant_group"],
            r["participant_id"],
            r["task_id"],
        )
        if r["workflow"] in paired[key]:
            raise ValueError(
                "Duplicate participant/task/workflow; analyze repeats separately"
            )
        paired[key][r["workflow"]] = {"time": elapsed, "success": r["success"] == "1"}
        groups[
            (
                r["dataset_version"],
                r["task_version"],
                r["participant_group"],
                r["task_id"],
                r["workflow"],
            )
        ].append(paired[key][r["workflow"]])
    summaries = []
    for (
        version,
        task_version,
        participant_group,
        task,
        workflow,
    ), rs in groups.items():
        successful = [r["time"] for r in rs if r["success"]]
        summaries.append(
            {
                "dataset_version": version,
                "task_version": task_version,
                "participant_group": participant_group,
                "task_id": task,
                "workflow": workflow,
                "attempts": len(rs),
                "successes": len(successful),
                "success_rate": len(successful) / len(rs),
                "successful_time_median": statistics.median(successful)
                if successful
                else None,
            }
        )
    comparisons = []
    for (
        version,
        task_version,
        participant_group,
        participant,
        task,
    ), pair in paired.items():
        b = pair.get("BASELINE")
        m = pair.get("MVDT")
        valid = bool(b and m and b["success"] and m["success"] and b["time"] > 0)
        comparisons.append(
            {
                "dataset_version": version,
                "task_version": task_version,
                "participant_group": participant_group,
                "participant_id": participant,
                "task_id": task,
                "baseline_seconds": b["time"] if b else None,
                "mvdt_seconds": m["time"] if m else None,
                "both_successful": bool(b and m and b["success"] and m["success"]),
                "comparison_eligible": valid,
                "pair_status": "PAIRED_SUCCESS"
                if valid
                else ("UNMATCHED" if not b or not m else "FAILED_OR_ZERO_BASELINE"),
                "time_reduction_percent": (b["time"] - m["time"]) / b["time"] * 100
                if valid
                else None,
            }
        )
    return summaries, comparisons


def summarize_usability(rows):
    groups = defaultdict(list)
    seen = set()
    for r in rows:
        if not all(
            r.get(k)
            for k in [
                "participant_id",
                "dataset_version",
                "participant_group",
                "evidence_reference",
            ]
        ):
            raise ValueError("Usability evidence reference required")
        if r["participant_group"] not in ("DOMAIN_STAFF", "RESEARCH_TEAM"):
            raise ValueError("Questionnaire participant group must be declared")
        key = (r["dataset_version"], r["participant_group"], r["participant_id"])
        if key in seen:
            raise ValueError("Duplicate participant questionnaire")
        seen.add(key)
        for q in range(1, 9):
            groups[(r["dataset_version"], r["participant_group"], f"Q{q}")]
            raw = r.get(f"Q{q}", "")
            if raw in ("", "NA"):
                continue
            value = number(raw, 1)
            if value not in (1, 2, 3, 4, 5):
                raise ValueError("Likert response must be an integer 1–5 or NA")
            groups[(r["dataset_version"], r["participant_group"], f"Q{q}")].append(
                value
            )
    return [
        {
            "dataset_version": v,
            "participant_group": group,
            "question": q,
            "n": len(xs),
            "mean": statistics.mean(xs) if xs else None,
            "median": statistics.median(xs) if xs else None,
            "min": min(xs) if xs else None,
            "max": max(xs) if xs else None,
            "sample_std_dev": statistics.stdev(xs) if len(xs) > 1 else None,
        }
        for (v, group, q), xs in groups.items()
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieval", type=Path, required=True)
    parser.add_argument("--usability", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    retrieval = read_csv(args.retrieval)
    usability = read_csv(args.usability)
    summaries, comparisons = summarize_retrieval(retrieval)
    scores = summarize_usability(usability)
    args.output.mkdir(parents=True, exist_ok=False)
    write_csv(
        args.output / "retrieval_results.csv",
        summaries,
        [
            "dataset_version",
            "task_version",
            "participant_group",
            "task_id",
            "workflow",
            "attempts",
            "successes",
            "success_rate",
            "successful_time_median",
        ],
    )
    write_csv(
        args.output / "retrieval_comparison.csv",
        comparisons,
        [
            "dataset_version",
            "task_version",
            "participant_group",
            "participant_id",
            "task_id",
            "baseline_seconds",
            "mvdt_seconds",
            "both_successful",
            "comparison_eligible",
            "pair_status",
            "time_reduction_percent",
        ],
    )
    write_csv(
        args.output / "usability_results.csv",
        scores,
        [
            "dataset_version",
            "participant_group",
            "question",
            "n",
            "mean",
            "median",
            "min",
            "max",
            "sample_std_dev",
        ],
    )
    (args.output / "status.json").write_text(
        json.dumps(
            {
                "retrieval_status": "OBSERVED" if retrieval else "NOT_COLLECTED",
                "usability_status": "OBSERVED" if usability else "NOT_COLLECTED",
                "instrument": "Custom 8-item questionnaire; not SUS",
                "inference": "Descriptive only; no statistical improvement claim",
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
