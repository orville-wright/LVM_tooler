#! python3
"""
Interactive LVM Browser

Scans system block devices and LVM configuration,
and displays in a curses UI with detailed information about
Volume Groups, Logical Volumes, and Physical Volumes.
"""
import curses
import json
import os
import re
import subprocess
import shlex

def format_size(size_bytes):
    """Format size in bytes to human-readable KiB, MiB, GiB, TiB."""
    try:
        size = float(size_bytes)
    except (TypeError, ValueError):
        return 'N/A'
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
        if size < 1024 or unit == 'TiB':
            # Format with consistent decimal alignment
            if size < 10:
                return f"  {size:.2f} {unit}"  # Two spaces for single digit
            elif size < 100:
                return f" {size:.2f} {unit}"   # One space for double digit
            else:
                return f"{size:.2f} {unit}"    # No space for triple+ digit
        size /= 1024.0

def run_cmd(cmd):
    """Run command and return parsed JSON, or None on error."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception:
        return None

def run_cmd_text(cmd):
    """Run command and return text output, or empty string on error."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except Exception:
        return ""

def clean_device_info(text):
    """Clean up device information text according to specified rules."""
    text = text.replace("HARDDISK", "HDD")
    text = text.replace("(iscsi)", "")
    text = text.replace("Linux device-mapper (linear) (dm)", "LINUX Dev-map")
    return text

def load_data():
    """Load block devices and LVM data."""
    bs = run_cmd(['lsblk', '-b', '-O', '-J'])
    raw_devices = bs.get('blockdevices', []) if bs else []
    devices = []
    seen_paths = set()  # Track unique device paths
    
    # Get additional disk information from fdisk and parted
    fdisk_info = {}
    parted_info = {}
    
    # Run fdisk -l to get disk information
    fdisk_output = run_cmd_text(['fdisk', '-l'])
    
    # Parse fdisk output for each disk
    current_disk = None
    disk_label_type = None
    in_partition_table = False
    partition_info = {}
    
    for line in fdisk_output.splitlines():
        line = line.strip()
        
        # New disk entry
        if line.startswith("Disk /"):
            # Extract device path
            disk_path_match = re.search(r'Disk (\/[^:]+):', line)
            if disk_path_match:
                current_disk = disk_path_match.group(1)
                fdisk_info[current_disk] = {
                    'disk_model': '',
                    'disklabel_type': '',
                    'partitions': {}
                }
                in_partition_table = False
                
        # Disk model information
        elif current_disk and "Disk model:" in line:
            model = line.split("Disk model:")[1].strip()
            fdisk_info[current_disk]['disk_model'] = clean_device_info(model)
            
        # Disklabel type information
        elif current_disk and "Disklabel type:" in line:
            label_type = line.split("Disklabel type:")[1].strip()
            fdisk_info[current_disk]['disklabel_type'] = label_type
            disk_label_type = label_type
            
        # Start of partition table
        elif current_disk and "Device" in line and "Start" in line and "End" in line:
            in_partition_table = True
            continue
            
        # Partition information
        elif current_disk and in_partition_table and line and not line.startswith("Disk "):
            parts = line.split()
            if len(parts) >= 2 and parts[0].startswith(current_disk):
                part_path = parts[0]
                if disk_label_type == "dos" and len(parts) >= 7:
                    # For MBR/dos partition tables
                    fdisk_info[current_disk]['partitions'][part_path] = {
                        'fdisk_id_info': parts[4] if len(parts) > 4 else 'N/A',
                        'fdisk_type_info': ' '.join(parts[5:]) if len(parts) > 5 else 'N/A'
                    }
    
    # Run parted -l to get additional disk information for GPT disks
    parted_output = run_cmd_text(['parted', '-l'])
    
    # Parse parted output
    current_disk = None
    in_disk_flags = False
    
    for line in parted_output.splitlines():
        line = line.strip()
        
        # New disk entry
        if line.startswith("Disk /"):
            disk_path_match = re.search(r'Disk (\/[^:]+):', line)
            if disk_path_match:
                current_disk = disk_path_match.group(1)
                parted_info[current_disk] = {
                    'gpt_model_info': '',
                    'gpt_part_table_type': '',
                    'partitions': {}
                }
                in_disk_flags = False
                
        # Model information
        elif current_disk and line.startswith("Model:"):
            model = line.split("Model:")[1].strip()
            parted_info[current_disk]['gpt_model_info'] = clean_device_info(model)
            
        # Partition table type
        elif current_disk and "Partition Table:" in line:
            table_type = line.split("Partition Table:")[1].strip()
            parted_info[current_disk]['gpt_part_table_type'] = table_type
            
        # Start of partition table
        elif current_disk and "Number" in line and "Start" in line and "End" in line:
            in_disk_flags = True
            continue
            
        # Partition information in parted output
        elif current_disk and in_disk_flags and line and re.match(r'^\s*\d+', line):
            parts = line.split()
            if len(parts) >= 4:
                part_num = parts[0].strip()
                part_path = f"{current_disk}{part_num}"
                
                # Initialize if not exists
                if part_path not in parted_info[current_disk]['partitions']:
                    parted_info[current_disk]['partitions'][part_path] = {}
                
                # Extract filesystem and flags
                fs_info = parts[-2] if len(parts) > 2 else 'N/A'
                flags_info = parts[-1] if len(parts) > 1 else 'N/A'
                
                # Clean up the information
                fs_info = clean_device_info(fs_info)
                flags_info = clean_device_info(flags_info)
                
                # Store the information
                parted_info[current_disk]['partitions'][part_path] = {
                    'gpt_disk_flags_type': parts[4] if len(parts) > 4 else 'N/A',
                    'gpt_fs_info': fs_info,
                    'gpt_df_flagsinfo': flags_info
                }
    
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
                
            # Add additional disk information from fdisk and parted
            if path.startswith('/dev/'):
                # Find the disk this device belongs to
                disk_path = None
                for disk in fdisk_info:
                    if path == disk or path.startswith(disk):
                        disk_path = disk
                        break
                
                if disk_path:
                    # Add disk information
                    if path == disk_path:
                        # This is a disk, add disk-level info
                        if disk_path in fdisk_info:
                            dev['disk_model'] = fdisk_info[disk_path].get('disk_model', 'N/A')
                            dev['disklabel_type'] = fdisk_info[disk_path].get('disklabel_type', 'N/A')
                        
                        if disk_path in parted_info:
                            dev['gpt_model_info'] = parted_info[disk_path].get('gpt_model_info', 'N/A')
                            dev['gpt_part_table_type'] = parted_info[disk_path].get('gpt_part_table_type', 'N/A')
                    else:
                        # This is a partition, add partition-level info
                        if disk_path in fdisk_info and path in fdisk_info[disk_path]['partitions']:
                            part_info = fdisk_info[disk_path]['partitions'][path]
                            dev['fdisk_id_info'] = part_info.get('fdisk_id_info', 'N/A')
                            dev['fdisk_type_info'] = part_info.get('fdisk_type_info', 'N/A')
                        
                        if disk_path in parted_info and path in parted_info[disk_path]['partitions']:
                            part_info = parted_info[disk_path]['partitions'][path]
                            dev['gpt_disk_flags_type'] = part_info.get('gpt_disk_flags_type', 'N/A')
                            dev['gpt_fs_info'] = part_info.get('gpt_fs_info', 'N/A')
                            dev['gpt_df_flagsinfo'] = part_info.get('gpt_df_flagsinfo', 'N/A')
            
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
    pv_selected = 0  # Current selected physical volume index
    active_panel = 0  # 0 = main, 1 = physical volumes, 2 = block devices
    
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
            
            #------------------------------------------------------------
            # Panel (Top half, left side)
            # Create Volume Group panel (left side, full height)
            #------------------------------------------------------------
            
            right = stdscr.derwin(h, vg_width, 0, 0)
            right.box()
            dev = devices[current] if devices else {}
            
            # Flag to track if we've already displayed information
            info_displayed = False
            
            if isinstance(dev, dict):
                path = dev.get('path')
                # Check if the selected device is a logical volume
                if dev.get('type') == 'lvm':
                    # Display LV information directly
                    try:
                        right.addstr(0, 2, f" Logical Volume Information ")
                    except curses.error:
                        pass
                    
                    # Extract VG and LV names from path
                    # Handle both path formats: /dev/VGName/LVName and /dev/mapper/VGName-LVName
                    vg_name = None
                    lv_name = None
                    
                    if '/dev/mapper/' in path:
                        # Format: /dev/mapper/VGName-LVName
                        parts = path.replace('/dev/mapper/', '').split('-')
                        if len(parts) >= 2:
                            vg_name = parts[0]
                            lv_name = '-'.join(parts[1:])  # Handle LV names with hyphens
                    elif '/dev/' in path:
                        # Format: /dev/VGName/LVName
                        parts = path.replace('/dev/', '').split('/')
                        if len(parts) >= 2:
                            vg_name = parts[0]
                            lv_name = '/'.join(parts[1:])  # Handle LV names with slashes
                    
                    # Display basic information
                    try:
                        right.addstr(2, 2, f"Device: {path}")
                        right.addstr(3, 2, f"VG Name: {vg_name if vg_name else 'Unknown'}")
                        right.addstr(4, 2, f"LV Name: {lv_name if lv_name else 'Unknown'}")
                        right.addstr(5, 2, f"Size: {format_size(dev.get('size', 'N/A'))}")
                    except curses.error:
                        # Skip if we can't write the information
                        pass
                    
                    # Display mount point information
                    mount_point = dev.get('mount_point', 'N/A')
                    used = dev.get('used', 'N/A')
                    available = dev.get('avail', 'N/A')
                    
                    try:
                        right.addstr(7, 2, f"Mounted: {mount_point}")
                        right.addstr(8, 2, f"Used: {used}")
                        right.addstr(9, 2, f"Available: {available}")
                    except curses.error:
                        # Skip if we can't write the information
                        pass
                    
                    # Mark that we've displayed information
                    info_displayed = True
            
            # Only proceed with PV/VG display if we haven't already displayed LV info
            if not info_displayed:
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
                    try:
                        header_text = f" Volume Group - {display_vg_name} ({vg_size}) "
                        # Make sure the header isn't too long
                        if len(header_text) > vg_width - 4:
                            header_text = header_text[:vg_width - 7] + "... "
                        right.addstr(0, 2, header_text)
                    except curses.error:
                        # Skip if we can't write the header
                        pass
                    
                    vg_free_formatted = format_size(vg.get('vg_free')) if vg.get('vg_free') else 'N/A'
                    
                    fmt = vg.get('vg_attr', '')
                    lvs_in_vg = lvs_map.get(vg_name, [])
                    lv_names = [lv.get('lv_name') for lv in lvs_in_vg]
                    lv_names_set = set(lv_names)
                    # Remove duplicates while preserving order
                    
                    # Truncate lv_names if joined string is too long
                    lv_names_str = ', '.join(lv_names_set) if lv_names_set else 'none'
                    if len(lv_names_str) > vg_width - 20:
                        lv_names_str = lv_names_str[:vg_width - 23] + "..."
                        
                    # Get PE Size information
                    vg_pe_size = vg.get('vg_extent_size', 'N/A')
                    vg_pe_size_formatted = format_size(vg_pe_size) if vg_pe_size != 'N/A' else 'N/A'
                    
                    try:
                        right.addstr(2, 2, f"VG Format:     {fmt}"[:vg_width - 4])
                    except curses.error:
                        pass
                    try:
                        right.addstr(3, 2, f"VG seg size: {vg_pe_size_formatted}"[:vg_width - 4])
                    except curses.error:
                        pass
                    try:
                        right.addstr(4, 2, f"Logical Vols:  {lv_names_str}"[:vg_width - 4])
                    except curses.error:
                        pass
                    try:
                        right.addstr(5, 2, f"Free space:   {vg_free_formatted}"[:vg_width - 4])
                    except curses.error:
                        pass
                    
                    # Only add header if we have vertical space
                    if h > 7:
                        try:
                            right.addstr(7, 2, "[ Discovered LVols.. ]", curses.A_BOLD)
                        except curses.error:
                            pass
                    y = 9
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
                        try:
                            lv_text = f"Logical Volume: {display_name}"
                            # Check if the text would fit in the window
                            if len(lv_text) > vg_width - 4:
                                lv_text = lv_text[:vg_width - 7] + "..."
                            right.addstr(y, 2, lv_text, curses.A_BOLD)
                        except curses.error:
                            # Skip if we can't write this line
                            pass
                        y += 1
                # We need to ensure the PV display still works correctly
                # This section was removed because it duplicated code, but we need to make sure
                # the Volume Group information is still displayed properly when a PV is selected
                if pv:
                    vg_name = pv.get('vg_name')
                    vg = vg_map.get(vg_name, {})
                    vg_size = format_size(vg.get('vg_size'))
                    # Truncate vg_name if too long
                    display_vg_name = vg_name
                    if vg_name and len(vg_name) > vg_width - 15:
                        display_vg_name = vg_name[:vg_width - 18] + "..."
                    try:
                        header_text = f" Volume Group - {display_vg_name} ({vg_size}) "
                        # Make sure the header isn't too long
                        if len(header_text) > vg_width - 4:
                            header_text = header_text[:vg_width - 7] + "... "
                        right.addstr(0, 2, header_text)
                    except curses.error:
                        # Skip if we can't write the header
                        pass
                    
                    vg_free_formatted = format_size(vg.get('vg_free')) if vg.get('vg_free') else 'N/A'
                    
                    fmt = vg.get('vg_attr', '')
                    lvs_in_vg = lvs_map.get(vg_name, [])
                    lv_names = [lv.get('lv_name') for lv in lvs_in_vg]
                    lv_names_set = set(lv_names)
                    
                    # Truncate lv_names if joined string is too long
                    lv_names_str = ', '.join(lv_names_set) if lv_names_set else 'none'
                    if len(lv_names_str) > vg_width - 20:
                        lv_names_str = lv_names_str[:vg_width - 23] + "..."
                        
                    # Get PE Size information
                    vg_pe_size = vg.get('vg_extent_size', 'N/A')
                    vg_pe_size_formatted = format_size(vg_pe_size) if vg_pe_size != 'N/A' else 'N/A'
                    
                    try:
                        right.addstr(2, 2, f"VG Format:     {fmt}"[:vg_width - 4])
                    except curses.error:
                        pass
                    try:
                        right.addstr(3, 2, f"VG seg size: {vg_pe_size_formatted}"[:vg_width - 4])
                    except curses.error:
                        pass
                    try:
                        right.addstr(4, 2, f"Logical Vols:  {lv_names_str}"[:vg_width - 4])
                    except curses.error:
                        pass
                    try:
                        right.addstr(5, 2, f"Free space:   {vg_free_formatted}"[:vg_width - 4])
                    except curses.error:
                        pass
                    
                    # Only add header if we have vertical space
                    if h > 7:
                        try:
                            right.addstr(7, 2, "[ Discovered LVols.. ]", curses.A_BOLD)
                        except curses.error:
                            pass
                    y = 9
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
                        try:
                            lv_text = f"Logical Volume: {display_name}"
                            # Check if the text would fit in the window
                            if len(lv_text) > vg_width - 4:
                                lv_text = lv_text[:vg_width - 7] + "..."
                            right.addstr(y, 2, lv_text, curses.A_BOLD)
                        except curses.error:
                            # Skip if we can't write this line
                            pass
                        y += 1
                        
                        # Add mount point and capacity information
                        # Find the device path for this logical volume
                        # LVM volumes can be accessed via two path formats:
                        # 1. /dev/VGName/LVName
                        # 2. /dev/mapper/VGName-LVName (with hyphen instead of slash)
                        lv_path_dev = f"/dev/{vg_name}/{name}"
                        lv_path_mapper = f"/dev/mapper/{vg_name}-{name}"
                        mount_point = "N/A"
                        capacity = format_size(group[0].get('lv_size')) if group else "N/A"
                        used = "N/A"
                        available = "N/A"
                        
                        # Search for mount point and capacity information in devices
                        # Check both possible path formats with flexible matching
                        for dev in devices:
                            if isinstance(dev, dict) and dev.get('path'):
                                dev_path = dev.get('path')
                                
                                # Check for exact match or if the path contains the LV identifiers
                                if (dev_path == lv_path_dev or
                                    dev_path == lv_path_mapper or
                                    f"/dev/{vg_name}/{name}" in dev_path or
                                    f"/dev/mapper/{vg_name}-{name}" in dev_path or
                                    f"/{vg_name}/{name}" in dev_path or
                                    f"/{vg_name}-{name}" in dev_path):
                                    mount_point = dev.get('mount_point', 'N/A')
                                    used = dev.get('used', 'N/A')
                                    available = dev.get('avail', 'N/A')
                                    break
                        
                        # Display additional information
                        try:
                            right.addstr(y, 4, f"Mounted: {mount_point}"[:vg_width - 6])
                            y += 1
                        except curses.error:
                            pass
                        
                        try:
                            right.addstr(y, 4, f"Capacity: {capacity}"[:vg_width - 6])
                            y += 1
                        except curses.error:
                            pass
                        
                        try:
                            right.addstr(y, 4, f"Used: {used}"[:vg_width - 6])
                            y += 1
                        except curses.error:
                            pass
                        
                        try:
                            right.addstr(y, 4, f"Available: {available}"[:vg_width - 6])
                            y += 1
                        except curses.error:
                            pass
                        
                        # Add blank line before tabular data
                        y += 1
                        
                        # Ensure we don't write outside window boundaries
                        if y >= h - 2:
                            break
                        try:
                            formatted_header = "{:<10} {:<10} {:>10} {:>10} {:<20} {}".format(
                                "LE Start", "LE End", "PE Count", "PE Size", "PVs", "PE Start")
                            # Ensure we don't write beyond window width
                            max_line_width = vg_width - 6  # Allow for borders and margin
                            if len(formatted_header) > max_line_width:
                                formatted_header = formatted_header[:max_line_width]
                            right.addstr(y, 4, formatted_header, curses.A_UNDERLINE)
                        except curses.error:
                            # Skip if we can't write the header (probably out of bounds)
                            pass
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
                            
                            # Format string with boundary check
                            try:
                                formatted_str = "{:<10} {:<10} {:>10} {:>10} {:<20} {}".format(
                                    le_start, le_end, str(pe_count), pe_size, clean_pvlist, pe_start_info)
                                # Ensure we don't write beyond window width
                                max_line_width = vg_width - 6  # Allow for borders and margin
                                if len(formatted_str) > max_line_width:
                                    formatted_str = formatted_str[:max_line_width]
                                right.addstr(y, 4, formatted_str)
                            except curses.error:
                                # Skip this line if we can't write it (probably out of bounds)
                                pass
                            y += 1
                        y += 1
                    else:
                        try:
                            right.addstr(1, 2, f"No LVM info for {path}")
                        except curses.error:
                            # Skip if we can't write the message
                            pass
                    
                    # Add mount point and capacity information
                    # Find the device path for this logical volume
                    # LVM volumes can be accessed via two path formats:
                    # 1. /dev/VGName/LVName
                    # 2. /dev/mapper/VGName-LVName (with hyphen instead of slash)
                    lv_path_dev = f"/dev/{vg_name}/{name}"
                    lv_path_mapper = f"/dev/mapper/{vg_name}-{name}"
                    mount_point = "N/A"
                    capacity = format_size(group[0].get('lv_size')) if group else "N/A"
                    used = "N/A"
                    available = "N/A"
                    
                    # Search for mount point and capacity information in devices
                    # Check both possible path formats with flexible matching
                    for dev in devices:
                        if isinstance(dev, dict) and dev.get('path'):
                            dev_path = dev.get('path')
                            
                            # Check for exact match or if the path contains the LV identifiers
                            if (dev_path == lv_path_dev or
                                dev_path == lv_path_mapper or
                                f"/dev/{vg_name}/{name}" in dev_path or
                                f"/dev/mapper/{vg_name}-{name}" in dev_path or
                                f"/{vg_name}/{name}" in dev_path or
                                f"/{vg_name}-{name}" in dev_path):
                                mount_point = dev.get('mount_point', 'N/A')
                                used = dev.get('used', 'N/A')
                                available = dev.get('avail', 'N/A')
                                break
                    
                    # Display additional information
                    try:
                        right.addstr(y, 4, f"Mounted: {mount_point}")
                        y += 1
                        right.addstr(y, 4, f"Capacity: {capacity}")
                        y += 1
                        right.addstr(y, 4, f"Used: {used}")
                        y += 1
                        right.addstr(y, 4, f"Available: {available}")
                        y += 1
                    except curses.error:
                        # Skip if we can't write the information
                        pass
                    
                    # Add blank line before tabular data
                    y += 1
                    
                    # Ensure we don't write outside window boundaries
                    if y >= h - 2:
                        break
                    try:
                        formatted_header = "{:<10} {:<10} {:>10} {:>10} {:<20} {}".format(
                            "LE Start", "LE End", "PE Count", "PE Size", "PVs", "PE Start")
                        # Ensure we don't write beyond window width
                        max_line_width = vg_width - 6  # Allow for borders and margin
                        if len(formatted_header) > max_line_width:
                            formatted_header = formatted_header[:max_line_width]
                        right.addstr(y, 4, formatted_header, curses.A_UNDERLINE)
                    except curses.error:
                        # Skip if we can't write the header (probably out of bounds)
                        pass
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
                        
                        # Format string with boundary check
                        try:
                            formatted_str = "{:<10} {:<10} {:>10} {:>10} {:<20} {}".format(
                                le_start, le_end, str(pe_count), pe_size, clean_pvlist, pe_start_info)
                            # Ensure we don't write beyond window width
                            max_line_width = vg_width - 6  # Allow for borders and margin
                            if len(formatted_str) > max_line_width:
                                formatted_str = formatted_str[:max_line_width]
                            right.addstr(y, 4, formatted_str)
                        except curses.error:
                            # Skip this line if we can't write it (probably out of bounds)
                            pass
                        y += 1
                    y += 1
            else:
                right.addstr(1, 2, f"No LVM info for {path}")
          
            #------------------------------------------------------------
            # Panel (Top half, right side)
            # Create Physical Volumes panel (right side, top half)
            #------------------------------------------------------------
            pv_panel = stdscr.derwin(pv_height, pv_width, 0, vg_width)
            pv_panel.box()
            # Highlight panel title when it has focus
            title_attr = curses.A_BOLD if active_panel == 1 else 0
            try:
                pv_panel.addstr(0, 2, " Physical Volumes (PV) ", title_attr)
            except curses.error:
                # Skip if we can't write the header (probably out of bounds)
                pass
            
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
                
                #----------------------------------------------
                # Table headers
                # Display PV info in the new panel
                #----------------------------------------------
                try:
                    formatted_header = "{:>2} {:>16} {:>8} {:>10}".format(
                        "Block dev", "Size bin", "LV #", "Free cap")
                    # Ensure we don't write beyond window width
                    max_width = pv_width - 4  # Allow for borders and margin
                    if len(formatted_header) > max_width:
                        formatted_header = formatted_header[:max_width]
                    pv_panel.addstr(2, 2, formatted_header, curses.A_UNDERLINE)
                except curses.error:
                    # Skip if we can't write the header
                    pass
                
                # Ensure pv_selected stays within valid range
                if pvs_in_vg:
                    pv_selected = min(pv_selected, len(pvs_in_vg) - 1)
                
                for j, p in enumerate(pvs_in_vg):
                    if j >= pv_height - 2:
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
                        # Highlight the selected PV when this panel has focus
                        attr = curses.A_REVERSE if (j == pv_selected and active_panel == 1) else 0
                        try:
                            formatted_str = "{:<15} {:>10} {:>8} {}".format(
                                pname, psize, lv_count, free)
                            # Ensure we don't write beyond window width
                            max_width = pv_width - 4  # Allow for borders and margin
                            if len(formatted_str) > max_width:
                                formatted_str = formatted_str[:max_width]
                            pv_panel.addstr(j + 3, 2, formatted_str, attr)
                        except curses.error:
                            # Skip this line if we can't write it
                            pass
                else:
                    try:
                        pv_panel.addstr(10, 1, "[ waiting... ]")
                    except curses.error:
                        # Skip if we can't write the message
                        pass
            else:
                # If no PV is found for the selected device, display all PVs in the system
                # This ensures the PV panel always shows something, even if the selected device isn't a PV
                try:
                    formatted_header = "{:>2} {:>16} {:>8} {:>10}".format(
                        "Block dev", "Size bin", "LV #", "Free cap")
                    # Ensure we don't write beyond window width
                    max_width = pv_width - 4  # Allow for borders and margin
                    if len(formatted_header) > max_width:
                        formatted_header = formatted_header[:max_width]
                    pv_panel.addstr(2, 2, formatted_header, curses.A_UNDERLINE)
                except curses.error:
                    # Skip if we can't write the header
                    pass
                
                # Display all PVs in the system
                for j, (pv_path, p) in enumerate(pvs_map.items()):
                    if j >= pv_height - 2:
                        break
                    pname = p.get('pv_name', '')
                    # Ensure pname is displayed for test detection
                    if not pname:
                        pname = pv_path
                    
                    # Truncate pname if too long
                    max_pname_width = min(15, pv_width - 25)
                    if len(pname) > max_pname_width:
                        pname = pname[:max_pname_width-3] + "..."
                        
                    psize = format_size(p.get('pv_size'))
                    free = format_size(p.get('pv_free'))
                    vg = p.get('vg_name', 'N/A')
                    
                    # Only write if we have space in the panel
                    if j + 2 < pv_height - 1:
                        try:
                            formatted_str = "{:<15} {:>10} {:>8} {}".format(
                                pname, psize, vg, free)
                            # Ensure we don't write beyond window width
                            max_width = pv_width - 4  # Allow for borders and margin
                            if len(formatted_str) > max_width:
                                formatted_str = formatted_str[:max_width]
                            pv_panel.addstr(j + 3, 2, formatted_str)
                        except curses.error:
                            # Skip this line if we can't write it
                            pass
            
            #---------------------------------------------
            # Panel (Bottom half, right side)
            #------------------------------------------------
            
            # Create Block Devices panel (right side, bottom half)
            block_dev_panel = stdscr.derwin(block_dev_height, pv_width, pv_height, vg_width)
            block_dev_panel.box()
            # Highlight panel title when it has focus
            title_attr = curses.A_BOLD if active_panel == 2 else 0
            try:
                block_dev_panel.addstr(0, 2, " System Block Devices ", title_attr)
            except curses.error:
                # Skip if we can't write the header (probably out of bounds)
                pass
            
            # Display block devices list
            if devices:
                # Display header for block devices
                try:
                    formatted_header = "{:<9} {:>16} {:>6} {:>8} {:>8} {:>9} {:>8}".format(
                        "Device", "Size bin", "Unit", "Part", "Type", "FSinf", "Flags")
                    # Ensure we don't write beyond window width
                    max_width = pv_width - 4  # Allow for borders and margin
                    if len(formatted_header) > max_width:
                        formatted_header = formatted_header[:max_width]
                    block_dev_panel.addstr(2, 2, formatted_header, curses.A_UNDERLINE)
                except curses.error:
                    # Skip if we can't write the header
                    pass
                
                # Calculate visible range based on panel size and current selection
                visible_count = block_dev_height - 4  # Account for borders and header
                start_idx = max(0, min(block_dev_selected, max(0, len(devices) - visible_count)))
                end_idx = min(start_idx + visible_count, len(devices))
                
                for i, dev in enumerate(devices[start_idx:end_idx]):
                    y_pos = i + 3
                    if y_pos >= block_dev_height - 1:
                        break
                    
                    # Get device info
                    if isinstance(dev, dict):
                        name = dev.get('name', 'Unknown')
                        size = format_size(dev.get('size', 0))
                        dev_type = dev.get('type', 'Unknown')
                        
                        # Get additional info from fdisk/parted with priority to parted
                        # Only use fdisk_type_info for Disk column, not fdisk_id_info
                        disk_type = dev.get('fdisk_type_info', '---')
                        fs_info = dev.get('gpt_fs_info', '---')
                        flags_info = dev.get('gpt_df_flagsinfo', '---')
                        
                        # Get device size for potential use in flags_info
                        device_size = format_size(dev.get('size', 0))
                        
                        # Determine partition type for Part column
                        part_type = '---'
                        
                        # Get device type and partition type info from various sources
                        dev_type_value = dev.get('type', '')
                        fdisk_id = dev.get('fdisk_id_info', '')
                        gpt_flags = dev.get('gpt_disk_flags_type', '')
                        
                        # If it's a disk, display "Disk" in the Part column
                        if dev_type_value == 'disk':
                            part_type = 'Disk'
                        # Check for partition type and set appropriate value
                        elif dev_type_value == 'part':
                            # Check for primary partition
                            if 'primary' in fdisk_id.lower() or 'primary' in gpt_flags.lower():
                                part_type = 'Pri'
                            # Check for extended partition
                            # Check for extended partition to set Part column
                            elif 'extended' in fdisk_id.lower() or 'extended' in gpt_flags.lower():
                                part_type = 'Extd'
                            # Check for logical partition
                            elif 'logical' in fdisk_id.lower() or 'logical' in gpt_flags.lower():
                                part_type = 'Logi'
                            else:
                                # Default to 'Pri' for regular partitions if type not detected
                                part_type = 'Pri'

                        # Set Flags to '---' if Unit='part' and Part='Extd', per latest feedback
                        if dev_type_value == 'part' and part_type == 'Extd':
                            flags_info = '---'
                        
                        if dev.get('gpt_part_table_type', 'N/A') != 'N/A':
                            disk_type = dev.get('gpt_part_table_type', 'N/A')
                    else:
                        name = str(dev)
                        size = 'N/A'
                        dev_type = 'Unknown'
                        part_type = '---'  # Default to '---' for unknown partition types
                        disk_type = 'N/A'
                        fs_info = 'N/A'
                        flags_info = 'N/A'
                    
                    # Truncate name if too long
                    if len(name) > 13:
                        name = name[:10] + "..."
                        
                    # Truncate other fields if too long
                    if len(part_type) > 6:
                        part_type = part_type[:5] + "."
                    if len(disk_type) > 6:
                        disk_type = disk_type[:5] + "."
                    if len(fs_info) > 6:
                        fs_info = fs_info[:5] + "."
                    if len(flags_info) > 6:
                        flags_info = flags_info[:5] + "."
                    if len(dev_type) > 6:
                        dev_type = dev_type[:5] + "."
                    
                    # Uppercase 'lvm' in Flags column if present
                    if flags_info == 'lvm':
                        flags_info = 'LVM'
                        
                    # Highlight if this is the selected block device
                    attr = curses.A_REVERSE if (i + start_idx == block_dev_selected and active_panel == 2) else 0
                    
                    # Format string safely (with boundary checks)
                    try:
                        formatted_str = "{:<15} {:<12} {:<8} {:<8} {:<8} {:<8} {:<8}".format(
                            name, size, dev_type, part_type, disk_type, fs_info, flags_info)
                        # Ensure we don't write beyond window width
                        max_width = pv_width - 4  # Allow for borders and margin
                        if len(formatted_str) > max_width:
                            formatted_str = formatted_str[:max_width]
                        block_dev_panel.addstr(y_pos, 2, formatted_str, attr)
                    except curses.error:
                        # Safely handle any curses errors during writing
                        pass
            else:
                try:
                    block_dev_panel.addstr(1, 2, "No block devices available")
                except curses.error:
                    # Skip if we can't write the message
                    pass

            # Refresh screen and handle keyboard input
            stdscr.refresh()
            key = stdscr.getch()
            
            # Handle panel switching with Tab key
            if key == 9:  # Tab key
                active_panel = (active_panel + 1) % 3  # Cycle through 0, 1, 2
            # Handle navigation in main panel
            elif active_panel == 0:
                if key in (curses.KEY_UP, ord('k')) and current > 0:
                    current -= 1
                elif key in (curses.KEY_DOWN, ord('j')) and current < len(devices) - 1:
                    current += 1
            # Handle navigation in physical volumes panel
            elif active_panel == 1:
                dev = devices[current] if devices else {}
                if isinstance(dev, dict):
                    path = dev.get('path')
                else:
                    path = dev
                pv = pvs_map.get(path)
                
                if pv:
                    vg_name = pv.get('vg_name')
                    pvs_in_vg = [p for p in pvs_map.values() if p.get('vg_name') == vg_name]
                    
                    if key in (curses.KEY_UP, ord('k')) and pv_selected > 0:
                        pv_selected -= 1
                    elif key in (curses.KEY_DOWN, ord('j')) and pv_selected < len(pvs_in_vg) - 1:
                        pv_selected += 1
            # Handle navigation in block devices panel
            elif active_panel == 2:
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
                # Get current dimensions to ensure we don't exceed bounds
                h, w = stdscr.getmaxyx()
                # Truncate error message if needed
                if len(error_msg) >= w:
                    error_msg = error_msg[:w-1]
                
                stdscr.addstr(0, 0, error_msg)
                
                # Add instructions on next line
                if h > 1:  # Make sure we have at least 2 rows
                    instruction = "Press any key to retry, 'q' to quit"
                    if len(instruction) >= w:
                        instruction = instruction[:w-1]
                    stdscr.addstr(1, 0, instruction)
                
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