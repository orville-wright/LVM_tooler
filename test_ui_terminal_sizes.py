#!/usr/bin/env python3
"""
Test UI with Different Terminal Sizes

This test verifies that the LVM Browser UI handles different terminal sizes
appropriately, particularly focusing on the vertical split panels:
1. Physical Volumes panel (upper right)
2. Block Devices panel (lower right)

The test ensures that:
- UI adapts to different terminal sizes
- Panels resize appropriately
- Content is displayed correctly within size constraints
- No crashes occur when terminal size changes
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

class TestUITerminalSizes(unittest.TestCase):
    """Test the UI with different terminal sizes."""

    def setUp(self):
        """Set up mock data for testing."""
        # Create mock devices and LVM data
        self.devices = [
            {'name': 'sda', 'path': '/dev/sda', 'size': '1073741824', 'type': 'disk'},
            {'name': 'sda1', 'path': '/dev/sda1', 'size': '1073741824', 'type': 'part'},
            {'name': 'sdb', 'path': '/dev/sdb', 'size': '2147483648', 'type': 'disk'},
            {'name': 'sdb1', 'path': '/dev/sdb1', 'size': '2147483648', 'type': 'part'},
            {'name': 'sdc', 'path': '/dev/sdc', 'size': '3221225472', 'type': 'disk'},
            {'name': 'sdc1', 'path': '/dev/sdc1', 'size': '3221225472', 'type': 'part'},
            {'name': 'sdd', 'path': '/dev/sdd', 'size': '4294967296', 'type': 'disk'},
            {'name': 'sdd1', 'path': '/dev/sdd1', 'size': '4294967296', 'type': 'part'}
        ]
        self.pvs_map = {
            '/dev/sda1': {'pv_name': '/dev/sda1', 'pv_size': '1073741824', 'pv_free': '536870912', 'vg_name': 'vg0'}
        }
        self.vg_map = {
            'vg0': {'vg_name': 'vg0', 'vg_size': '1073741824', 'vg_free': '536870912', 'pv_count': '1', 'lv_count': '1'}
        }
        self.lvs_map = {
            'vg0': [{'vg_name': 'vg0', 'lv_name': 'lv0', 'lv_size': '536870912', 'seg_size_pe': '128', 'seg_start_pe': '0', 'devices': '/dev/sda1(0)'}]
        }

    def test_minimum_terminal_size(self):
        """Test that the UI handles minimum terminal size requirements."""
        # Create a mock curses window with a size below the minimum
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (5, 40)  # Too small (below 10x80)
        mock_stdscr.derwin.return_value = MagicMock()
        
        # Simulate one iteration of the UI loop with 'q' to exit
        with patch.object(mock_stdscr, 'getch', return_value=ord('q')):
            try:
                app.draw_ui(mock_stdscr, self.devices, self.pvs_map, self.vg_map, self.lvs_map)
                # Verify that the error message was displayed
                mock_stdscr.addstr.assert_any_call(0, 0, "Terminal too small. Please resize to at least 80x10.")
            except Exception as e:
                self.fail(f"UI raised an exception with small terminal: {str(e)}")

    def test_different_terminal_sizes(self):
        """Test that the UI adapts to different terminal sizes."""
        # Test with different terminal sizes
        test_sizes = [
            (24, 80),    # Minimum acceptable size
            (30, 100),   # Medium size
            (40, 120),   # Large size
            (50, 150)    # Very large size
        ]
        
        for h, w in test_sizes:
            # Create a mock curses window with the test size
            mock_stdscr = MagicMock()
            mock_stdscr.getmaxyx.return_value = (h, w)
            mock_stdscr.derwin.return_value = MagicMock()
            
            # Simulate one iteration of the UI loop with 'q' to exit
            with patch.object(mock_stdscr, 'getch', return_value=ord('q')):
                try:
                    app.draw_ui(mock_stdscr, self.devices, self.pvs_map, self.vg_map, self.lvs_map)
                    
                    # Verify that panels were created with the correct dimensions
                    calls = mock_stdscr.derwin.call_args_list
                    
                    # First call should be for the Volume Group panel (left panel)
                    vg_call = calls[0]
                    vg_height, vg_width, vg_y, vg_x = vg_call[0]
                    self.assertEqual(vg_height, h, "VG panel height should be full screen height")
                    self.assertEqual(vg_width, w // 2, "VG panel width should be half screen width")
                    self.assertEqual(vg_y, 0, "VG panel should start at top of screen")
                    self.assertEqual(vg_x, 0, "VG panel should start at left of screen")
                    
                    # Second call should be for the Physical Volumes panel (upper right)
                    pv_call = calls[1]
                    pv_height, pv_width, pv_y, pv_x = pv_call[0]
                    self.assertEqual(pv_height, h // 2, "PV panel height should be half screen height")
                    self.assertEqual(pv_width, w - (w // 2), "PV panel width should be remaining screen width")
                    self.assertEqual(pv_y, 0, "PV panel should start at top of screen")
                    self.assertEqual(pv_x, w // 2, "PV panel should start at middle of screen")
                    
                    # Third call should be for the Block Devices panel (lower right)
                    bd_call = calls[2]
                    bd_height, bd_width, bd_y, bd_x = bd_call[0]
                    self.assertEqual(bd_height, h - (h // 2), "Block Devices panel height should be remaining screen height")
                    self.assertEqual(bd_width, w - (w // 2), "Block Devices panel width should be remaining screen width")
                    self.assertEqual(bd_y, h // 2, "Block Devices panel should start at middle of screen height")
                    self.assertEqual(bd_x, w // 2, "Block Devices panel should start at middle of screen width")
                    
                except Exception as e:
                    self.fail(f"UI raised an exception with terminal size {h}x{w}: {str(e)}")

    def test_panel_content_truncation(self):
        """Test that panel content is truncated appropriately for different terminal sizes."""
        # Create a mock curses window with a medium size
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        
        # Create mock subwindows for each panel
        mock_vg_panel = MagicMock()
        mock_pv_panel = MagicMock()
        mock_bd_panel = MagicMock()
        
        def mock_derwin_side_effect(*args):
            # Return the appropriate mock panel based on the arguments
            height, width, y, x = args
            if y == 0 and x == 0:
                return mock_vg_panel  # Volume Group panel
            elif y == 0 and x == 40:
                return mock_pv_panel  # Physical Volumes panel
            elif y == 12 and x == 40:
                return mock_bd_panel  # Block Devices panel
            else:
                return MagicMock()  # Default
        
        mock_stdscr.derwin.side_effect = mock_derwin_side_effect
        
        # Simulate one iteration of the UI loop with 'q' to exit
        with patch.object(mock_stdscr, 'getch', return_value=ord('q')):
            try:
                app.draw_ui(mock_stdscr, self.devices, self.pvs_map, self.vg_map, self.lvs_map)
                
                # Verify that long device names are truncated in the Block Devices panel
                for call_args in mock_bd_panel.addstr.call_args_list:
                    args, kwargs = call_args
                    if len(args) >= 4:  # Only check calls with enough arguments
                        text = args[3]
                        if isinstance(text, str) and "sda" in text:
                            # The device name column should be limited to 20 characters
                            name_part = text.split()[0]
                            self.assertLessEqual(len(name_part), 20, 
                                                "Device names should be truncated to fit in the column")
                
            except Exception as e:
                self.fail(f"UI raised an exception during content truncation test: {str(e)}")

    def test_visible_range_calculation(self):
        """Test that the visible range is calculated correctly for different terminal sizes."""
        import inspect
        draw_ui_code = inspect.getsource(app.draw_ui)
        
        # Check for visible range calculation
        self.assertIn("visible_count = block_dev_height - 4", draw_ui_code,
                     "Should calculate visible range based on panel height")
        self.assertIn("start_idx = max(0, min(block_dev_selected, len(devices) - visible_count))", draw_ui_code,
                     "Should calculate start index based on selected item and visible range")
        self.assertIn("end_idx = min(start_idx + visible_count, len(devices))", draw_ui_code,
                     "Should calculate end index based on start index and visible range")
        
        # Create a mock curses window with a small size
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        mock_stdscr.derwin.return_value = MagicMock()
        
        # Create a large list of devices to test scrolling
        many_devices = []
        for i in range(50):  # 50 devices, more than can fit in the panel
            many_devices.append({
                'name': f'sd{chr(97 + (i % 26))}{i // 26}',
                'path': f'/dev/sd{chr(97 + (i % 26))}{i // 26}',
                'size': str(1073741824 * (i + 1)),
                'type': 'disk' if i % 2 == 0 else 'part'
            })
        
        # Simulate navigation through the list
        with patch.object(mock_stdscr, 'getch') as mock_getch:
            # First simulate Tab to switch to block devices panel
            # Then simulate multiple down keys to navigate down the list
            # Then simulate 'q' to exit
            mock_getch.side_effect = [9] + [curses.KEY_DOWN] * 20 + [ord('q')]
            
            try:
                app.draw_ui(mock_stdscr, many_devices, self.pvs_map, self.vg_map, self.lvs_map)
                # If we get here without exceptions, the test passes
                pass
            except Exception as e:
                self.fail(f"UI raised an exception during scrolling test: {str(e)}")

    def test_resizing_during_execution(self):
        """Test that the UI handles resizing during execution."""
        # Create a mock curses window that changes size during execution
        mock_stdscr = MagicMock()
        
        # Simulate a terminal that changes size between getch calls
        sizes = [(24, 80), (30, 100), (20, 90), (40, 120)]
        size_iter = iter(sizes)
        
        def get_next_size():
            try:
                return next(size_iter)
            except StopIteration:
                return (24, 80)  # Default if we run out of sizes
        
        mock_stdscr.getmaxyx.side_effect = get_next_size
        mock_stdscr.derwin.return_value = MagicMock()
        
        # Simulate multiple iterations of the UI loop with different key presses
        with patch.object(mock_stdscr, 'getch') as mock_getch:
            # Simulate Tab, navigation keys, and finally 'q' to exit
            mock_getch.side_effect = [9, curses.KEY_DOWN, curses.KEY_UP, ord('q')]
            
            try:
                app.draw_ui(mock_stdscr, self.devices, self.pvs_map, self.vg_map, self.lvs_map)
                # If we get here without exceptions, the test passes
                pass
            except Exception as e:
                self.fail(f"UI raised an exception during resizing test: {str(e)}")
        
        # Verify that getmaxyx was called multiple times
        self.assertGreater(mock_stdscr.getmaxyx.call_count, 1, 
                          "Should call getmaxyx multiple times to handle resizing")

if __name__ == '__main__':
    unittest.main()