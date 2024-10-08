import os
import math
import constants
import threading
import ffmpeg
import click
import translators as ts

from dataclasses import dataclass
from faster_whisper import WhisperModel, transcribe


@dataclass
class Subtitle:
    time: str
    text: str

    def __init__(self, time, text):
        self.time = time
        self.text = text


def translate_to_lang(sub: Subtitle, sl: str, dl: str, o: int):
    if o == 0:
        return

    text = sub.text
    try:
        new_text = ts.translate_text(
            text, from_language=sl, to_language=dl, translator="bing")
        if o == 1:
            sub.text = new_text
        elif o == 2:
            sub.text = text + "\n" + new_text
    except Exception as e:
        print("** Translating for '{0}' was failed **".format(text))
        print(e)
        pass


def convert_subtitle_to_2lang(subtitles: list[Subtitle], sl: str, dl: str, o: int, level: int):
    sub_lens = len(subtitles)
    i = 0

    while i < sub_lens:
        end_idx = i + 10
        start_idx = i
        threads = []
        while i < sub_lens and i < end_idx:
            threads.append(threading.Thread(
                target=translate_to_lang, args=(subtitles[i], sl, dl, o,)))
            i += 1

        i = start_idx
        while i < sub_lens and i < end_idx:
            threads[i-start_idx].start()
            i += 1

        i = start_idx
        while i < sub_lens and i < end_idx:
            threads[i-start_idx].join()
            i += 1
        percent = i*100.0/sub_lens
        print(
            f"{"  " * level}|- The translation process has reached {round(percent, 2)}%", end="\r")

    return subtitles


def gen_subtitles(subtitles: list[Subtitle], file_path: str):
    file = open(file_path, 'w', encoding="utf-8")
    i = 1
    for sub in subtitles:
        text = f"{str(i)}\n{sub.time}\n{sub.text}\n\n"
        file.write(text)
        i += 1
    file.close()


def get_subtitles(file_path: str):
    with open(file_path, 'r', encoding="utf-8") as FILE:
        lines = FILE.readlines()

    subtitles = []
    current_subtitle = None

    for line in lines:
        if "-->" in line:
            current_subtitle = Subtitle(time=line.strip(), text="")
        elif line == "\n" and current_subtitle:
            subtitles.append(current_subtitle)
            current_subtitle = None
        elif current_subtitle:
            current_subtitle.text += line.strip()

    return subtitles


def get_file_names(folder_p: str):
    files = []
    for file_name in os.listdir(folder_p):
        if os.path.isfile(os.path.join(folder_p, file_name)) and \
                file_name.endswith(".srt") and \
                "_en-vi.srt" not in file_name:
            files.append(file_name)
    return files


def get_folder_names(folder_p: str):
    folders = []
    for f_name in os.listdir(folder_p):
        if f_name == "result":
            continue
        new_f_name = os.path.join(folder_p, f_name)
        if os.path.isdir(new_f_name):
            folders.append(new_f_name)
    return folders


def gen_for_file(folder_p: str, file: str, level: int, sl: str, dl: str, k: int, f: int):
    level = level+1
    print("  " * level + "|- Processing for file", "'{0}'".format(file))

    file_name = os.path.basename(file)
    file_name_without_extension, _ = os.path.splitext(file_name)
    file_name = file_name_without_extension + \
        (f"_{sl}-{dl}.srt" if k == 2 else f"_{dl}.srt")
    new_file_name = os.path.join(folder_p + "/result", file_name)
    if os.path.isfile(new_file_name) and f == 0:
        return

    file_path = os.path.join(folder_p, file)
    subtitles = get_subtitles(file_path)
    subtitles = convert_subtitle_to_2lang(subtitles, sl, dl, k, level+1)
    gen_subtitles(subtitles, new_file_name)
    print("  " * level + f"|- {file} has been successfully processed")


def gen_for_folder(folder_p: str, level: int, sl: str, dl: str, k: int, f: int, r: int = 1):
    print(f"{"  "*level}{"-"*20}")
    print(f"{"  "*level}|+ Processing for folder '{folder_p}'")
    file_srt = get_file_names(folder_p)
    if not os.path.isdir(folder_p + "/result") and len(file_srt) > 0:
        os.mkdir(folder_p + "/result")
    for file in file_srt:
        gen_for_file(folder_p, file, level, sl, dl, k, f)

    if r == 0:
        return

    for folder in get_folder_names(folder_p):
        gen_for_folder(folder, level + 1, sl, dl, k, f)


def extract_audio(input_video: str):
    audio_name = os.path.basename(input_video)
    audio_name, _ = os.path.splitext(audio_name)
    extracted_audio = f"{audio_name}.aac"
    stream = ffmpeg.input(input_video)
    stream = ffmpeg.output(stream, extracted_audio)
    ffmpeg.run(stream, overwrite_output=True)
    return extracted_audio


def transcribe_audio(audio: str, sl: str):
    model = WhisperModel("small")
    seg, _ = model.transcribe(audio, vad_filter=False, language=sl)
    return list(seg)


def format_time(seconds: float):
    hours = math.floor(seconds / 3600)
    seconds %= 3600
    minutes = math.floor(seconds / 60)
    seconds %= 60
    milliseconds = round((seconds - math.floor(seconds)) * 1000)
    seconds = math.floor(seconds)
    formatted_time = f"{hours:02d}:{minutes:02d}:{
        seconds:01d},{milliseconds:03d}"

    return formatted_time


def generate_subtitle_file(subtitle_file: str, sl: str, dl: str, segments: list[transcribe.Segment], o: int):
    subtitles = []
    for index, segment in enumerate(segments):
        segment_start = format_time(segment.start)
        segment_end = format_time(segment.end)
        time = f"{segment_start} --> {segment_end}"
        subtitles.append(Subtitle(time=time, text=segment.text.strip()))

    subtitles = convert_subtitle_to_2lang(subtitles, sl, dl, o, level=0)
    gen_subtitles(subtitles, subtitle_file)


@click.command()
@click.argument("p")
@click.argument("sl")
@click.argument("dl")
@click.option("--k", count=True, help="Keep both source & destination language.")
@click.option("--r", count=True, help="Recursively translate for folder.")
@click.option("--f", count=True, help="Overwrite if the translated file already exists.")
def trans(p: str, sl: str, dl: str, k: int, r: int, f: int):
    """Translate from english to another language by folder/file path"""
    if sl not in constants.LANGUAGES or dl not in constants.LANGUAGES:
        click.echo(f"'{sl}' or '{
                   dl}' is not in the list of supported languages.")
        click.echo(f"The following languages are supported:")
        click.echo("\n".join(
            [f"  - {item}: {constants.LANGUAGES[item]}" for item in constants.LANGUAGES]))
        return

    if os.path.isfile(p) and p.endswith(".srt"):
        base_folder = os.path.dirname(p)
        if not os.path.isdir(base_folder + "/result"):
            os.mkdir(base_folder + "/result")
        gen_for_file(base_folder, os.path.basename(p),
                     0, sl, dl, 2 if k == 1 else 1, f)
        return

    if os.path.isdir(p):
        gen_for_folder(p, 0, sl, dl, 2 if k == 1 else 1, f, r)
        return

    click.echo(f"'{p}' is not the path of srt file or folder.")


@click.command()
@click.argument("vp")
@click.argument("sl")
@click.option("--dl", default="", show_default=True, help="The destination language.")
@click.option("--k", count=True, help="Keep both source & destination language.")
def subv(vp: str, sl: str, dl: str, k: int):
    """Get subtitles from audio file"""
    if not os.path.isfile(vp):
        click.echo(f"'{vp}' is not a file.")
        return

    if k == 1 and dl == "":
        click.echo(
            f"You can not keep both source & destination language without --dl input.")
        return

    flag = False

    if sl not in constants.LANGUAGES:
        flag = True
        click.echo(f"'{sl}' is not in the list of supported languages.")

    if dl != "" and dl not in constants.LANGUAGES:
        flag = True
        click.echo(f"'{dl}' is not in the list of supported languages.")

    if flag:
        click.echo(f"The following languages are supported:")
        click.echo("\n".join(
            [f"  - {item}: {constants.LANGUAGES[item]}" for item in constants.LANGUAGES]))
        return

    file_name, _ = os.path.splitext(vp)

    ext_file = sl
    if dl != "":
        ext_file = f"{sl}-{dl}" if k == 1 else dl
    subtitle_file = f"{file_name}_{ext_file}.srt"

    if os.path.isfile(subtitle_file):
        click.echo(f"'{subtitle_file}' file is already exist.")
        return

    audio_name = extract_audio(vp)

    segments = transcribe_audio(audio=audio_name, sl=sl)

    o = 0
    if dl != "":
        o = 2 if k == 1 else 1

    generate_subtitle_file(subtitle_file, sl, dl, segments, o)


@click.group()
def cli():
    pass


cli.add_command(trans)
cli.add_command(subv)


if __name__ == '__main__':
    cli()
