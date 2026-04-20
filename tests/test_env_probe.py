"""Environment Probe Test — verifies GMSH and CalculiX availability."""

import shutil
import subprocess
from tools.calculix_driver import _find_ccx
from tools.gmsh_driver import _find_gmsh

def test_ccx_detection():
    path, is_wsl = _find_ccx()
    print(f"\nCalculiX Detection: Path='{path}', IsWSL={is_wsl}")
    if path:
        if is_wsl:
            # Check if wsl ccx -v works
            res = subprocess.run(["wsl", "ccx", "-v"], capture_output=True, text=True)
            print(f"WSL ccx Version Info: {res.stdout.splitlines()[0] if res.stdout else 'No output'}")
        else:
            res = subprocess.run([path, "-v"], capture_output=True, text=True)
            print(f"Native ccx Version Info: {res.stdout.splitlines()[0] if res.stdout else 'No output'}")

def test_gmsh_detection():
    path, is_wsl = _find_gmsh()
    print(f"Gmsh Detection: Path='{path}', IsWSL={is_wsl}")
    if path:
        if is_wsl:
            res = subprocess.run(["wsl", "gmsh", "--version"], capture_output=True, text=True)
            print(f"WSL gmsh Version: {res.stdout.strip()}")
        else:
            res = subprocess.run([path, "--version"], capture_output=True, text=True)
            print(f"Native gmsh Version: {res.stdout.strip()}")
    else:
        try:
            import gmsh
            print("Gmsh Python API: Available")
        except ImportError:
            print("Gmsh Python API: Missing")

if __name__ == "__main__":
    test_ccx_detection()
    test_gmsh_detection()
