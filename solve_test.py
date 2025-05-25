import os
from solve.astrometry_handler import AstrometryNetSolver
import time
import threading
from concurrent.futures import ThreadPoolExecutor

root_dir = "C:\\Users\\314ow\\rpicam_samples"
solver = AstrometryNetSolver()
solver.scale = 19
solver.downsample = 0
executor = ThreadPoolExecutor(max_workers=5)

results = {}


def attempt(path):
    start = time.time()
    folder_name = os.path.basename(os.path.dirname(path))
    exposure = folder_name.split("_")[0].split(".")[0]

    a = solver.solve(path)
    end = time.time()
    print(f"{path} Time taken: {end - start} seconds")
    if results.get(exposure) is None:
        results[exposure] = []
    results[exposure].append((path, end - start))

    

def main():
    futures = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            futures.append(executor.submit(attempt, filepath))

    for future in futures:
        future.result()
        
    executor.shutdown(wait=True)

    # average solve time for each exposure
    for exposure, times in results.items():
        total_time = sum(time for _, time in times)
        average_time = total_time / len(times)
        print(f"Exposure: {exposure}, Average Solve Time: {average_time:.2f} seconds")

if __name__ == "__main__":
    #main()
    img = "./captures/20250525_003152.jpg"
    res = attempt(img)
    print(res)