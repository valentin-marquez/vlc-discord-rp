# Changelog

## [2.0.1] - 2025-03-07
### Fixed
- Fixed false positive detection in media status

## [2.0.0] - 2025-03-06
### Added
- HTTP interface integration using `http://localhost:port/requests/status.json` for media data
- System tray icon with auto-detection
- Enhanced cover art tracking for better Discord display
- Improved audio media implementation
- Automatic VLC configuration during installation

### Changed
- Complete overhaul of media status detection method
- Migrated from file-based tracking to HTTP interface

### Fixed
- More reliable media metadata extraction
- Consistent cover art display in Discord

## [1.1.0] - 2025-03-05
### Added
- Cover art fetching from MusicBrainz (Fixes #1)
- Better media type detection

### Changed
- Improved error handling for Discord connection
- Updated installer UI with modern design

### Fixed
- Status file path detection issues
- Media position tracking