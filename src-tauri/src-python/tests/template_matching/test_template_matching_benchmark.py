import time
from pathlib import Path

from adb_auto_player.image_manipulation import IO
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.template_matching import TemplateMatcher


def test_template_matching_benchmark():
    """Benchmark template matching FPS and latency."""
    base_image = IO.load_image(
        Path(__file__).parent / "data" / "guitar_girl_with_notes.png"
    )
    template = IO.load_image(Path(__file__).parent / "data" / "small_note.png")

    # Warmup
    for _ in range(5):
        TemplateMatcher.find_template_match(
            base_image,
            template,
            threshold=ConfidenceValue("90%"),
        )

    # Benchmark loop
    iterations = 50
    start_time = time.perf_counter()
    for _ in range(iterations):
        TemplateMatcher.find_template_match(
            base_image,
            template,
            threshold=ConfidenceValue("90%"),
        )
    end_time = time.perf_counter()

    duration = end_time - start_time
    avg_latency = (duration / iterations) * 1000  # in ms
    fps = iterations / duration

    print("\nTemplate matching benchmark (guitar_girl_with_notes.png):")
    print(f"Iterations: {iterations}")
    print(f"Total time: {duration:.4f} s")
    print(f"Average latency: {avg_latency:.2f} ms")
    print(f"FPS: {fps:.2f}")

    # Latency should be under 100ms on modern machines
    assert avg_latency < 100.0
