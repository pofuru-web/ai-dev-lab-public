"""Read same-day work sessions from CSV and print a duration report."""

import argparse
import csv
from dataclasses import dataclass
import re
import sys


class WorktimeError(Exception):
    """Invalid worktime input or an unreadable input file."""


@dataclass(frozen=True)
class WorkSession:
    task: str
    start: str
    end: str
    duration: int


def parse_time(value, field, line):
    """Convert a strictly zero-padded HH:MM time to minutes since midnight."""
    if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value):
        raise WorktimeError(
            f"line {line}: invalid {field} time {value!r} (expected HH:MM)"
        )
    hours, minutes = map(int, value.split(":"))
    return hours * 60 + minutes


def calculate_duration(start, end):
    """Return a positive same-day duration from integer minute values."""
    if end <= start:
        raise WorktimeError("end time must be after start time")
    return end - start


def parse_csv(stream):
    """Parse a text stream, preserving input order and physical line numbers."""
    reader = csv.reader(stream, strict=True)
    sessions = []
    try:
        header = next(reader, None)
        if header is None or [cell.strip() for cell in header] != [
            "task", "start", "end"
        ]:
            raise WorktimeError("line 1: invalid header: expected task,start,end")
        while True:
            line = reader.line_num + 1
            row = next(reader, None)
            if row is None:
                break
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            if len(row) != 3:
                raise WorktimeError(
                    f"line {line}: expected 3 columns, got {len(row)}"
                )
            task, start, end = (cell.strip() for cell in row)
            if not task:
                raise WorktimeError(f"line {line}: task name is empty")
            start_minutes = parse_time(start, "start", line)
            end_minutes = parse_time(end, "end", line)
            if end_minutes <= start_minutes:
                raise WorktimeError(
                    f"line {line}: end time must be after start time"
                )
            sessions.append(WorkSession(
                task, start, end, calculate_duration(start_minutes, end_minutes)
            ))
    except csv.Error as exc:
        raise WorktimeError(
            f"line {reader.line_num}: invalid CSV: {exc}"
        ) from exc
    if not sessions:
        raise WorktimeError("no data rows found")
    return sessions


def format_duration(minutes):
    """Format integer minutes as Hh MMm."""
    hours, remainder = divmod(minutes, 60)
    return f"{hours}h {remainder:02d}m"


def format_report(sessions):
    """Return a report without merging sessions with identical names."""
    width = max([len("Task")] + [len(session.task) for session in sessions])
    lines = [f"{'Task':<{width}}  Start  End    Duration"]
    for session in sessions:
        lines.append(
            f"{session.task:<{width}}  {session.start}  {session.end}  "
            f"{format_duration(session.duration)}"
        )
    lines.append("-" * max(map(len, lines)))
    total = sum(session.duration for session in sessions)
    lines.append(f"{'Total':<{width}}                {format_duration(total)}")
    return "\n".join(lines)


def main(argv=None):
    """Run the CLI and return its exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", help="UTF-8 CSV file with task,start,end columns")
    args = parser.parse_args(argv)
    try:
        try:
            with open(args.csv_path, encoding="utf-8-sig", newline="") as stream:
                sessions = parse_csv(stream)
        except (OSError, UnicodeError) as exc:
            raise WorktimeError(f"cannot read file {args.csv_path}: {exc}") from exc
        print(format_report(sessions))
    except WorktimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
