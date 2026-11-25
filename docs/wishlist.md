# Wishlist

[English](wishlist.md) · [Deutsch](wishlist.de.md) · [README](../README.md)

These ideas are recorded for later consideration and are not scheduled for implementation.

## Campaign development and DLC history

- One card per campaign, with its current state and expandable history.
- Distinguish DLC first observed as active, a region first found in a save, and visits/settlements where supported. Each statement needs matching save evidence.
- Use “First observed as active in the save dated …”, rather than claiming an exact activation date. Where possible, bound the interval between an explicitly inactive and an active save.
- Treat incomplete save histories as normal: many users do not retain every autosave. Autosave counts and retention can vary with game settings. Analysis must not require a complete history.
- A DLC already active in the earliest available save has an unknown activation date. Missing DLC metadata does not establish inactivity.
- Account for loading older saves, alternate continuations and archive copies; do not infer DLC deactivation from these alone.
- Account for different DLC mechanisms in Anno 117 and 1800. Historical map previews could optionally join the timeline; a DLC event alone need not create a map variant.

Before implementation, verify detectability and usefulness with incomplete real save collections. This document does not assert Anno 117's current default autosave retention setting.

## Desktop application

See the [desktop GUI proposal](desktop-gui.md) for the proposed portable Windows application, MVP scope and acceptance criteria.
