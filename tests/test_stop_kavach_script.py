import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


POWERSHELL = shutil.which("powershell.exe")
SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "stop_kavach.ps1"

HARNESS = r"""
param(
    [string]$ScriptPath,
    [string]$CaseRoot,
    [string]$Scenario
)

$ErrorActionPreference = "Stop"
$parseErrors = $null
[System.Management.Automation.Language.Parser]::ParseFile(
    $ScriptPath,
    [ref]$null,
    [ref]$parseErrors
) | Out-Null
if ($parseErrors.Count) {
    exit 90
}

$ExpectedExe = [IO.Path]::GetFullPath(
    (Join-Path $CaseRoot ".venv\Scripts\python.exe")
)

function Get-CimInstance {
    param([string]$ClassName, [string]$Filter, [string]$ErrorAction)

    if ($Scenario -eq "query-failure") {
        throw "Simulated CIM query failure."
    }

    if ($Scenario -eq "stale") {
        return $null
    }

    $executable = if ($Scenario -eq "wrong-identity") {
        "C:\other\python.exe"
    } else {
        $ExpectedExe
    }
    $commandLine = if ($Scenario -eq "wrong-command") {
        "python.exe -m http.server"
    } else {
        "python.exe -m uvicorn app:app --port 8000"
    }

    return [pscustomobject]@{
        ProcessId = if ($Scenario -eq "wrong-pid") { 4343 } else { 4242 }
        ExecutablePath = $executable
        CommandLine = $commandLine
    }
}

function Stop-Process {
    param([int]$Id)
    Set-Content -LiteralPath (Join-Path $CaseRoot "stop-called.txt") -Value $Id
}

function Wait-Process {
    param([int]$Id, [int]$Timeout, [string]$ErrorAction)
}

try {
    & $ScriptPath
} catch {
    if ($Scenario -eq "query-failure") {
        exit 23
    }
    exit 24
}
"""


@unittest.skipUnless(POWERSHELL, "Windows PowerShell is required")
class StopKavachScriptTests(unittest.TestCase):
    def run_script_case(self, scenario):
        with tempfile.TemporaryDirectory(prefix="kavach-stop-test-") as temp:
            root = Path(temp)
            tools = root / "tools"
            data = root / "data"
            tools.mkdir()
            data.mkdir()
            script_copy = tools / "stop_kavach.ps1"
            script_copy.write_bytes(SCRIPT.read_bytes())
            pid_file = data / "kavach.pid"
            pid_file.write_text("4242", encoding="ascii")
            harness = root / "harness.ps1"
            harness.write_text(HARNESS, encoding="utf-8")

            result = subprocess.run(
                [
                    POWERSHELL,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(harness),
                    "-ScriptPath",
                    str(script_copy),
                    "-CaseRoot",
                    str(root),
                    "-Scenario",
                    scenario,
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            stop_marker = root / "stop-called.txt"
            return (
                result,
                pid_file.exists(),
                stop_marker.exists(),
                stop_marker.read_text(encoding="ascii").strip()
                if stop_marker.exists() else None,
            )

    def test_cim_query_failure_preserves_pid_file_and_does_not_stop(self):
        result, pid_file_exists, stop_called, _ = self.run_script_case(
            "query-failure"
        )

        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertTrue(pid_file_exists)
        self.assertFalse(stop_called)

    def test_stale_pid_removes_pid_file_without_stopping(self):
        result, pid_file_exists, stop_called, _ = self.run_script_case("stale")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(pid_file_exists)
        self.assertFalse(stop_called)

    def test_wrong_executable_identity_does_not_stop_or_remove_pid_file(self):
        result, pid_file_exists, stop_called, _ = self.run_script_case(
            "wrong-identity"
        )

        self.assertEqual(result.returncode, 24, result.stderr)
        self.assertTrue(pid_file_exists)
        self.assertFalse(stop_called)

    def test_wrong_pid_does_not_stop_or_remove_pid_file(self):
        result, pid_file_exists, stop_called, _ = self.run_script_case(
            "wrong-pid"
        )

        self.assertEqual(result.returncode, 24, result.stderr)
        self.assertTrue(pid_file_exists)
        self.assertFalse(stop_called)

    def test_wrong_command_does_not_stop_or_remove_pid_file(self):
        result, pid_file_exists, stop_called, _ = self.run_script_case(
            "wrong-command"
        )

        self.assertEqual(result.returncode, 24, result.stderr)
        self.assertTrue(pid_file_exists)
        self.assertFalse(stop_called)

    def test_verified_kavach_process_is_stopped(self):
        result, pid_file_exists, stop_called, stop_pid = self.run_script_case(
            "valid-kavach"
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(pid_file_exists)
        self.assertTrue(stop_called)
        self.assertEqual(stop_pid, "4242")


if __name__ == "__main__":
    unittest.main()
