#!/bin/sh


userresources=$HOME/.Xresources
usermodmap=$HOME/.Xmodmap
sysresources=/etc/X11/xinit/.Xresources
sysmodmap=/etc/X11/xinit/.Xmodmap


# merge in defaults and keymaps
if [ -f $sysresources ]; then
    xrdb -merge $sysresources
fi

if [ -f $sysmodmap ]; then
    xmodmap $sysmodmap
fi

if [ -f "$userresources" ]; then
    xrdb -merge "$userresources"
fi

if [ -f "$usermodmap" ]; then
    xmodmap "$usermodmap"
fi


# start some nice programs
if [ -d /etc/X11/xinit/xinitrc.d ] ; then
 for f in /etc/X11/xinit/xinitrc.d/?*.sh ; do
  [ -x "$f" ] && . "$f"
 done
 unset f
fi


# start picom
picom &!

# set numlock to be on 
numlockx &!

# set backgrounds as a backup
feh --bg-center ~/hq/etc/wallpapers/eboy_tok.png &!

# set keyboard params
xset r rate 250 50 &!

# # Configure xinput
# $HOME/.local/bin/configure-xinput

# map caps-lock to super - only required for IBM Model M. Don't want this for Displaywriter
# setxkbmap -option caps:super &!

# # start the emacs server. disown so that exiting x session doesn't kill emacs
# emacs --daemon &!

# Start the ssh agent
(eval "$(ssh-agent -s)" && ssh-add ~/.ssh/id_rsa) &!

# this is the last thing we do!
# exec startxfce4
exec i3
