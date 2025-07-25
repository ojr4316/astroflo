import numpy as np
from PIL import Image
import cv2
import matplotlib.pyplot as plt
import time

class ImageAnalysis:
    def __init__(self):
        self.background_levels = []
        self.noise_levels = []
        self.star_counts = []
        self.fwhm_values = []

    def calculate_background_cheap(self, image, level = 5):
        background = cv2.medianBlur(image, level)
        noise = np.std(image - background)

        self.background_levels.append(np.mean(background))
        self.noise_levels.append(noise)

        return np.mean(background), noise

    def calculate_background(self, image, sigma=5.0, iterations=5):
        pixels = image.flatten().astype(float)

        # Perform sigma clipping to remove outliers
        for i in range(iterations):
            mean = np.mean(pixels)
            std = np.std(pixels)
            mask = np.abs(pixels - mean) < (sigma * std)
            pixels = pixels[mask]
            # early stopping if not enough pixels left
            if len(pixels) < 100:
                break
        # Estiamte background and noise levels
        background = np.median(pixels)
        noise = np.std(pixels)

        self.background_levels.append(background)
        self.noise_levels.append(noise)        

        return background, noise

    def _limit_values(self, max_idx: int = 100):
        self.background_levels = self.background_levels[:max_idx]
        self.noise_levels = self.noise_levels[:max_idx]
        self.star_counts = self.star_counts[:max_idx]
        self.fwhm_values = self.fwhm_values[:max_idx]

    def add_image(self, image):
        image = np.array(image)
        # Convert to grayscale if not already
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        image = image.astype(np.float32)
        
        bg, noise = self.calculate_background_cheap(image)
        
        clean = (image-bg).clip(0)

        self.calculate_fwhm_radial(clean)
        self.calculate_star_count(clean, noise)

        self._limit_values()

    def find_brightest(self, image):
        # blur first to reduce hot pixels/outliers
        blurred = cv2.GaussianBlur(image, (5, 5), 0)
        # Find the brightest pixel
        brightest_value= np.max(blurred)
        brightest_pixel = np.unravel_index(np.argmax(blurred), blurred.shape)
        return brightest_pixel, brightest_value
    
    def calculate_fwhm_radial(self, image):
        loc, val = self.find_brightest(image)
        y, x = loc
        half_max = val / 2.0
        radius = 0

        # Crop around brightest pixel
        half_size = 40
        y_min, y_max = max(0, y-half_size), min(image.shape[0], y+half_size)
        x_min, x_max = max(0, x-half_size), min(image.shape[1], x+half_size)
        cropped_image = image[y_min:y_max, x_min:x_max]

        # Calculate radial profile
        center_y, center_x = cropped_image.shape[0] // 2, cropped_image.shape[1] // 2
        y_indices, x_indices = np.indices(cropped_image.shape)
        radii = np.sqrt((y_indices - center_y)**2 + (x_indices - center_x)**2)

        # Find FWHM
        radial_profile = np.mean(cropped_image, axis=1)
        above_half = radial_profile >= half_max
        if np.any(above_half):
            indices = np.where(above_half)[0]
            radius = indices[-1] - indices[0] + 1
        else:
            radius = 0
        self.fwhm_values.append(radius)
        return radius, (center_x, center_y)

    def calculate_fwhm_linear(self, image):
        loc, val = self.find_brightest(image)
        half_max = val / 2.0
        y, x = loc
        half_size = 40
        fwhm_x = fwhm_y = 0

        # Crop around brightest pixel
        y_min, y_max = max(0, y-half_size), min(image.shape[0], y+half_size)
        x_min, x_max = max(0, x-half_size), min(image.shape[1], x+half_size)
        cropped_image = image[y_min:y_max, x_min:x_max]
        
        # Calculate intensity-weighted centroid
        y_indices, x_indices = np.mgrid[0:cropped_image.shape[0], 0:cropped_image.shape[1]]
        
        total_intensity = np.sum(cropped_image)
        if total_intensity == 0:
            return
        
        center_y = np.sum(y_indices * cropped_image) / total_intensity
        center_x = np.sum(x_indices * cropped_image) / total_intensity
        
        # Measure FWHM along horizontal and vertical profiles through centroid
        center_y_int = int(round(center_y))
        center_x_int = int(round(center_x))
        
        # Horizontal FWHM
        if 0 <= center_y_int < cropped_image.shape[0]:
            horizontal_profile = cropped_image[center_y_int, :]
            above_half = horizontal_profile >= half_max
            if np.any(above_half):
                indices = np.where(above_half)[0]
                fwhm_x = indices[-1] - indices[0] + 1
        
        # Vertical FWHM  
        if 0 <= center_x_int < cropped_image.shape[1]:
            vertical_profile = cropped_image[:, center_x_int]
            above_half = vertical_profile >= half_max
            if np.any(above_half):
                indices = np.where(above_half)[0]
                fwhm_y = indices[-1] - indices[0] + 1
        
        # Average horizontal and vertical FWHM
        fwhm = (fwhm_x + fwhm_y) / 2.0 if (fwhm_x > 0 and fwhm_y > 0) else max(fwhm_x, fwhm_y)
        
        self.fwhm_values.append(fwhm)

        return fwhm, (center_x, center_y)

    def calculate_star_count(self, image, noise):
        # blur image first
        image = cv2.GaussianBlur(image, (5, 5), 0)
        image = ((image - image.min()) / (image.max() - image.min()) * 255).astype(np.uint8)

        # Threshold the image to count stars
        threshold = noise * 5
        binary_image = (image > threshold).astype(np.uint8)
        # Find connected components (stars)
        num_labels, labels_im = cv2.connectedComponents(binary_image, connectivity=8, ltype=cv2.CV_32S)
        # Subtract 1 to exclude the background label
        star_count = num_labels - 1
        self.star_counts.append(star_count)

        # visualize the binary image
        #plt.imshow(binary_image, cmap='gray')
        #plt.title(f'Star Count: {star_count}')
        #plt.show()

        return star_count
    
    def get_latest(self):
        if not self.fwhm_values:
            return None
        
        latest_index = -1
        return {
            'background': self.background_levels[latest_index],
            'noise': self.noise_levels[latest_index],
            'star_count': self.star_counts[latest_index],
            'fwhm': self.fwhm_values[latest_index]
        }