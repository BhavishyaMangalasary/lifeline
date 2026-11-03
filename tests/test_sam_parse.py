"""Offline test: parses the example line from Meta's SAM docs. Costs nothing, needs no API key."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lifeline.perception.sam import parse_raw  # noqa: E402

DOC_LINE = (
    "<0f>0<|box;x1=211;y1=228;x2=270;y2=254;w=320;h=334|>"
    "<|mask;x=0;y=0;data=27,60,~!!!!M!0c[0o91w?q1!pIH4pPRVp2B3'7`e.ioeAf6-k/#Xd8%dX9x(|>,"
    "1<|box;x1=155;y1=228;x2=202;y2=254;w=320;h=334|>"
    "<|mask;x=0;y=0;data=27,48,~!!!!J!0c[q=Pj_zs=*4C4(/./x#:/`S_GnD`=o3?X{emCgO$y@|>"
)


def test_doc_example():
    dets = parse_raw(DOC_LINE, 320, 334)
    assert len(dets) == 2
    assert dets[0].box == (211, 228, 271, 255)
    assert dets[0].mask.shape == (334, 320)
    assert int(dets[0].mask.sum()) == 1539
    assert int(dets[1].mask.sum()) == 1236


def test_empty_output_means_no_matches():
    assert parse_raw("", 100, 100) == []


if __name__ == "__main__":
    test_doc_example()
    test_empty_output_means_no_matches()
    print("OK: SAM output parsing works offline.")
