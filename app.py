#!/usr/bin/env python3
"""
Interactive LVM Browser

Scans system block devices and LVM configuration,
and displays in a curses UI with detailed information about
Volume Groups, Logical Volumes, and Physical Volumes.
"""
import curses
import json
import os
import subprocess

def format_size(size_bytes):
    """Format size in bytes to human-readable KiB, MiB, GiB, TiB."""
    try:
        size = float(size_bytes)
    except (TypeError, ValueError):
        return 'N/A'
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
        if size < 1024 or unit == 'TiB':
            return f"{size:.2f} {unit}"
        size /= 1024.0

def run_cmd(cmd):
    """Run command and return parsed JSON, or None on error."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception:
        return None

def load_data():
    """Load block devices and LVM data."""
    bs = run_cmd(['lsblk', '-b', '-O', '-J'])
    raw_devices = bs.get('blockdevices', []) if bs else []
    devices = []
    seen_paths = set()  # Track unique device paths
    
    # Get mount point and capacity information using df command
    df_info = {}
    try:
        df_output = subprocess.run(
            ['df', '--output=source,size,used,avail,pcent,target'],
            capture_output=True, text=True, check=True
        ).stdout.strip()
        
        # Parse df output (skip header)
        for line in df_output.split('\n')[1:]:
            parts = line.split()
            if len(parts) < 6:
                continue
            
            source = parts[0]
            size_blocks = parts[1]
            used_blocks = parts[2]
            avail_blocks = parts[3]
            use_percent = parts[4].replace('%', '')
            mount_point = ' '.join(parts[5:])  # Handle mount points with spaces
            
            df_info[source] = {
                'mount_point': mount_point,
                'used': format_size(int(used_blocks) * 1024),  # Convert 1K blocks to bytes
                'avail': format_size(int(avail_blocks) * 1024)  # Convert 1K blocks to bytes
            }
    except Exception as e:
        # If df command fails, continue without mount information
        pass
    
    def dfs(dev):
        # Use path if available, otherwise use name
        path = dev.get('path') or dev.get('name', '')
        if path and path not in seen_paths:
            seen_paths.add(path)
            
            # Add mount point and capacity information if available
            if path in df_info:
                dev['mount_point'] = df_info[path]['mount_point']
                dev['used'] = df_info[path]['used']
                dev['avail'] = df_info[path]['avail']
            else:
                dev['mount_point'] = 'N/A'
                dev['used'] = 'N/A'
                dev['avail'] = 'N/A'
                
            devices.append(dev)
        for child in dev.get('children', []):
            dfs(child)
            
    for d in raw_devices:
        dfs(d)
    pvs_json = run_cmd([
        'pvs', '--reportformat', 'json', '--units', 'b', '--nosuffix',
        '-o', 'pv_name,pv_size,pv_free,vg_name,pv_fmt'
    ])
    vgs_json = run_cmd([
        'vgs', '--reportformat', 'json', '--units', 'b', '--nosuffix',
        '-o', 'vg_name,vg_size,vg_free,pv_count,lv_count,vg_attr,vg_extent_size'
    ])
    lvs_json = run_cmd([
        'lvs', '--reportformat', 'json', '--units', 'b', '--nosuffix',
        '-o', 'vg_name,lv_name,lv_size,seg_size_pe,seg_start_pe,devices'
    ])

    pvs = pvs_json.get('report', [{}])[0].get('pv', []) if pvs_json else []
    vgs = vgs_json.get('report', [{}])[0].get('vg', []) if vgs_json else []
    lvs = lvs_json.get('report', [{}])[0].get('lv', []) if lvs_json else []

    pvs_map = {pv.get('pv_name'): pv for pv in pvs}
    vg_map = {vg.get('vg_name'): vg for vg in vgs}
    lvs_map = {}
    for lv in lvs:
        vg_name = lv.get('vg_name')
        lvs_map.setdefault(vg_name, []).append(lv)

    return devices, pvs_map, vg_map, lvs_map

def draw_ui(stdscr, devices, pvs_map, vg_map, lvs_map):
    """Draw the curses UI with LVM information."""
    # Initialize curses settings
    curses.curs_set(0)  # Hide cursor
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Selected item highlight

    current = 0  # Current selected device index
    block_dev_selected = 0  # Current selected block device index
    active_panel = 0  # 0 = main, 1 = block devices
    
    # Main UI loop
    while True:
        try:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            
            # Ensure minimum window size
            if h < 10 or w < 80:
                stdscr.clear()
                stdscr.addstr(0, 0, "Terminal too small. Please resize to at least 80x10.")
                stdscr.refresh()
                key = stdscr.getch()
                if key in (ord('q'), 27):  # q or ESC to quit
                    break
                continue
            
            # Calculate widths for the two panels
            vg_width = w // 2
            pv_width = w - vg_width
            
            # Calculate heights for the split right panels
            pv_height = h // 2
            block_dev_height = h - pv_height
            
            # Create Volume Group panel (left side, full height)
            right = stdscr.derwin(h, vg_width, 0, 0)
            right.box()
            dev = devices[current] if devices else {}
            if isinstance(dev, dict):
                path = dev.get('path')
            else:
                path = dev
            pv = pvs_map.get(path)
            if pv:
                vg_name = pv.get('vg_name')
                vg = vg_map.get(vg_name, {})
                vg_size = format_size(vg.get('vg_size'))
                # Truncate vg_name if too long
                display_vg_name = vg_name
                if vg_name and len(vg_name) > vg_width - 15:
                    display_vg_name = vg_name[:vg_width - 18] + "..."
                right.addstr(0, 2, f" Volume Group - {display_vg_name} ({vg_size}) ")
                
                fmt = vg.get('vg_attr', '')
                lvs_in_vg = lvs_map.get(vg_name, [])
                lv_names = [lv.get('lv_name') for lv in lvs_in_vg]
                
                # Truncate lv_names if joined string is too long
                lv_names_str = ', '.join(lv_names) if lv_names else 'none'
                if len(lv_names_str) > vg_width - 20:
                    lv_names_str = lv_names_str[:vg_width - 23] + "..."
                    
                # Get PE Size information
                vg_pe_size = vg.get('vg_extent_size', 'N/A')
                vg_pe_size_formatted = format_size(vg_pe_size) if vg_pe_size != 'N/A' else 'N/A'
                
                right.addstr(2, 2, f"Format: {fmt}")
                right.addstr(3, 2, f"VG PE size: {vg_pe_size_formatted}")
                right.addstr(4, 2, f"Logical Volumes: {lv_names_str}")
                
                # Only add header if we have vertical space
                if h > 7:
                    right.addstr(6, 2, "[  Logical Volumes  ]", curses.A_BOLD)
                y = 8
                # Group Logical Volumes by name
                lv_groups = {}
                for lv in lvs_in_vg:
                    name = lv.get('lv_name')
                    lv_groups.setdefault(name, []).append(lv)
                for name, group in lv_groups.items():
                    if y >= h - 2:  # Check against right window height instead of full screen
                        break
                    # Truncate name if too long to prevent boundary errors
                    display_name = name[:vg_width-20] + '...' if len(name) > vg_width-17 else name
                    right.addstr(y, 2, f"Logical Volume: {display_name}", curses.A_BOLD)
                    y += 1
                    
                    # Add mount point and capacity information
                    # Find the device path for this logical volume
                    lv_path = f"/dev/{vg_name}/{name}"
                    mount_point = "N/A"
                    capacity = format_size(group[0].get('lv_size')) if group else "N/A"
                    used = "N/A"
                    available = "N/A"
                    
                    # Search for mount point and capacity information in devices
                    for dev in devices:
                        if isinstance(dev, dict) and dev.get('path') == lv_path:
                            mount_point = dev.get('mount_point', 'N/A')
                            used = dev.get('used', 'N/A')
                            available = dev.get('avail', 'N/A')
                            break
                    
                    # Display additional information
                    right.addstr(y, 4, f"Mounted: {mount_point}")
                    y += 1
                    right.addstr(y, 4, f"Capacity: {capacity}")
                    y += 1
                    right.addstr(y, 4, f"Used: {used}")
                    y += 1
                    right.addstr(y, 4, f"Available: {available}")
                    y += 1
                    
                    # Add blank line before tabular data
                    y += 1
                    
                    # Ensure we don't write outside window boundaries
                    if y >= h - 2:
                        break
                    right.addstr(y, 4, "{:<10} {:<10} {:>10} {:>10} {:<20} {}".format(
                        "LE Start", "LE End", "PE Count", "PE Size", "PVs", "PE Start"), curses.A_UNDERLINE)
                    y += 1
                    for lv in group:
                        if y >= h - 2:  # Check against full screen height
                            break
                        
                        # Calculate PE count and PE size
                        pe_count = "N/A"
                        pe_size = "N/A"
                        
                        # Get segment size in PEs
                        seg_size_pe = lv.get('seg_size_pe', '0')
                        if seg_size_pe and seg_size_pe != "":
                            try:
                                pe_count = int(float(seg_size_pe))
                                
                                # Calculate PE size using VG PE size
                                if vg_pe_size != 'N/A':
                                    try:
                                        pe_size_bytes = int(float(vg_pe_size)) * pe_count
                                        pe_size = format_size(pe_size_bytes)
                                    except (ValueError, TypeError):
                                        pe_size = "N/A"
                            except (ValueError, TypeError):
                                pe_count = "N/A"
                        
                        pvlist = lv.get('devices', '')
                        
                        # Get LE start and end values
                        le_start = "N/A"
                        le_end = "N/A"
                        
                        # First try to get LE start directly from LV metadata
                        seg_start_pe = lv.get('seg_start_pe')
                        if seg_start_pe and seg_start_pe != "":
                            try:
                                start_le = int(float(seg_start_pe))
                                le_start = str(start_le)
                                
                                # Calculate LE end based on LE start and size
                                seg_size_pe = lv.get('seg_size_pe', '0')
                                if seg_size_pe and seg_size_pe != "":
                                    try:
                                        le_count = int(float(seg_size_pe))
                                        le_end = str(start_le + le_count - 1)
                                    except (ValueError, TypeError):
                                        le_end = "N/A"
                            except (ValueError, TypeError):
                                pass
                        
                        # Fallback: Parse from device string if direct metadata not available
                        if le_start == "N/A" and pvlist:
                            # Parse LE start from device string, format is like "/dev/sda1(123)"
                            # where 123 is the LE start
                            for pv_segment in pvlist.split(','):
                                pv_segment = pv_segment.strip()
                                # Extract LE start from segment
                                start_pos = pv_segment.find('(')
                                end_pos = pv_segment.find(')')
                                if start_pos > 0 and end_pos > start_pos:
                                    le_start = pv_segment[start_pos+1:end_pos]
                                    # Calculate LE end based on LE start and size
                                    try:
                                        start_le = int(float(le_start))
                                        # Get segment size in LEs
                                        seg_size_pe = lv.get('seg_size_pe', '0')
                                        if seg_size_pe and seg_size_pe != "":
                                            try:
                                                le_count = int(float(seg_size_pe))
                                                le_end = str(start_le + le_count - 1)
                                            except (ValueError, TypeError):
                                                le_end = "N/A"
                                    except (ValueError, TypeError):
                                        le_end = "N/A"
                                    break
                        
                        # Ensure we don't write outside window boundaries
                        if y >= h - 2:
                            break
                            
                        # Truncate pvlist if too long to prevent boundary errors
                        max_width = vg_width - 40  # Reserve space for other columns
                        if len(pvlist) > max_width:
                            pvlist = pvlist[:max_width-3] + "..."
                            
                        # Extract PE start info and clean device names
                        clean_pvlist = ""
                        pe_start_info = ""
                        
                        for pv_segment in pvlist.split(','):
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
                        
                        # Truncate if too long
                        max_dev_width = vg_width - 60  # Reserve space for other columns
                        if len(clean_pvlist) > max_dev_width:
                            clean_pvlist = clean_pvlist[:max_dev_width-3] + "..."
                            
                        right.addstr(y, 4, "{:<10} {:<10} {:>10} {:>10} {:<20} {}".format(
                            le_start, le_end, str(pe_count), pe_size, clean_pvlist, pe_start_info))
                        y += 1
                    y += 1
            else:
                right.addstr(1, 2, f"No LVM info for {path}")
                
            # Create Physical Volumes panel (right side, top half)
            pv_panel = stdscr.derwin(pv_height, pv_width, 0, vg_width)
            pv_panel.box()
            pv_panel.addstr(0, 2, " LVM - Physical Volumes (PV) ")
            
            dev = devices[current] if devices else {}
            if isinstance(dev, dict):
                path = dev.get('path')
            else:
                path = dev
            pv = pvs_map.get(path)
            
            if pv:
                vg_name = pv.get('vg_name')
                pvs_in_vg = [p for p in pvs_map.values() if p.get('vg_name') == vg_name]
                
                # Calculate LV count per PV
                pv_lv_count = {}
                lvs_in_vg = lvs_map.get(vg_name, [])
                for lv in lvs_in_vg:
                    lv_devices = lv.get('devices', '')
                    for dev in lv_devices.split(','):
                        dev = dev.strip()
                        if dev:
                            # Match physical volume names by checking if pv_name is in dev string
                            for pv_name in pvs_map:
                                if pv_name in dev:
                                    pv_lv_count[pv_name] = pv_lv_count.get(pv_name, 0) + 1
                
                # Display PV info in the new panel
                pv_panel.addstr(1, 2, "{:<15} {:>10} {:>8} {}".format(
                    "Name", "Size", "LV count", "Free"), curses.A_UNDERLINE)
                
                for j, p in enumerate(pvs_in_vg):
                    if j >= pv_height - 3:
                        break
                    pname = p.get('pv_name', '')
                    # Truncate pname if too long, accounting for narrower panel
                    max_pname_width = min(15, pv_width - 25)  # Ensure it fits in the narrower panel
                    if len(pname) > max_pname_width:
                        pname = pname[:max_pname_width-3] + "..."
                        
                    psize = format_size(p.get('pv_size'))
                    free = format_size(p.get('pv_free'))
                    lv_count = pv_lv_count.get(pname, 0)
                    
                    # Only write if we have space in the panel
                    if j + 2 < pv_height - 1:
                        pv_panel.addstr(j + 2, 2, "{:<15} {:>10} {:>8} {}".format(
                            pname, psize, lv_count, free))
                else:
                    pv_panel.addstr(1, 2, "No Physical Volume information available")
            
            # Create Block Devices panel (right side, bottom half)
            block_dev_panel = stdscr.derwin(block_dev_height, pv_width, pv_height, vg_width)
            block_dev_panel.box()
            block_dev_panel.addstr(0, 2, " System Block Devices ")
            
            # Display block devices list
            if devices:
                # Display header for block devices
                block_dev_panel.addstr(1, 2, "{:<20} {:>10} {:<15}".format(
                    "Device", "Size", "Type"), curses.A_UNDERLINE)
                
                # Calculate visible range based on panel size and current selection
                visible_count = block_dev_height - 4  # Account for borders and header
                start_idx = max(0, min(block_dev_selected, max(0, len(devices) - visible_count)))
                end_idx = min(start_idx + visible_count, len(devices))
                
                for i, dev in enumerate(devices[start_idx:end_idx]):
                    y_pos = i + 2
                    if y_pos >= block_dev_height - 1:
                        break
                    
                    # Get device info
                    if isinstance(dev, dict):
                        name = dev.get('name', 'Unknown')
                        size = format_size(dev.get('size', 0))
                        dev_type = dev.get('type', 'Unknown')
                    else:
                        name = str(dev)
                        size = 'N/A'
                        dev_type = 'Unknown'
                    
                    # Truncate name if too long
                    if len(name) > 18:
                        name = name[:15] + "..."
                    
                    # Highlight if this is the selected block device
                    attr = curses.A_REVERSE if (i + start_idx == block_dev_selected and active_panel == 1) else 0
                    block_dev_panel.addstr(y_pos, 2, "{:<20} {:>10} {:<15}".format(
                        name, size, dev_type), attr)
            else:
                block_dev_panel.addstr(1, 2, "No block devices available")

            # Refresh screen and handle keyboard input
            stdscr.refresh()
            key = stdscr.getch()
            
            # Handle panel switching with Tab key
            if key == 9:  # Tab key
                active_panel = 1 - active_panel
            # Handle navigation in main panel
            elif active_panel == 0:
                if key in (curses.KEY_UP, ord('k')) and current > 0:
                    current -= 1
                elif key in (curses.KEY_DOWN, ord('j')) and current < len(devices) - 1:
                    current += 1
            # Handle navigation in block devices panel
            elif active_panel == 1:
                if key in (curses.KEY_UP, ord('k')) and block_dev_selected > 0:
                    block_dev_selected -= 1
                elif key in (curses.KEY_DOWN, ord('j')) and block_dev_selected < len(devices) - 1:
                    block_dev_selected += 1
            
            # Global quit key
            if key in (ord('q'), 27):  # q or ESC to quit
                break
                
        except curses.error as e:
            # Handle curses errors gracefully
            stdscr.clear()
            error_msg = f"Curses error: {str(e)}"
            try:
                stdscr.addstr(0, 0, error_msg[:w-1])
                stdscr.addstr(1, 0, "Press any key to retry, 'q' to quit")
                stdscr.refresh()
                key = stdscr.getch()
                if key in (ord('q'), 27):  # q or ESC to quit
                    break
            except:
                # If we can't even display the error, just break out
                break

def main():
    """Main entry point for the application."""
    try:
        devices, pvs_map, vg_map, lvs_map = load_data()
        if not devices:
            print("No block devices found or permission denied.")
            return
        curses.wrapper(draw_ui, devices, pvs_map, vg_map, lvs_map)
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    main()