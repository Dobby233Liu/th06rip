import argparse
import pathlib

argparser = argparse.ArgumentParser(
                prog="th06rip",
                description="Make a joshw.info set from BGM files of EoSD/PCB (trial)")
argparser.add_argument("game_path", type=pathlib.Path)
argparser.add_argument("datfile", type=pathlib.Path,
                       help="DAT file that contains MIDI, loop data and Music Room comments. e.g. th07md.dat")
argparser.add_argument("destination", type=pathlib.Path)
argparser.add_argument("--game-version", type=int, required=False,
                       help="game version (6, 7)")

argparser.parse_args()