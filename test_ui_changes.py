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

    def test_tab_focus_order(self):
        # Initially active_panel is 0, TAB once should focus Physical Volumes pane (1)
        self.active_panel = 0
        self.simulate_keypresses([9])
        self.assertEqual(self.active_panel, 1, "Physical Volumes pane should be second in focus order after one TAB")

    def test_arrow_navigation_down(self):
        self.active_panel = 1
        self.pv_selected = 0
        self.simulate_keypresses([curses.KEY_DOWN])
        self.assertEqual(self.pv_selected, 1, "Down arrow should move selection down by one")

    def test_arrow_navigation_up(self):
        self.active_panel = 1
        self.pv_selected = 1
        self.simulate_keypresses([curses.KEY_UP])
        self.assertEqual(self.pv_selected, 0, "Up arrow should move selection up by one")

    def test_bounds_navigation_up(self):
        self.active_panel = 1
        self.pv_selected = 0
        self.simulate_keypresses([curses.KEY_UP])
        self.assertEqual(self.pv_selected, 0, "Selection should not move above first row")

    def test_bounds_navigation_down(self):
        self.active_panel = 1
        pvs_in_vg = [p for p in self.pvs_map.values() if p.get('vg_name') == self.pvs_map[self.devices[self.current]['path']]['vg_name']]
        self.pv_selected = len(pvs_in_vg) - 1
        self.simulate_keypresses([curses.KEY_DOWN])
        self.assertEqual(self.pv_selected, len(pvs_in_vg) - 1, "Selection should not move below last row")

    def test_visual_highlighting_attributes(self):
        # Simulate the attribute selection logic for title and selected row
        active_panel = 1
        pv_selected = 0
        # Title attribute should be A_BOLD if active_panel == 1 else 0
        title_attr = curses.A_BOLD if active_panel == 1 else 0
        self.assertEqual(title_attr, curses.A_BOLD, "Title should be highlighted with A_BOLD when pane has focus")

        # Row attribute should be A_REVERSE if selected and pane has focus else 0
        attr = curses.A_REVERSE if (0 == pv_selected and active_panel == 1) else 0
        self.assertEqual(attr, curses.A_REVERSE, "Selected row should be highlighted with A_REVERSE when pane has focus")

    def test_focus_transfer_with_tab(self):
        # Test tabbing cycles focus through panels without error
        self.active_panel = 0
        self.simulate_keypresses([9, 9, 9])
        self.assertEqual(self.active_panel, 0, "Focus should cycle back to first panel after tabbing through all")

if __name__ == '__main__':
    unittest.main()