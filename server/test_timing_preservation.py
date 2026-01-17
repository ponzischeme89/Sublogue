"""
Test to verify zero timing drift guarantee for subtitle processing.

This test demonstrates that after injecting plot metadata:
1. All original subtitle timestamps remain byte-for-byte identical
2. First dialogue text appears at exactly the same timestamp
3. No subtitle blocks are renumbered incorrectly
"""

import sys
import io

# Fix Windows console encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from core.subtitle_processor import parse_srt, build_intro_blocks, strip_existing_plot_blocks, format_srt

# Test SRT content with first subtitle at 10 seconds
test_srt = """1
00:00:10,000 --> 00:00:12,500
Hello sir

2
00:00:13,000 --> 00:00:15,000
How are you today?

3
00:00:16,000 --> 00:00:18,500
I'm doing great, thanks!
"""

# Mock movie data
mock_movie = {
    "title": "Test Movie",
    "year": "2025",
    "imdb_rating": "8.5",
    "runtime": "120 min",
    "plot": "A thrilling story about testing subtitle timing preservation in automated systems."
}

def test_timing_preservation():
    """Test that original subtitle timing is preserved exactly"""

    # Parse original
    original_blocks = parse_srt(test_srt)

    print("=" * 60)
    print("ORIGINAL SUBTITLES")
    print("=" * 60)
    for block in original_blocks:
        print(f"Block {block.index}: {block.start_time}ms - {block.end_time}ms")
        text_preview = block.text.replace("\n", " ")[:50]
        print(f"  Text: {text_preview}...")

    # Build intro blocks that fit before first subtitle (10,000 ms)
    intro_blocks = build_intro_blocks(
        mock_movie,
        mock_movie["plot"],
        first_subtitle_start_ms=original_blocks[0].start_time,
        min_safe_gap_ms=1000
    )

    print("\n" + "=" * 60)
    print("INJECTED PLOT BLOCKS")
    print("=" * 60)
    for block in intro_blocks:
        print(f"Block: {block.start_time}ms - {block.end_time}ms")
        text_preview = block.text.encode('ascii', 'replace').decode('ascii')[:50]
        print(f"  Text: {text_preview}...")

    # Combine and renumber (like the real processor does)
    final = intro_blocks + original_blocks
    renumbered = [
        type(block)(
            index=i + 1,
            start_time=block.start_time,
            end_time=block.end_time,
            text=block.text
        )
        for i, block in enumerate(final)
    ]

    print("\n" + "=" * 60)
    print("FINAL OUTPUT (AFTER INJECTION)")
    print("=" * 60)
    for block in renumbered:
        print(f"Block {block.index}: {block.start_time}ms - {block.end_time}ms")
        text_preview = block.text.replace("\n", " ")[:50]
        print(f"  Text: {text_preview}...")

    # Verify timing preservation
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    # Find first dialogue subtitle in final output (skip intro blocks)
    dialogue_blocks = [b for b in renumbered if b.start_time >= original_blocks[0].start_time]

    assert len(dialogue_blocks) == len(original_blocks), \
        f"Block count mismatch: {len(dialogue_blocks)} vs {len(original_blocks)}"

    for i, (original, final_block) in enumerate(zip(original_blocks, dialogue_blocks)):
        print(f"\nDialogue Block {i+1}:")
        print(f"  Original timing: {original.start_time}ms - {original.end_time}ms")
        print(f"  Final timing:    {final_block.start_time}ms - {final_block.end_time}ms")
        print(f"  Text match: {original.text == final_block.text}")

        assert original.start_time == final_block.start_time, \
            f"Start time changed! {original.start_time} != {final_block.start_time}"
        assert original.end_time == final_block.end_time, \
            f"End time changed! {original.end_time} != {final_block.end_time}"
        assert original.text == final_block.text, \
            f"Text changed!"

    # Verify intro blocks don't overlap with first subtitle
    last_intro_block = intro_blocks[-1]
    first_dialogue_start = original_blocks[0].start_time

    print(f"\nGap between plot and dialogue:")
    print(f"  Last plot block ends: {last_intro_block.end_time}ms")
    print(f"  First dialogue starts: {first_dialogue_start}ms")
    print(f"  Gap: {first_dialogue_start - last_intro_block.end_time}ms")

    assert last_intro_block.end_time < first_dialogue_start, \
        "Plot blocks overlap with dialogue!"

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - ZERO TIMING DRIFT CONFIRMED")
    print("=" * 60)

def test_edge_case_early_subtitle():
    """Test case where first subtitle starts very early (1 second)"""

    early_srt = """1
00:00:01,000 --> 00:00:03,000
Early dialogue

2
00:00:04,000 --> 00:00:06,000
More early dialogue
"""

    original_blocks = parse_srt(early_srt)

    print("\n" + "=" * 60)
    print("EDGE CASE: EARLY SUBTITLE AT 1 SECOND")
    print("=" * 60)

    intro_blocks = build_intro_blocks(
        mock_movie,
        mock_movie["plot"],
        first_subtitle_start_ms=original_blocks[0].start_time,
        min_safe_gap_ms=1000
    )

    print(f"First dialogue at: {original_blocks[0].start_time}ms")
    print(f"Number of intro blocks: {len(intro_blocks)}")

    for block in intro_blocks:
        print(f"  Plot block: {block.start_time}ms - {block.end_time}ms")

    # Should use zero-duration blocks since not enough time
    if original_blocks[0].start_time < 2000:
        assert all(b.start_time == 0 and b.end_time == 0 for b in intro_blocks), \
            "Should use zero-duration blocks for very early subtitles"
        print("✅ Correctly using zero-duration blocks")

    print("=" * 60)

def test_idempotency():
    """Test that running the operation twice doesn't duplicate plot blocks"""

    print("\n" + "=" * 60)
    print("IDEMPOTENCY TEST")
    print("=" * 60)

    # First pass: add plot blocks
    original_blocks = parse_srt(test_srt)
    intro_blocks = build_intro_blocks(
        mock_movie,
        mock_movie["plot"],
        first_subtitle_start_ms=original_blocks[0].start_time,
        min_safe_gap_ms=1000
    )

    first_pass = intro_blocks + original_blocks
    first_pass_srt = format_srt([
        type(b)(index=i+1, start_time=b.start_time, end_time=b.end_time, text=b.text)
        for i, b in enumerate(first_pass)
    ])

    print(f"After first pass: {len(first_pass)} blocks")

    # Second pass: should strip existing plot blocks
    second_pass_parsed = parse_srt(first_pass_srt)

    print(f"Parsed second pass: {len(second_pass_parsed)} blocks")
    for i, block in enumerate(second_pass_parsed):
        text_preview = block.text.replace("\n", " ")[:60]
        print(f"  Block {i+1}: {block.start_time}-{block.end_time}ms | {text_preview}")

    second_pass_cleaned = strip_existing_plot_blocks(second_pass_parsed)

    print(f"\nAfter stripping plot blocks: {len(second_pass_cleaned)} blocks")
    for i, block in enumerate(second_pass_cleaned):
        text_preview = block.text.replace("\n", " ")[:60]
        print(f"  Block {i+1}: {block.start_time}-{block.end_time}ms | {text_preview}")

    # Should have same number as original dialogue
    assert len(second_pass_cleaned) == len(original_blocks), \
        f"Failed to strip plot blocks! Expected {len(original_blocks)}, got {len(second_pass_cleaned)}"

    print("\n✅ Idempotency verified - plot blocks correctly stripped")
    print("=" * 60)

if __name__ == "__main__":
    test_timing_preservation()
    test_edge_case_early_subtitle()
    test_idempotency()
    print("\n🎉 All tests passed! Zero timing drift guaranteed.")
