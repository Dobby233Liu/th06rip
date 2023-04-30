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
    """
    Parses a musiccmt.txt file - what the engine reads to populate the
    content of the Music Room

    It's something like this

    # comment
    @file1
    item name
    comment
    @file2
    item name
    comment
    """

    res: collections.OrderedDict[str, MusicCmtInfo] = collections.OrderedDict()

    status = MusicCmtParserStatus.FINDING_BLOCK
    cur_mus_id, cur_title, cur_comment = (None, None, None)

    def commit():
        nonlocal cur_mus_id, cur_title, cur_comment, status

        if cur_mus_id is None: # do we have nothing loaded?
            return

        res[cur_mus_id] = MusicCmtInfo(cur_title, "\n".join(cur_comment).rstrip())

        status = MusicCmtParserStatus.FINDING_BLOCK
        cur_mus_id, cur_title, cur_comment = (None, None, None)

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