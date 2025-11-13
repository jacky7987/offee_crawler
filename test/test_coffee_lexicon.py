from typing import Any


from pathlib import Path
from normalizer.coffee_lexicon import CoffeeLexicon


def lex():
    return CoffeeLexicon(Path("data/normalize/coffee_lexicon.yaml"))


def test_process():
    l = lex()
    assert l.normalize_process("厭氧水洗") == "厭氧（Anaerobic）"
    assert l.normalize_process("日曬") == "日曬（Natural）"

def test_roast():
    l = lex()
    assert l.normalize_roast("淺中焙") == "淺中焙（Light-medium）"

def test_variety_mixed():
    l = lex()
    got = l.normalize_variety("卡度拉 caturra / 黃波旁 Yellow Bourbon")
    print(got)
    assert set[Any](got) == {"黃波旁（Yellow Bourbon）", "卡度拉（Caturra）"}