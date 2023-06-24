import sys
import tty
import termios



getchar = GetchUnix()
while True:
    char = getchar()
    if char == b"\r":
        break
    print(char)
