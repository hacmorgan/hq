# Make a simple prompt for dumb terminals (fixes emacs' problem logging into remotes with zsh)
[[ $TERM == "dumb" ]] && unsetopt zle && PS1='$ ' && return


# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block, everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:/usr/local/bin:$PATH

# Path to your oh-my-zsh installation.
export ZSH="$HOME/.oh-my-zsh"

# Set name of the theme to load --- if set to "random", it will
# load a random theme each time oh-my-zsh is loaded, in which case,
# to know which specific one was loaded, run: echo $RANDOM_THEME
# See https://github.com/ohmyzsh/ohmyzsh/wiki/Themes
ZSH_THEME=powerlevel10k/powerlevel10k

# Set list of themes to pick from when loading at random
# Setting this variable when ZSH_THEME=random will cause zsh to load
# a theme from this variable instead of looking in ~/.oh-my-zsh/themes/
# If set to an empty array, this variable will have no effect.
# ZSH_THEME_RANDOM_CANDIDATES=( "robbyrussell" "agnoster" )

# Uncomment the following line to use case-sensitive completion.
# CASE_SENSITIVE="true"

# Uncomment the following line to use hyphen-insensitive completion.
# Case-sensitive completion must be off. _ and - will be interchangeable.
# HYPHEN_INSENSITIVE="true"

# Uncomment the following line to disable bi-weekly auto-update checks.
# DISABLE_AUTO_UPDATE="true"

# Uncomment the following line to automatically update without prompting.
# DISABLE_UPDATE_PROMPT="true"

# Uncomment the following line to change how often to auto-update (in days).
# export UPDATE_ZSH_DAYS=13

# Uncomment the following line if pasting URLs and other text is messed up.
# DISABLE_MAGIC_FUNCTIONS=true

# Uncomment the following line to disable colors in ls.
# DISABLE_LS_COLORS="true"

# Uncomment the following line to disable auto-setting terminal title.
# DISABLE_AUTO_TITLE="true"

# Uncomment the following line to enable command auto-correction.
# ENABLE_CORRECTION="true"

# Uncomment the following line to display red dots whilst waiting for completion.
COMPLETION_WAITING_DOTS="true"

# Uncomment the following line if you want to disable marking untracked files
# under VCS as dirty. This makes repository status check for large repositories
# much, much faster.
# DISABLE_UNTRACKED_FILES_DIRTY="true"

# Uncomment the following line if you want to change the command execution time
# stamp shown in the history command output.
# You can set one of the optional three formats:
# "mm/dd/yyyy"|"dd.mm.yyyy"|"yyyy-mm-dd"
# or set a custom format using the strftime function format specifications,
# see 'man strftime' for details.
# HIST_STAMPS="mm/dd/yyyy"

# Would you like to use another custom folder than $ZSH/custom?
# ZSH_CUSTOM=/path/to/new-custom-folder

# Which plugins would you like to load?
# Standard plugins can be found in ~/.oh-my-zsh/plugins/*
# Custom plugins may be added to ~/.oh-my-zsh/custom/plugins/
# Example format: plugins=(rails git textmate ruby lighthouse)
# Add wisely, as too many plugins slow down shell startup.
plugins=(git zsh-syntax-highlighting zsh-autosuggestions)

source $ZSH/oh-my-zsh.sh
# source /opt/ros/noetic/setup.zsh


# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

# Source ROS if installed
ROS_SETUP=/opt/ros/noetic/setup.zsh
[[ ! -e $ROS_SETUP ]] || source $ROS_SETUP

# Allow use of the `nvm` command (from the AUR)
source /usr/share/nvm/init-nvm.sh


# # Source hq python venv
# HQ_VENV=$HOME/venvs/hq
# [[ ! -e $HQ_VENV ]] || source $HQ_VENV/bin/activate


#################
#    ALIASES    #
#################
alias sdn='sudo shutdown now'
alias rsn='sudo shutdown -r now'
alias ip3='ipython3'
alias p3='python3'
alias p3m='python3 -m'
alias p3mp='python3 -m pip'
alias p3iu='python3 -m pip install --use-pep517 --upgrade'
alias p3ir='python3 -m pip install --use-pep517 --requirement'
alias p3iue='python3 -m pip install --use-pep517 --upgrade --editable'
alias p2='python2'
alias pm='pulsemixer'
alias tm='tmux attach || tmux'
alias d2p="pwd | sed 's/datasets/processed/g'"
alias p2d="pwd | sed 's/processed/datasets/g'"
alias r2p="pwd | sed 's/rapid/pond/g'"
alias p2r="pwd | sed 's/pond/rapid/g'"
alias b2s="pwd | sed 's/build/src/g'"
alias s2b="pwd | sed 's/src/build/g'"
alias l='ls -lh'
alias ll='ls -la'
alias lt='ls -lt'
alias lh='ls -lh'
alias cdl='{ dir="$(cat)" ; cd "$dir" ; ls -la } <<< '
alias display_off='xset -display :0.0 dpms force off'
alias display_on='xset -display :0.0 dpms force on'
alias startvnc='systemctl --user restart x0vncserver'
alias gca='git commit -a -v'
alias gcp='git cherry-pick'
alias glg='git log --graph'
alias gdu='git push origin --delete'
alias gpu='gp --set-upstream origin "$(git branch --show-current)"'
alias vb='vim.basic'
alias vpn_connect='openvpn3 session-start --config abyss'
alias vpn_status='openvpn3 sessions-list'
alias vpn_disconnect='openvpn3 session-manage --disconnect --config abyss'
alias rs='rsync -avhP'
alias nomachine='/usr/NX/bin/nxplayer'
alias rmundotree='find . -name "*~undo-tree~*" -delete'
alias rgn='rg --files-with-matches'
alias gdn='gd --name-only'
alias gdnu='gd --diff-filter=U --name-only'
alias gdup='gd $(git merge-base HEAD origin/master)'
alias gdnup='gdup --name-only'
alias cdscr='cd /mnt/vault/scratch/dataforce/hamish'


#################
#    EXPORTS    #
#################

# Add new directories to $PATH
path=(
    "$HOME/devtools/bin"   # Abyss dev scripts
    "$HOME/.cargo/bin"     # Local Rust installs
    "$HOME/.local/bin"     # Mostly comma, snark, and old stages
    "/usr/local/cuda/bin"  # For manual CUDA installs from runfile
    $path
)
export PATH

# Set $LD_LIBRARY_PATH as a special zsh environment variable and add new library paths
typeset -T LD_LIBRARY_PATH ld_library_path :
ld_library_path=(
    "$HOME/.local/lib"       # Comma, snark and Abyss C++ libraries
    "/usr/local/cuda/lib64"  # For manual CUDA installs from runfile
    $ld_library_path
)
export LD_LIBRARY_PATH

# Default editor (for git commits etc)
export EDITOR="/usr/bin/nvim"

# Music Player Daemon
export MPD_HOST="localhost"
export MPD_PORT="6600"

# This should start emacs if the daemon is not already running
export ALTERNATE_EDITOR=""

# # In the past there were reasons to manually set TERM
# export TERM="xterm-256color"

# # Set python's debugger as ipython (still doesn't bring tab-complete)
# export PYTHONBREAKPOINT='IPython.core.debugger.set_trace'

# AWS Credentials
export ABYSS_AWS_ENVFILE="$HOME/.aws/credentials.env"

# MLflow server address
export MLFLOW_URI="http://10.137.8.100:5000"

# Tensorflow logging
export TF_CPP_MIN_LOG_LEVEL=3


##############
#    VENV    #
##############
export HQ_VENV="$HOME/venvs/py3.11"
source "$HQ_VENV/bin/activate"
