import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from jenkins_smoke import build_simulation_command, expand_simulation_cases


class ExpandSimulationCasesTest(unittest.TestCase):
    def test_build_simulation_command_includes_outdir_and_case_name(self) -> None:
        """Verify that the built command includes the output directory and case name.
        This ensures the generated gem5 invocation targets the expected run folder.
        """
        repo_dir = Path("/tmp/repo")
        gem5_binary = Path("/tmp/gem5.opt")
        command = build_simulation_command(
            repo_dir,
            gem5_binary,
            "CHIP_1",
            {"sim_script_args": ["-c", "/bin/true"], "case_name": "o3"},
            "o3",
        )

        self.assertIn(str(gem5_binary), command)
        self.assertTrue(any(str(token).startswith("--outdir=") for token in command))
        self.assertIn("/tmp/repo/RESULTS/simulation/CHIP_1/o3/CHIP_1_o3", command)

    def test_expands_named_cases_from_chip_config(self) -> None:
        """Verify that named test cases are expanded into separate runnable cases.
        This checks the config parsing path used by the smoke workflow.
        """
        chip_config = {
            "simulate": {
                "tests": {
                    "o3": {"description": "basic o3", "sim_script_args": ["-c", "/bin/true"]},
                    "minor": {"sim_script_args": ["-c", "/bin/true"]},
                }
            }
        }

        cases = expand_simulation_cases(chip_config)

        self.assertEqual([case["name"] for case in cases], ["o3", "minor"])

    def test_uses_single_case_when_no_tests_key(self) -> None:
        """Verify the fallback path for a chip config without explicit test cases.
        The workflow should still create one default case entry.
        """
        chip_config = {"simulate": {"sim_script_args": ["-c", "/bin/true"]}}

        cases = expand_simulation_cases(chip_config)

        self.assertEqual([case["name"] for case in cases], ["default"])


if __name__ == "__main__":
    unittest.main()
