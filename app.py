#!/usr/bin/env python3
"""
Interactive LVM and Block Device Browser

Scans system block devices and LVM configuration,
and displays in a curses UI with a list of block devices
and details of LVM usage for selected device.
"""
import curses
import json
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
    def dfs(dev):
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
        '-o', 'vg_name,lv_name,lv_size,devices'
    ])

    pvs = pvs_json.get('report', [{}])[0].get('pv', []) if pvs_json else []
    vgs = vgs_json.get('report', [{}])[0].get('vg', []) if vgs_json else []
    lvs = lvs_json.get('report', [{}])[0].get('lv', []) if lvs_json else []

    pvs_map = {pv.get('pv_name'): pv for pv in pvs}
    # Debug print PV names
    # print(f"PV names: {list(pvs_map.keys())}")
    # Debug print devices in Logical Volumes
    # for lv in lvs:
    #     print(f"LV devices: {lv.get('devices')}")
    vg_map = {vg.get('vg_name'): vg for vg in vgs}
    lvs_map = {}
    for lv in lvs:
        vg_name = lv.get('vg_name')
        lvs_map.setdefault(vg_name, []).append(lv)

    return devices, pvs_map, vg_map, lvs_map

def draw_ui(stdscr, devices, pvs_map, vg_map, lvs_map):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)

    current = 0
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        left_w = max(40, w // 3)
        left = stdscr.derwin(h, left_w, 0, 0)
        left.box()
        left.addstr(0, 2, " Block Devices ")
        header = "{:<15} {:<8} {:>10} {:<8}".format("Name", "Type", "Size", "PTType")
        left.addstr(1, 1, header, curses.A_BOLD)
        for idx, dev in enumerate(devices):
            if idx >= h - 3:
                break
            if isinstance(dev, dict):
                name = dev.get('path') or dev.get('name', '')
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

        right = stdscr.derwin(h, w - left_w, 0, left_w)
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
            right.addstr(0, 2, f" {vg_name} ({vg_size}) ")
            fmt = vg.get('vg_attr', '')
            lvs_in_vg = lvs_map.get(vg_name, [])
            lv_names = [lv.get('lv_name') for lv in lvs_in_vg]
            right.addstr(2, 2, f"Format: {fmt}")
            right.addstr(3, 2, f"Logical Volumes: {', '.join(lv_names) if lv_names else 'none'}")
            right.addstr(5, 2, "Logical Volumes:", curses.A_BOLD)
            y = 6
            # Group Logical Volumes by name
            lv_groups = {}
            for lv in lvs_in_vg:
                name = lv.get('lv_name')
                lv_groups.setdefault(name, []).append(lv)
            for name, group in lv_groups.items():
                if y >= h - 2:
                    break
                right.addstr(y, 2, f"Logical Volume: {name}", curses.A_BOLD)
                y += 1
                right.addstr(y, 4, "{:<15} {:>10} {}".format("Name", "Size", "PVs"), curses.A_UNDERLINE)
                y += 1
                for lv in group:
                    if y >= h - 2:
                        break
                    size = format_size(lv.get('lv_size'))
                    pvlist = lv.get('devices', '')
                    right.addstr(y, 4, "{:<15} {:>10} {}".format(name, size, pvlist))
                    y += 1
                y += 1
            if y + 2 < h - 1:
                right.addstr(y, 2, "Physical Volumes:", curses.A_BOLD)
                right.addstr(y + 1, 2, "{:<15} {:>10} {:>8} {}".format("Name", "Size", "LV count", "Free"), curses.A_UNDERLINE)
                pvs_in_vg = [p for p in pvs_map.values() if p.get('vg_name') == vg_name]
                # Calculate LV count per PV
                pv_lv_count = {}
                for lv in lvs_in_vg:
                    devices = lv.get('devices', '')
                    # Debug print devices string
                    # print(f"LV devices: {devices}")
                    for dev in devices.split(','):
                        dev = dev.strip()
                        if dev:
                            dev_basename = dev.split('/')[-1]
                            # Debug print device basename
                            # print(f"Device basename: {dev_basename}")
                            pv_lv_count[dev_basename] = pv_lv_count.get(dev_basename, 0) + 1
                for j, p in enumerate(pvs_in_vg):
                    if y + 2 + j >= h - 1:
                        break
                    pname = p.get('pv_name')
                    psize = format_size(p.get('pv_size'))
                    free = format_size(p.get('pv_free'))
                    lv_count = pv_lv_count.get(pname, 0)
                    right.addstr(y + 2 + j, 2, "{:<15} {:>10} {:>8} {}".format(pname, psize, lv_count, free))
        else:
            right.addstr(1, 2, f"No LVM info for {path}")

        stdscr.refresh()
        key = stdscr.getch()
        if key in (curses.KEY_UP, ord('k')) and current > 0:
            current -= 1
        elif key in (curses.KEY_DOWN, ord('j')) and current < len(devices) - 1:
            current += 1
        elif key in (ord('q'), 27):
            break

def main():
    devices, pvs_map, vg_map, lvs_map = load_data()
    curses.wrapper(draw_ui, devices, pvs_map, vg_map, lvs_map)

if __name__ == '__main__':
    main()