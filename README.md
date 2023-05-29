# ToggleDebug
A py script to toggle debug settings in an OC config.plist.
```
usage: ToggleDebug.py [-h] [-d DEBUG] [plist_path ...]

ToggleDebug - a py script to toggle debug settings in an OC config.plist

positional arguments:
  plist_path            Path to the target plist - if missing, the script will open in interactive mode.

options:
  -h, --help            show this help message and exit
  -d DEBUG, --debug DEBUG
                        on/off/toggle (default is toggle). Sets AppleDebug, ApplePanic, Target, boot-args as needed.
```
