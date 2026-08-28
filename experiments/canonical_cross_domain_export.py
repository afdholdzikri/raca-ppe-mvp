"""Research-ready exports for canonical V15 cross-domain replication."""
from __future__ import annotations

import csv
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, pstdev

from .canonical_cross_domain import RULE_IDS


def _cell(value):
    return json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value


def csv_bytes(rows):
    if not rows: return b""
    fields = []
    for row in rows:
        for key in row:
            if key not in fields: fields.append(key)
    stream = io.StringIO(newline=""); writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
    writer.writerows({key: _cell(value) for key, value in row.items()} for row in rows)
    return stream.getvalue().encode()


def aggregate(result):
    runs, cycles = result["run_rows"], result["cycle_rows"]
    summaries = []; rules = []; scenarios = []; fidelity = []
    for domain in sorted({r["domain"] for r in runs}):
        dr = [r for r in runs if r["domain"] == domain]; dc = [c for c in cycles if c["domain"] == domain]
        activated = sorted({c["selected_rule"] for c in dc})
        summaries.append({
            "domain": domain, "runs": len(dr), "valid_runs": sum(bool(r["valid_run"]) for r in dr),
            "VRR": round(mean(bool(r["valid_run"]) for r in dr), 6),
            "SVR": round(mean(bool(c["next_scenario_valid"]) for c in dc), 6),
            "rules_exercised": f"{len(activated)}/5", "RAC": round(len(activated) / 5, 6),
            "AR": round(mean(float(r["AR"]) for r in dr), 6), "DC": round(mean(float(r["DC"]) for r in dr), 6),
            "TC": round(mean(float(r["TC"]) for r in dr), 6), "CDRS": round(mean(float(r["CDRS"]) for r in dr), 6),
            "mean_latency_ms": round(mean(float(c["adaptation_latency_ms"]) for c in dc), 6),
            "std_latency_ms": round(pstdev(float(c["adaptation_latency_ms"]) for c in dc), 6),
            "bounded_rotation_count": sum(bool(c["bounded_rotation_triggered"]) for c in dc),
            "repeat_request_rate": round(mean(bool(c["repeat_required"]) for c in dc), 6),
            "assistance_distribution": dict(sorted(Counter(c["assistance"] for c in dc).items())),
            "difficulty_distribution": dict(sorted(Counter(int(c["difficulty"]) for c in dc).items())),
            "unactivated_rules": [rule for rule in RULE_IDS if rule not in activated],
        })
        for rule in RULE_IDS:
            rows = [c for c in dc if c["selected_rule"] == rule]
            rules.append({"domain": domain, "rule": rule, "activations": len(rows),
                          "cycle_percentage": round(len(rows) / len(dc), 6),
                          "execution_validity": round(mean(bool(r["rule_execution_valid"]) for r in rows), 6) if rows else None,
                          "repeat_request_rate": round(mean(bool(r["repeat_required"]) for r in rows), 6) if rows else None,
                          "bounded_rotation_count": sum(bool(r["bounded_rotation_triggered"]) for r in rows),
                          "assistance_distribution": dict(sorted(Counter(r["assistance"] for r in rows).items())),
                          "difficulty_distribution": dict(sorted(Counter(int(r["difficulty"]) for r in rows).items())),
                          "exercised": bool(rows)})
        for scenario_id, count in sorted(Counter(c["scenario_id"] for c in dc).items()):
            scenarios.append({"domain": domain, "scenario_id": scenario_id, "exposures": count,
                              "exposure_percentage": round(count / len(dc), 6)})
        fidelity.extend({"domain": domain, "dimension": key, "value": summary[key]} for summary in summaries[-1:]
                        for key in ("VRR", "SVR", "RAC", "AR", "DC", "TC", "CDRS"))
    overall_cycles = cycles; overall_runs = runs; all_rules = {c["selected_rule"] for c in cycles}
    summaries.append({"domain": "ALL", "runs": len(runs), "valid_runs": sum(bool(r["valid_run"]) for r in runs),
                      "VRR": round(mean(bool(r["valid_run"]) for r in runs), 6),
                      "SVR": round(mean(bool(c["next_scenario_valid"]) for c in cycles), 6),
                      "rules_exercised": f"{len(all_rules)}/5", "RAC": round(len(all_rules) / 5, 6),
                      "AR": round(mean(float(r["AR"]) for r in runs), 6), "DC": round(mean(float(r["DC"]) for r in runs), 6),
                      "TC": round(mean(float(r["TC"]) for r in runs), 6), "CDRS": round(mean(float(r["CDRS"]) for r in runs), 6),
                      "mean_latency_ms": round(mean(float(c["adaptation_latency_ms"]) for c in cycles), 6),
                      "std_latency_ms": round(pstdev(float(c["adaptation_latency_ms"]) for c in cycles), 6),
                      "bounded_rotation_count": sum(bool(c["bounded_rotation_triggered"]) for c in cycles),
                      "repeat_request_rate": round(mean(bool(c["repeat_required"]) for c in cycles), 6),
                      "assistance_distribution": dict(sorted(Counter(c["assistance"] for c in cycles).items())),
                      "difficulty_distribution": dict(sorted(Counter(int(c["difficulty"]) for c in cycles).items())),
                      "unactivated_rules": [r for r in RULE_IDS if r not in all_rules]})
    return summaries, rules, scenarios, fidelity


def schema_audit_markdown(audits):
    lines = ["# Canonical Cross-Domain Schema Audit", ""]
    for audit in audits:
        lines += [f"## {audit['domain']}", "", f"Status: **{audit['execution_readiness']}**", "",
                  f"Scenarios: {audit['scenario_count']}; hazards: {audit['hazard_count']}; PPE: {audit['ppe_count']}; competencies: {audit['competence_count']}.", "",
                  f"Duplicate IDs: {audit['duplicate_ids'] or 'none'}", f"Invalid references: {audit['invalid_references'] or 'none'}",
                  f"Missing urgency: {audit['missing_urgency'] or 'none'}", f"Missing risk components: {audit['missing_risk_components'] or 'none'}", ""]
    return "\n".join(lines)


def save_cross_domain(result, config, domains, output_root):
    folder = Path(output_root) / result["experiment_id"]; folder.mkdir(parents=True, exist_ok=False)
    summary, rules, scenarios, fidelity = aggregate(result)
    target = [{k: r[k] for k in ("canonical_cross_domain_run_id", "domain", "profile", "repetition", "repetition_seed", "target_reached", "episodes_to_target", "censored", "TAR")} for r in result["run_rows"]]
    configuration = {"protocol": "canonical_v15_cross_domain", "experiment_id": result["experiment_id"], "domains": list(domains), "config": config.to_dict()}
    manifest = {"method": "proposed", "canonical_parameters_frozen": True, "domain_specific_thresholds": False,
                "schema_audits": result["schema_audits"], "primary_metrics": ["VRR", "SVR", "RAC", "AR", "DC", "TC", "CDRS", "adaptation_latency_ms"],
                "secondary_synthetic_metrics": ["CCG_star", "RWCS_star", "TAR", "CER", "CMR", "SOR", "episodes_to_target"]}
    report = "# Canonical V15 Cross-Domain Replication\n\nSoftware portability and rule stability under synthetic simulation. This is not evidence of human learning effectiveness.\n\n" + "\n".join(f"- {r['domain']}: VRR={r['VRR']}, SVR={r['SVR']}, rules={r['rules_exercised']}, CDRS={r['CDRS']}" for r in summary)
    files = {
        "canonical_cross_domain_configuration.json": json.dumps(configuration, indent=2).encode(),
        "canonical_cross_domain_manifest.json": json.dumps(manifest, indent=2).encode(),
        "canonical_cross_domain_schema_audit.md": schema_audit_markdown(result["schema_audits"]).encode(),
        "canonical_cross_domain_run_results.csv": csv_bytes(result["run_rows"]),
        "canonical_cross_domain_cycle_results.csv": csv_bytes(result["cycle_rows"]),
        "canonical_cross_domain_summary.csv": csv_bytes(summary),
        "canonical_cross_domain_rule_summary.csv": csv_bytes(rules),
        "canonical_cross_domain_scenario_summary.csv": csv_bytes(scenarios),
        "canonical_cross_domain_trace_fidelity.csv": csv_bytes(fidelity),
        "canonical_cross_domain_target_attainment.csv": csv_bytes(target),
        "canonical_cross_domain_figure_data.csv": csv_bytes(summary),
        "canonical_cross_domain_report.md": report.encode(),
    }
    for name, content in files.items(): (folder / name).write_bytes(content)
    return folder
