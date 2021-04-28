# hq
Config files, utilities, and other useful stuff

## sysbs
sysbs (system bootstrapper) performs a multitude of functions, see `sysbs --help` for the full list. It is intended to save a large amount of time when setting up a new system, e.g. installing fonts, installing oh-my-zsh, etc. It also provides simple way to keep things up to date, e.g. reinstalling scripts after new features are added.

## dots
The dots directory contains configurations for various programs. They are automatically symlinked to the correct spot by [sysbs --symlink-dots](sysbs), using [etc/homedots](etc/homedots) to specify which need to be symlinked to ~/, instead of ~/.config/

## scripts
A number of scripts for doing various useful things. Most of them have `--help` functions for more info.

## etc
The etc directory stores various other things that don't fit into dots or scripts, such as reference information for `sysbs`, boilerplate code, etc.

### boilerplates
A number of templates are kept here for various languages and use cases. This saves time when creating a new script compared to copying an existing one, as very little needs to be deleted.

### packagelist
This stores a list of the packages intalled on any given system. The main branch should not have this file.

packagelist should have the following structure:
- line 1: command to list all packages installed on system
- line 2: command to install packages
- lines 3+: package names, one per line
  - "#" at the start of the line if we know about the package but don't want to auto install it in future
  
sysbs --update-package-list will find new packages that aren't already accounted for, and give the user the option to comment them out before they are added to packagelist
