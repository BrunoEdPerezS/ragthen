# ragthen-content

## Purpose
Library structure documentation and sync scripts for Ragthen content management.

## Requirements

### Requirement: Library Directory Structure
The system SHALL define a standard library directory structure under `~/.ragthen/libraries/<name>/` where PDFs, TXTs, and MDs are stored. ChromaDB indexes SHALL live in a `.index/` subdirectory. PDFs SHALL NOT be versioned in Git.

#### Scenario: New library creation
- **WHEN** a user creates a directory under `~/.ragthen/libraries/marketing/` and places PDFs inside
- **THEN** running `ragthen ingest -l marketing` indexes all files into `~/.ragthen/libraries/marketing/.index/`

#### Scenario: Git ignores binaries
- **WHEN** PDFs or ChromaDB index files are added to the repo's libraries directory
- **THEN** Git ignores them (handled by `.gitignore` in each library path)

### Requirement: Google Drive Sync (Placeholder)
The system SHALL include a placeholder script `sync_from_drive.py` that outlines the interface for downloading PDFs from Google Drive into local library directories. Implementation is deferred.

#### Scenario: Sync script invocation
- **WHEN** `python sync_from_drive.py` is run
- **THEN** it prints a message indicating it's not yet implemented and shows the planned usage interface
