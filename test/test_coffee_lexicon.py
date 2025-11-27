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
    got = l.normalize_variety("古優種（ Heirloom）",)
    print(got)
    assert set[Any](got) == {"古優原生種（Heirloom）"}

def test_country():
    l = lex()
    assert l.normalize_country("Colombia") == "哥倫比亞（Colombia）"
    assert l.normalize_country("哥斯大黎加") == "哥斯大黎加（Costa Rica）"
