import os
from solve.astrometry_handler import AstrometryNetSolver
from solve.tetra3 import Tetra3Solver

import time
import threading
from concurrent.futures import ThreadPoolExecutor

root_dir = "C:\\Users\\314ow\\rpicam_samples"


astro = AstrometryNetSolver()
astro.scale = 19
astro.downsample = 0
astro.sigma = 5

tetra3 = Tetra3Solver()
tetra3.fov = 22


executor = ThreadPoolExecutor(max_workers=5)

results = {}


def attempt(s, path):
    start = time.time()
    folder_name = os.path.basename(os.path.dirname(path))
    exposure = folder_name.split("_")[0]
    if type(s) is Tetra3Solver:
        from PIL import Image
        path = Image.open(path) 
    a = s.solve(path)
    end = time.time()
    print(f"{path} Time taken: {end - start} seconds")
    if results.get(exposure) is None:
        results[exposure] = []
    results[exposure].append((path, end - start))
    return a

    

def main():
    futures = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            futures.append(executor.submit(attempt, filepath))

    for future in futures:
        future.result()
        
    executor.shutdown(wait=True)
    print(results)
    # average solve time for each exposure
    for exposure, times in results.items():
        total_time = sum(time for _, time in times)
        average_time = total_time / len(times)
        print(f"Exposure: {exposure}, Average Solve Time: {average_time:.2f} seconds")

if __name__ == "__main__":
    #main()
    img = "../captures/20250525_002719.jpg" # Trees
    #img = "../captures/20250526_225224.jpg" # Clouds

    short_exposure = "/mnt/c/Users/314ow/rpicam_samples/0.5_16.0/output_0.jpg"

    print("\nSHORT \n\n")
    res = attempt(tetra3, short_exposure)
    print(res)

    print("\nLONG(more stars but also trees) \n\n")
    res = attempt(tetra3, img)
    print(res)

    tetra3.cleanup()


    # TODO: figure out which coords are more accurate, wildly different

    
    # For our use case, a fast tracking solver, AstrometryNet is NOT nearly fast enough.
    # Solves are completed in seconds, but Tetra3 can (more than average) solve in under 1 second.

    #res2 = attempt(astro, short_exposure)
    #print(res2)