import subprocess
import re
import os

from solve.Solver import Solver

base_cmd = [ "solve-field", "--overwrite", "--no-plots",
        "--new-fits", "none",
        "--solved", "none",
        "--match", "none",
        "--rdls", "none",
        "--index-xyls", "none",
        "--keep-xylist", "none",
        "--wcs", "none",
        "--corr", "none",
        "--temp-axy",
        "--uniformize", "0",
        "--no-remove-lines",
        "--no-background-subtraction",]

class AstrometryNetSolver(Solver):
    
    def __init__(self):
        super().__init__()
        
        # Astrometry.net specific parameters
        self.scale = 68.5
        self.scale_uncertainty = 2

        # Limits for solving
        self.limit = 30
        self.min_limit = 1
        self.max_limit = 60

        self.depth = None

        self.downsample = 0
        self.max_downsample = 8

    def solve(self, image_path):
        cmd = self.build_cmd(image_path)

        try:
            result = self.run_solver(cmd)
            if result is not None:
                return result
        except subprocess.CalledProcessError:
            pass
        return [cmd[-1], "Failed", float("-inf")]

    def run_solver(self, cmd):
        solve = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
        )
        highest_odds = float("-inf")
        for line in solve.stdout:
            #print(line)
            if "log-odds" in line:
                parts = line.strip().split(" ")
                odds = float(parts[2])
                if odds > highest_odds:
                    highest_odds = odds
            
            if "RA,Dec = (" in line:
                res = extract_coordinates(line)
                if res is not None:
                    ra, dec, new_scale = res
                    if abs(new_scale - self.scale) > self.scale_uncertainty:
                        self.scale = new_scale
                    return [cmd[-1], (ra, dec), highest_odds]
        solve.wait()
        

    def build_scale(self, unit="arcsecperpix"):
        if self.scale is None:
            return []
        lower = self.scale - self.scale_uncertainty
        upper = self.scale + self.scale_uncertainty
        return ["--scale-units", unit, "--scale-low", str(lower), "--scale-high", str(upper)]

    def build_limit(self):
        if self.limit is None:
            return []
        return ["--cpulimit", str(self.limit)]

    def build_depth(self):
        if self.depth is None:
            return []
        return ["--depth", str(self.depth)]

    def build_downsample(self):
        if self.downsample is None:
            return []
        return ["--downsample", str(self.downsample)]

    def build_cmd(self, image_path):
        cmd = base_cmd.copy()
        if os.name == 'nt':
            cmd.insert(0, "wsl")
        cmd += self.build_scale()
        cmd += self.build_limit()
        cmd += self.build_downsample()
        cmd += self.build_depth()


         # always add image path last
        if os.name == 'nt':
            cmd.append(wsl_path(image_path)) # On windows, should use mounted path
        else:
            cmd.append(image_path)


        return cmd

    
def extract_coordinates(line):
    """
    Extracts the float coordinate pair from a line.

    Args:
        line (str): A line containing a coordinate pair in the format 'RA,Dec = (x,y)'

    Returns:
        tuple: A tuple containing the extracted RA and Dec values as floats, and the pixel scale.
    """
    pattern = r'\(([-+]?\d+\.\d+),\s*([-+]?\d+\.\d+)\),\s*pixel scale\s+([-+]?\d+\.\d+)\s*arcsec/pix'
    match = re.search(pattern, line)
    if match:
        ra, dec, scale = map(float, match.groups())
        return ra, dec, scale
    else:
        return None
    
def wsl_path(path):
    return path.replace("\\", "/").replace("C:", "/mnt/c")