alias vb=vim.basic

# Import aliases from .zshrc
[[ ! -e ~/.zshrc ]] || . <(grep "^alias" ~/.zshrc)

# Import git aliases from oh-my-zsh
GIT_ALIASES=~/.oh-my-zsh/plugins/git/git.plugin.zsh
[[ ! -e $GIT_ALIASES ]] || . <(grep "^alias" $GIT_ALIASES)
