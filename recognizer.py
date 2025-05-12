import os
import torch
from pathlib import Path
from typing import Union
import contextlib

import numpy as np
from ultralytics import YOLO
import onnxruntime as ort
from loguru import logger

DEFAULT_CONF = 0.25


class Recognizer:
    def __init__(self):
        # Configure ONNX Runtime session options to optimize for CUDA
        self._configure_onnxruntime()

        root_dir = os.path.dirname(os.path.dirname(__file__))
        multi_cls_model_path = os.path.join(root_dir, 'captcha-solver', 'models', 'multi_cls.onnx')
        single_cls_model_path = os.path.join(root_dir, 'captcha-solver', 'models', 'single_cls.onnx')

        # Initialize models with optimized settings
        self.multi_cls_model = YOLO(multi_cls_model_path, task='detect')
        self.single_cls_model = YOLO(single_cls_model_path, task='detect')

        logger.info("Models loaded with ONNX Runtime optimizations")

    @staticmethod
    def _configure_onnxruntime():
        """Configure ONNX Runtime session options to optimize for CUDA execution"""
        # Set global session options
        options = ort.SessionOptions()

        # Enable memory pattern optimization
        options.enable_mem_pattern = True

        # Set graph optimization level to all optimizations
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        # Set execution mode to parallel (can help reduce memory copies)
        options.execution_mode = ort.ExecutionMode.ORT_PARALLEL

        # Enable memory reuse (can help reduce memory copies)
        options.enable_mem_reuse = True

        # Set inter-op thread count to minimize overhead
        options.inter_op_num_threads = 1

        # Set CUDA provider options
        cuda_provider_options = {
            'arena_extend_strategy': 'kSameAsRequested',
            'cudnn_conv_algo_search': 'EXHAUSTIVE',
            'do_copy_in_default_stream': True,
            # This option can help reduce memory copies between CPU and GPU
            'device_id': 0,
            # Force CPU kernels to stay on CPU, improving memory transfer
            'gpu_mem_limit': 2 * 1024 * 1024 * 1024  # 2GB GPU memory limit
        }

        # Register the session options and CUDA provider options
        with contextlib.suppress(Exception):
            providers = [
                ('CUDAExecutionProvider', cuda_provider_options),
                'CPUExecutionProvider'
            ] if torch.cuda.is_available() else ['CPUExecutionProvider']

            # Set as environment variable that YOLO will use
            os.environ['ULTRALYTICS_ORT_PROVIDERS'] = str(providers)
            os.environ['OMP_NUM_THREADS'] = '1'
            os.environ['OMP_WAIT_POLICY'] = 'PASSIVE'

            logger.info(f"ONNX Runtime configured with providers: {providers}")

    @staticmethod
    def predict(model, source: Union[str, Path, int, list, tuple, np.ndarray] = None,
                **kwargs):
        if torch.cuda.is_available():
            os.environ['ORT_TENSORRT_FP16_ENABLE'] = '1'  # Enable fp16 for TensorRT if available
            os.environ['ORT_TENSORRT_INT8_ENABLE'] = '0'  # Disable int8 to avoid memory copying

            with open(os.devnull, 'w') as devnull:
                import sys
                stderr_backup = sys.stderr
                try:
                    # Only set when running in non-production
                    if os.environ.get('ENVIRONMENT') != 'production':
                        sys.stderr = devnull

                    # Set parameters
                    params = {
                        'source': source,
                        'device': "0" if torch.cuda.is_available() else "cpu",
                        'conf': 0.8,
                        'imgsz': [416, 416],
                        'half': torch.cuda.is_available(),  # Use FP16 if CUDA is available
                        'optimize': True,  # Enable ONNX Runtime optimizations
                        'verbose': True
                    }
                    params.update(kwargs)

                    # Perform prediction
                    results = model.predict(**params)
                    if len(results):
                        return results[0]
                    return []
                finally:
                    # Restore stderr
                    if os.environ.get('ENVIRONMENT') != 'production':
                        sys.stderr = stderr_backup

    def identify_gap(self, source, show_result=False, **kwargs):
        box = []
        box_conf = 0
        results = self.predict(model=self.multi_cls_model, source=source, classes=[0], conf=DEFAULT_CONF, **kwargs)
        if not len(results):
            return box, box_conf

        box_with_max_conf = max(results, key=lambda x: x.boxes.conf.max())
        if show_result:
            box_with_max_conf.show()

        box_with_conf = box_with_max_conf.boxes.data.tolist()[0]
        return box_with_conf[:-2], box_with_conf[-2]

    @staticmethod
    def calculate_difference(slider, box):

        slider_with_conf = slider.boxes.data.tolist()[0]
        box_with_conf = box.boxes.data.tolist()[0]

        slider_height_mid = int((slider_with_conf[1] + slider_with_conf[3]) / 2)
        box_height_mid = int((box_with_conf[1] + box_with_conf[3]) / 2)

        width_slider = slider_with_conf[2] - slider_with_conf[0]
        height_slider = slider_with_conf[3] - slider_with_conf[1]

        width_box = box_with_conf[2] - box_with_conf[0]
        height_box = box_with_conf[3] - box_with_conf[1]

        return abs(box_height_mid - slider_height_mid) * 2 + abs(width_box - width_slider) + abs(
            height_box - height_slider)

    def identify_boxes_by_screenshot(self, source, **kwargs):
        results = self.predict(model=self.single_cls_model, source=source,
                               **kwargs)

        box_list = []
        if not len(results):
            return box_list

        for result in results:
            box_list.append(result)

        box_list.sort(key=lambda x: x.boxes.data.tolist()[0][0])
        return box_list

    def identify_target_boxes_by_screenshot(self, source, **kwargs):
        slider_box = box_nearest = None

        box_list = self.identify_boxes_by_screenshot(source, **kwargs)

        if not box_list or len(box_list) == 1:
            return slider_box, box_nearest

        slider_box = box_list[0]

        others = box_list[1:]

        box_nearest = None
        min_box_diff = None

        for box in others:
            box_diff = self.calculate_difference(slider_box, box)
            if not min_box_diff:
                min_box_diff = box_diff
                box_nearest = box
                continue
            if box_diff < min_box_diff:
                min_box_diff = box_diff
                box_nearest = box

        return slider_box, box_nearest

    def identify_screenshot(self, source, show_result=False, **kwargs):
        slider_box, box_nearest = self.identify_target_boxes_by_screenshot(source, **kwargs)
        if not slider_box or not box_nearest:
            return [], 0
        if show_result:
            box_nearest.show()

        box_with_conf = box_nearest.boxes.data.tolist()[0]
        return box_with_conf[:-2], box_with_conf[-2]

    def identify_distance_by_screenshot(self, source, show_result=False, **kwargs):
        slider_box, box_nearest = self.identify_target_boxes_by_screenshot(source, **kwargs)
        if not slider_box or not box_nearest:
            return
        if show_result:
            box_nearest.show()

        box_with_conf = box_nearest.boxes.data.tolist()[0]
        slider_with_conf = slider_box.boxes.data.tolist()[0]
        return int(box_with_conf[0] - slider_with_conf[0])
