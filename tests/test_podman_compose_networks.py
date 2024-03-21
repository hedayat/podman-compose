# SPDX-License-Identifier: GPL-2.0

"""
test_podman_compose_networks.py

Tests the podman networking parameters
"""

# pylint: disable=redefined-outer-name
import os
import unittest

from .test_podman_compose import podman_compose_path
from .test_podman_compose import test_path
from .test_utils import RunSubprocessMixin


class TestPodmanComposeNetwork(RunSubprocessMixin, unittest.TestCase):
    @staticmethod
    def compose_file():
        """Returns the path to the compose file used for this test module"""
        return os.path.join(test_path(), "nets_test_ip", "docker-compose.yml")

    def teardown(self):
        """
        Ensures that the services within the "profile compose file" are removed between
        each test case.
        """
        # run the test case
        yield

        down_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            self.compose_file(),
            "kill",
            "-a",
        ]
        self.run_subprocess(down_cmd)

    def test_networks(self):
        up_cmd = [
            "coverage",
            "run",
            podman_compose_path(),
            "-f",
            self.compose_file(),
            "up",
            "-d",
            "--force-recreate",
        ]

        self.run_subprocess_assert_returncode(up_cmd)

        check_cmd = [
            podman_compose_path(),
            "-f",
            self.compose_file(),
            "ps",
            "--format",
            '"{{.Names}}"',
        ]
        out, _ = self.run_subprocess_assert_returncode(check_cmd)
        self.assertIn(b"nets_test_ip_web1_1", out)
        self.assertIn(b"nets_test_ip_web2_1", out)

        expected_wget = {
            "172.19.1.10": "test1",
            "172.19.2.10": "test1",
            "172.19.2.11": "test2",
            "web3": "test3",
            "172.19.1.13": "test4",
        }

        for service in ("web1", "web2"):
            for ip, expect in expected_wget.items():
                wget_cmd = [
                    podman_compose_path(),
                    "-f",
                    self.compose_file(),
                    "exec",
                    service,
                    "wget",
                    "-q",
                    "-O-",
                    f"http://{ip}:8001/index.txt",
                ]
                out, _ = self.run_subprocess_assert_returncode(wget_cmd)
                self.assertEqual(f"{expect}\r\n", out.decode('utf-8'))

        expected_macip = {
            "web1": {"eth0": ["172.19.1.10"], "eth1": ["172.19.2.10"]},
            "web2": {"eth0": ["172.19.2.11"]},
        }

        for service, interfaces in expected_macip.items():
            ip_cmd = [
                podman_compose_path(),
                "-f",
                self.compose_file(),
                "exec",
                service,
                "ip",
                "addr",
                "show",
            ]
            out, _ = self.run_subprocess_assert_returncode(ip_cmd)
            for interface, values in interfaces.items():
                ip = values[0]
                self.assertIn(f"inet {ip}/", out.decode('utf-8'))
