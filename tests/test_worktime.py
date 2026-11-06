import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import worktime


class WorktimeTests(unittest.TestCase):
    def run_cli(self, content):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(content, encoding="utf-8")
            return self.capture([str(path)])

    def capture(self, argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = worktime.main(argv)
        return status, stdout.getvalue(), stderr.getvalue()

    def assert_error(self, content, *parts):
        status, stdout, stderr = self.run_cli(content)
        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Error:", stderr)
        self.assertNotIn("Traceback", stderr)
        for part in parts:
            self.assertIn(part, stderr)

    def test_durations_and_total(self):
        rows = worktime.parse_csv(io.StringIO(
            "task,start,end\n設計,09:00,10:30\n実装,10:45,12:00\n"
            "レビュー,13:00,13:45\n"
        ))
        self.assertEqual([row.duration for row in rows], [90, 75, 45])
        self.assertEqual(sum(row.duration for row in rows), 210)
        report = worktime.format_report(rows)
        self.assertIn("Total", report.splitlines()[-1])
        self.assertIn("3h 30m", report.splitlines()[-1])

    def test_format_duration(self):
        for value, expected in [(0, "0h 00m"), (45, "0h 45m"),
                                (90, "1h 30m"), (600, "10h 00m")]:
            with self.subTest(value=value):
                self.assertEqual(worktime.format_duration(value), expected)

    def test_bom_blank_lines_and_whitespace(self):
        status, stdout, stderr = self.run_cli(
            "\ufeff task , start , end \n\n  \n 設計 , 00:00 , 23:59 \n"
        )
        self.assertEqual((status, stderr), (0, ""))
        self.assertIn("23h 59m", stdout)
        self.assertIn("設計", stdout)

    def test_duplicate_tasks_and_main_success(self):
        status, stdout, stderr = self.run_cli(
            "task,start,end\n作業,09:00,09:30\n作業,10:00,11:00\n"
        )
        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual(stdout.count("作業"), 2)
        self.assertIn("0h 30m", stdout)
        self.assertIn("1h 00m", stdout)
        self.assertIn("Total", stdout)
        self.assertIn("1h 30m", stdout.splitlines()[-1])

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            status, stdout, stderr = self.capture([str(Path(directory) / "missing")])
        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Error:", stderr)
        self.assertIn("cannot read file", stderr)
        self.assertNotIn("Traceback", stderr)

    def test_invalid_headers(self):
        for header in ["name,start,end", "task,start", "task,end,start"]:
            with self.subTest(header=header):
                self.assert_error(header + "\n", "line 1", "invalid header")

    def test_column_counts(self):
        for row, count in [("作業,09:00", 2), ("作業,09:00,10:00,extra", 4)]:
            with self.subTest(row=row):
                self.assert_error("task,start,end\n\n" + row,
                                  "line 3", "expected 3 columns", str(count))

    def test_empty_task(self):
        self.assert_error("task,start,end\n  ,09:00,10:00", "line 2", "task name")

    def test_invalid_times(self):
        for field in ["start", "end"]:
            for value in ["9:00", "24:00", "25:00", "12:60", "abc", "０９:00", ""]:
                with self.subTest(field=field, value=value):
                    start, end = (value, "23:59") if field == "start" else ("00:00", value)
                    self.assert_error(f"task,start,end\n作業,{start},{end}",
                                      "line 2", f"invalid {field} time", "HH:MM")

    def test_nonpositive_duration(self):
        for end in ["09:00", "08:59"]:
            with self.subTest(end=end):
                self.assert_error(f"task,start,end\n作業,09:00,{end}",
                                  "line 2", "after start")

    def test_no_data(self):
        self.assert_error("task,start,end\n\n", "no data")
        self.assert_error("", "line 1", "invalid header")

    def test_first_error_line(self):
        self.assert_error(
            "task,start,end\n\n作業,09:00,10:00\n作業,bad,11:00\n,12:00,11:00",
            "line 4", "invalid start"
        )

    def test_invalid_csv_and_encoding(self):
        self.assert_error('task,start,end\n"unterminated', "line 2", "invalid CSV")
        self.assert_error(b"task,start,end\n\xff", "cannot read file")

    def test_unreadable_path(self):
        with tempfile.TemporaryDirectory() as directory:
            status, stdout, stderr = self.capture([directory])
        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Error:", stderr)
        self.assertNotIn("Traceback", stderr)

    def test_no_arguments(self):
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            with self.assertRaises(SystemExit) as raised:
                worktime.main([])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("usage:", stderr.getvalue())

    def test_help(self):
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            with self.assertRaises(SystemExit) as raised:
                worktime.main(["-h"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("usage:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
