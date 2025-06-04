import numpy as np
import pylab
import mahotas as mh
from skimage import measure
from PIL import Image

from feedback_classifier.metrics.StarCount import StarCount

exposures = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
sc = StarCount()
for e in exposures:
    if e == 3.0:
        sky=Image.open(f"C:\\Users\\314ow\\rpicam_samples\\{str(e)}_8.0\\output_1.jpg")
    else:
        sky=Image.open(f"C:\\Users\\314ow\\rpicam_samples\\{str(e)}_16.0\\output_1.jpg")

    
    image = np.array(sky)
    image = mh.colors.rgb2gray(image)
    stars = sc.compute(image)
    print(f"Exposure: {e} seconds, Star Count: {stars}")


#pylab.show()