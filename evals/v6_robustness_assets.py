from __future__ import annotations

import csv
import json
import math
import platform
import random
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
RAW_DIR = RESULTS_DIR / "raw"
TABLES_DIR = RESULTS_DIR / "tables"
FIGURES_DIR = RESULTS_DIR / "figures"
AGG_DIR = RESULTS_DIR / "aggregate"
RELEASE_DIR = RESULTS_DIR / "release"
MANUSCRIPT_DIR = ROOT / "manuscript"
SEED = 42
BOOTSTRAP_SAMPLES = 4000

TRACK_A_MODES = [
    "direct_answer",
    "mindstate_only",
    "mindstate_mirror",
    "mindstate_mirror_local_memory",
    "mindstate_mirror_dual_memory",
]
TRACK_B_MODES = [
    "direct_answer",
    "mindstate_mirror_local_memory",
    "mindstate_mirror_dual_memory",
]
TRACK_C_MODES = TRACK_B_MODES
MODE_LABELS = {
    "direct_answer": "Direct",
    "mindstate_only": "MindState",
    "mindstate_mirror": "Mirror",
    "mindstate_mirror_local_memory": "Mirror+Local",
    "mindstate_mirror_dual_memory": "Mirror+Dual",
}
CATEGORY_LABELS = {
    "constants_and_units": "Constants and units",
    "condition_sensitive_properties": "Condition-sensitive properties",
    "abstention_boundary_cases": "Abstention-boundary cases",
}


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


TITLE_FONT = load_font(34, bold=True)
LABEL_FONT = load_font(22)
TEXT_FONT = load_font(18)
TICK_FONT = load_font(16)
SMALL_FONT = load_font(15)
BG = "white"
AX = (40, 40, 40)
GRID = (220, 220, 220)
COLORS = {
    "direct_answer": (91, 121, 167),
    "mindstate_only": (160, 181, 205),
    "mindstate_mirror": (234, 170, 94),
    "mindstate_mirror_local_memory": (96, 165, 126),
    "mindstate_mirror_dual_memory": (167, 96, 145),
}


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def _draw_rotated_text(
    img: Image.Image, position: tuple[int, int], text: str, font: ImageFont.ImageFont, fill: tuple[int, int, int]
) -> None:
    dummy = Image.new("RGBA", (10, 10), (255, 255, 255, 0))
    draw = ImageDraw.Draw(dummy)
    width, height = _text_size(draw, text, font)
    txt = Image.new("RGBA", (width + 10, height + 10), (255, 255, 255, 0))
    td = ImageDraw.Draw(txt)
    td.text((5, 5), text, font=font, fill=fill)
    rotated = txt.rotate(90, expand=1)
    img.alpha_composite(rotated, dest=position)


def _load_raw_results() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(RAW_DIR.glob("*/*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_path"] = str(path)
        rows.append(payload)
    return rows


def _binary_mean(items: list[bool | int | float]) -> float:
    if not items:
        return 0.0
    return sum(bool(x) if isinstance(x, bool) else float(x) for x in items) / len(items)


def _bootstrap_ci(values: list[float], *, seed: int = SEED, n_boot: int = BOOTSTRAP_SAMPLES) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return values[0], values[0]
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(0.025 * len(means))]
    hi = means[int(0.975 * len(means))]
    return lo, hi


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _extract_record(payload: dict[str, Any]) -> dict[str, Any]:
    case = payload["case"]
    run = payload["run"]
    scoring = payload["scoring"]
    metrics = scoring["metrics"]
    pass_case = not scoring["failure_reasons"]
    return {
        "case_id": case["case_id"],
        "track": case["track"],
        "family": case["family"],
        "mode": run["mode"],
        "pass_case": pass_case,
        "metrics": metrics,
        "raw_output": run["raw_output"],
        "main_claim": run["final_state"]["main_claim"],
        "final_verdict": run["final_verdict"]["verdict"],
        "retrieved_lessons": run.get("retrieved_lessons", []),
        "memory_matches": run.get("memory_matches", {}),
        "sequence_id": case.get("sequence_id"),
        "sequence_step": case.get("sequence_step"),
        "ground_truth_source": case["ground_truth_source"],
        "prompt": case["prompt"],
        "goal": case["goal"],
        "failure_reasons": scoring["failure_reasons"],
        "path": payload["_path"],
    }


def _summarize_track_a(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    uncertainty_rows: list[dict[str, Any]] = []
    variability_rows: list[dict[str, Any]] = []
    for mode in TRACK_A_MODES:
        items = [r for r in records if r["mode"] == mode]
        metrics = {
            "pass_rate": [1.0 if r["pass_case"] else 0.0 for r in items],
            "correction_retention_rate": [1.0 if r["metrics"]["correction_retained"] else 0.0 for r in items],
            "unsupported_certainty_rate": [1.0 if r["metrics"]["unsupported_certainty_present"] else 0.0 for r in items],
        }
        row = {"mode": mode, "case_count": len(items)}
        for metric, values in metrics.items():
            point = sum(values) / len(values)
            lo, hi = _bootstrap_ci(values)
            row[metric] = round(point, 4)
            row[f"{metric}_ci_low"] = round(lo, 4)
            row[f"{metric}_ci_high"] = round(hi, 4)
        uncertainty_rows.append(row)
    families = sorted({r["family"] for r in records})
    for family in families:
        for mode in TRACK_A_MODES:
            items = [r for r in records if r["family"] == family and r["mode"] == mode]
            passes = [1.0 if r["pass_case"] else 0.0 for r in items]
            variability_rows.append(
                {
                    "family": family,
                    "mode": mode,
                    "case_count": len(items),
                    "pass_rate": round(sum(passes) / len(passes), 4),
                    "case_spread_std": round(statistics.pstdev(passes), 4) if len(passes) > 1 else 0.0,
                    "mean_revisions": round(sum(r["metrics"]["revision_count"] for r in items) / len(items), 4),
                }
            )
    return uncertainty_rows, variability_rows


def _summarize_track_b(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    uncertainty_rows: list[dict[str, Any]] = []
    variability_rows: list[dict[str, Any]] = []
    for family in sorted({r["family"] for r in records}):
        for mode in TRACK_B_MODES:
            items = [r for r in records if r["family"] == family and r["mode"] == mode]
            metric_map = {
                "pass_rate": [1.0 if r["pass_case"] else 0.0 for r in items],
                "condition_preservation": [1.0 if r["metrics"]["condition_preserved"] else 0.0 for r in items],
                "abstention_precision": [1.0 if r["metrics"]["abstained_or_qualified"] else 0.0 for r in items],
            }
            row = {"category": family, "mode": mode, "case_count": len(items)}
            for metric, values in metric_map.items():
                point = sum(values) / len(values)
                lo, hi = _bootstrap_ci(values)
                row[metric] = round(point, 4)
                row[f"{metric}_ci_low"] = round(lo, 4)
                row[f"{metric}_ci_high"] = round(hi, 4)
            uncertainty_rows.append(row)

            passes = [1.0 if r["pass_case"] else 0.0 for r in items]
            condition = [1.0 if r["metrics"]["condition_preserved"] else 0.0 for r in items]
            abstain = [1.0 if r["metrics"]["abstained_or_qualified"] else 0.0 for r in items]
            variability_rows.append(
                {
                    "category": family,
                    "mode": mode,
                    "case_count": len(items),
                    "pass_rate": round(sum(passes) / len(passes), 4),
                    "pass_spread_std": round(statistics.pstdev(passes), 4) if len(passes) > 1 else 0.0,
                    "condition_spread_std": round(statistics.pstdev(condition), 4) if len(condition) > 1 else 0.0,
                    "abstention_spread_std": round(statistics.pstdev(abstain), 4) if len(abstain) > 1 else 0.0,
                }
            )
    return uncertainty_rows, variability_rows


def _summarize_track_c(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    uncertainty_rows: list[dict[str, Any]] = []
    family_rows: list[dict[str, Any]] = []
    for mode in TRACK_C_MODES:
        items = [r for r in records if r["mode"] == mode and r["case_id"].endswith("-S2")]
        metric_map = {
            "cross_session_correction_retention_rate": [1.0 if r["metrics"]["correction_retained"] else 0.0 for r in items],
            "error_recurrence_rate": [
                1.0 if (r["metrics"]["concept_mixing_present"] or r["metrics"]["unsupported_certainty_present"]) else 0.0
                for r in items
            ],
            "memory_scope_isolation_rate": [1.0 if r["metrics"]["project_local_precedence_preserved"] else 0.0 for r in items],
        }
        row = {"mode": mode, "sequence_count": len(items)}
        for metric, values in metric_map.items():
            point = sum(values) / len(values)
            lo, hi = _bootstrap_ci(values)
            row[metric] = round(point, 4)
            row[f"{metric}_ci_low"] = round(lo, 4)
            row[f"{metric}_ci_high"] = round(hi, 4)
        uncertainty_rows.append(row)
    families = sorted({r["family"] for r in records if r["case_id"].endswith("-S2")})
    for family in families:
        for mode in TRACK_C_MODES:
            items = [r for r in records if r["family"] == family and r["mode"] == mode and r["case_id"].endswith("-S2")]
            values = [1.0 if r["metrics"]["correction_retained"] else 0.0 for r in items]
            family_rows.append(
                {
                    "family": family,
                    "mode": mode,
                    "sequence_count": len(items),
                    "retention_rate": round(sum(values) / len(values), 4),
                    "retention_spread_std": round(statistics.pstdev(values), 4) if len(values) > 1 else 0.0,
                }
            )
    return uncertainty_rows, family_rows


def _overview_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    track_meta = {
        "A": ("Five-way ablation", "30", "5 modes", "150", "pass rate; condition preservation; correction retention", "Isolate control-structure gains"),
        "B": ("Science-facing benchmark", "36", "3 modes", "108", "pass rate; condition preservation; abstention precision", "Test evidence-bounded scientific behavior"),
        "C": ("Longitudinal correction retention", "20", "3 modes", "60", "retention; recurrence; scope isolation", "Test cross-session correction carryover"),
    }
    for track, meta in track_meta.items():
        name, cases, modes, runs, metrics, purpose = meta
        rows.append(
            {
                "track": track,
                "name": name,
                "case_count": cases,
                "modes": modes,
                "total_runs": runs,
                "primary_metrics": metrics,
                "scientific_purpose": purpose,
            }
        )
    return rows


def _select_case_examples(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def row_for(rec: dict[str, Any], label: str, observation: str) -> dict[str, Any]:
        output = rec["raw_output"].replace("\n", " ")
        if len(output) > 180:
            output = output[:177] + "..."
        return {
            "label": label,
            "track": rec["track"],
            "case_id": rec["case_id"],
            "mode": rec["mode"],
            "family": rec["family"],
            "final_verdict": rec["final_verdict"],
            "observation": observation,
            "output_excerpt": output,
        }

    examples: list[dict[str, Any]] = []
    direct_hallucination = next(
        r
        for r in records
        if r["case_id"] == "B3-01" and r["mode"] == "direct_answer"
    )
    examples.append(
        row_for(
            direct_hallucination,
            "Direct baseline ignores condition mismatch",
            "The direct baseline returns the 1 atm boiling point for a 2 atm query, despite a mismatch warning in the local evidence pack.",
        )
    )
    reflective_boundary = next(
        r
        for r in records
        if r["case_id"] == "B3-01" and r["mode"] == "mindstate_mirror_dual_memory"
    )
    examples.append(
        row_for(
            reflective_boundary,
            "Reflective mode abstains under unsupported conditions",
            "The reflective mode preserves the local condition boundary and exits with a qualified or deferred answer instead of asserting a fabricated value.",
        )
    )
    over_deferral = next(
        r
        for r in records
        if r["case_id"] == "B2-01" and r["mode"] == "mindstate_mirror_local_memory"
    )
    examples.append(
        row_for(
            over_deferral,
            "Condition recognition without calibrated answer yield",
            "The reflective mode recognizes the condition-sensitive structure of the task but continues revising until it defers, revealing the current calibration gap.",
        )
    )
    correction_carryover = next(
        r
        for r in records
        if r["case_id"] == "C-Seq03-S2" and r["mode"] == "mindstate_mirror_dual_memory"
    )
    examples.append(
        row_for(
            correction_carryover,
            "Correction lineage constrains later claims",
            "A later step reuses prior correction lessons about unsupported pressure conditions and waits instead of overgeneralizing from the 1 atm record.",
        )
    )
    return examples


def _draw_legend(draw: ImageDraw.ImageDraw, items: list[tuple[str, tuple[int, int, int]]], start_x: int, start_y: int) -> None:
    x = start_x
    for label, color in items:
        draw.rectangle((x, start_y + 6, x + 20, start_y + 26), fill=color, outline=color)
        draw.text((x + 28, start_y), label, font=TEXT_FONT, fill=AX)
        width, _ = _text_size(draw, label, TEXT_FONT)
        x += width + 72


def _draw_axes(draw: ImageDraw.ImageDraw, x0: int, y0: int, x1: int, y1: int, title: str) -> None:
    draw.text((x0, y0 - 40), title, font=LABEL_FONT, fill=AX)
    draw.line((x0, y1, x1, y1), fill=AX, width=3)
    draw.line((x0, y0, x0, y1), fill=AX, width=3)
    for tick in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        y = y1 - int((y1 - y0) * tick)
        draw.line((x0, y, x1, y), fill=GRID, width=1)
        label = f"{tick:.1f}"
        tw, th = _text_size(draw, label, TICK_FONT)
        draw.text((x0 - tw - 10, y - th / 2), label, font=TICK_FONT, fill=AX)


def _bar_positions(x0: int, x1: int, groups: int, series: int, gap: int = 26, inner_gap: int = 10) -> list[tuple[int, int, int, list[int]]]:
    plot_w = x1 - x0
    group_w = (plot_w - gap * (groups + 1)) / groups
    bar_w = (group_w - inner_gap * (series - 1)) / series
    positions = []
    cur = x0 + gap
    for _ in range(groups):
        xs = []
        for i in range(series):
            xs.append(int(cur + i * (bar_w + inner_gap)))
        positions.append((int(cur), int(group_w), int(bar_w), xs))
        cur += group_w + gap
    return positions


def _draw_ci(draw: ImageDraw.ImageDraw, x_center: int, y0: int, y1: int) -> None:
    draw.line((x_center, y0, x_center, y1), fill=AX, width=2)
    draw.line((x_center - 8, y0, x_center + 8, y0), fill=AX, width=2)
    draw.line((x_center - 8, y1, x_center + 8, y1), fill=AX, width=2)


def _draw_track_a_figure(track_a_uncertainty: list[dict[str, Any]]) -> None:
    img = Image.new("RGBA", (1800, 1120), BG)
    draw = ImageDraw.Draw(img)
    draw.text((70, 34), "Figure 2. Track A Ablation Results with Bootstrap Intervals", font=TITLE_FONT, fill=AX)
    draw.text((70, 86), "Bars show point estimates; error bars show 95% bootstrap intervals over case-level resampling.", font=TEXT_FONT, fill=AX)
    panels = [
        ("Pass rate", "pass_rate"),
        ("Correction retention", "correction_retention_rate"),
        ("Unsupported certainty", "unsupported_certainty_rate"),
    ]
    coords = [(90, 220, 560, 860), (670, 220, 1140, 860), (1250, 220, 1720, 860)]
    for (title, key), (x0, y0, x1, y1) in zip(panels, coords):
        _draw_axes(draw, x0, y0, x1, y1, title)
        positions = _bar_positions(x0, x1, len(track_a_uncertainty), 1)
        for row, (_, group_w, bar_w, xs) in zip(track_a_uncertainty, positions):
            value = float(row[key])
            lo = float(row[f"{key}_ci_low"])
            hi = float(row[f"{key}_ci_high"])
            bx = xs[0] + int(group_w * 0.18)
            bw = int(group_w * 0.64)
            top = y1 - int((y1 - y0) * value)
            mode = row["mode"]
            draw.rectangle((bx, top, bx + bw, y1), fill=COLORS[mode], outline=COLORS[mode])
            ci_top = y1 - int((y1 - y0) * hi)
            ci_bottom = y1 - int((y1 - y0) * lo)
            _draw_ci(draw, bx + bw // 2, ci_top, ci_bottom)
            label = MODE_LABELS[mode].replace("+", "+\n") if len(MODE_LABELS[mode]) > 10 else MODE_LABELS[mode]
            ly = y1 + 10
            for line in label.split("\n"):
                tw, th = _text_size(draw, line, TICK_FONT)
                draw.text((bx + (bw - tw) / 2, ly), line, font=TICK_FONT, fill=AX)
                ly += th + 2
            v = f"{value:.2f}"
            tw, th = _text_size(draw, v, TICK_FONT)
            draw.text((bx + (bw - tw) / 2, top - th - 6), v, font=TICK_FONT, fill=AX)
        _draw_rotated_text(img, (x0 - 82, y0 + (y1 - y0) // 2 - 40), "Rate", LABEL_FONT, AX)
    _draw_legend(draw, [(MODE_LABELS[m], COLORS[m]) for m in TRACK_A_MODES], 180, 970)
    img.convert("RGB").save(FIGURES_DIR / "figure2_ablation.png", quality=95)


def _draw_track_b_figure(track_b_uncertainty: list[dict[str, Any]]) -> None:
    img = Image.new("RGBA", (1800, 1120), BG)
    draw = ImageDraw.Draw(img)
    draw.text((70, 34), "Figure 3. Science-Facing Benchmark Results with Bootstrap Intervals", font=TITLE_FONT, fill=AX)
    draw.text((70, 86), "Category-level rates are shown with 95% bootstrap intervals based on case resampling.", font=TEXT_FONT, fill=AX)
    panels = [
        ("Pass rate", "pass_rate"),
        ("Condition preservation", "condition_preservation"),
        ("Abstention precision", "abstention_precision"),
    ]
    coords = [(90, 220, 560, 860), (670, 220, 1140, 860), (1250, 220, 1720, 860)]
    category_order = ["constants_and_units", "condition_sensitive_properties", "abstention_boundary_cases"]
    for (title, key), (x0, y0, x1, y1) in zip(panels, coords):
        _draw_axes(draw, x0, y0, x1, y1, title)
        positions = _bar_positions(x0, x1, len(category_order), len(TRACK_B_MODES), gap=40, inner_gap=10)
        for category, (_, group_w, bar_w, xs) in zip(category_order, positions):
            for mode, bx in zip(TRACK_B_MODES, xs):
                row = next(r for r in track_b_uncertainty if r["category"] == category and r["mode"] == mode)
                value = float(row[key])
                lo = float(row[f"{key}_ci_low"])
                hi = float(row[f"{key}_ci_high"])
                top = y1 - int((y1 - y0) * value)
                draw.rectangle((bx, top, bx + bar_w, y1), fill=COLORS[mode], outline=COLORS[mode])
                ci_top = y1 - int((y1 - y0) * hi)
                ci_bottom = y1 - int((y1 - y0) * lo)
                _draw_ci(draw, bx + bar_w // 2, ci_top, ci_bottom)
                label = f"{value:.2f}"
                tw, th = _text_size(draw, label, TICK_FONT)
                draw.text((bx + (bar_w - tw) / 2, top - th - 6), label, font=TICK_FONT, fill=AX)
            cx = xs[0] + ((xs[-1] + bar_w) - xs[0]) / 2
            ly = y1 + 10
            for line in CATEGORY_LABELS[category].replace(" and ", "\nand ").replace("-", "-\n").split("\n"):
                tw, th = _text_size(draw, line, TICK_FONT)
                draw.text((cx - tw / 2, ly), line, font=TICK_FONT, fill=AX)
                ly += th + 1
            _draw_rotated_text(img, (x0 - 82, y0 + (y1 - y0) // 2 - 40), "Rate", LABEL_FONT, AX)
    _draw_legend(draw, [(MODE_LABELS[m], COLORS[m]) for m in TRACK_B_MODES], 540, 972)
    img.convert("RGB").save(FIGURES_DIR / "figure3_science_qa.png", quality=95)


def _draw_track_c_figure(track_c_uncertainty: list[dict[str, Any]]) -> None:
    img = Image.new("RGBA", (1800, 1100), BG)
    draw = ImageDraw.Draw(img)
    draw.text((70, 34), "Figure 4. Longitudinal Memory Outcomes with Bootstrap Intervals", font=TITLE_FONT, fill=AX)
    draw.text((70, 86), "Step-two sequence rates are shown with 95% bootstrap intervals over sequence resampling.", font=TEXT_FONT, fill=AX)
    x0, y0, x1, y1 = 130, 220, 1680, 820
    _draw_axes(draw, x0, y0, x1, y1, "Track C aggregate metrics")
    metrics = [
        ("Retention", "cross_session_correction_retention_rate"),
        ("Recurrence", "error_recurrence_rate"),
        ("Scope isolation", "memory_scope_isolation_rate"),
    ]
    positions = _bar_positions(x0, x1, len(metrics), len(TRACK_C_MODES), gap=55, inner_gap=12)
    for (label, key), (_, group_w, bar_w, xs) in zip(metrics, positions):
        for mode, bx in zip(TRACK_C_MODES, xs):
            row = next(r for r in track_c_uncertainty if r["mode"] == mode)
            value = float(row[key])
            lo = float(row[f"{key}_ci_low"])
            hi = float(row[f"{key}_ci_high"])
            top = y1 - int((y1 - y0) * value)
            draw.rectangle((bx, top, bx + bar_w, y1), fill=COLORS[mode], outline=COLORS[mode])
            ci_top = y1 - int((y1 - y0) * hi)
            ci_bottom = y1 - int((y1 - y0) * lo)
            _draw_ci(draw, bx + bar_w // 2, ci_top, ci_bottom)
            txt = f"{value:.2f}"
            tw, th = _text_size(draw, txt, TICK_FONT)
            draw.text((bx + (bar_w - tw) / 2, top - th - 6), txt, font=TICK_FONT, fill=AX)
        cx = xs[0] + ((xs[-1] + bar_w) - xs[0]) / 2
        ly = y1 + 10
        for line in label.split(" "):
            tw, th = _text_size(draw, line, TICK_FONT)
            draw.text((cx - tw / 2, ly), line, font=TICK_FONT, fill=AX)
            ly += th + 1
    _draw_rotated_text(img, (x0 - 82, y0 + (y1 - y0) // 2 - 40), "Rate", LABEL_FONT, AX)
    _draw_legend(draw, [(MODE_LABELS[m], COLORS[m]) for m in TRACK_C_MODES], 610, 918)
    img.convert("RGB").save(FIGURES_DIR / "figure4_longitudinal.png", quality=95)


def _draw_heatmap(track_a_variability: list[dict[str, Any]]) -> None:
    families = sorted({row["family"] for row in track_a_variability})
    img = Image.new("RGBA", (1500, 940), BG)
    draw = ImageDraw.Draw(img)
    draw.text((70, 34), "Figure 5. Track A Family-Level Pass-Rate Heatmap", font=TITLE_FONT, fill=AX)
    draw.text((70, 86), "Cell values show pass rates by family and mode, highlighting where gains are concentrated.", font=TEXT_FONT, fill=AX)
    x0, y0 = 260, 180
    cell_w, cell_h = 190, 92
    for j, mode in enumerate(TRACK_A_MODES):
        label = MODE_LABELS[mode].replace("+", "+\n") if len(MODE_LABELS[mode]) > 10 else MODE_LABELS[mode]
        ly = y0 - 70
        for line in label.split("\n"):
            tw, th = _text_size(draw, line, TICK_FONT)
            draw.text((x0 + j * cell_w + (cell_w - tw) / 2, ly), line, font=TICK_FONT, fill=AX)
            ly += th + 1
    for i, family in enumerate(families):
        fam_label = family.replace("_", " ")
        tw, th = _text_size(draw, fam_label, TICK_FONT)
        draw.text((40, y0 + i * cell_h + (cell_h - th) / 2), fam_label, font=TICK_FONT, fill=AX)
        for j, mode in enumerate(TRACK_A_MODES):
            row = next(r for r in track_a_variability if r["family"] == family and r["mode"] == mode)
            val = float(row["pass_rate"])
            color = (
                int(245 - 120 * val),
                int(245 - 100 * val),
                int(255 - 60 * val),
            )
            x = x0 + j * cell_w
            y = y0 + i * cell_h
            draw.rectangle((x, y, x + cell_w - 8, y + cell_h - 8), fill=color, outline=AX, width=1)
            txt = f"{val:.2f}"
            tw, th = _text_size(draw, txt, LABEL_FONT)
            draw.text((x + (cell_w - 8 - tw) / 2, y + 18), txt, font=LABEL_FONT, fill=AX)
            spread = f"sd={row['case_spread_std']:.2f}"
            sw, sh = _text_size(draw, spread, SMALL_FONT)
            draw.text((x + (cell_w - 8 - sw) / 2, y + 52), spread, font=SMALL_FONT, fill=AX)
    img.convert("RGB").save(FIGURES_DIR / "figure5_track_a_heatmap.png", quality=95)


def _draw_figure1() -> None:
    img = Image.new("RGBA", (1800, 1080), BG)
    draw = ImageDraw.Draw(img)
    draw.text((70, 36), "Figure 1. Mirror Reflection Agent Design Envelope and Validated Control Loop", font=TITLE_FONT, fill=AX)
    draw.text((70, 88), "The current benchmark validates the explicit-state, typed-verdict, and memory-mediated control loop highlighted below.", font=TEXT_FONT, fill=AX)

    # Main chain boxes
    boxes = [
        ("Input task", (90, 320, 250, 430), (210, 228, 245)),
        ("Evidence routing", (320, 250, 560, 500), (220, 239, 225)),
        ("MindState", (660, 320, 860, 430), (247, 231, 181)),
        ("MirrorVerdict", (940, 320, 1170, 430), (234, 205, 205)),
        ("Action selection\\nrevise / retrieve / wait / pass", (1240, 285, 1550, 465), (224, 230, 250)),
        ("Output", (1610, 320, 1735, 430), (210, 228, 245)),
    ]
    for label, (x0, y0, x1, y1), fill in boxes:
        draw.rounded_rectangle((x0, y0, x1, y1), radius=18, fill=fill, outline=AX, width=3)
        ly = y0 + 26
        for line in label.split("\\n"):
            tw, th = _text_size(draw, line, LABEL_FONT)
            draw.text((x0 + (x1 - x0 - tw) / 2, ly), line, font=LABEL_FONT, fill=AX)
            ly += th + 10
    # Memory and knowledge
    draw.rounded_rectangle((330, 610, 760, 840), radius=18, fill=(228, 239, 228), outline=AX, width=3)
    draw.text((370, 640), "Scientific evidence layer", font=LABEL_FONT, fill=AX)
    draw.text((370, 690), "Local CODATA / NIST / PubChem /", font=TEXT_FONT, fill=AX)
    draw.text((370, 720), "ChEBI / Materials Project caches", font=TEXT_FONT, fill=AX)
    draw.text((370, 765), "Supports deterministic provenance-aware lookup", font=TEXT_FONT, fill=AX)

    draw.rounded_rectangle((980, 610, 1440, 840), radius=18, fill=(233, 228, 244), outline=AX, width=3)
    draw.text((1030, 640), "Memory layer", font=LABEL_FONT, fill=AX)
    draw.text((1030, 690), "Project-local memory", font=TEXT_FONT, fill=AX)
    draw.text((1030, 720), "Optional shared-growth memory", font=TEXT_FONT, fill=AX)
    draw.text((1030, 765), "Writes correction lineage and reusable constraints", font=TEXT_FONT, fill=AX)

    # Validated region
    draw.rounded_rectangle((610, 210, 1480, 880), radius=24, outline=(87, 123, 182), width=5)
    draw.text((1170, 225), "Validated in the current benchmark", font=SMALL_FONT, fill=(87, 123, 182))
    draw.rounded_rectangle((70, 200, 1750, 900), radius=26, outline=(170, 170, 170), width=2)
    draw.text((80, 210), "Full design envelope", font=SMALL_FONT, fill=(120, 120, 120))

    # Arrows
    arrows = [
        (250, 375, 320, 375),
        (560, 375, 660, 375),
        (860, 375, 940, 375),
        (1170, 375, 1240, 375),
        (1550, 375, 1610, 375),
        (760, 725, 760, 430),
        (1210, 610, 1210, 430),
        (1330, 465, 1210, 610),
    ]
    for x0, y0, x1, y1 in arrows:
        draw.line((x0, y0, x1, y1), fill=AX, width=4)
        # simple arrow heads
        if x1 > x0 and abs(y1 - y0) < 4:
            draw.polygon([(x1, y1), (x1 - 18, y1 - 8), (x1 - 18, y1 + 8)], fill=AX)
        elif y1 < y0 and abs(x1 - x0) < 4:
            draw.polygon([(x1, y1), (x1 - 8, y1 + 18), (x1 + 8, y1 + 18)], fill=AX)
        else:
            draw.polygon([(x1, y1), (x1 - 14, y1 - 8), (x1 - 5, y1 - 18)], fill=AX)
    img.convert("RGB").save(MANUSCRIPT_DIR / "Figure 1.png", quality=95)


def _write_release_assets() -> None:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=False).stdout
    except Exception:
        freeze = ""
    env_text = [
        f"generated_utc={datetime.now(timezone.utc).isoformat()}",
        f"python={sys.version}",
        f"platform={platform.platform()}",
        "",
        "[pip_freeze]",
        freeze.strip(),
    ]
    (RELEASE_DIR / "environment_snapshot.txt").write_text("\n".join(env_text), encoding="utf-8")
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_policy": "An anonymized review package should include manuscript sources, raw benchmark outputs, aggregate summaries, table CSVs, figure scripts, and the environment snapshot.",
        "included_local_artifacts": [
            "results/raw/",
            "results/aggregate/",
            "results/tables/",
            "results/figures/",
            "results/release/environment_snapshot.txt",
        ],
        "non_public_limitations": [
            "The current local scientific caches are repository-bundled snapshots rather than externally hosted review data services.",
            "No external cloud judge or proprietary evaluation service is required for the reported metrics.",
        ],
    }
    _write_json(RELEASE_DIR / "release_manifest.json", manifest)


def main() -> None:
    payloads = _load_raw_results()
    records = [_extract_record(p) for p in payloads]
    track_a = [r for r in records if r["track"] == "A"]
    track_b = [r for r in records if r["track"] == "B"]
    track_c = [r for r in records if r["track"] == "C"]

    track_a_uncertainty, track_a_variability = _summarize_track_a(track_a)
    track_b_uncertainty, track_b_variability = _summarize_track_b(track_b)
    track_c_uncertainty, track_c_families = _summarize_track_c(track_c)
    examples = _select_case_examples(records)
    overview = _overview_rows(records)

    _write_csv(TABLES_DIR / "table0_benchmark_overview.csv", overview)
    _write_csv(TABLES_DIR / "table1a_track_a_uncertainty.csv", track_a_uncertainty)
    _write_csv(TABLES_DIR / "table2a_track_a_family_variability.csv", track_a_variability)
    _write_csv(TABLES_DIR / "table3a_track_b_uncertainty.csv", track_b_uncertainty)
    _write_csv(TABLES_DIR / "table3b_track_b_variability.csv", track_b_variability)
    _write_csv(TABLES_DIR / "table5a_track_c_uncertainty.csv", track_c_uncertainty)
    _write_csv(TABLES_DIR / "table5b_track_c_family_breakdown.csv", track_c_families)
    _write_csv(TABLES_DIR / "table6_representative_cases.csv", examples)

    _write_json(
        AGG_DIR / "robustness_summary.json",
        {
            "track_a_uncertainty": track_a_uncertainty,
            "track_b_uncertainty": track_b_uncertainty,
            "track_c_uncertainty": track_c_uncertainty,
            "representative_cases": examples,
        },
    )

    _draw_track_a_figure(track_a_uncertainty)
    _draw_track_b_figure(track_b_uncertainty)
    _draw_track_c_figure(track_c_uncertainty)
    _draw_heatmap(track_a_variability)
    _draw_figure1()
    _write_release_assets()


if __name__ == "__main__":
    main()
