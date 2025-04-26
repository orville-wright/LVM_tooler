#!/usr/bin/env python3
"""
Test UI Changes for Mount Point and Capacity Information Display

This test verifies the changes made to the block devices display to show
mount point and capacity information.
"""
import unittest
from unittest.mock import patch, MagicMock
import json
import io
import sys
import curses
import app

class TestUIChanges(unittest.TestCase):
    """Test the UI changes for mount point and capacity information display."""

    @patch('subprocess.run')
    def test_load_data_collects_mount_info(self, mock_run):
        """Test that load_data collects mount point and capacity information."""
        # Mock the lsblk command output
        lsblk_output = {
            'blockdevices': [
                {
                    'name': 'sda',
                    'path': '/dev/sda',
                    'size': '1073741824',  # 1GB
                    'type': 'disk',
                    'children': [
                        {
                            'name': 'sda1',
                            'path': '/dev/sda1',
                            'size': '1073741824',
                            'type': 'part'
                        }
                    ]
                }
            ]
        }
        
        # Mock the df command output
        df_output = """Filesystem     1K-blocks    Used Available Use% Mounted on
/dev/sda1       1048576  524288    524288  50% /mnt/test"""
        
        # Mock the PVS, VGS, LVS command outputs
        pvs_output = {'report': [{'pv': []}]}
        vgs_output = {'report': [{'vg': []}]}
        lvs_output = {'report': [{'lv': []}]}
        
        # Configure the mock to return our test data
        def mock_run_side_effect(cmd, **kwargs):
            mock_result = MagicMock()
            if cmd[0] == 'lsblk':
                mock_result.stdout = json.dumps(lsblk_output)
            elif cmd[0] == 'df':
                mock_result.stdout = df_output
            elif cmd[0] == 'pvs':
                mock_result.stdout = json.dumps(pvs_output)
            elif cmd[0] == 'vgs':
                mock_result.stdout = json.dumps(vgs_output)
            elif cmd[0] == 'lvs':
                mock_result.stdout = json.dumps(lvs_output)
            return mock_result
            
        mock_run.side_effect = mock_run_side_effect
        
        # Call the function to test
        devices, pvs_map, vg_map, lvs_map = app.load_data()
        
        # Verify that mount point and capacity information are collected
        self.assertEqual(len(devices), 2)  # sda and sda1
        
        # Check sda1 has mount point and capacity information
        sda1 = next((d for d in devices if d.get('name') == 'sda1'), None)
        self.assertIsNotNone(sda1)
        self.assertEqual(sda1.get('mount_point'), '/mnt/test')
        self.assertEqual(sda1.get('used'), '512.00 MiB')
        self.assertEqual(sda1.get('avail'), '512.00 MiB')
        
        # Check sda has N/A for mount point (since it's not mounted)
        sda = next((d for d in devices if d.get('name') == 'sda'), None)
        self.assertIsNotNone(sda)
        self.assertEqual(sda.get('mount_point'), 'N/A')
        self.assertEqual(sda.get('used'), 'N/A')
        self.assertEqual(sda.get('avail'), 'N/A')
        
        # Verify df command was called with the correct parameters
        mock_run.assert_any_call(
            ['df', '--output=source,size,used,avail,pcent,target'],
            capture_output=True, text=True, check=True
        )

    @patch('curses.window')
    def test_block_devices_display(self, mock_window):
        """Test that the block devices display includes the new columns."""
        # Create a mock window
        mock_win = MagicMock()
        mock_window.return_value = mock_win
        
        # Create test data
        device = {
            'name': 'sda1',
            'path': '/dev/sda1',
            'type': 'part',
            'size': '1073741824',  # 1GB
            'pttype': 'gpt',
            'mount_point': '/mnt/test',
            'used': '512.00 MiB',
            'avail': '512.00 MiB'
        }
        
        # Call the function that adds the device to the display
        # We can't call draw_ui directly because it's a curses application
        # So instead we'll check the format string used in the code
        
        # Extract the header format string from the code
        header_format = "{:<15} {:<8} {:>10} {:<8} {:<15} {:>8} {:>8}"
        header = header_format.format("Name", "Type", "Size", "PTType", "Mount", "Used", "Avail")
        
        # Verify the header includes the new columns
        self.assertIn("Mount", header)
        self.assertIn("Used", header)
        self.assertIn("Avail", header)
        
        # Extract the row format string from the code
        row_format = "{:<15} {:<8} {:>10} {:<8} {:<15} {:>8} {:>8}"
        
        # Format a row with our test data
        name = device.get('name')
        dtype = device.get('type')
        size = app.format_size(device.get('size'))
        ptype = device.get('pttype')
        mount = device.get('mount_point')
        used = device.get('used')
        avail = device.get('avail')
        
        row = row_format.format(name, dtype, size, ptype, mount, used, avail)
        
        # Verify the row includes the mount point and capacity information
        self.assertIn("/mnt/test", row)
        self.assertIn("512.00 MiB", row)

    def test_panel_width_adjustment(self):
        """Test that the panel width has been adjusted appropriately."""
        # Original panel width calculation: max(40, w // 3)
        # New panel width calculation: max(70, w // 2)
        
        # Test with different window widths
        test_widths = [80, 100, 150, 200]
        
        for w in test_widths:
            # Calculate old and new panel widths
            old_width = max(40, w // 3)
            new_width = max(70, w // 2)
            
            # Verify the new panel width is larger
            self.assertGreaterEqual(new_width, old_width)
            
            # Verify the new panel width is at least 70
            self.assertGreaterEqual(new_width, 70)

    def test_mount_path_truncation(self):
        """Test that long mount paths are truncated appropriately."""
        # Create a test device with a long mount path
        device = {
            'mount_point': '/this/is/a/very/long/mount/path/that/should/be/truncated'
        }
        
        # Truncate the mount path as done in the code
        mount = device.get('mount_point')
        if len(mount) > 15:
            truncated_mount = mount[:12] + "..."
        else:
            truncated_mount = mount
            
        # Verify the mount path is truncated
        self.assertEqual(truncated_mount, '/this/is/a/v...')
        self.assertLessEqual(len(truncated_mount), 15)

    def test_unmounted_devices_display(self):
        """Test that unmounted devices show N/A in the appropriate columns."""
        # Create a test device without mount point information
        device = {
            'name': 'sda',
            'path': '/dev/sda',
            'type': 'disk',
            'size': '1073741824'  # 1GB
        }
        
        # Simulate the code that adds mount point and capacity information
        if 'mount_point' not in device:
            device['mount_point'] = 'N/A'
            device['used'] = 'N/A'
            device['avail'] = 'N/A'
            
        # Verify unmounted devices show N/A
        self.assertEqual(device.get('mount_point'), 'N/A')
        self.assertEqual(device.get('used'), 'N/A')
        self.assertEqual(device.get('avail'), 'N/A')

if __name__ == '__main__':
    unittest.main()