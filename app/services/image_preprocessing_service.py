from __future__ import annotations

import cv2
import numpy as np


class ImagePreprocessingService:
    def load_image(self, image_path: str) -> np.ndarray:
        """Read image by path with unicode-safe logic for Windows."""
        data = np.fromfile(image_path, dtype=np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Не удалось открыть изображение")
        return image

    def preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Denoise before thresholding to reduce OCR artifacts.
        denoised = cv2.fastNlMeansDenoising(gray, None, h=18, templateWindowSize=7, searchWindowSize=21)

        # Local contrast improvement (helps for uneven lighting).
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        deskewed = self._deskew(binary)
        return deskewed

    def _deskew(self, binary_image: np.ndarray) -> np.ndarray:
        inverted = cv2.bitwise_not(binary_image)
        coords = np.column_stack(np.where(inverted > 0))

        if len(coords) < 15:
            return binary_image

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) < 0.5:
            return binary_image

        height, width = binary_image.shape[:2]
        matrix = cv2.getRotationMatrix2D((width // 2, height // 2), angle, 1.0)

        return cv2.warpAffine(
            binary_image,
            matrix,
            (width, height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
