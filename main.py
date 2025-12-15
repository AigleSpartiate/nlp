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
    parser.add_argument("--no-mix", action="store_true", help="Skip final audio mixing")
    parser.add_argument("--melody-volume", type=float, default=0.9, help="Melody volume (0.0-1.0)")
    parser.add_argument("--vocal-volume", type=float, default=0.4, help="Vocal volume (0.0-1.0)")
    parser.add_argument("--soundfont", type=str, help="Path to soundfont (.sf2) for MIDI rendering")
    parser.add_argument("--print-input", action="store_true", help="Print DiffSinger input only")

    # Standalone mixing mode
    parser.add_argument("--mix-only", action="store_true", help="Only mix existing files")
    parser.add_argument("--midi-file", type=str, help="MIDI file for mixing")
    parser.add_argument("--vocal-file", type=str, help="Vocal WAV file for mixing")

    args = parser.parse_args()

    # config
    config = SongComposerConfig(output_dir=args.output_dir)

    pipeline = SongPipeline(
        config,
        soundfont_path=args.soundfont
    )

    if args.mix_only:
        if not args.midi_file or not args.vocal_file:
            logger.error("--mix-only requires --midi-file and --vocal-file")
            return

        output_path = os.path.join(args.output_dir, f"{args.title}_final.wav")
        result = pipeline.mix_existing_files(
            midi_path=args.midi_file,
            vocal_path=args.vocal_file,
            output_path=output_path,
            melody_volume=args.melody_volume,
            vocal_volume=args.vocal_volume
        )
        print(f"\nFinal mixed audio: {result}")
        return

    # get lyrics
    lyrics = args.lyrics
    if lyrics and os.path.isfile(lyrics):
        with open(lyrics, 'r', encoding='utf-8') as f:
            lyrics = f.read()

    if not lyrics:
        # demo lyrics
        lyrics = """小酒窝长睫毛是你最美的记号"""

    if args.print_input:
        ds_input = pipeline.get_diffsinger_input(lyrics)
        print("\nDiffSinger input format:")
        for key, value in ds_input.items():
            print(f"{key}: {repr(value)}")
        return

    # compose song
    try:
        song = pipeline.compose(
            lyrics=lyrics,
            title=args.title,
            synthesize=not args.no_synthesis,
            export_midi=not args.no_midi,
            create_final_mix=not args.no_mix,
            melody_volume=args.melody_volume,
            vocal_volume=args.vocal_volume
        )

        print("\n" "Composition complete.")

        if song.diffsinger_input:
            print("\nDiffSinger input:")
            print(f" Text: {song.diffsinger_input.text}")
            print(f" Notes: {song.diffsinger_input.notes}")
            print(f" Durations: {song.diffsinger_input.notes_duration}")

        print("\nOutput files:")
        if song.midi_path:
            print(f"MIDI: {song.midi_path}")
        if song.vocal_audio_path:
            print(f"Vocals: {song.vocal_audio_path}")
        if song.final_audio_path:
            print(f"Final mix: {song.final_audio_path}")

    except Exception as e:
        logger.error(f"Composition failed: {e}")
        raise


if __name__ == "__main__":
    main()