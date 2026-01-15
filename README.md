# audiodumper

Dumb little wrapper around librosa and ffmpeg. Reads an audio (or video) file
and dumps the output to a .wav. Optionally, it can also transpose by a specified
number of semitones. Believe it or not these are things I do quite often.

```bash
audiodumper --help

Usage: python -m audiodumper [OPTIONS] FILEPATH

  Read input audio/video FILEPATH with ffmpeg and dump processed output.

  By default the output is `basename.wav` in the current directory. Use
  `--output` to control the output path.

Options:
  -o, --output FILE        Output file path (defaults to input basename with
                           .wav)
  -t, --transpose INTEGER  Transpose audio by N semitones (e.g. +3, -4)
  -y, --yes                Overwrite output without prompting (non-
                           interactive)
  --version                Show the version and exit.
  --help                   Show this message and exit.
```
