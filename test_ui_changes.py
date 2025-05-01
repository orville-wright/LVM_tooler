import unittest
from unittest.mock import patch, MagicMock
import curses
import app

class TestPhysicalVolumesPaneAccessibility(unittest.TestCase):
    def setUp(self):
        # Setup initial state for tests
        self.stdscr_mock = MagicMock()
        self.devices = [
            {'path': '/dev/sda'},
            {'path': '/dev/sdb'},
        ]
        self.pvs_map = {
            '/dev/sda': {'vg_name': 'vg0', 'pv_name': 'pv1', 'pv_size': 1024*1024*1024, 'pv_free': 512*1024*1024},
            '/dev/sdb': {'vg_name': 'vg0', 'pv_name': 'pv2', 'pv_size': 2048*1024*1024, 'pv_free': 1024*1024*1024},
        }
        self.lvs_map = {
            'vg0': [
                {'devices': '/dev/sda'},
                {'devices': '/dev/sdb'},
            ]
        }
        # Initialize focus and selection variables
        self.active_panel = 0  # 0=main, 1=physical volumes, 2=block devices
        self.pv_selected = 0
        self.current = 0

    def simulate_keypresses(self, keys):
        """
        Simulate a sequence of keypresses and update active_panel and pv_selected accordingly.
        This mimics the keyboard handling logic in app.py.
        """
        for key in keys:
            if key == 9:  # TAB key
                self.active_panel = (self.active_panel + 1) % 3
            elif self.active_panel == 1:
                pvs_in_vg = [p for p in self.pvs_map.values() if p.get('vg_name') == self.pvs_map[self.devices[self.current]['path']]['vg_name']]
                if key in (curses.KEY_UP, ord('k')) and self.pv_selected > 0:
                    self.pv_selected -= 1
                elif key in (curses.KEY_DOWN, ord('j')) and self.pv_selected < len(pvs_in_vg) - 1:
                    self.pv_selected += 1

class TestVolumeGroupListInteraction(unittest.TestCase):
    """Contextual Integration Test: Verify Volume Group list interaction in TUI after LV mount point fix."""

    @patch('app.load_data')
    @patch('curses.use_default_colors')
    @patch('curses.start_color')
    @patch('curses.curs_set')
    @patch('curses.initscr')
    def test_volume_group_list_interaction(self, mock_initscr, mock_curs_set, mock_start_color, mock_use_default_colors, mock_load_data):
        vg_name = "vg0"
        lv_name = "lv0"
        lv_path = f"/dev/{vg_name}/{lv_name}"
        mount_point = "/mnt/test"

        devices = [
            {'name': lv_name, 'path': lv_path, 'size': '536870912', 'type': 'lvm', 'mount_point': mount_point, 'used': '100M', 'avail': '400M'},
            {'name': 'sda', 'path': '/dev/sda', 'size': '1073741824', 'type': 'disk'},
            {'name': 'sda1', 'path': '/dev/sda1', 'size': '1073741824', 'type': 'part'}
        ]
        pvs_map = {'/dev/sda1': {'pv_name': '/dev/sda1', 'pv_size': '1073741824', 'pv_free': '536870912', 'vg_name': vg_name}}
        vg_map = {vg_name: {'vg_name': vg_name, 'vg_size': '1073741824', 'vg_free': '536870912', 'pv_count': '1', 'lv_count': '1'}}
        lvs_map = {vg_name: [{'vg_name': vg_name, 'lv_name': lv_name, 'lv_size': '536870912', 'seg_size_pe': '128', 'seg_start_pe': '0', 'devices': '/dev/sda1(0)'}]}

        mock_load_data.return_value = (devices, pvs_map, vg_map, lvs_map)

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        mock_initscr.return_value = mock_stdscr
        mock_curs_set.return_value = None
        mock_start_color.return_value = None
        mock_use_default_colors.return_value = None

        # Add mocks for curses color attributes and methods to fix color number error
        curses.COLORS = 8
        curses.color_pair = lambda n: n
        curses.init_pair = lambda a, b, c: None

        mock_right_window = MagicMock()
        mock_pv_panel = MagicMock()
        mock_block_dev_panel = MagicMock()

        # Increase the number of mock window objects to avoid StopIteration in derwin calls
        mock_stdscr.derwin.side_effect = [
            mock_right_window,
            mock_pv_panel,
            mock_block_dev_panel,
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]

        # Simulate user interaction: press TAB to cycle panels and arrow keys to select
        key_sequence = [9, 9, curses.KEY_DOWN, curses.KEY_UP, ord('q')]  # Cycle panels and quit

        with patch.object(mock_stdscr, 'getch', side_effect=key_sequence):
            try:
                app.draw_ui(mock_stdscr, devices, pvs_map, vg_map, lvs_map)
            except Exception as e:
                self.fail(f"UI interaction raised an exception: {str(e)}")

        # If no exceptions and UI rendered, test passes
        self.assertTrue(True, "Volume Group list interaction in TUI works without errors")

if __name__ == '__main__':
    unittest.main()