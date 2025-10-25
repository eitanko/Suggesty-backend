from collections import defaultdict, OrderedDict
from statistics import mean
from typing import Dict, List, Tuple, Any, Optional

from utils.norm_and_compare import compare_elements
from utils.url_utils import extract_base_url_pattern, urls_match_pattern, urls_glob_match

def _to_ms(ts: Any) -> Optional[int]:
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return int(ts)
    try:
        return int(ts.timestamp() * 1000)
    except Exception:
        return None

def generate_step_insights_from_ideal_path(
    ideal_path_steps: List[Dict[str, Any]],
    completed_journeys: List[List[Dict[str, Any]]],
    threshold: float,
    repeated_events: Optional[Dict[Tuple[str, str], float]] = None,
    drop_off_events: Optional[Dict[Tuple[str, str], float]] = None,
    *,
    debug: bool = True,               # <— turn on verbose prints
) -> Tuple[Dict[str, Any], List[Tuple[str, str, str, float]]]:

    repeated_events = repeated_events or {}
    drop_off_events = drop_off_events or {}

    # 0) Precompute patterns
    ideal_with_patterns = []
    for s in ideal_path_steps:
        ideal_with_patterns.append({
            **s,
            "url_pattern": extract_base_url_pattern(s["url"]),
        })

    if debug:
        print("\n[DEBUG] Ideal steps with patterns:")
        for idx, s in enumerate(ideal_with_patterns, start=1):
            print(f"  step_{idx}: step={s.get('step')} url={s['url']} pattern={s['url_pattern']} xPath={s.get('xPath')}")

    # 1) Ideal durations
    ideal_durations: Dict[Tuple[str, str], float] = {}
    for i in range(1, len(ideal_with_patterns)):
        prev = ideal_with_patterns[i - 1]
        curr = ideal_with_patterns[i]
        key = (curr["url"], curr["xPath"])
        prev_ms = _to_ms(prev.get("timestamp"))
        curr_ms = _to_ms(curr.get("timestamp"))
        if prev_ms is None or curr_ms is None:
            continue
        ideal_durations[key] = max(0.0, float(curr_ms - prev_ms))
    if debug:
        print("\n[DEBUG] Ideal durations (ms) keyed by (url, element of dest step):")
        for k, v in ideal_durations.items():
            print("  ", k, "=>", v)

    # 2) Actual times
    step_stats: Dict[Tuple[str, str], Dict[str, Any]] = defaultdict(lambda: {
        "times": [],
        "delayed_sessions": set(),
        "all_sessions": set(),
    })
    delayed_events: List[Tuple[str, str, str, float]] = []

    for journey_idx, journey in enumerate(completed_journeys, start=1):
        if not journey:
            continue
        session_id = journey[0].get("session_id") or "unknown"
        if debug:
            print(f"\n[DEBUG] Journey #{journey_idx} session={session_id}, events={len(journey)}")

        for i in range(1, len(journey)):
            prev_event = journey[i - 1]
            curr_event = journey[i]

            prev_ms = _to_ms(prev_event.get("timestamp"))
            curr_ms = _to_ms(curr_event.get("timestamp"))
            if prev_ms is None or curr_ms is None or curr_ms < prev_ms:
                if debug:
                    print(f"    pair {i-1}->{i}: BAD TIMESTAMPS prev={prev_ms} curr={curr_ms}")
                continue
            duration = float(curr_ms - prev_ms)

            matched = False
            # Try to match to an ideal transition
            for ideal_index in range(1, len(ideal_with_patterns)):
                ideal_prev = ideal_with_patterns[ideal_index - 1]
                ideal_curr = ideal_with_patterns[ideal_index]
                ideal_key = (ideal_curr["url"], ideal_curr["xPath"])

                # URL checks
                url_prev_ok = urls_glob_match(prev_event.get("url",""), ideal_prev["url_pattern"])
                url_curr_ok = urls_glob_match(curr_event.get("url",""), ideal_curr["url_pattern"])
                # Element checks
                el_prev_ok = compare_elements(ideal_prev["xPath"], prev_event.get("xPath",""))
                el_curr_ok = compare_elements(ideal_curr["xPath"], curr_event.get("xPath",""))

                is_match_ok = bool(curr_event.get("is_match"))

                if debug:
                    print(f"    pair {i-1}->{i} trying ideal {ideal_index}: "
                          f"urlPrev={url_prev_ok} urlCurr={url_curr_ok} "
                          f"elPrev={el_prev_ok} elCurr={el_curr_ok} "
                          f"isMatch={is_match_ok} "
                          f"prevURL={prev_event.get('url')} -> currURL={curr_event.get('url')}")

                if url_prev_ok and url_curr_ok and el_prev_ok and el_curr_ok and is_match_ok:
                    step_stats[ideal_key]["times"].append(duration)
                    step_stats[ideal_key]["all_sessions"].add(session_id)

                    ideal_ms = ideal_durations.get(ideal_key)
                    if ideal_ms is not None and duration > threshold * ideal_ms:
                        step_stats[ideal_key]["delayed_sessions"].add(session_id)
                        delayed_events.append((
                            curr_event.get("xPath", ""),
                            curr_event.get("url", ""),
                            session_id,
                            duration,
                        ))
                    matched = True
                    if debug:
                        print(f"      ✓ MATCH ideal_key={ideal_key} duration={duration}ms (ideal={ideal_ms}ms)")
                    break

            if not matched and debug:
                print(f"      ✗ NO MATCH for pair {i-1}->{i} "
                      f"prev=({prev_event.get('url')}, {prev_event.get('xPath')}) "
                      f"curr=({curr_event.get('url')}, {curr_event.get('xPath')}) "
                      f"is_match={curr_event.get('is_match')} duration={duration}")

    # 3) Build insights (and print per-step averages)
    step_insights: "OrderedDict[str, Any]" = OrderedDict()
    sorted_steps = sorted(ideal_with_patterns, key=lambda x: x.get("step", 0))

    if debug:
        print("\n[DEBUG] Per-step timing stats before averaging:")
    for i, step in enumerate(sorted_steps):
        key = (step["url"], step["xPath"])
        stats = step_stats.get(key, {
            "times": [],
            "delayed_sessions": set(),
            "all_sessions": set(),
        })

        avg_time = mean(stats["times"]) if stats["times"] else 0.0
        all_count = len(stats["all_sessions"])
        delayed_count = len(stats["delayed_sessions"])
        delay_rate = (delayed_count / all_count) if all_count else 0.0

        if debug:
            print(f"  step_{i+1} ({step['url']} | el len={len(step['element'])}): "
                  f"times={stats['times']} avg={avg_time}ms sessions={all_count} delayed={delayed_count}")

        anomalies = []
        if delay_rate > 0:
            anomalies.append({
                "type": "delay",
                "severity": "high" if delay_rate > 0.5 else "medium",
                "detail": f"{int(delay_rate * 100)}% of users are delayed",
            })

        repeated_rate = next(
            (rate for (el, url), rate in (repeated_events or {}).items()
             if urls_glob_match(url, step["url_pattern"]) and compare_elements(step["element"], el)),
            0.0
        )
        drop_off_rate = next(
            (rate for (el, url), rate in (drop_off_events or {}).items()
             if urls_glob_match(url, step["url_pattern"]) and compare_elements(step["element"], el)),
            0.0
        )

        step_insights[f"step_{i+1}"] = {
            "step_index": step.get("step", i+1),
            "name": step.get("name"),
            "url": step["url"],
            "xPath": step.get("xPath"),
            "avg_time_ms": int(round(avg_time)),
            "drop_off_rate": round(drop_off_rate, 2),
            "repeated_rate": round(repeated_rate, 2),
            "anomalies": anomalies,
            "paths": {
                "next_step": f"step_{i + 2}" if i < len(sorted_steps) - 1 else None,
                "indirect_transitions": {},
                "drop_off": False,
            },
        }

    return step_insights, delayed_events
