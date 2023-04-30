import os
import pathlib
import subprocess
import tempfile
import typing
import re
import shutil

"""
Janky way to work with the janky thdat CLI tool instead of the thtk library
"""

THDAT_TOOL = "thdat"
TOOL_TIMEOUT = 5  # s


def check_avaliablity() -> None:
    try:
        subprocess.run(
            [THDAT_TOOL, "-V"],
            check=True,
            timeout=TOOL_TIMEOUT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        raise Exception(
            "thdat doesn't seem to be avaliable."
            "Try installing Touhou Toolkit ( https://github.com/thpatch/thtk ) to PATH."
        ) from e


class ThDatfileFile(object):
    path: str
    size: int
    stored_size: int
    datfile: "ThDatfile"

    def __init__(self, path: str, size: int, stored_size: int, datfile: "ThDatfile"):
        super().__init__()

        self.path = os.path.normpath(path)
        self.size = size
        self.stored_size = stored_size
        self.datfile = datfile

    def extract(self, dest: pathlib.Path):
        self.datfile._extract_by_path(self.path, dest)

    def __repr__(self) -> str:
        return f"<th06rip.thdat.ThDatfilefile {self.path} in {self.datfile.path} at {id(self)}>"


class ThDatfile(object):
    path: pathlib.Path
    version: int
    files: list[ThDatfileFile]

    def __init__(
        self, path: pathlib.Path, version: typing.Optional[int] = None
    ) -> None:
        super().__init__()

        check_avaliablity()

        self.path = path
        self.version = version if version else self.detect_version()

        self.load_file_list()

    def detect_version(self) -> int:
        # List outputs the detected version
        out = subprocess.check_output(
            [THDAT_TOOL, "-ld", self.path.absolute()],
            timeout=TOOL_TIMEOUT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        for line in out.splitlines():
            rmatch = re.fullmatch(r"^Detected version ([0-9]+)$", line)
            if rmatch:
                return int(rmatch[1])
        raise Exception(
            f"could not detect version of datfile {self.path.relative_to(os.getcwd())}"
        )

    def load_file_list(self) -> None:
        out = subprocess.check_output(
            [THDAT_TOOL, f"-l{self.version}", self.path.absolute()],
            timeout=TOOL_TIMEOUT,
            text=True,
            stderr=subprocess.DEVNULL,
        )

        filelist_found = False
        raw_file_list = []
        for line in out.splitlines():
            if not filelist_found:
                if re.fullmatch(r"^Name(?:\s*)Size(?:\s*)Stored$", line):
                    filelist_found = True
                continue

            rmatch = re.fullmatch(
                r"^([A-Za-z0-9_\-.]+)(?:\s*)([0-9]+)(?:\s*)([0-9]+)$", line
            )
            if rmatch:
                raw_file_list.append(rmatch.group(1, 2, 3))
            else:
                break

        if not filelist_found:
            raise Exception("thdat did not return a file list")

        def rawinfo_to_objects(x):
            return ThDatfileFile(
                path=x[0], size=int(x[1]), stored_size=int(x[2]), datfile=self
            )

        self.files = list(map(rawinfo_to_objects, raw_file_list))

    def file_exists(self, path: str) -> bool:
        return any(x.path == path for x in self.files)

    def _extract_by_path(self, path: str, dest: pathlib.Path):
        if not self.file_exists(path):
            raise FileNotFoundError(path)

        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                [
                    THDAT_TOOL,
                    f"-x{self.version}",
                    self.path.absolute(),
                    "-C",
                    tmpdir,
                    path,
                ],
                timeout=TOOL_TIMEOUT,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            shutil.move(os.path.join(tmpdir, path), dest)

    def _extract_by_path_batch(self, paths: list[str], dest: pathlib.Path):
        if not dest.is_dir():
            raise NotADirectoryError(dest)

        for path in paths:
            self._extract_by_path(path, dest)

    def __repr__(self) -> str:
        return (
            f"<th06rip.thdat.ThDatfile for {self.path} (v{self.version}) at {id(self)}>"
        )
