# LVM Browser User Guide: Navigating the Enhanced UI

## Introduction

This guide covers the recent enhancements to the LVM Browser user interface. The primary change involves a new split-panel layout on the right side, designed to provide simultaneous visibility into Physical Volumes (PVs) and Block Devices. Navigation has also been streamlined for efficient switching and movement between these panels. This :Pattern facilitates easier correlation between the PV :Context and the underlying Block Device :Context.

## New UI Layout: Split Right Panel

The LVM Browser window is now organized as follows:

*   **Left Panel:** Displays the list of Volume Groups (VGs). This panel remains unchanged.
*   **Right Panel:** This area is now vertically split into two distinct sections:
    *   **Upper Section (Physical Volumes):** Shows detailed information about the Physical Volumes associated with the selected Volume Group.
    *   **Lower Section (Block Devices):** Lists the underlying Block Devices related to the selected components.

This :Solution allows users to view PV details and the corresponding Block Devices side-by-side, improving workflow efficiency when analyzing LVM configurations.

## Navigation Controls

Navigating the new interface is primarily done using the keyboard:

*   **`Tab` Key:**
    *   Toggles focus between the **Physical Volumes** (upper right) panel and the **Block Devices** (lower right) panel.
    *   The active panel will typically be indicated by a highlighted border or cursor position.
*   **Arrow Keys (`Up Arrow`, `Down Arrow`, `Left Arrow`, `Right Arrow`):**
    *   Used for navigation *within* the currently active panel.
    *   When the **Physical Volumes** panel is active, arrows might navigate between different PVs or fields (depending on specific implementation).
    *   When the **Block Devices** panel is active, the `Up Arrow` and `Down Arrow` keys are used to scroll through the list of block devices.

## Using the Split Panel View Effectively

Here are some examples of how to leverage the new layout:

1.  **Correlating PVs and Block Devices:**
    *   Select a Volume Group in the left panel.
    *   Observe the PVs listed in the upper right panel.
    *   Press `Tab` to switch focus to the Block Devices panel.
    *   Use the `Down Arrow` key to scroll through the block devices and identify those associated with the PVs shown above.
2.  **Quickly Switching Context:**
    *   While examining PV details in the upper right panel, press `Tab` to instantly switch focus to the Block Devices list for further investigation.
    *   Press `Tab` again to return focus to the PV panel.

## Keyboard Shortcuts Summary

*   **`Tab`**: Switch focus between Physical Volumes panel and Block Devices panel.
*   **`Up Arrow` / `Down Arrow`**: Navigate items within the active panel (especially useful for the Block Devices list).
*   **`Left Arrow` / `Right Arrow`**: Navigate elements/fields within the active panel (behavior might vary).

This enhanced UI aims to provide a more integrated and efficient experience for managing LVM structures.