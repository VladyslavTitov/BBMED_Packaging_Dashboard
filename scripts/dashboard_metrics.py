"""Small, auditable transformations shared by the dashboard build and checks."""
import math
from decimal import Decimal, InvalidOperation


def normalize_order(value):
    text = str(value or '').strip().upper()
    try:
        number = Decimal(text)
        if number.is_finite() and number == number.to_integral_value():
            return str(int(number))
    except InvalidOperation:
        pass
    return text


def meter_intervals(readings):
    """Reject resets, invalid values and conflicting duplicate timestamps.

    Invalid samples break the chain; do not bridge an unknown counter reset.
    """
    grouped = {}
    for stamp, value in readings:
        grouped.setdefault(stamp, []).append(value)
    previous = None
    result = []
    issues = 0
    for stamp, values in sorted(grouped.items()):
        valid = all(v is not None and math.isfinite(v) and v >= 0 for v in values)
        if not valid or len(set(values)) != 1:
            issues += 1
            previous = None
            continue
        value = values[0]
        if previous:
            start, old = previous
            delta = value - old
            if delta < 0:
                issues += 1
            else:
                result.append({'start': start.isoformat(timespec='seconds'),
                               'end': stamp.isoformat(timespec='seconds'),
                               'delta': round(delta, 8),
                               'hours': (stamp-start).total_seconds()/3600})
        previous = (stamp, value)
    return result, issues


def allocate_energy(intervals, periods):
    """Time-overlap allocation, assuming constant consumption within each meter interval.

    Period tuples: (start datetime, end datetime, order). Ambiguous overlap is
    left unallocated, as are gaps. No output or machine state is inferred.
    """
    from collections import defaultdict
    from datetime import datetime
    allocated = defaultdict(float)
    unallocated = 0.0
    for reading in intervals:
        start = datetime.fromisoformat(reading['start'])
        end = datetime.fromisoformat(reading['end'])
        relevant = [(max(start, a), min(end, b), order) for a, b, order in periods if a < end and b > start]
        boundaries = sorted({start, end, *(a for a, _, _ in relevant), *(b for _, b, _ in relevant)})
        for a, b in zip(boundaries, boundaries[1:]):
            candidates = {order for x, y, order in relevant if x <= a and y >= b}
            value = reading['delta'] * (b-a).total_seconds() / (end-start).total_seconds()
            if len(candidates) == 1:
                allocated[next(iter(candidates))] += value
            else:
                unallocated += value
    return dict(allocated), unallocated
