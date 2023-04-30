import argparse
import pathlib
import os
import enum
import atexit
import shutil
import glob
import stat
import typing

import py7zr

from th06rip import thdat
from th06rip import musiccmt
from th06rip import m3u


class MainVerbosity(enum.IntEnum):
    NORMAL = 1
    MANY = 2

    @classmethod
    def from_argparse(cls, x):
        return cls(int(x))


APP_NAME = "th06rip"
APP_URL = "https://github.com/Dobby233Liu/th06rip"

ALBUM_ARTIST = "Team Shanghai Alice"
ARTIST = 'Jun\'ya "ZUN" Ōta'

argparser = argparse.ArgumentParser(
    prog=APP_NAME,
    description="Make a joshw.info set from BGM files of EoSD/PCB (trial)",
)
argparser.add_argument("game_path", type=pathlib.Path)
argparser.add_argument(
    "datfile",
    type=pathlib.Path,
    help="DAT file that contains MIDI, loop data and Music Room comments. e.g. th07md.dat",
)
argparser.add_argument("destination", type=pathlib.Path)
argparser.add_argument(
    "--game-version", type=int, required=False, help="game version (6, 7)"
)
argparser.add_argument("--game-name", type=str, required=True)
argparser.add_argument(
    "--verbosity",
    type=MainVerbosity.from_argparse,
    default=MainVerbosity.NORMAL,
    choices=range(MainVerbosity.NORMAL, MainVerbosity.MANY + 1),
)
argparser.add_argument(
    "--clobber", type=bool, default=True, help="Remove existing files?"  # !!!
)


def main() -> None:
    args = argparser.parse_args()

    def vprint2(*aargs, **kwargs):
        if args.verbosity >= MainVerbosity.MANY:
            print(*aargs, **kwargs)

    ## TODO: Move these out of __main__

    bgm_dir = os.path.join(args.game_path, "bgm")
    if not os.path.exists(bgm_dir):
        raise FileNotFoundError(
            "bgm directory doesn't exist in game dir. Wrong argument?"
        )

    thdat.check_avaliablity()

    vprint2("Prepping dest directory")
    if args.destination.exists():
        if not args.clobber:
            raise FileExistsError(args.destination)
        if not args.destination.is_dir():
            raise NotADirectoryError(args.destination)
        vprint2("Removing the original")
        shutil.rmtree(args.destination)  # !!!
        os.makedirs(args.destination)

    vprint2("Copying BGM files to dest")
    for file in glob.iglob("*.wav", root_dir=bgm_dir):
        vprint2(file)
        dir = os.path.dirname(file)
        dir_ours = os.path.join(args.destination, dir + "/" if dir != "" else "")
        os.makedirs(dir_ours, exist_ok=True)
        shutil.copy2(os.path.join(bgm_dir, file), dir_ours)
        os.chmod(
            os.path.join(dir_ours, file), stat.S_IWRITE
        )  # remove (bad) readonly prop

    vprint2("Loading dat file")
    mdat = thdat.ThDatfile(
        pathlib.Path(os.path.join(args.game_path, args.datfile)), args.game_version
    )

    vprint2("Extracting midi files")
    midifile_names = []
    for midifile in (
        x for _, x in mdat.files.items() if os.path.splitext(x.path)[1] == ".mid"
    ):
        vprint2(midifile.path)
        midifile.extract(args.destination)
        midifile_names.append(midifile.path)

    vprint2("Extracting pos files")
    mus_loop_data_file = {}
    for posfile in (
        x for _, x in mdat.files.items() if os.path.splitext(x.path)[1] == ".pos"
    ):
        vprint2(posfile.path)
        posfile.extract(args.destination)
        bgmname = os.path.splitext(posfile.path)[0]
        mus_loop_data_file[bgmname] = posfile.path
    for posfile in (
        x for _, x in mdat.files.items() if os.path.splitext(x.path)[1] == ".sli"
    ):
        vprint2(posfile.path)
        posfile.extract(args.destination)
        bgmfile = os.path.splitext(posfile.path)[0]
        bgmname = os.path.splitext(bgmfile)[0]
        mus_loop_data_file[bgmname] = posfile.path

    vprint2("Extracting musiccmt.txt")
    musiccmt_file = pathlib.Path(os.path.join(args.destination, ".musiccmt.txt"))
    atexit.register(lambda: os.remove(musiccmt_file))
    mdat.files["musiccmt.txt"].extract(musiccmt_file)
    vprint2("Parsing musiccmt.txt")
    with open(musiccmt_file, "r", encoding="shift-jis") as musiccmt_fileobj:
        musiccmt_data = musiccmt.parse(musiccmt_fileobj)

    vprint2("Splitting musiccmt.txt")
    musiccmt_split_files = []
    for name, info in musiccmt_data.items():
        outfilename = name + ".musiccmt.txt"
        outfile = os.path.join(args.destination, outfilename)
        vprint2(outfilename)
        musiccmt_split_files.append(outfile)
        with open(outfile, "w", encoding="utf-8") as out:
            out.write(info.comment)

    vprint2("Putting together !tags.m3u")
    tagsm3u = m3u.M3UFile()
    tagsm3u_normal_files: list[m3u.M3UPart] = []
    unknown_audio_files = list(glob.iglob("*.wav", root_dir=args.destination))
    for name, info in musiccmt_data.items():
        this_wav = name + ".wav"
        if this_wav in unknown_audio_files:
            unknown_audio_files.remove(this_wav)
        else:
            raise FileNotFoundError(this_wav)
        preferred_fp = (
            mus_loop_data_file[name] if name in mus_loop_data_file else this_wav
        )
        tagsm3u_normal_files.extend(
            [m3u.M3UVgmstreamTag("TITLE", info.title), m3u.M3UMediaFile(preferred_fp)]
        )
    tagsm3u_unk_files: list[m3u.M3UMediaFile] = [
        m3u.M3UMediaFile(file) for file in unknown_audio_files
    ]
    tagsm3u.push(
        m3u.M3UVgmstreamGlobalTag("ALBUM ARTIST", ALBUM_ARTIST),
        m3u.M3UVgmstreamGlobalTag("ALBUM", args.game_name),
        m3u.M3UVgmstreamGlobalTag("ARTIST", ARTIST),
        m3u.M3UVgmstreamGlobalCommand("AUTOTRACK"),
    )
    tagsm3u.push(m3u.M3UBlankLine(), *tagsm3u_normal_files)
    if len(tagsm3u_unk_files) > 0:
        tagsm3u.push(
            m3u.M3UBlankLine(), m3u.M3UComment("UNKNOWN FILES"), m3u.M3UBlankLine()
        )
        tagsm3u.push(*tagsm3u_unk_files)
    with open(os.path.join(args.destination, "!tags.m3u"), "w", encoding="utf-8") as f:
        tagsm3u.write(f)

    has_midi_playlist = False
    unknown_midi_files = list(glob.iglob("*.mid", root_dir=args.destination))
    if len(unknown_midi_files) > 0:
        has_midi_playlist = True
        vprint2("Putting together !playlist_midi.m3u")
        midiplaylistm3u = m3u.M3UFile()
        for name, info in musiccmt_data.items():
            this_mid = name + ".mid"
            if this_mid in unknown_midi_files:
                unknown_midi_files.remove(this_mid)
            else:
                raise FileNotFoundError(this_mid)
            midiplaylistm3u.push(m3u.M3UMediaFile(this_mid))
        if len(unknown_midi_files) > 0:
            midiplaylistm3u.push(
                m3u.M3UBlankLine(), m3u.M3UComment("UNKNOWN FILES"), m3u.M3UBlankLine()
            )
            midiplaylistm3u.push(
                *(m3u.M3UMediaFile(file) for file in unknown_midi_files)
            )
        with open(
            os.path.join(args.destination, "!playlist_midi.m3u"), "w", encoding="utf-8"
        ) as f:
            midiplaylistm3u.write(f)

    vprint2("Creating !extra.7z")
    extra_files = [*musiccmt_split_files]
    with py7zr.SevenZipFile(
        os.path.join(args.destination, "!extra.7z"),
        "w",
        filters=[
            {"id": py7zr.FILTER_DELTA},
            {"id": py7zr.FILTER_LZMA2, "preset": py7zr.PRESET_EXTREME},
        ],
    ) as archive:
        for file in extra_files:
            file_rel = os.path.relpath(file, args.destination)
            vprint2(file_rel)
            archive.write(file, file_rel)
    for file in extra_files:
        os.remove(file)

    with open(
        os.path.join(args.destination, "!notes.txt"), "w", encoding="utf-8"
    ) as notes:
        print(
            f"Game: {args.game_name}\n"
            f"Developer: {ALBUM_ARTIST}\n"
            f"Release date: <fill in>\n",
            file=notes,
        )
        print(f"Composer: {ARTIST}" "\n", file=notes)
        print(f"Ripped by: <your name here>" "\n", file=notes)
        print(
            "<your words here>\n",
            file=notes,
        )
        print(
            f"Song titles and ordering from {args.datfile}/musiccmt.txt\n"
            f"WAV soundtrack files from bgm/\n"
            "MIDI soundtrack files and WAV soundtrack loop points\n"
            f"from {args.datfile}, extracted with Touhou Toolkit\n"
            "\n"
            "MIDI soundtrack tags require foo_external_tags\n"
            "( https://www.foobar2000.org/components/view/foo_external_tags )\n"
            f"Comments from {args.datfile}/musiccmt.txt are in !extra.7z"  # "\n"
            # "\n"
            # f"Generated by {APP_NAME}\n"
            # f"( {APP_URL} )"
            ,
            file=notes,
        )

    vprint2("OK")
    vprint2("Please write !notes.txt")
    if has_midi_playlist:
        vprint2("Please manually tag MIDI files with foo_external_tags")
    vprint2(
        "Then 7z the files with filename:\n"
        f"[YOUR NAME] {args.game_name} (DATE)({ALBUM_ARTIST})[PC].7z"
    )


main()
