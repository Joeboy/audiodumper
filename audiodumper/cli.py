import click
import ffmpeg
import os
import tempfile
from . import __version__


def _default_output_path(input_path: str) -> str:
    base, _ext = os.path.splitext(os.path.basename(input_path))
    return f"{base}.wav"


@click.command()
@click.argument('filepath', type=click.Path(exists=True, dir_okay=False))
@click.option('--output', '-o', type=click.Path(dir_okay=False), default=None,
              help='Output file path (defaults to input basename with .wav)')
@click.option('--transpose', '-t', type=int, default=None,
              help='Transpose audio by N semitones (e.g. +3, -4)')
@click.option('--yes', '-y', is_flag=True, default=False,
              help='Overwrite output without prompting (non-interactive)')
@click.version_option(__version__)
def main(filepath, output, transpose, yes):
    """Read input audio/video FILEPATH with ffmpeg and dump processed output.

    By default the output is `basename.wav` in the current directory. Use
    `--output` to control the output path.
    """
    out_path = output or _default_output_path(filepath)
    # If the output file already exists, ask the user unless `--yes` was provided.
    overwrite = bool(yes)
    if os.path.exists(out_path) and not overwrite:
        try:
            if not click.confirm(f"Output file '{out_path}' already exists. Overwrite?", default=False):
                click.echo("Aborted: output file exists and overwrite not confirmed.")
                raise click.Abort()
            overwrite = True
        except click.Abort:
            raise

    # Validate transpose input (click's int type already ensures integerness).
    if transpose is not None:
        # transpose is an int; no further parsing required here. Keep value for processing.
        semitones = int(transpose)
    else:
        semitones = None

    try:
        # If no transpose requested, use ffmpeg directly
        if semitones is None:
            stream = ffmpeg.input(filepath)
            stream = ffmpeg.output(stream, out_path, format='wav', acodec='pcm_s16le', ac=2, ar='44100')
            # Respect user's overwrite choice: use overwrite flag only if confirmed
            if overwrite:
                ffmpeg.run(ffmpeg.overwrite_output(stream), capture_stdout=False, capture_stderr=True)
            else:
                ffmpeg.run(stream, capture_stdout=False, capture_stderr=True)

        else:
            # Use ffmpeg to extract a WAV to a temporary file, process with librosa,
            # then write final output with soundfile.
            try:
                import librosa
                import soundfile as sf
            except Exception:  # pragma: no cover - dependency error surfaced to user
                raise click.ClickException(
                    "Missing optional dependencies for transpose: install 'librosa' and 'soundfile' (e.g. uv install . or pip install librosa soundfile)"
                )

            tmp = None
            try:
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as t:
                    tmp = t.name

                # extract to temporary wav (44.1k stereo PCM)
                stream = ffmpeg.input(filepath)
                stream = ffmpeg.output(stream, tmp, format='wav', acodec='pcm_s16le', ac=2, ar='44100')
                ffmpeg.run(ffmpeg.overwrite_output(stream), capture_stdout=False, capture_stderr=True)

                # load as mono for reliable pitch-shift, then write result
                y, sr = librosa.load(tmp, sr=None, mono=True)
                # Use keyword args for compatibility with different librosa versions
                y_shifted = librosa.effects.pitch_shift(y, n_steps=semitones, sr=sr)

                # write shifted audio to requested out_path as 16-bit PCM WAV
                # ensure we don't unintentionally overwrite unless confirmed
                if overwrite and os.path.exists(out_path):
                    try:
                        os.remove(out_path)
                    except Exception:
                        pass
                sf.write(out_path, y_shifted, sr, subtype='PCM_16')
            finally:
                if tmp and os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except Exception:
                        pass

        msg = f"Wrote: {out_path}"
        if semitones is not None:
            msg += f" (transpose: {semitones:+d} semitones)"
        click.echo(msg)

    except ffmpeg.Error as e:
        # ffmpeg-python raises ffmpeg.Error on failures
        stderr = getattr(e, 'stderr', None)
        if isinstance(stderr, bytes):
            stderr = stderr.decode('utf-8', errors='ignore')
        raise click.ClickException(f"ffmpeg error: {stderr}")
    except click.ClickException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise click.ClickException(f"Failed processing file: {exc}")
