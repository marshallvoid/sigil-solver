import contextlib
import os
from pathlib import Path
from typing import Any, List, Tuple, Union

import numpy as np
import onnxruntime as ort
import torch
from loguru import logger
from ultralytics import YOLO
from ultralytics.engine.model import Results

DEFAULT_CONF = 0.25


class RecognizerService:
    def __init__(self) -> None:
        # Configure ONNX Runtime session options to optimize for CUDA
        self._configure_onnxruntime()

        root_dir = os.path.dirname(os.path.dirname(__file__))
        multi_cls_model_path = os.path.join(root_dir, "models", "yolo", "multi_cls.onnx")
        single_cls_model_path = os.path.join(root_dir, "models", "yolo", "single_cls.onnx")

        # Initialize models with optimized settings
        self.multi_cls_model = YOLO(multi_cls_model_path, task="detect")
        self.single_cls_model = YOLO(single_cls_model_path, task="detect")

    def identify_gap(self, source: str, show_result: bool = False, **kwargs: Any) -> Tuple[List[float], float]:
        results = self._predict(model=self.multi_cls_model, source=source, classes=[0], conf=DEFAULT_CONF, **kwargs)
        if not len(results):
            return [], 0.0

        box_with_max_conf: Results = max(results, key=lambda x: x.boxes.conf.max())
        if show_result:
            box_with_max_conf.show()

        box_with_conf = box_with_max_conf.boxes.data.tolist()[0]
        return box_with_conf[:-2], box_with_conf[-2]

    def _predict(
        self,
        model: YOLO,
        source: Union[str, Path, int, list, tuple, np.ndarray] = None,
        **kwargs: Any,
    ) -> List[Results]:
        os.environ["ORT_TENSORRT_FP16_ENABLE"] = "1"  # Enable fp16 for TensorRT if available
        os.environ["ORT_TENSORRT_INT8_ENABLE"] = "0"  # Disable int8 to avoid memory copying

        with open(os.devnull, "w") as devnull:
            import sys

            stderr_backup = sys.stderr
            try:
                # Only set when running in non-production
                if os.environ.get("ENVIRONMENT") != "production":
                    sys.stderr = devnull

                # Set parameters
                params = {
                    "source": source,
                    "device": "0" if torch.cuda.is_available() else "cpu",
                    "conf": 0.8,
                    "imgsz": [416, 416],
                    "half": torch.cuda.is_available(),  # Use FP16 if CUDA is available
                    "optimize": True,  # Enable ONNX Runtime optimizations
                    "verbose": True,
                }
                params.update(kwargs)

                # Perform prediction
                results = model.predict(**params)
                if len(results):
                    return results

                return []

            except Exception as e:
                logger.error(f"Error predicting: {e}")
                raise e

            finally:
                # Restore stderr
                if os.environ.get("ENVIRONMENT") != "production":
                    sys.stderr = stderr_backup

    def _configure_onnxruntime(self) -> None:
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
            "arena_extend_strategy": "kSameAsRequested",
            "cudnn_conv_algo_search": "EXHAUSTIVE",
            "do_copy_in_default_stream": True,
            # This option can help reduce memory copies between CPU and GPU
            "device_id": 0,
            # Force CPU kernels to stay on CPU, improving memory transfer
            "gpu_mem_limit": 2 * 1024 * 1024 * 1024,  # 2GB GPU memory limit
        }

        # Register the session options and CUDA provider options
        with contextlib.suppress(Exception):
            providers = (
                [
                    ("CUDAExecutionProvider", cuda_provider_options),
                    "CPUExecutionProvider",
                ]
                if torch.cuda.is_available()
                else ["CPUExecutionProvider"]
            )

            # Set as environment variable that YOLO will use
            os.environ["ULTRALYTICS_ORT_PROVIDERS"] = str(providers)
            os.environ["OMP_NUM_THREADS"] = "1"
            os.environ["OMP_WAIT_POLICY"] = "PASSIVE"
