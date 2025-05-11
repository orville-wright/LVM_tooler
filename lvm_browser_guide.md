# LVM Browser Guide

## Overview

The LVM Browser is an interactive terminal-based application for browsing and inspecting Logical Volume Manager (LVM) configuration on Linux systems. It provides a comprehensive view of Volume Groups, Logical Volumes, and Physical Volumes using a curses-based user interface.

## Features

- **Real-time System Detection**: Automatically scans and detects block devices and LVM configurations
- **Multi-panel Interface**: Displays Volume Groups, Physical Volumes, and Block Devices in separate panels
- **Detailed Information Display**: Shows complete information about LVM components including:
  - Volume Group attributes, size, and free space
  - Logical Volume details with mount points and usage statistics
  - Physical Volume characteristics and relationships
  - Block device properties including partition types and filesystem information
- **Interactive Navigation**: Navigate between panels and components using keyboard shortcuts
- **Responsive Design**: Adapts to terminal window size with appropriate error handling

## Installation

### Prerequisites

- Python 3.6+
- Administrative privileges (required to read device information)
- LVM tools (`lvm2` package)

### Dependencies

The application requires the following system utilities:
- `lsblk` - Lists block devices
- `fdisk` - Disk partitioning utility
- `parted` - Partition manipulation tool
- `pvs` - Physical volume display command
- `vgs` - Volume group display command
- `lvs` - Logical volume display command
- `df` - Disk free space reporting tool

### Installation Steps

1. Ensure your system has Python 3.6 or newer installed:
   ```bash
   python3 --version
   ```

2. Install required LVM utilities if not already present:
   ```bash
   # On Debian/Ubuntu
   sudo apt-get install lvm2
   
   # On RHEL/CentOS/Fedora
   sudo yum install lvm2
   ```

3. Save the `app.py` script to your preferred location

4. Make the script executable:
   ```bash
   chmod +x app.py
   ```

## Usage

### Starting the Application

Run the application with root privileges to ensure access to all system device information:

```bash
sudo ./app.py
```

### Interface Layout

The LVM Browser displays information in three main panels:

1. **Volume Group Panel** (Left): Displays the selected Volume Group's information including:
   - Volume Group name and size
   - VG format and extent size
   - Logical volumes in the group
   - Free space
   
2. **Physical Volumes Panel** (Top-Right): Shows Physical Volumes associated with the selected VG:
   - Physical device names
   - Size information
   - Logical volume count
   - Free capacity
   
3. **Block Devices Panel** (Bottom-Right): Displays system block devices:
   - Device names
   - Size information
   - Device type and partition information
   - Filesystem and flag details

### Navigation Controls

- **Tab**: Cycle between the three panels
- **Up/Down** or **k/j**: Navigate within the current panel
- **q or ESC**: Exit the application

### Reading the Display

#### Volume Group Panel

The Volume Group panel shows:
- VG name and total size
- Format and segment size
- List of logical volumes
- Free space
- Detailed information for each LV including:
  - Mount points
  - Capacity
  - Usage statistics
  - Extent allocation details

#### Physical Volumes Panel

The Physical Volumes panel shows:
- Device paths
- Size information
- Number of logical volumes using each PV
- Free capacity

#### Block Devices Panel

The Block Devices panel shows:
- Device names
- Size information
- Unit type (disk, part, etc.)
- Partition type (Pri, Extd, Logi)
- Disk type
- Filesystem information
- Special flags (like LVM)

## Troubleshooting

### Common Issues

#### Application Crashes with "No block devices found or permission denied"

**Cause**: The application doesn't have sufficient privileges to access device information.

**Solution**: Run the application with sudo or as the root user.

#### "Terminal too small" Message

**Cause**: The terminal window doesn't meet the minimum size requirements.

**Solution**: Resize your terminal window to at least 80x10 characters.

#### "Curses error: addwstr() returned ERR"

**Cause**: This occurs when attempting to write text beyond the available screen space, typically when displaying long text strings or when the terminal is resized to a very small dimension.

**Solution**: The application now handles this error internally by safely truncating text or skipping display elements that won't fit. Simply resize your terminal to a larger size if you notice missing information.

#### Physical Volumes Not Displaying

**Cause**: Either there are no PVs on the system, or they're not accessible.

**Solution**: Verify LVM is properly configured and that the application has the necessary permissions.

## Architecture

The LVM Browser consists of several key components:

1. **Data Collection Layer**:
   - Executes system commands to gather block device information
   - Parses output from `lsblk`, `fdisk`, `parted`, `pvs`, `vgs`, `lvs`, and `df`
   - Creates structured data representations of all devices and volumes

2. **Data Processing Layer**:
   - Transforms raw command output into structured objects
   - Establishes relationships between different components
   - Formats sizes for human-readable display

3. **UI Layer**:
   - Initializes curses interface with appropriate settings
   - Creates and manages three display panels
   - Handles user input and navigation
   - Ensures graceful error handling for display issues

## Advanced Usage

### Understanding LVM Extent Information

The detailed Logical Volume displays show information about Physical Extents (PE) and Logical Extents (LE):

- **LE Start**: The starting Logical Extent number 
- **LE End**: The ending Logical Extent number
- **PE Count**: Number of Physical Extents allocated to this segment
- **PE Size**: Size of the segment in bytes
- **PVs**: Physical volumes used by this logical volume
- **PE Start**: Starting Physical Extent number on each PV

This information is particularly valuable for understanding how logical volumes are physically mapped across storage devices.

## Limitations

- LVM snapshots may not display all details
- Very complex LVM configurations with many PVs and LVs may be difficult to navigate in smaller terminals
- The application requires root privileges to access full device information