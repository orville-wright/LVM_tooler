#!/usr/bin/env python3
"""
Interactive LVM and Block Device Browser

Scans system block devices and LVM configuration,
and displays in a curses UI with a list of block devices
and details of LVM usage for selected device.
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
    
    def dfs(dev):
        # Use path if available, otherwise use name
        path = dev.get('path') or dev.get('name', '')
        if path and path not in seen_paths:
            seen_paths.add(path)
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
        '-o', 'vg_name,vg_size,vg_free,pv_count,lv_count,vg_attr'
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
    """Draw the curses UI with block devices and LVM information."""
    # Initialize curses settings
    curses.curs_set(0)  # Hide cursor
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Selected item highlight

    current = 0  # Current selected device index
    
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
                
            left_w = max(40, w // 3)
            
            # Calculate heights for the three panels
            vg_height = h // 2
            pv_height = h - vg_height
            
            # Create left panel (Block Devices)
            left = stdscr.derwin(h, left_w, 0, 0)
            left.box()
            left.addstr(0, 2, " Block Devices ")
            header = "{:<15} {:<8} {:>10} {:<8}".format("Name", "Type", "Size", "PTType")
            left.addstr(1, 1, header, curses.A_BOLD)
            for idx, dev in enumerate(devices):
                if idx >= h - 3:
                    break
                if isinstance(dev, dict):
                    # Extract just the device name without path prefixes
                    path = dev.get('path') or dev.get('name', '')
                    name = os.path.basename(path)
                    dtype = dev.get('type', '')
                    size = format_size(dev.get('size'))
                    ptype = dev.get('pttype') or 'none'
                else:
                    name = dev
                    dtype = ''
                    size = 'N/A'
                    ptype = 'none'
                line = "{:<15} {:<8} {:>10} {:<8}".format(name, dtype, size, ptype)
                attr = curses.color_pair(1) if idx == current else curses.A_NORMAL
                left.addstr(idx + 2, 1, line, attr)

            # Create right top panel (Volume Group)
            right = stdscr.derwin(vg_height, w - left_w, 0, left_w)
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
                if vg_name and len(vg_name) > w - left_w - 15:
                    display_vg_name = vg_name[:w - left_w - 18] + "..."
                right.addstr(0, 2, f" {display_vg_name} ({vg_size}) ")
                
                fmt = vg.get('vg_attr', '')
                lvs_in_vg = lvs_map.get(vg_name, [])
                lv_names = [lv.get('lv_name') for lv in lvs_in_vg]
                
                # Truncate lv_names if joined string is too long
                lv_names_str = ', '.join(lv_names) if lv_names else 'none'
                if len(lv_names_str) > w - left_w - 20:
                    lv_names_str = lv_names_str[:w - left_w - 23] + "..."
                    
                right.addstr(2, 2, f"Format: {fmt}")
                right.addstr(3, 2, f"Logical Volumes: {lv_names_str}")
                
                # Only add header if we have vertical space
                if vg_height > 6:
                    right.addstr(5, 2, "[  Logical Volumes  ]", curses.A_BOLD)
                y = 6
                # Group Logical Volumes by name
                lv_groups = {}
                for lv in lvs_in_vg:
                    name = lv.get('lv_name')
                    lv_groups.setdefault(name, []).append(lv)
                for name, group in lv_groups.items():
                    if y >= vg_height - 2:  # Check against right window height instead of full screen
                        break
                    # Truncate name if too long to prevent boundary errors
                    display_name = name[:left_w-20] + '...' if len(name) > left_w-17 else name
                    right.addstr(y, 2, f"Logical Volume: {display_name}", curses.A_BOLD)
                    y += 1
                    # Ensure we don't write outside window boundaries
                    if y >= vg_height - 2:
                        break
                    right.addstr(y, 4, "{:<10} {:<10} {:>10} {}".format("PE Start", "PE End", "Size", "PVs"), curses.A_UNDERLINE)
                    y += 1
                    for lv in group:
                        if y >= vg_height - 2:  # Check against right window height
                            break
                        size = format_size(lv.get('lv_size'))
                        pvlist = lv.get('devices', '')
                        
                        # Get PE start and end values
                        pe_start = "N/A"
                        pe_end = "N/A"
                        
                        # First try to get PE start directly from LV metadata
                        seg_start_pe = lv.get('seg_start_pe')
                        if seg_start_pe and seg_start_pe != "":
                            try:
                                start_pe = int(float(seg_start_pe))
                                pe_start = str(start_pe)
                                
                                # Calculate PE end based on PE start and size
                                seg_size_pe = lv.get('seg_size_pe', '0')
                                if seg_size_pe and seg_size_pe != "":
                                    try:
                                        pe_count = int(float(seg_size_pe))
                                        pe_end = str(start_pe + pe_count - 1)
                                    except (ValueError, TypeError):
                                        pe_end = "N/A"
                            except (ValueError, TypeError):
                                pass
                        
                        # Fallback: Parse from device string if direct metadata not available
                        if pe_start == "N/A" and pvlist:
                            # Parse PE start from device string, format is like "/dev/sda1(123)"
                            # where 123 is the PE start
                            for pv_segment in pvlist.split(','):
                                pv_segment = pv_segment.strip()
                                # Extract PE start from segment
                                start_pos = pv_segment.find('(')
                                end_pos = pv_segment.find(')')
                                if start_pos > 0 and end_pos > start_pos:
                                    pe_start = pv_segment[start_pos+1:end_pos]
                                    # Calculate PE end based on PE start and size
                                    try:
                                        start_pe = int(float(pe_start))
                                        # Get segment size in PEs
                                        seg_size_pe = lv.get('seg_size_pe', '0')
                                        if seg_size_pe and seg_size_pe != "":
                                            try:
                                                pe_count = int(float(seg_size_pe))
                                                pe_end = str(start_pe + pe_count - 1)
                                            except (ValueError, TypeError):
                                                pe_end = "N/A"
                                    except (ValueError, TypeError):
                                        pe_end = "N/A"
                                    break
                        
                        # Ensure we don't write outside window boundaries
                        if y >= vg_height - 2:
                            break
                            
                        # Truncate pvlist if too long to prevent boundary errors
                        max_width = w - left_w - 40  # Reserve space for other columns
                        if len(pvlist) > max_width:
                            pvlist = pvlist[:max_width-3] + "..."
                            
                        right.addstr(y, 4, "{:<10} {:<10} {:>10} {}".format(pe_start, pe_end, size, pvlist))
                        y += 1
                    y += 1
            else:
                right.addstr(1, 2, f"No LVM info for {path}")
                
            # Create right bottom panel (Physical Volumes)
            pv_panel = stdscr.derwin(pv_height, w - left_w, vg_height, left_w)
            pv_panel.box()
            pv_panel.addstr(0, 2, " Physical Volumes ")
            
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
                    devices = lv.get('devices', '')
                    for dev in devices.split(','):
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
                    # Truncate pname if too long
                    if len(pname) > 15:
                        pname = pname[:12] + "..."
                        
                    psize = format_size(p.get('pv_size'))
                    free = format_size(p.get('pv_free'))
                    lv_count = pv_lv_count.get(pname, 0)
                    
                    # Only write if we have space in the panel
                    if j + 2 < pv_height - 1:
                        pv_panel.addstr(j + 2, 2, "{:<15} {:>10} {:>8} {}".format(
                            pname, psize, lv_count, free))
            else:
                pv_panel.addstr(1, 2, "No Physical Volume information available")

            # Refresh screen and handle keyboard input
            stdscr.refresh()
            key = stdscr.getch()
            if key in (curses.KEY_UP, ord('k')) and current > 0:
                current -= 1
            elif key in (curses.KEY_DOWN, ord('j')) and current < len(devices) - 1:
                current += 1
            elif key in (ord('q'), 27):  # q or ESC to quit
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