import pyudev
import random,os,string
import ctypes
import ctypes.util
import yaml
import sh
#import psutil


libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
libc.mount.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_ulong, ctypes.c_char_p)
b64chars = string.ascii_letters+string.digits+"-_"

mounts = {}


def getId(length=11,chars=b64chars):
    return "".join([random.choice(chars) for i in range(length)])

def unmount(node):
    if mounts.get(node) is not None:
        network_config(node, False)

        try:
            sh.umount(node, mounts[node]["dir"])
        # exception only occurs when trying to remove 2nd partition
        # after 1st
        except Exception:
            pass
        
        os.rmdir(mounts[node]["dir"])
        del mounts[node]
        
def parse_config(path):
    config_path = os.path.join(path, "config.yml")
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
        return config

    return None

def network_config(node, new_changes):
    if mounts.get(node) is None:
        return None
    config = mounts[node]["config"]

    if config is not None and 'network' in config:
        for interface in config['network']:
            params = config['network'][interface][0]
            interface_dir = f"/sys/class/net/{interface}"
            # change IP, DNS, and gateway settings only if the interface
            # in the config.yml exists on this device
            if os.path.exists(interface_dir):
                if new_changes:
                    sh.ip("addr", "add", params['address'], "dev", interface)
                    # parse through output to get current gateway config
                    current_route = sh.ip("r", "show", "dev", interface)
                    current_route = str(current_route).split("\n")[0]
                    mounts[node]["gateway"] = current_route.split()[2]
                    
                    sh.ip("route", "delete", "default")
                    sh.ip("route", "add", "default", "via", params['gateway'])
                    sh.resolvectl("dns", interface, params['dns'])
                else:
                    sh.ip("addr", "delete", params['address'], "dev", interface)
                    sh.ip("route", "delete", "default")
                    sh.ip("route", "add", "default", "via", mounts[node]["gateway"])
                
def url_setup(node):
    config = parse_config(node)
    if config is None:
        return

    if 'ignition' in config:
        new_url = config['ignition']['project-url']
        sh.snap("set", "wpe-webkit-mir-kiosk", f"url={new_url}")

def main():
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='block')

    for device in iter(monitor.poll, None):
        if device.action == 'add':
            if device.device_type == "partition":
                mnt_dir = f'/mnt/usb/{getId()}'
                node = device.device_node
                os.makedirs(mnt_dir)

                if node in mounts.keys():
                    unmount(node)

                _ = sh.mount(node,mnt_dir)
                mounts[node] = {"dir":mnt_dir, "config":parse_config(mnt_dir)}
                network_config(node, True)

        elif device.action == 'remove':
            if device.device_type == "partition":
                unmount(device.device_node)

if __name__ == "__main__":
    main()
