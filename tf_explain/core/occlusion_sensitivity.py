"""
Core Module for Occlusion Sensitivity
"""
import math

import numpy as np
import cv2

from tf_explain.utils.display import grid_display, heatmap_display
from tf_explain.utils.image import apply_grey_patch
from tf_explain.utils.saver import save_rgb
from tqdm import tqdm

class OcclusionSensitivity:

    """
    Perform Occlusion Sensitivity for a given input
    """

    def __init__(self, batch_size=None):
        self.batch_size = batch_size

    def explain(
        self,
        validation_data,
        model,
        class_index,
        patch_size,
        colormap=cv2.COLORMAP_VIRIDIS,
    ):
        """
        Compute Occlusion Sensitivity maps for a specific class index.

        Args:
            validation_data (Tuple[np.ndarray, Optional[np.ndarray]]): Validation data
                to perform the method on. Tuple containing (x, y).
            model (tf.keras.Model): tf.keras model to inspect
            class_index (int): Index of targeted class
            patch_size (int): Size of patch to apply on the image
            colormap (int): OpenCV Colormap to use for heatmap visualization

        Returns:
            np.ndarray: Grid of all the sensitivity maps with shape (batch_size, H, W, 3)
        """
        images, _ = validation_data
        sensitivity_maps = np.array(
            [
                self.get_sensitivity_map(model, image, class_index, patch_size)
                for image in images
            ]
        )
        print(f"Sensitivity map 0: {sensitivity_maps[0]}")
        heatmaps = np.array(
            [
                heatmap_display(heatmap, image, colormap)
                for heatmap, image in zip(sensitivity_maps, images)
            ]
        )

        print(f"Heatmap 0: {heatmaps[0]}")
        grid = grid_display(heatmaps)

        return grid

    def get_sensitivity_map(self, model, image, class_index, patch_size):
        """
        Compute sensitivity map on a given image for a specific class index.

        Args:
            model (tf.keras.Model): tf.keras model to inspect
            image:
            class_index (int): Index of targeted class
            patch_size (int): Size of patch to apply on the image

        Returns:
            np.ndarray: Sensitivity map with shape (H, W, 3)
        """
        sensitivity_map = np.zeros(
            (
                math.ceil(image.shape[0] / patch_size),
                math.ceil(image.shape[1] / patch_size),
            )
        )

        coordinates = [
            (index_y, index_x)
            for index_x in range(
                sensitivity_map.shape[1]  # pylint: disable=unsubscriptable-object
            )
            for index_y in range(
                sensitivity_map.shape[0]  # pylint: disable=unsubscriptable-object
            )
        ]

        target_class_predictions = []
        base_confidence = model.predict(np.array([image]), batch_size=1)[0][class_index]
        print(f"Base_confidence: {base_confidence}")
        with tqdm(total=math.ceil(image.shape[0] * image.shape[1] / patch_size ** 2),position=0,leave=True) as pbar:
            for index_y, top_left_y in enumerate(range(0, image.shape[1], patch_size)):
                for index_x, top_left_x in enumerate(range(0, image.shape[0], patch_size)):
                    patch = np.array([apply_grey_patch(image, top_left_x, top_left_y, patch_size)])
                    prediction = model.predict(patch, batch_size=1)[0][class_index]
                    target_class_predictions.append(prediction)
                    triggered = pbar.update(1)

        print(f"Confidence scores: {target_class_predictions}")
        for (index_y, index_x), confidence in zip(
            coordinates, target_class_predictions
        ):
            sensitivity_map[index_y, index_x] = base_confidence - confidence

        return cv2.resize(sensitivity_map, image.shape[0:2])

    def save(self, grid, output_dir, output_name):
        """
        Save the output to a specific dir.

        Args:
            grid (numpy.ndarray): Grid of all heatmaps
            output_dir (str): Output directory path
            output_name (str): Output name
        """
        save_rgb(grid, output_dir, output_name)
