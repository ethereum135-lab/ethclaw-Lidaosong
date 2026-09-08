import os, subprocess, json

# 1. Check ssh keys
ssh_dir = os.path.expanduser('~/.ssh')
print("=== SSH keys ===")
for f in os.listdir(ssh_dir):
    fp = os.path.join(ssh_dir, f)
    if os.path.isfile(fp):
        print(f"  {f} ({os.path.getsize(fp)} bytes)")

# 2. Check config/auth.json for ssh keys
cfg_path = os.path.expanduser('~/zq_web4_trading_system/config/auth.json')
if os.path.exists(cfg_path):
    with open(cfg_path) as f:
        cfg = json.load(f)
    print("\n=== SSH config ===")
    if 'ssh' in cfg:
        print(f"  keys in config: {list(cfg['ssh'].keys())}")
    else:
        print("  no ssh key in auth.json")
else:
    print("\n=== No auth.json found ===")
