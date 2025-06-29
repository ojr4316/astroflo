from abc import ABC, abstractmethod

from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
import cv2

class ImageProcessor(ABC):

    @abstractmethod
    def process(self, image: Image) -> Image:
        """ Process an image """
        pass