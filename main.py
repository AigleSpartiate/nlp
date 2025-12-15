import argparse
import logging
import os

from dotenv import load_dotenv

from config import SongComposerConfig
from pipelines import SongPipeline

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lyrics", type=str, help="Lyrics text or path to lyrics file")
    parser.add_argument("--title", type=str, default="MySong", help="Song title")
    parser.add_argument("--output-dir", type=str, default="./output", help="Output directory")
    parser.add_argument("--no-synthesis", action="store_true", help="Skip audio synthesis")
    parser.add_argument("--no-midi", action="store_true", help="Skip MIDI export")
    parser.add_argument("--print-input", action="store_true", help="Print DiffSinger input only")

    args = parser.parse_args()

    # config
    config = SongComposerConfig(output_dir=args.output_dir)

    # get lyrics
    lyrics = args.lyrics
    if lyrics and os.path.isfile(lyrics):
        with open(lyrics, 'r', encoding='utf-8') as f:
            lyrics = f.read()

    if not lyrics:
        # demo lyrics
        lyrics = """小酒窝长睫毛是你最美的记号"""

    pipeline = SongPipeline(config)

    if args.print_input:
        # simply print DiffSinger input format
        ds_input = pipeline.get_diffsinger_input(lyrics)
        print("\n" + "DiffSinger input format:")
        for key, value in ds_input.items():
            print(f"{key}: {repr(value)}")
        return

    # compose song
    try:
        song = pipeline.compose(
            lyrics=lyrics,
            title=args.title,
            synthesize=not args.no_synthesis,
            export_midi=not args.no_midi
        )

        print("\n" "Composition complete.")

        if song.diffsinger_input:
            print("\nDiffSinger Input:")
            print(f" Text: {song.diffsinger_input.text}")
            print(f" Notes: {song.diffsinger_input.notes}")
            print(f" Durations: {song.diffsinger_input.notes_duration}")

        if song.midi_path:
            print(f"\nMIDI file: {song.midi_path}")

        if song.audio_path:
            print(f"Audio file: {song.audio_path}")

    except Exception as e:
        logger.error(f"Composition failed: {e}")
        raise


def demo():
    config = SongComposerConfig()

    pipeline = SongPipeline(config)

    # example with Chinese lyrics
    chinese_lyrics = "小酒窝长睫毛是你最美的记号"
    print(f"\nInput lyrics (Chinese): {chinese_lyrics}")

    ds_input = pipeline.get_diffsinger_input(chinese_lyrics)
    print("\nGenerated DiffSinger Input:")
    print(f" text: '{ds_input['text']}'")
    print(f" notes: '{ds_input['notes']}'")
    print(f" notes_duration: '{ds_input['notes_duration']}'")
    print(f" input_type: '{ds_input['input_type']}'")

    # validate format
    word_count = len(ds_input['text'])
    note_groups = ds_input['notes'].split(' | ')
    duration_groups = ds_input['notes_duration'].split(' | ')

    print(f"\nValidation:")
    print(f" Word count: {word_count}")
    print(f" Note groups: {len(note_groups)}")
    print(f" Duration groups: {len(duration_groups)}")
    print(f" Match: {'YES' if word_count == len(note_groups) == len(duration_groups) else 'NO'}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo()
    else:
        main()
