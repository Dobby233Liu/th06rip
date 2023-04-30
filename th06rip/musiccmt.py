import typing
import enum
import collections
import os

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
        nonlocal cur_mus_id, cur_title, cur_comment, status

        if cur_mus_id is None:
            return
        res.append(MusicCmtInfo(cur_mus_id, cur_title, "\n".join(cur_comment)))
        cur_mus_id = None
        cur_title = None
        cur_comment = None
        status = MusicCmtParserStatus.FINDING_BLOCK

    while True:
        line = f.readline()
        if line == "":
            break

        if line.startswith("#"):
            continue
        elif line.startswith("@"):
            commit()
            cur_mus_id = os.path.splitext(os.path.basename(line[1:-1]))[0]
            status = MusicCmtParserStatus.IN_TITLE
        elif status == MusicCmtParserStatus.IN_TITLE:
            cur_title = line[:-1]
            status = MusicCmtParserStatus.IN_BODY
            cur_comment = []
        elif status == MusicCmtParserStatus.IN_BODY:
            linest = line.strip()
            if linest == "":
                continue
            cur_comment.append(linest)

    commit()

    return res