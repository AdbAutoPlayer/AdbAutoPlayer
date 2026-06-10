"""Script to extract frames from a video file."""

import os

import cv2


def main():
    """Extract frames from a video at regular intervals."""
    video_path = (
        "C:/Users/sacri/.gemini/antigravity-ide/brain/"
        "759c5b63-0e78-4046-9e3a-d24808c79db0/supreme_arena_record.mp4"
    )
    output_dir = (
        "C:/Users/sacri/.gemini/antigravity-ide/brain/"
        "759c5b63-0e78-4046-9e3a-d24808c79db0/video_frames"
    )
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"FPS: {fps}, Total Frames: {total_frames}")

    # Extract one frame every 30 frames (approx. 1s if 30fps)
    frame_idx = 0
    saved_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        # Save every 30th frame
        if frame_idx % 30 == 0:
            cv2.imwrite(os.path.join(output_dir, f"frame_{frame_idx}.png"), frame)
            saved_count += 1
        frame_idx += 1

    cap.release()
    print(f"Extracted {saved_count} frames to {output_dir}")


if __name__ == "__main__":
    main()
