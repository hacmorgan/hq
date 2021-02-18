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

# set backgrounds
feh --bg-center ~/src/hq/etc/wallpapers/eboy_tok.png &!

# set keyboard params
xset r rate 250 50 &!

# set some touchpad & trackpoint settings
xinput set-prop 'SynPS/2 Synaptics TouchPad' 'libinput Tapping Enabled' 1
xinput set-prop 'SynPS/2 Synaptics TouchPad' 'libinput Natural Scrolling Enabled' 1
xinput set-prop 'SynPS/2 Synaptics TouchPad' 'libinput Accel Speed' 0.6

# map caps-lock to super
setxkbmap -option caps:super &!

# start the emacs server. disown so that exiting x session doesn't kill emacs
emacs --daemon &!

# self-explanatory
mount-shared-drives &!

# this is the last thing we do!
exec i3
