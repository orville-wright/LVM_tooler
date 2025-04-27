#!/usr/bin/env python3
"""
Test UI Vertical Split and Navigation

This test verifies the UI modifications made to the LVM Browser:
1. Split the right panel into two vertical sections:
   - Upper panel: Physical Volumes
   - Lower panel: Block Devices list
2. Added independent navigation:
   - Tab key to switch between panels
   - Up/down arrow keys to navigate within the active panel
"""
import unittest
from unittest.mock import patch, MagicMock
import curses
import app

# Mock curses functions to avoid initialization errors
curses.initscr = MagicMock()
curses.curs_set = MagicMock()
curses.start_color = MagicMock()
curses.use_default_colors = MagicMock()
curses.init_pair = MagicMock()
curses.color_pair = MagicMock()
curses.A_BOLD = 1
curses.A_UNDERLINE = 2
curses.A_REVERSE = 4
curses.KEY_UP = 259
curses.KEY_DOWN = 258

class TestUIVerticalSplit(unittest.TestCase):
    """Test the vertical split and navigation in the UI."""

    def test_right_panel_split(self):
        """Test that the right panel is split into two vertical sections."""
        import inspect
        draw_ui_code = inspect.getsource(app.draw_ui)
        
        # Check for panel height calculations
        self.assertIn("pv_height = h // 2", draw_ui_code, 
                      "Physical Volumes panel height should be half the screen height")
        self.assertIn("block_dev_height = h - pv_height", draw_ui_code, 
                      "Block Devices panel height should be the remaining screen height")
        
        # Check for panel creation
        self.assertIn("pv_panel = stdscr.derwin(pv_height, pv_width, 0, vg_width)", draw_ui_code, 
                     "Physical Volumes panel should be created at the top right")
        self.assertIn("block_dev_panel = stdscr.derwin(block_dev_height, pv_width, pv_height, vg_width)", draw_ui_code, 
                     "Block Devices panel should be created at the bottom right")
        
        # Check panel titles
        self.assertIn('pv_panel.addstr(0, 2, " Physical Volumes ")', draw_ui_code,
                     "Physical Volumes panel should have the correct title")
        self.assertIn('block_dev_panel.addstr(0, 2, " Block Devices ")', draw_ui_code,
                     "Block Devices panel should have the correct title")

    def test_active_panel_tracking(self):
        """Test that the code tracks which panel is active."""
        import inspect
        draw_ui_code = inspect.getsource(app.draw_ui)
        
        # Check for active panel variable initialization
        self.assertIn("active_panel = 0", draw_ui_code, 
                     "Active panel should be initialized")
        
        # Check for tab key handling to switch panels
        tab_handling = "if key == 9:  # Tab key" in draw_ui_code and "active_panel = 1 - active_panel" in draw_ui_code
        self.assertTrue(tab_handling, "Tab key should switch between panels")

    def test_independent_navigation(self):
        """Test that navigation works independently in each panel."""
        import inspect
        draw_ui_code = inspect.getsource(app.draw_ui)
        
        # Check for navigation in main panel (active_panel == 0)
        main_panel_nav = "elif active_panel == 0:" in draw_ui_code
        self.assertTrue(main_panel_nav, "Should have navigation for main panel")
        
        # Check for navigation in block devices panel (active_panel == 1)
        block_dev_nav = "elif active_panel == 1:" in draw_ui_code
        self.assertTrue(block_dev_nav, "Should have navigation for block devices panel")
        
        # Check for current index and block_dev_selected variables
        self.assertIn("current = 0", draw_ui_code, 
                     "Current device index should be initialized for main panel")
        self.assertIn("block_dev_selected = 0", draw_ui_code, 
                     "Selected block device index should be initialized")
        
        # Check for updating indices based on key presses in the active panel
        self.assertIn("if key in (curses.KEY_UP, ord('k')) and current > 0:", draw_ui_code,
                     "Should handle up navigation in main panel")
        self.assertIn("elif key in (curses.KEY_DOWN, ord('j')) and current < len(devices) - 1:", draw_ui_code,
                     "Should handle down navigation in main panel")
        self.assertIn("if key in (curses.KEY_UP, ord('k')) and block_dev_selected > 0:", draw_ui_code,
                     "Should handle up navigation in block devices panel")
        self.assertIn("elif key in (curses.KEY_DOWN, ord('j')) and block_dev_selected < len(devices) - 1:", draw_ui_code,
                     "Should handle down navigation in block devices panel")

    def test_block_device_highlighting(self):
        """Test that the selected block device is highlighted in the active panel."""
        import inspect
        draw_ui_code = inspect.getsource(app.draw_ui)
        
        # Check for highlighting the selected block device when active_panel == 1
        self.assertIn("attr = curses.A_REVERSE if (i + start_idx == block_dev_selected and active_panel == 1) else 0", draw_ui_code,
                     "Selected block device should be highlighted when block devices panel is active")

    def test_block_devices_display(self):
        """Test that the block devices panel displays the correct information."""
        import inspect
        draw_ui_code = inspect.getsource(app.draw_ui)
        
        # Check for block devices display format
        self.assertIn('"{:<20} {:>10} {:<15}"', draw_ui_code,
                     "Block devices should display device name, size, and type")
        
        # Check for handling of device information extraction
        self.assertIn("name = dev.get('name', 'Unknown')", draw_ui_code,
                     "Should extract device name from device object")
        self.assertIn("size = format_size(dev.get('size', 0))", draw_ui_code,
                     "Should format device size for display")
        self.assertIn("dev_type = dev.get('type', 'Unknown')", draw_ui_code,
                     "Should extract device type from device object")

    def test_boundary_handling(self):
        """Test that the UI handles boundary conditions correctly."""
        import inspect
        draw_ui_code = inspect.getsource(app.draw_ui)
        
        # Check for boundary checks in navigation
        self.assertIn("if key in (curses.KEY_UP, ord('k')) and current > 0:", draw_ui_code,
                     "Should prevent navigating above the first item in main panel")
        self.assertIn("elif key in (curses.KEY_DOWN, ord('j')) and current < len(devices) - 1:", draw_ui_code,
                     "Should prevent navigating below the last item in main panel")
        self.assertIn("if key in (curses.KEY_UP, ord('k')) and block_dev_selected > 0:", draw_ui_code,
                     "Should prevent navigating above the first item in block devices panel")
        self.assertIn("elif key in (curses.KEY_DOWN, ord('j')) and block_dev_selected < len(devices) - 1:", draw_ui_code,
                     "Should prevent navigating below the last item in block devices panel")
        
        # Check for visible range calculation based on panel size
        self.assertIn("visible_count = block_dev_height - 4", draw_ui_code,
                     "Should calculate visible range based on panel size")
        self.assertIn("start_idx = max(0, min(block_dev_selected, len(devices) - visible_count))", draw_ui_code,
                     "Should calculate start index based on selected item and visible range")
        self.assertIn("end_idx = min(start_idx + visible_count, len(devices))", draw_ui_code,
                     "Should calculate end index based on start index and visible range")

    @patch('app.load_data')
    def test_ui_with_mock_data(self, mock_load_data):
        """Test that the UI works correctly with mock data."""
        # Create mock data
        devices = [
            {'name': 'sda', 'path': '/dev/sda', 'size': '1073741824', 'type': 'disk'},
            {'name': 'sda1', 'path': '/dev/sda1', 'size': '1073741824', 'type': 'part'},
            {'name': 'sdb', 'path': '/dev/sdb', 'size': '2147483648', 'type': 'disk'},
            {'name': 'sdb1', 'path': '/dev/sdb1', 'size': '2147483648', 'type': 'part'}
        ]
        pvs_map = {'/dev/sda1': {'pv_name': '/dev/sda1', 'pv_size': '1073741824', 'pv_free': '536870912', 'vg_name': 'vg0'}}
        vg_map = {'vg0': {'vg_name': 'vg0', 'vg_size': '1073741824', 'vg_free': '536870912', 'pv_count': '1', 'lv_count': '1'}}
        lvs_map = {'vg0': [{'vg_name': 'vg0', 'lv_name': 'lv0', 'lv_size': '536870912', 'seg_size_pe': '128', 'seg_start_pe': '0', 'devices': '/dev/sda1(0)'}]}
        
        # Configure mock
        mock_load_data.return_value = (devices, pvs_map, vg_map, lvs_map)
        
        # Create a mock curses window
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)  # 80x24 terminal
        mock_stdscr.derwin.return_value = MagicMock()  # Mock subwindows
        
        # Test UI with different key presses to simulate navigation
        with patch.object(mock_stdscr, 'getch') as mock_getch:
            # First call to getch returns Tab key to switch panels
            # Second call returns down arrow to navigate in block devices panel
            # Third call returns 'q' to quit
            mock_getch.side_effect = [9, curses.KEY_DOWN, ord('q')]
            
            try:
                app.draw_ui(mock_stdscr, devices, pvs_map, vg_map, lvs_map)
                # If we get here without exceptions, the test passes
                pass
            except Exception as e:
                self.fail(f"UI raised an exception: {str(e)}")
        
        # Verify that getch was called the expected number of times
        self.assertEqual(mock_getch.call_count, 3, "Should have called getch 3 times")

    def test_terminal_size_handling(self):
        """Test that the UI handles different terminal sizes appropriately."""
        import inspect
        draw_ui_code = inspect.getsource(app.draw_ui)
        
        # Check for minimum size check
        self.assertIn("if h < 10 or w < 80:", draw_ui_code,
                     "Should check for minimum terminal size")
        self.assertIn("Terminal too small", draw_ui_code,
                     "Should display an error message when terminal is too small")
        
        # Check for adaptive panel sizing
        self.assertIn("pv_height = h // 2", draw_ui_code,
                     "Physical Volumes panel height should adapt to terminal height")
        self.assertIn("block_dev_height = h - pv_height", draw_ui_code,
                     "Block Devices panel height should adapt to terminal height")
        
        # Check for boundary checks when displaying content
        self.assertIn("if j >= pv_height - 3:", draw_ui_code,
                     "Should check panel boundaries when displaying Physical Volumes")
        self.assertIn("if y_pos >= block_dev_height - 1:", draw_ui_code,
                     "Should check panel boundaries when displaying Block Devices")

if __name__ == '__main__':
    unittest.main()