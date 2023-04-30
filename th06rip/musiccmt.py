import typing
import enum
import collections
import os

class MusicCmtInfo(typing.NamedTuple):
    title: str
    comment: str

class MusicCmtParserStatus(enum.Enum):
    FINDING_BLOCK = 0
    IN_TITLE = 1
    IN_BODY = 2

def parse(f: typing.TextIO) -> collections.OrderedDict[str, MusicCmtInfo]:
    res = collections.OrderedDict()

    status = MusicCmtParserStatus.FINDING_BLOCK
    cur_mus_id = None
    cur_title = None
    cur_comment = None

    def commit():
        nonlocal cur_mus_id, cur_title, cur_comment, status

        if cur_mus_id is None: # do we have nothing loaded?
            return

        res_comment = "\n".join(cur_comment)
        res_comment = res_comment.rstrip()
        res[cur_mus_id] = MusicCmtInfo(cur_title, res_comment)

        status = MusicCmtParserStatus.FINDING_BLOCK
        cur_mus_id = None
        cur_title = None
        cur_comment = None

    for line in f:
        if line.startswith("#"):
            continue

        linest = line[:-1]
        if line.startswith("@"):
            commit()

            status = MusicCmtParserStatus.IN_TITLE
            cur_mus_id = os.path.splitext(os.path.basename(linest[1:]))[0]
        elif status == MusicCmtParserStatus.IN_TITLE:
            cur_title = linest

            status = MusicCmtParserStatus.IN_BODY
            cur_comment = []
        elif status == MusicCmtParserStatus.IN_BODY:
            cur_comment.append(linest)
    commit()

    return res