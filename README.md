# hq
Config files, utilities, and other useful stuff

[![Test](https://github.com/hacmorgan/hq/actions/workflows/test.yml/badge.svg)](https://github.com/hacmorgan/hq/actions/workflows/test.yml)

## bash-std

`bash-std` is a bash library providing formatting helpers, a logging system, and declarative CLI argument parsing. Source it in any bash script with:

```bash
source $(type -p bash-std)
```

### Argument parsing

Define your CLI interface in an `options` function and pass it to `bash-std-application-init`:

```bash
source $(type -p bash-std)

function options {
    cat <<EOF
input-file; Input file to process
--output,-o=<path>; default=/dev/stdout; Output file path
--verbose,-v; Enable verbose output
--mode=<mode>; Processing mode
files*; Extra files
EOF
}

bash-std-application-init "$@" < <(options) || die "failed"

# Variables are now set:
echo "input: $options_input_file"
echo "output: $options_output"
((options_verbose)) && echo "verbose mode on"
for f in "${options_files[@]}"; do echo "extra: $f"; done
```

Option types:
- **Positional**: no leading `-`, filled in definition order (e.g. `input-file; Description`)
- **Variadic positional**: trailing `*` collects remaining positionals into an array (e.g. `files*; Description`)
- **Flag**: no `=<...>`, set to `1` when present (e.g. `--verbose,-v; Description`)
- **Value option**: `=<placeholder>` syntax, optionally with `default=` (e.g. `--output,-o=<path>; default=/dev/stdout; Description`)

Variable names are always `options_` + the first long name with hyphens replaced by underscores.

### Using bash-std from outside this repo

To use `bash-std` in a script on a machine where it may not be installed, use `type -p` to find it in PATH and fall back to a cached copy under `~/.local/bin`, pulling from GitHub only if that doesn't exist yet:

```bash
bash_std_path="$(type -p bash-std)"
if [[ -z "$bash_std_path" ]]; then
    echo "Could not find bash-std in PATH, pulling from GitHub..." >&2
    bash_std_path="$HOME/.local/bin/bash-std"
    if [[ ! -e "$bash_std_path" ]]; then
        mkdir --parents --verbose "$(dirname "$bash_std_path")"
        curl -sSL https://raw.githubusercontent.com/hacmorgan/hq/refs/heads/main/applications/bash-std \
            -o "$bash_std_path"
    fi
fi
source "$bash_std_path"
```

---

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
