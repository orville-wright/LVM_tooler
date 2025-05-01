#!/usr/bin/env python3
"""
Test Mount Point Display for Logical Volumes

This test verifies that mount points for Logical Volumes are correctly displayed
in the Volume Group view, specifically addressing the issue where mount points
were showing as "N/A" despite being available in the device information.
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

class TestMountPointDisplay(unittest.TestCase):
    """Test the display of mount points for Logical Volumes."""

    @patch('app.load_data')
    def test_mount_point_display_dev_path(self, mock_load_data):
        """Test that mount points are correctly displayed for /dev/VGName/LVName path format."""
        # Create mock data with a logical volume using /dev/VGName/LVName path format
        vg_name = "vg0"
        lv_name = "lv0"
        lv_path = f"/dev/{vg_name}/{lv_name}"
        mount_point = "/mnt/test"
        # Put the LV first so it's selected by default in the UI
        devices = [
            {'name': lv_name, 'path': lv_path, 'size': '536870912', 'type': 'lvm', 'mount_point': mount_point, 'used': '100M', 'avail': '400M'},
            {'name': 'sda', 'path': '/dev/sda', 'size': '1073741824', 'type': 'disk'},
            {'name': 'sda1', 'path': '/dev/sda1', 'size': '1073741824', 'type': 'part'}
        ]
        pvs_map = {'/dev/sda1': {'pv_name': '/dev/sda1', 'pv_size': '1073741824', 'pv_free': '536870912', 'vg_name': vg_name}}
        vg_map = {vg_name: {'vg_name': vg_name, 'vg_size': '1073741824', 'vg_free': '536870912', 'pv_count': '1', 'lv_count': '1'}}
        lvs_map = {vg_name: [{'vg_name': vg_name, 'lv_name': lv_name, 'lv_size': '536870912', 'seg_size_pe': '128', 'seg_start_pe': '0', 'devices': '/dev/sda1(0)'}]}
        
        # Configure mock
        mock_load_data.return_value = (devices, pvs_map, vg_map, lvs_map)
        
        # Create a mock curses window
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)  # 80x24 terminal
        
        # Create mock windows for each panel
        mock_right_window = MagicMock()
        mock_pv_panel = MagicMock()
        mock_block_dev_panel = MagicMock()
        
        # Configure derwin to return different windows based on call order
        mock_stdscr.derwin.side_effect = [mock_right_window, mock_pv_panel, mock_block_dev_panel]
        
        # Test UI with 'q' to quit after rendering
        with patch.object(mock_stdscr, 'getch') as mock_getch:
            mock_getch.return_value = ord('q')  # Press 'q' to quit
            
            try:
                app.draw_ui(mock_stdscr, devices, pvs_map, vg_map, lvs_map)
            except Exception as e:
                self.fail(f"UI raised an exception: {str(e)}")
        
        # Check if the mount point was correctly displayed
        mount_point_displayed = False
        
        for call_args in mock_right_window.addstr.call_args_list:
            args, kwargs = call_args
            if len(args) >= 3 and isinstance(args[2], str):
                if f"Mounted: {mount_point}" in args[2]:
                    mount_point_displayed = True
                    break
        
        self.assertTrue(mount_point_displayed, f"Mount point '{mount_point}' was not displayed in the UI")

    @patch('app.load_data')
    def test_mount_point_display_mapper_path(self, mock_load_data):
        """Test that mount points are correctly displayed for /dev/mapper/VGName-LVName path format."""
        vg_name = "vg0"
        lv_name = "lv0"
        lv_path = f"/dev/mapper/{vg_name}-{lv_name}"
        mount_point = "/mnt/test_mapper"
        
        devices = [
            {'name': f"{vg_name}-{lv_name}", 'path': lv_path, 'size': '536870912', 'type': 'lvm', 'mount_point': mount_point, 'used': '200M', 'avail': '300M'},
            {'name': 'sda', 'path': '/dev/sda', 'size': '1073741824', 'type': 'disk'},
            {'name': 'sda1', 'path': '/dev/sda1', 'size': '1073741824', 'type': 'part'}
        ]
        pvs_map = {'/dev/sda1': {'pv_name': '/dev/sda1', 'pv_size': '1073741824', 'pv_free': '536870912', 'vg_name': vg_name}}
        vg_map = {vg_name: {'vg_name': vg_name, 'vg_size': '1073741824', 'vg_free': '536870912', 'pv_count': '1', 'lv_count': '1'}}
        lvs_map = {vg_name: [{'vg_name': vg_name, 'lv_name': lv_name, 'lv_size': '536870912', 'seg_size_pe': '128', 'seg_start_pe': '0', 'devices': '/dev/sda1(0)'}]}
        
        mock_load_data.return_value = (devices, pvs_map, vg_map, lvs_map)
        
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        
        mock_right_window = MagicMock()
        mock_pv_panel = MagicMock()
        mock_block_dev_panel = MagicMock()
        
        mock_stdscr.derwin.side_effect = [mock_right_window, mock_pv_panel, mock_block_dev_panel]
        
        with patch.object(mock_stdscr, 'getch') as mock_getch:
            mock_getch.return_value = ord('q')
            
            try:
                app.draw_ui(mock_stdscr, devices, pvs_map, vg_map, lvs_map)
            except Exception as e:
                self.fail(f"UI raised an exception: {str(e)}")
        
        mount_point_displayed = False
        
        for call_args in mock_right_window.addstr.call_args_list:
            args, kwargs = call_args
            if len(args) >= 3 and isinstance(args[2], str):
                if f"Mounted: {mount_point}" in args[2]:
                    mount_point_displayed = True
                    break
        
        self.assertTrue(mount_point_displayed, f"Mount point '{mount_point}' was not displayed in the UI")

    @patch('app.load_data')
    def test_mount_point_display_no_mount(self, mock_load_data):
        """Test that LVs without mount points display 'N/A' or similar."""
        vg_name = "vg0"
        lv_name = "lv0"
        lv_path = f"/dev/{vg_name}/{lv_name}"
        mount_point = None  # No mount point
        
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
        
        mock_right_window = MagicMock()
        mock_pv_panel = MagicMock()
        mock_block_dev_panel = MagicMock()
        
        mock_stdscr.derwin.side_effect = [mock_right_window, mock_pv_panel, mock_block_dev_panel]
        
        with patch.object(mock_stdscr, 'getch') as mock_getch:
            mock_getch.return_value = ord('q')
            
            try:
                app.draw_ui(mock_stdscr, devices, pvs_map, vg_map, lvs_map)
            except Exception as e:
                self.fail(f"UI raised an exception: {str(e)}")
        
        mount_point_displayed = False
        
        for call_args in mock_right_window.addstr.call_args_list:
            args, kwargs = call_args
            if len(args) >= 3 and isinstance(args[2], str):
                # Accept "N/A" or "Not Mounted" or similar as valid display for no mount point
                if "Mounted: N/A" in args[2] or "Mounted: Not Mounted" in args[2] or "Mounted: None" in args[2]:
                    mount_point_displayed = True
                    break
        
        self.assertTrue(mount_point_displayed, "LV without mount point did not display 'N/A' or equivalent")

    @patch('app.load_data')
    def test_physical_volume_display_unchanged(self, mock_load_data):
        """Confirm Physical Volume display remains unaffected by LV mount point fix."""
        vg_name = "vg0"
        
        devices = [
            {'name': 'sda', 'path': '/dev/sda', 'size': '1073741824', 'type': 'disk'},
            {'name': 'sda1', 'path': '/dev/sda1', 'size': '1073741824', 'type': 'part'}
        ]
        pvs_map = {'/dev/sda1': {'pv_name': '/dev/sda1', 'pv_size': '1073741824', 'pv_free': '536870912', 'vg_name': vg_name}}
        vg_map = {vg_name: {'vg_name': vg_name, 'vg_size': '1073741824', 'vg_free': '536870912', 'pv_count': '1', 'lv_count': '0'}}
        lvs_map = {vg_name: []}
        
        mock_load_data.return_value = (devices, pvs_map, vg_map, lvs_map)
        
        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        
        mock_right_window = MagicMock()
        mock_pv_panel = MagicMock()
        mock_block_dev_panel = MagicMock()
        
        mock_stdscr.derwin.side_effect = [mock_right_window, mock_pv_panel, mock_block_dev_panel]
        
        with patch.object(mock_stdscr, 'getch') as mock_getch:
            mock_getch.return_value = ord('q')
            
            try:
                app.draw_ui(mock_stdscr, devices, pvs_map, vg_map, lvs_map)
            except Exception as e:
                self.fail(f"UI raised an exception: {str(e)}")
        
        pv_displayed = False
        
        for call_args in mock_pv_panel.addstr.call_args_list:
            args, kwargs = call_args
            if len(args) >= 3 and isinstance(args[2], str):
                if "pv_name" in args[2] or "/dev/sda1" in args[2]:
                    pv_displayed = True
                    break
        
        self.assertTrue(pv_displayed, "Physical Volume display was affected unexpectedly")

if __name__ == '__main__':
    unittest.main()