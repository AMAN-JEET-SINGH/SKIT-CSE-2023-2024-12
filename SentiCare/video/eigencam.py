"""
Eigen-CAM Visualization Tool for Uploaded Videos
Modified to save Eigen-CAM frames instead of creating a full video.
"""

import torch
from transformers import AutoImageProcessor, AutoModelForImageClassification
from PIL import Image
import numpy as np
from pytorch_grad_cam import EigenCAM
from pytorch_grad_cam.utils.image import show_cam_on_image
import cv2
from facenet_pytorch import MTCNN
from pathlib import Path
import os
import json
import warnings

warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)


class EigenCAMVisualizer:
    """Generate Eigen-CAM heatmaps for facial emotion detection."""

    def __init__(self, model_name="dima806/facial_emotions_image_detection"):
        print("🔄 Loading emotion model with Eigen-CAM...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = AutoModelForImageClassification.from_pretrained(model_name).to(self.device)
        self.model.eval()
        self.emotion_labels = list(self.model.config.id2label.values())

        # Wrap model for Eigen-CAM
        class ModelWrapper(torch.nn.Module):
            def __init__(self, model):
                super().__init__()
                self.model = model

            def forward(self, x):
                return self.model(pixel_values=x).logits

        self.wrapped_model = ModelWrapper(self.model)

        # For ViT, use the last encoder block output
        self.target_layers = [self.model.vit.encoder.layer[-1].output]
        self.cam = EigenCAM(model=self.wrapped_model, target_layers=self.target_layers)
        print(f"✅ Eigen-CAM initialized on {self.device}")

        # MTCNN for face detection
        self.mtcnn = MTCNN(
            keep_all=True,
            device=self.device,
            min_face_size=40,
            thresholds=[0.6, 0.7, 0.7],
            post_process=False,
        )

    def _detect_faces(self, frame):
        """Detect faces using MTCNN."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        boxes, probs = self.mtcnn.detect(rgb_frame)
        faces = []
        if boxes is not None:
            for box, prob in zip(boxes, probs):
                if prob > 0.9:
                    x1, y1, x2, y2 = box
                    x, y = int(x1), int(y1)
                    w, h = int(x2 - x1), int(y2 - y1)
                    x = max(0, x)
                    y = max(0, y)
                    w = min(w, frame.shape[1] - x)
                    h = min(h, frame.shape[0] - y)
                    faces.append((x, y, w, h, prob))
        return faces

    def generate_eigencam(self, face_roi):
        """Generate Eigen-CAM heatmap for a cropped face."""
        rgb_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_face)
        inputs = self.processor(images=pil_image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=1)[0]

        pred_id = logits.argmax(dim=1).item()
        pred_label = self.model.config.id2label[pred_id]
        confidence = probs[pred_id].item()

        # Generate Eigen-CAM heatmap
        grayscale_cam = self.cam(input_tensor=inputs["pixel_values"])[0, :]
        rgb_img = cv2.resize(rgb_face, (grayscale_cam.shape[1], grayscale_cam.shape[0])) / 255.0
        eigencam_overlay = show_cam_on_image(rgb_img, grayscale_cam, use_rgb=True)
        eigencam_overlay = cv2.resize(eigencam_overlay, (face_roi.shape[1], face_roi.shape[0]))

        return eigencam_overlay, pred_label, confidence

    def visualize_video(
        self,
        video_path: str,
        output_dir: str = "eigencam_images",
        sample_interval: int = 30,
    ):
        """
        Sample frames from video and save Eigen-CAM overlays as images.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(f"🎬 Processing {total_frames} frames, sampling every {sample_interval} frames...")

        frame_count = 0
        saved_frames = 0
        emotion_counts = {emotion: 0 for emotion in self.emotion_labels}

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_count += 1

            if frame_count % sample_interval == 0:
                faces = self._detect_faces(frame)
                if len(faces) > 0:
                    x, y, w, h, conf = max(faces, key=lambda f: f[2] * f[3])
                    face_roi = frame[y:y+h, x:x+w]

                    try:
                        eigencam_overlay, emotion, confidence = self.generate_eigencam(face_roi)
                        frame[y:y+h, x:x+w] = eigencam_overlay

                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        label = f"{emotion} ({confidence*100:.1f}%)"
                        cv2.putText(frame, label, (x, y-10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                        save_path = os.path.join(output_dir, f"frame_{frame_count:05d}.jpg")
                        cv2.imwrite(save_path, frame)
                        saved_frames += 1
                        emotion_counts[emotion] += 1
                        print(f"🖼 Saved Eigen-CAM frame {frame_count} → {save_path}")

                    except Exception as e:
                        print(f"⚠️ Error processing frame {frame_count}: {e}")

        cap.release()
        dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]
        print(f"\n✅ Eigen-CAM extraction complete!")
        print(f"🖼 Saved {saved_frames} frames to '{output_dir}'")
        print(f"🎭 Dominant emotion: {dominant_emotion}")

        return {
            "input_video": video_path,
            "output_dir": output_dir,
            "total_frames": total_frames,
            "saved_frames": saved_frames,
            "emotion_distribution": emotion_counts,
            "dominant_emotion": dominant_emotion,
        }


# CLI usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Eigen-CAM visualizations for selected frames")
    parser.add_argument("--video", type=str, required=True, help="Path to video file")
    parser.add_argument("--output_dir", type=str, default="eigencam_images", help="Output directory")
    parser.add_argument("--interval", type=int, default=30, help="Sample every N frames")

    args = parser.parse_args()

    visualizer = EigenCAMVisualizer()
    result = visualizer.visualize_video(
        video_path=args.video,
        output_dir=args.output_dir,
        sample_interval=args.interval,
    )

    print("\n📊 Summary:")
    print(json.dumps(result, indent=2))
