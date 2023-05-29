from Scripts import utils, plist
import os, argparse, re

class ToggleDebug:
    def __init__(self, **kwargs):
        self.u = utils.Utils("Toggle Debug")
        self.plist_path = None
        # Set up a regex match for any boot-args we are looking for to disable debugging
        self.debug_match = re.compile(r"(?i)(-v|keepsyms=[^\s]+|debug=[^\s]+)")
        # We need a tuple of args to set when enabling debug
        self.debug_args  = ("-v","keepsyms=1","debug=0x100")
        self.debug_on = (
            {"path":("Misc","Debug"),"key":"AppleDebug","value_type":bool,"value":True,"force":True},
            {"path":("Misc","Debug"),"key":"ApplePanic","value_type":bool,"value":True,"force":True},
            {"path":("Misc","Debug"),"key":"Target","value_type":int,"value":67,"force":True},
            {"path":("Misc","Debug"),"key":"DisplayLevel","value_type":int,"value":2147483714,"force":True},
            {"path":("NVRAM","Add"),"key":"7C436110-AB2A-4BBB-A880-FE41995C9F82","value_type":dict,"value":{}},
            {"path":("NVRAM","Delete"),"key":"7C436110-AB2A-4BBB-A880-FE41995C9F82","value_type":list,"value":[]}
        )
        self.debug_off = (
            {"path":("Misc","Debug"),"key":"AppleDebug","value_type":bool,"value":False,"force":True},
            {"path":("Misc","Debug"),"key":"ApplePanic","value_type":bool,"value":False,"force":True},
            {"path":("Misc","Debug"),"key":"Target","value_type":int,"value":0,"force":True},
            {"path":("Misc","Debug"),"key":"DisplayLevel","value_type":int,"value":2147483714,"force":True},
            {"path":("NVRAM","Add"),"key":"7C436110-AB2A-4BBB-A880-FE41995C9F82","value_type":dict,"value":{}},
            {"path":("NVRAM","Delete"),"key":"7C436110-AB2A-4BBB-A880-FE41995C9F82","value_type":list,"value":[]}
        )

    def ensure_path(self,plist_data,path=None,key=None,value=None,value_type=None,force=False):
        if any((x is None for x in (plist_data,path,key,value))):
            return plist_data # Incorrect incoming data
        temp_data = plist_data
        for p in path:
            if not p in temp_data:
                temp_data[p] = {}
            temp_data = temp_data[p]
        if force or not key in temp_data or (value_type is not None and not isinstance(temp_data[key],value_type)):
            temp_data[key] = value
        return plist_data

    def parse_boot_args(self,boot_args):
        debug = []
        other = []
        for arg in boot_args.split():
            if self.debug_match.match(arg): # Got a match
                debug.append(arg)
            else:
                other.append(arg)
        return (debug,other)

    def adjust_boot_args(self,boot_args,debug=True):
        d,o = self.parse_boot_args(boot_args)
        return " ".join(o+(list(self.debug_args) if debug else []))

    def auto_detect(self,plist_data):
        debug = {}
        if not isinstance(plist_data,dict):
            return debug # Something is wrong - return nothing
        # Let's initialize some values
        debug["boot-args"] = ""
        debug["boot-args-debug"] = ""
        debug["boot-args-delete"] = False
        debug["AppleDebug"] = debug["ApplePanic"] = False
        debug["Target"] = 0
        debug["DisplayLevel"] = 2147483714
        debug["EmulatedNvram"] = False

        # Time to walk the config.plist and gather info
        debug_section = plist_data.get("Misc",{}).get("Debug",{})
        if debug_section: # Let's pull our data if possible
            for x in ("AppleDebug","ApplePanic","DisplayLevel","Target"):
                debug[x] = debug_section.get(x,debug[x])
        
        # Check for boot-args, make sure we look in both NVRAM -> Add and Delete
        nvram_guid = "7C436110-AB2A-4BBB-A880-FE41995C9F82"
        nvram_add = plist_data.get("NVRAM",{}).get("Add",{}).get(nvram_guid,{})
        if "boot-args" in nvram_add:
            debug["boot-args"] = nvram_add["boot-args"]
            d,o = self.parse_boot_args(nvram_add["boot-args"])
            debug["boot-args-debug"] = d
        if "boot-args" in plist_data.get("NVRAM",{}).get("Delete",{}).get(nvram_guid,[]):
            debug["boot-args-delete"] = True

        # Check for emulated NVRAM
        drivers = plist_data.get("UEFI",{}).get("Drivers",[])
        for driver in drivers:
            enabled = True
            if isinstance(driver,dict):
                try:
                    enabled = bool(driver.get("Enabled",True))
                    driver = str(driver.get("Path",""))
                except:
                    continue # Borked
            if enabled and driver.lower() == "openvariableruntimedxe.efi":
                debug["EmulatedNvram"] = True
                break

        # Return our findings
        return debug

    def ensure_plist(self):
        if not self.plist_path or not os.path.isfile(self.plist_path):
            self.plist_path = self.select_plist()
        if not self.plist_path or not os.path.isfile(self.plist_path):
            return False
        return True

    def _load_plist(self,plist_path,cli=False):
        try:
            with open(plist_path,"rb") as f:
                plist_data = plist.load(f)
            if not isinstance(plist_data,dict):
                raise Exception("Plist root is not a dictionary")
        except Exception as e:
            self.u.head("Failed To Load Plist")
            print(" ")
            print("Failed to load {}:\n{}".format(plist_path,e))
            print(" ")
            if not cli:
                self.u.grab("Press [enter] to return...")
            return None
        return plist_data

    def select_plist(self):
        while True:
            self.u.head("Select Plist")
            print(" ")
            print("Current plist: {}".format(self.plist_path or "None selected"))
            print(" ")
            print("M. Return")
            print("Q. Quit")
            print(" ")
            menu = self.u.grab("Please drag and drop the target plist:  ")
            if not len(menu):
                continue
            elif menu.lower() == "m":
                return self.plist_path
            elif menu.lower() == "q":
                self.u.custom_quit()
            # Should have a path attempt
            path = self.u.check_path(menu)
            if not path: continue # Invalid - show the menu again
            # Try to load it
            plist_data = self._load_plist(path)
            if plist_data is None: continue
            # Return the detected path
            return path

    def save_plist(self,plist_data,cli=False):
        if not self.plist_path: return
        try:
            with open(self.plist_path,"wb") as f:
                plist.dump(plist_data,f)
        except Exception as e:
            self.u.head("Failed To Save Plist")
            print(" ")
            print("Failed to save {}:\n{}".format(self.plist_path,e))
            print(" ")
            if not cli:
                self.u.grab("Press [enter] to return...")

    def toggle_debugging(self,enable=True,cli=False):
        if not self.ensure_plist():
            return
        if not cli:
            self.u.head("{} Debugging".format("Enabling" if enable else "Disabling"))
            print(" ")
        print("{} debugging for {}...".format("Enabling" if enable else "Disabling",self.plist_path))
        # We have a valid plist at this point, let's try loading it
        print("Loading plist...")
        plist_data = self._load_plist(self.plist_path,cli=cli)
        if plist_data is None: return
        print("Setting target values...")
        # Got a valid plist - let's enable our debugging values
        for entry in (self.debug_on if enable else self.debug_off):
            plist_data = self.ensure_path(plist_data,**entry)
            if entry.get("force"):
                print(" - {} -> {}".format(entry.get("key","?"),entry.get("value","?")))
        # Let's gather boot args, then ensure they're in both NVRAM -> Add and Delete
        print("Parsing boot-args...")
        orig_args = " ".join(plist_data["NVRAM"]["Add"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"].get("boot-args","").split())
        d,o = self.parse_boot_args(orig_args)
        print(" Original: {}".format(orig_args))
        new_args = " ".join(o+(list(self.debug_args) if enable else []))
        plist_data["NVRAM"]["Add"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"]["boot-args"] = new_args
        print("  Updated: {}".format(new_args if new_args else "None set"))
        if not "boot-args" in plist_data["NVRAM"]["Delete"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"]:
            print("Adding boot-args to NVRAM -> Delete...")
            plist_data["NVRAM"]["Delete"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"].append("boot-args")
        self.save_plist(plist_data)
        print(" ")
        print("Done.")
        if not cli:
            print(" ")
            self.u.grab("Press [enter] to return...")

    def is_debug(self,plist_data):
        # Let's check for a few things
        info = self.auto_detect(plist_data)
        debug = total = 0
        for x in ("boot-args-debug","AppleDebug","ApplePanic","Target"):
            total += 1
            if (x == "Target" and info.get(x) == 67) or info.get(x):
                debug += 1
        if total == debug: return True
        return None # Mixed

    def main(self):
        while True:
            self.u.head()
            print(" ")
            if self.plist_path:
                plist_data = self._load_plist(self.plist_path)
                info = self.auto_detect(plist_data)
                # Print the info detected
                print("Current plist: {}".format(self.plist_path))
                if info["boot-args"]:
                    print(" - Boot args: {}".format(info["boot-args"]))
                    if not info["boot-args-delete"]:
                        print(" --> Only in NVRAM -> Add, may not be set properly!")
                    if info["EmulatedNvram"]:
                        print(" --> Detected OpenVariableRuntimeDxe, boot-args will not be set!")
                else:
                    print(" - Boot args: None set")
                for x in ("AppleDebug","ApplePanic","Target"):
                    print(" - {}: {}".format(x,info[x]))
                if info["Target"] != 0 and info["DisplayLevel"] == 0:
                    print(" --> DisplayLevel is {}, 2147483714 (0x80000042) is recommended!")
            else:
                print("Current plist: None selected")
            print(" ")
            print("1. Select plist")
            print("2. Enable debugging")
            print("3. Disable debugging")
            print(" ")
            print("Q. Quit")
            print(" ")
            menu = self.u.grab("Please select an option:  ")
            if not len(menu):
                continue
            elif menu.lower() == "q":
                self.u.custom_quit()
            elif menu == "1":
                self.plist_path = self.select_plist()
            elif menu == "2":
                self.toggle_debugging(enable=True)
            elif menu == "3":
                self.toggle_debugging(enable=False)

if __name__ == '__main__':
    # Setup the cli args
    parser = argparse.ArgumentParser(prog="ToggleDebug.py", description="ToggleDebug - a py script to toggle debug settings in an OC config.plist")
    parser.add_argument("-d","--debug",help="on/off/toggle (default is toggle).  Sets AppleDebug, ApplePanic, Target, boot-args as needed.")
    parser.add_argument("plist_path",nargs="*", help="Path to the target plist - if missing, the script will open in interactive mode.")
    args = parser.parse_args()

    d = ToggleDebug()

    # Check if we have a valid plist path
    if args.plist_path:
        plist_path = args.plist_path[0] # Get the first
        plist_data = d._load_plist(plist_path,cli=True)
        if not plist_data:
            exit(1) # Borked - bail
        d.plist_path = plist_path
        # Let's gather our info
        enable = None
        if args.debug: # Try to normalize
            if args.debug.lower() in ("on","yes","y","true","1","enable","enabled"):
                enable = True
            elif args.debug.lower() in ("off","no","n","false","0","disable","disabled"):
                enable = False
        if enable is None:
            enable = False if d.is_debug(plist_data) else True
        d.toggle_debugging(enable=enable,cli=True)
    else:
        d.main()
