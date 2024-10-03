# Generate subtitles from video

#### There are 2 features in this repository:

- Translate an existing file, can keep both languages
- Get subtitles from a video, can translate subtitles and keep both languages

#### Requirements:
- [python 3](https://www.python.org/downloads/)
- [ffmpeg](https://ffmpeg.org/download.html) (for getting subtitles from video)

### Translate `.srt` file

The details of `trans` command:
```
Usage: main.py trans [OPTIONS] P SL DL

  Translate from english to another language by folder/file path

Parameters:
  P       File/folder path.
  SL      Source language.
  DL      Destination language.

Options:
  --k     Keep both source & destination language.
  --r     Recursively translate for folder.
  --help  Show this message and exit.
```

To translate `.srt` file, for example, I want to translate `example.srt` from english to vietnamese:
```commandline
python main.py trans example.srt en vi
```
If you want to keep both languages, run it with `--k` argument:
```commandline
python main.py trans --k example.srt en vi
```

### Translate all `.srt` files in folder:
For example, I want to translate all `.srt` files in folder from english to vietnamese:
```commandline
python main.py trans folder_name en vi
```

Similar to file, you can also use `--k` option to keep both languages. In addition,
use `--r` if you want to recursively translate a folder

```commandline
python main.py transc --k --r folder_name en vi
```

### Get subtitles from video
To get subtitles from video, you have to install [ffmpeg](https://ffmpeg.org/download.html)


```
Usage: main.py subv [OPTIONS] VP SL

  Get subtitles from audio file

Parameters:
  VP      Video path.
  SL      Source language.

Options:
  --dl TEXT  The destination language.
  --k        Keep both source & destination language.
  --help     Show this message and exit.
```

Execute the following command to get subtitles from video:
```commandline
python main.py subv example.mp4 en
```

If you want to translate subtitles to Vietnamese, please run:
```commandline
python main.py subv --dl vi example.mp4 en
```
and keep both languages:
```commandline
python main.py subv --dl vi --k example.mp4 en
```
