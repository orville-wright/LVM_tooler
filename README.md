# LVM Browser

An interactive terminal-based application for browsing and inspecting Logical Volume Manager (LVM) configuration on Linux systems.

![LVM Browser Screenshot](https://example.com/screenshot.png)

## About

LVM Browser provides a comprehensive view of Volume Groups, Logical Volumes, and Physical Volumes using a curses-based user interface. It allows system administrators to easily visualize and explore their LVM configurations through an intuitive multi-panel interface.

## Features

- Real-time scanning and detection of block devices and LVM components
- Multi-panel interface showing Volume Groups, Physical Volumes, and Block Devices
- Detailed information display for all LVM components
- Interactive keyboard navigation between panels and components
- Responsive design that adapts to terminal window size
- Robust error handling for reliable operation in various environments

## Installation

### Prerequisites

- Python 3.6+
- Administrative privileges (required to read device information)
- LVM tools (`lvm2` package)

### Quick Start

1. Clone this repository or download `app.py`
2. Make the script executable:
   ```bash
   chmod +x app.py
   ```
3. Run with appropriate permissions:
   ```bash
   sudo ./app.py
   ```

## Usage

Navigate the interface using:
- **Tab**: Cycle between panels
- **Up/Down** or **k/j**: Navigate within a panel
- **q or ESC**: Exit the application

## Documentation

For detailed information, see the following documentation:

- [LVM Browser User Guide](lvm_browser_guide.md) - Complete guide to installing, using, and troubleshooting the application
- [LVM Concepts](lvm_concepts.md) - Explanation of LVM concepts and how they relate to the browser display
- [Curses Error Handling](curses_error_handling.md) - Technical details about the curses error handling implementation

## Error Handling

The application includes comprehensive error handling to manage display issues gracefully. If you encounter the error "Curses error: addwstr() returned ERR", simply resize your terminal to a larger size. The application will handle text that doesn't fit on the screen without crashing.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
