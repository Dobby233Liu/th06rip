import typing

class M3UPart(object):
    def write(self, m3u: "M3UFile", f: typing.TextIO) -> None:
        raise NotImplementedError

class M3UBlankLine(M3UPart):
    def write(self, m3u: "M3UFile", f: typing.TextIO) -> None:
        print("", file=f)

class M3UComment(M3UPart):
    line: str

    def __init__(self, line: str):
        super().__init__()
        self.line = line

    def write(self, m3u: "M3UFile", f: typing.TextIO) -> None:
        print(f"# {self.line}", file=f)

def fixlate(tagname: str, char: str, /, allow_spaces: bool = True) -> str:
    res = char + tagname
    if " " in tagname:
        if not allow_spaces:
            raise ValueError("tag name \"{tagname}\" should not contain spaces")
        res += char
    return res

class M3UVgmstreamCommentWithKey(M3UPart):
    def get_name_to_be_written(self, width: typing.Optional[int] = None) -> str:
        raise NotImplementedError

class M3UVgmstreamTag(M3UVgmstreamCommentWithKey):
    name: str
    content: str
    psfix_char: str = "%"
    name_can_contain_spaces: bool = True

    def __init__(self, name: str, content: str):
        super().__init__()
        if " " in name and not self.name_can_contain_spaces:
            raise ValueError("tag name \"{name}\" should not contain spaces")
        self.name = name
        self.content = content

    def get_name_to_be_written(self, width: typing.Optional[int] = None) -> str:
        res = fixlate(self.name.upper(), self.psfix_char, allow_spaces=self.name_can_contain_spaces)
        if width:
            res = res.ljust(width)
        return res

    def write(self, m3u: "M3UFile", f: typing.TextIO) -> None:
        line = f"# {self.get_name_to_be_written(m3u.tag_name_width)} {self.content}"
        print(line, file=f)

class M3UVgmstreamGlobalTag(M3UVgmstreamTag):
    psfix_char = "@"
    name_can_contain_spaces = True

class M3UVgmstreamGlobalCommand(M3UVgmstreamCommentWithKey):
    name: str
    psfix_char: str = "$"

    def __init__(self, name: str):
        super().__init__()
        if " " in name:
            raise ValueError("command name \"{name}\" should not contain spaces")
        self.name = name

    def get_name_to_be_written(self, width: typing.Optional[int] = None) -> str:
        res = fixlate(self.name.upper(), self.psfix_char, allow_spaces=False)
        if width:
            res = res.ljust(width)
        return res

    def write(self, m3u: "M3UFile", f: typing.TextIO) -> None:
        line = f"# {self.get_name_to_be_written(m3u.tag_name_width)}"
        print(line, file=f)

class M3UFile(M3UPart):
    filename: str

    def __init__(self, filename: str):
        super().__init__()
        self.filename = filename

    def get_filename_to_be_written(self) -> str: # for M3UVgmstreamFile
        return self.filename

    def write(self, m3u: "M3UFile", f: typing.TextIO) -> None:
        print(self.get_filename_to_be_written(), file=f)

class M3UVgmstreamFile(M3UFile):
    mini_txtp_info: str

    def __init__(self, filename: str, mini_txtp_info: typing.Optional[str] = None):
        super().__init__(filename)
        self.mini_txtp_info = mini_txtp_info

    def get_filename_to_be_written(self) -> str:
        return self.filename + (self.mini_txtp_info if self.mini_txtp_info else "")

class M3UExtendedPart(M3UPart):
    pass

class M3UExtendedDirectives(M3UExtendedPart):
    name: str
    content: typing.Optional[str]

    def __init__(self, name: str, content: typing.Optional[str] = None):
        self.name = name
        self.content = content

    def write(self, m3u: "M3UFile", f: typing.TextIO):
        content = f":{self.content}" if self.content else ""
        print("#{name}{content}", file=f)

class M3UFile(object):
    parts: list["M3UPart"] = []
    tag_name_width: int = None
    is_extended: bool = False

    def __init__(self, extended: bool = False):
        super().__init__()
        self.is_extended = extended

    def sanitize_parts(self):
        for part in self.parts:
            if isinstance(part, M3UExtendedPart) and not self.is_extended:
                raise ValueError("non-extended M3U file contains EXTM3U parts")

    def push(self, *new_parts: tuple["M3UPart"]) -> None:
        self.parts.extend(new_parts)
        self.sanitize_parts()

    def pop(self) -> M3UPart:
        return self.parts.pop()

    def calc_tag_name_width(self) -> int:
        res = 0

        for part in self.parts:
            if not isinstance(part, M3UVgmstreamCommentWithKey):
                continue
            res = max(res, len(part.get_name_to_be_written()))

        self.tag_name_width = res
        return res

    def write(self, f: typing.TextIO):
        self.sanitize_parts()

        if self.is_extended:
            print("#EXTM3U\n", file=f)

        self.calc_tag_name_width()
        for part in self.parts:
            part.write(self, f)