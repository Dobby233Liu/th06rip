import typing
import enum
import collections

MusicCmtInfo = collections.namedtuple("MusicCmtInfo", ["music_id", "title", "comment"])

class MusicCmtParserStatus(enum.Enum):
    FINDING_BLOCK = 0
    IN_TITLE = 1
    IN_BODY = 2

def parse(f: typing.TextIO):
    status = MusicCmtParserStatus.FINDING_BLOCK
    cur_mus_id = None
    cur_title = None
    cur_comment = None
    res = []

    def commit():
        nonlocal cur_mus_id, cur_title, cur_comment

        if cur_mus_id is None:
            return
        res.append(MusicCmtInfo(cur_mus_id, cur_title, cur_comment))
        cur_mus_id = None
        cur_title = None
        cur_comment = None
        mode = MusicCmtParserStatus.FINDING_BLOCK

    while True:
        line = f.readline()
        if line == "":
            break

        if line.startswith("@"):
            commit()
            cur_mus_id = line[1:-1]
            status = MusicCmtParserStatus.IN_TITLE
        elif status == MusicCmtParserStatus.IN_TITLE:
            cur_title = line[:-1]
            status = MusicCmtParserStatus.IN_BODY
            cur_comment = ""
        elif status == MusicCmtParserStatus.IN_BODY:
            if line == "\n":
                commit()
                continue
            cur_comment += line

    commit()

    return res