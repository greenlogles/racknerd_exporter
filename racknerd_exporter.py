#!/usr/bin/env python3
"""
RackNerd Prometheus Exporter

Exports metrics from RackNerd VPS control panel to Prometheus format.
"""

import argparse
import logging
import time
from typing import Dict, List, Optional
import re

import requests
from bs4 import BeautifulSoup
from prometheus_client import start_http_server, Gauge, Info, Enum
from prometheus_client.core import GaugeMetricFamily, REGISTRY, CounterMetricFamily


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('racknerd_exporter')


class RackNerdClient:
    """Client to interact with RackNerd control panel."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RackNerd-Prometheus-Exporter/1.0'
        })
        self._logged_in = False

    def is_logged_in(self) -> bool:
        """Check if user is currently logged in by testing access to home page."""
        try:
            response = self.session.get(f'{self.base_url}/home.php')
            if response.status_code == 200:
                # Check if we're actually logged in or redirected to login page
                if 'logout.php' in response.text and 'vmlist' in response.text:
                    logger.debug("Session is valid")
                    return True
                else:
                    logger.debug("Session invalid - not logged in")
                    return False
            return False
        except Exception as e:
            logger.debug(f"Session check failed: {e}")
            return False

    def ensure_logged_in(self) -> bool:
        """Ensure user is logged in, re-login if necessary."""
        if self._logged_in and self.is_logged_in():
            return True

        logger.info("Session expired or not logged in, attempting login...")
        self._logged_in = False
        return self.login()

    def login(self) -> bool:
        """Login to RackNerd control panel."""
        try:
            # The login page uses AJAX with JSON responses
            # The login function posts with act: "login" and Submit: "1"
            login_data = {
                'act': 'login',
                'Submit': '1',
                'username': self.username,
                'password': self.password,
            }

            logger.debug(f"Attempting login for user: {self.username}")

            # Perform login via AJAX endpoint
            response = self.session.post(
                f'{self.base_url}/login.php',
                data=login_data,
            )
            response.raise_for_status()

            logger.debug(f"Login response status: {response.status_code}")
            logger.debug(f"Login response text: {response.text[:500]}")
            logger.debug(f"Cookies after login: {self.session.cookies.get_dict()}")

            # Parse JSON response
            try:
                json_response = response.json()
                logger.debug(f"Login JSON response: {json_response}")

                if json_response.get('success'):
                    status = json_response.get('status')
                    if status == "1":
                        # Login successful
                        self._logged_in = True
                        logger.info("Successfully logged in to RackNerd")
                        logger.debug(f"Session cookies: {self.session.cookies.get_dict()}")

                        # Verify login by checking home page
                        verify = self.session.get(f'{self.base_url}/home.php')
                        if 'logout.php' in verify.text:
                            logger.info("Login verified successfully")
                            return True
                        else:
                            logger.error("Login succeeded but verification failed")
                            logger.debug(f"Verification page preview: {verify.text[:500]}")
                            return False
                    elif status == "4":
                        logger.error("2FA is enabled - not currently supported")
                        return False
                    elif status == "2":
                        logger.error("Account blacklisted due to multiple failed login attempts")
                        return False
                    elif status == "3":
                        logger.error("Invalid username or password")
                        return False
                    else:
                        logger.error(f"Unknown login status: {status}")
                        return False
                else:
                    logger.error("Login failed - success=false in response")
                    return False

            except ValueError as e:
                logger.error(f"Failed to parse login response as JSON: {e}")
                logger.debug(f"Response content: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    def get_vms(self) -> List[Dict]:
        """Get list of VMs from home page."""
        if not self.ensure_logged_in():
            return []

        try:
            response = self.session.get(f'{self.base_url}/home.php')
            response.raise_for_status()

            logger.debug(f"Home page response status: {response.status_code}")

            soup = BeautifulSoup(response.text, 'html.parser')
            vms = []

            # Check if we're actually logged in
            if 'logout.php' not in response.text:
                logger.warning("Not logged in - logout link not found on page")
                logger.debug(f"Page content preview: {response.text[:500]}")
                # Try to re-login
                self._logged_in = False
                if self.ensure_logged_in():
                    return self.get_vms()  # Retry
                return []

            # Find the VM table
            table = soup.find('table', {'id': 'vmlist'})
            if not table:
                logger.warning("VM table not found on home page")
                logger.debug(f"Page title: {soup.title.string if soup.title else 'No title'}")
                logger.debug(f"Page content preview: {response.text[:1000]}")
                return []

            tbody = table.find('tbody')
            if not tbody:
                return []

            for row in tbody.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) < 6:
                    continue

                # Extract VM ID from control.php link
                link = cells[1].find('a')
                if not link:
                    continue

                href = link.get('href', '')
                vm_id_match = re.search(r'\?_v=([^&]+)', href)
                if not vm_id_match:
                    continue

                vm_id = vm_id_match.group(1)
                hostname = link.text.strip()

                # Extract other details
                vm_type = 'kvm' if 'kvm.png' in str(cells[0]) else 'openvz'
                ip_address = cells[2].text.strip()
                os = cells[3].text.strip()
                memory = cells[4].text.strip()
                disk = cells[5].text.strip()

                vms.append({
                    'vm_id': vm_id,
                    'hostname': hostname,
                    'vm_type': vm_type,
                    'ip_address': ip_address,
                    'os': os,
                    'memory': memory,
                    'disk': disk
                })

            logger.info(f"Found {len(vms)} VMs")
            return vms

        except Exception as e:
            logger.error(f"Error getting VMs: {e}")
            return []

    def get_vm_stats(self, vm_id: str) -> Optional[Dict]:
        """Get detailed stats for a specific VM."""
        if not self.ensure_logged_in():
            return None

        try:
            # Get VM stats via AJAX endpoint
            response = self.session.post(
                f'{self.base_url}/_vm_remote.php',
                data={
                    'act': 'getstatsdiskusage',
                    'vi': vm_id
                }
            )
            response.raise_for_status()

            data = response.json()
            if data.get('success') == '1':
                return data
            else:
                logger.warning(f"Failed to get stats for VM {vm_id}")
                return None

        except Exception as e:
            logger.error(f"Error getting VM stats for {vm_id}: {e}")
            return None


class RackNerdCollector:
    """Prometheus collector for RackNerd metrics."""

    def __init__(self, client: RackNerdClient):
        self.client = client

    def parse_size(self, size_str: str) -> float:
        """Parse size string (e.g., '20.31 GB') to bytes."""
        if not size_str or size_str == 'null':
            return 0.0

        size_str = size_str.strip()
        match = re.match(r'([\d.]+)\s*(GB|MB|TB|KB)?', size_str, re.IGNORECASE)
        if not match:
            return 0.0

        value = float(match.group(1))
        unit = (match.group(2) or 'GB').upper()

        multipliers = {
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
            'TB': 1024 ** 4
        }

        return value * multipliers.get(unit, 1024 ** 3)

    def collect(self):
        """Collect metrics from RackNerd."""
        # Get all VMs
        vms = self.client.get_vms()

        if not vms:
            logger.warning("No VMs found")
            return

        # Create metric families
        vm_info = GaugeMetricFamily(
            'racknerd_vm_info',
            'Information about the VM',
            labels=['hostname', 'ip_address', 'os', 'vm_type']
        )

        vm_state = GaugeMetricFamily(
            'racknerd_vm_state',
            'VM power state (1=online, 0=offline)',
            labels=['hostname']
        )

        vm_stats_up = GaugeMetricFamily(
            'racknerd_vm_stats_available',
            'Whether VM stats are available (1=available, 0=unavailable)',
            labels=['hostname']
        )

        # Bandwidth metrics
        bandwidth_total = GaugeMetricFamily(
            'racknerd_bandwidth_total_bytes',
            'Total bandwidth allocation in bytes',
            labels=['hostname']
        )

        bandwidth_used = GaugeMetricFamily(
            'racknerd_bandwidth_used_bytes',
            'Used bandwidth in bytes',
            labels=['hostname']
        )

        bandwidth_percent = GaugeMetricFamily(
            'racknerd_bandwidth_usage_percent',
            'Bandwidth usage percentage',
            labels=['hostname']
        )

        # Disk metrics
        disk_total = GaugeMetricFamily(
            'racknerd_disk_total_bytes',
            'Total disk space in bytes',
            labels=['hostname']
        )

        disk_used = GaugeMetricFamily(
            'racknerd_disk_used_bytes',
            'Used disk space in bytes',
            labels=['hostname']
        )

        disk_percent = GaugeMetricFamily(
            'racknerd_disk_usage_percent',
            'Disk usage percentage',
            labels=['hostname']
        )

        # Memory metrics
        memory_total = GaugeMetricFamily(
            'racknerd_memory_total_bytes',
            'Total memory in bytes',
            labels=['hostname']
        )

        memory_used = GaugeMetricFamily(
            'racknerd_memory_used_bytes',
            'Used memory in bytes',
            labels=['hostname']
        )

        memory_percent = GaugeMetricFamily(
            'racknerd_memory_usage_percent',
            'Memory usage percentage',
            labels=['hostname']
        )

        # VSwap metrics
        vswap_total = GaugeMetricFamily(
            'racknerd_vswap_total_bytes',
            'Total vswap in bytes',
            labels=['hostname']
        )

        vswap_used = GaugeMetricFamily(
            'racknerd_vswap_used_bytes',
            'Used vswap in bytes',
            labels=['hostname']
        )

        vswap_percent = GaugeMetricFamily(
            'racknerd_vswap_usage_percent',
            'VSwap usage percentage',
            labels=['hostname']
        )

        # Collect stats for each VM
        for vm in vms:
            vm_id = vm['vm_id']
            hostname = vm['hostname']

            # Add VM info
            vm_info.add_metric(
                [hostname, vm['ip_address'], vm['os'], vm['vm_type']],
                1
            )

            # Get detailed stats
            stats = self.client.get_vm_stats(vm_id)

            if stats:
                # VM stats are available
                vm_stats_up.add_metric([hostname], 1)

                # VM State (power state)
                state_value = stats.get('state', '0')
                try:
                    state = int(state_value)
                except (ValueError, TypeError):
                    state = 0
                vm_state.add_metric([hostname], state)

                logger.debug(f"VM {hostname} state: {state} ({'online' if state == 1 else 'offline'})")

                # Bandwidth
                if stats.get('totalbw'):
                    bandwidth_total.add_metric([hostname], self.parse_size(stats['totalbw']))
                    bandwidth_used.add_metric([hostname], self.parse_size(stats.get('usedbw', '0')))
                    bandwidth_percent.add_metric([hostname], float(stats.get('percentbw', '0')))

                # Disk
                if stats.get('totalhdd'):
                    disk_total.add_metric([hostname], self.parse_size(stats['totalhdd']))
                    disk_used.add_metric([hostname], self.parse_size(stats.get('usedhdd', '0')))
                    disk_percent.add_metric([hostname], float(stats.get('percenthdd', '0')))

                # Memory
                if stats.get('totalmem') and stats['totalmem'] not in ['null', None]:
                    memory_total.add_metric([hostname], self.parse_size(stats['totalmem']))
                    memory_used.add_metric([hostname], self.parse_size(stats.get('usedmem', '0')))
                    memory_percent.add_metric([hostname], float(stats.get('percentmem', '0')))

                # VSwap
                if stats.get('totalvswap') and stats['totalvswap'] not in ['null', None]:
                    vswap_total.add_metric([hostname], self.parse_size(stats['totalvswap']))
                    vswap_used.add_metric([hostname], self.parse_size(stats.get('usedvswap', '0')))
                    vswap_percent.add_metric([hostname], float(stats.get('percentvswap', '0')))
            else:
                # No stats available
                vm_stats_up.add_metric([hostname], 0)
                # Set state to offline when stats unavailable
                vm_state.add_metric([hostname], 0)
                logger.warning(f"Stats unavailable for VM {hostname}")

        # Yield all metrics
        yield vm_info
        yield vm_state
        yield vm_stats_up
        yield bandwidth_total
        yield bandwidth_used
        yield bandwidth_percent
        yield disk_total
        yield disk_used
        yield disk_percent
        yield memory_total
        yield memory_used
        yield memory_percent
        yield vswap_total
        yield vswap_used
        yield vswap_percent


def main():
    parser = argparse.ArgumentParser(description='RackNerd Prometheus Exporter')
    parser.add_argument('--url', required=True, help='RackNerd control panel URL')
    parser.add_argument('--username', required=True, help='RackNerd username')
    parser.add_argument('--password', required=True, help='RackNerd password')
    parser.add_argument('--port', type=int, default=9100, help='Exporter port (default: 9100)')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')

    args = parser.parse_args()

    # Set logging level
    logger.setLevel(getattr(logging, args.log_level))

    # Create client and collector
    client = RackNerdClient(args.url, args.username, args.password)

    # Test login
    if not client.login():
        logger.error("Failed to login to RackNerd. Exiting.")
        return 1

    # Register collector
    REGISTRY.register(RackNerdCollector(client))

    # Start HTTP server
    start_http_server(args.port)
    logger.info(f"RackNerd exporter started on port {args.port}")

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Exporter stopped")
        return 0


if __name__ == '__main__':
    exit(main())
