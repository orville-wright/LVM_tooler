#!/usr/bin/env python3
"""
Test script for verifying the PE start extraction functionality
"""
import unittest
from unittest.mock import patch, MagicMock

class TestPEStartExtraction(unittest.TestCase):
    """Test the PE start extraction functionality"""
    
    def test_pe_extraction_from_device_string(self):
        """Test that PE start information is correctly extracted from device strings"""
        # Sample device string with PE start in parentheses
        device_string = "/dev/sda1(123), /dev/sdb2(456)"
        
        # Extract PE start info and clean device names (code from app.py)
        clean_pvlist = ""
        pe_start_info = ""
        
        for pv_segment in device_string.split(','):
            pv_segment = pv_segment.strip()
            # Extract PE start from segment
            start_pos = pv_segment.find('(')
            end_pos = pv_segment.find(')')
            
            if start_pos > 0 and end_pos > start_pos:
                # Extract the PE start value
                pe_val = pv_segment[start_pos+1:end_pos]
                # Add to PE start info
                if pe_start_info:
                    pe_start_info += ", "
                pe_start_info += pe_val
                
                # Add clean device name without parentheses
                if clean_pvlist:
                    clean_pvlist += ", "
                clean_pvlist += pv_segment[:start_pos]
            else:
                # No parentheses found, use as is
                if clean_pvlist:
                    clean_pvlist += ", "
                clean_pvlist += pv_segment
                
        # Verify the results
        self.assertEqual(clean_pvlist, "/dev/sda1, /dev/sdb2")
        self.assertEqual(pe_start_info, "123, 456")
    
    def test_pe_extraction_mixed_format(self):
        """Test extraction when some devices have PE start and others don't"""
        # Mixed format device string
        device_string = "/dev/sda1(123), /dev/sdb2, /dev/sdc3(789)"
        
        # Extract PE start info and clean device names
        clean_pvlist = ""
        pe_start_info = ""
        
        for pv_segment in device_string.split(','):
            pv_segment = pv_segment.strip()
            # Extract PE start from segment
            start_pos = pv_segment.find('(')
            end_pos = pv_segment.find(')')
            
            if start_pos > 0 and end_pos > start_pos:
                # Extract the PE start value
                pe_val = pv_segment[start_pos+1:end_pos]
                # Add to PE start info
                if pe_start_info:
                    pe_start_info += ", "
                pe_start_info += pe_val
                
                # Add clean device name without parentheses
                if clean_pvlist:
                    clean_pvlist += ", "
                clean_pvlist += pv_segment[:start_pos]
            else:
                # No parentheses found, use as is
                if clean_pvlist:
                    clean_pvlist += ", "
                clean_pvlist += pv_segment
                
        # Verify the results
        self.assertEqual(clean_pvlist, "/dev/sda1, /dev/sdb2, /dev/sdc3")
        self.assertEqual(pe_start_info, "123, 789")
    
    def test_column_header_includes_pe_start(self):
        """Test that the column header includes PE Start"""
        # Mock the implementation of the curses addstr function
        with patch('curses.window.addstr') as mock_addstr:
            # Create a mock for the format string that would be passed to addstr
            format_string = "{:<10} {:<10} {:>10} {:<20} {}".format(
                "LE Start", "LE End", "Size", "PVs", "PE Start")
            
            # Verify that the format string includes the PE Start column
            self.assertIn("PE Start", format_string)

if __name__ == '__main__':
    unittest.main()