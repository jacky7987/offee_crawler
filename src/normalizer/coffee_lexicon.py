from pathlib import Path
import re
import unicodedata
import yaml


class CoffeeLexicon:
    def __init__(self, yaml_path:Path):
        # 把 Lexicon 的 YAML 打開
        with yaml_path.open("r", encoding='utf-8') as f:
            data = yaml.safe_load(f)

        #初始化
        self.process = self._prep_category(data.get("process", {}))
        self.variety = self._prep_category(data.get("variety", {}))
        self.roast = self._prep_category(data.get("roast", {}))
        self.country = self._prep_category(data.get("country", {}))

    # ===== helpers =====
    @staticmethod
    def _to_halfwidth(s: str) -> str:
        return unicodedata.normalize("NFKC", s)

    @staticmethod
    def _has_cjk(s: str) -> bool:
        # 粗略判斷是否含中日韓字元
        return any('\u4e00' <= ch <= '\u9fff' for ch in s)

    @staticmethod
    def _has_latin(s: str) -> bool:
        return any('a' <= ch.lower() <= 'z' for ch in s)

    # ===== 專供品種用的預處理 =====
    def _preprocess_variety_raw(self, raw: str) -> list[str]:
        if not raw:
            return []

        text = self._to_halfwidth(raw).strip()

        # 1) 大分隔符統一換成逗號
        seps = ["/", "、", "，", ",", "│", "|", "（", "）", "(", ")"]
        for sep in seps:
            text = text.replace(sep, ",")

        # 2) 多空白壓成單一空白
        text = re.sub(r"\s+", " ", text)

        tokens: list[str] = []

        for chunk in text.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue

            has_cjk = self._has_cjk(chunk)
            has_latin = self._has_latin(chunk)

            if has_cjk and has_latin:
                # e.g. "黃波旁 Yellow Bourbon"
                parts = chunk.split()
                chinese_part = []
                latin_parts = []

                for p in parts:
                    if self._has_cjk(p):
                        chinese_part.append(p)
                    else:
                        latin_parts.append(p)

                if chinese_part:
                    tokens.append("".join(chinese_part).lower())
                if latin_parts:
                    # 把英文部分再黏回去，避免 yellow / bourbon 被拆開
                    tokens.append(" ".join(latin_parts).lower())
            else:
                # 純英文或純中文
                tokens.append(chunk.lower())

        return tokens

    def _prep_category(self, cat:dict):
        """準備好每個屬性，並且已經預處理

        Args:
            cat (dict): _description_

        Returns:
            _type_: _description_
        """
        out = {}
        for norm_key, spec in cat.items():
            aliases = {self._canon(s) for s in spec.get("aliases", [])}
            regex = [re.compile(p, re.I) for p in spec.get("regex", [])]
            out[norm_key] = {"aliases": aliases, "regex": regex}
        return out

    #會用到的字串預處理
    def _canon(self, s:str) -> str:
        if s is None : return ""
        s = unicodedata.normalize("NFKC", s)
        s = s.strip().lower()
        s = re.sub(r"\s+", " ", s)
        return s

    
    def _match(self, text:str, category: dict, heuristics=None):
        """
        通用的比對，把yaml 下面層級的 aliases 換成上面的

        Args:
            text (str): _description_
            heuristics (_type_, optional): _description_. Defaults to None.
        """
        t = self._canon(text)

        #1. 精準命中
        for k, spec in category.items():
            if t in spec["aliases"]:
                return k

        #2. 正則表示法比對
        for k, spec in category.items():
            for rgx in spec["regex"]:
                if rgx.search(t):
                    return k
        
        #3. 最後補看看動
        if heuristics:
            got = heuristics(t)
            if got: 
                return got
        return None


    #--------- Public ---------------
    def normalize_process(self, raw:str) -> str:
        def heur(t: str):
            if "厭氧" in t or "anaerobic" in t:
                return "厭氧（Anaerobic）"
            if "水洗" in t or "washed" in t:
                return "水洗（Washed）"
            if "日曬" in t or "natural" in t or "sun dried" in t:
                return "日曬（Natural）"
            if "蜜" in t or "honey" in t:
                return "蜜處理（Honey）"
            if "溼剝" in t or "濕剝" in t or "giling basah" in t:
                return "溼剝法（Wet hulled）"
            return None
        return self._match(raw, self.process, heuristics=heur)

    
    def normalize_variety(self, raw:str) -> list:
        """
        1) 先把 raw 用 _preprocess_variety_raw 拆成 tokens（含中文 token 與英文 token）
        2) 每個 token 用 lexicon 的 variety 區做 _match
        3) 去重、保序
        """
        tokens = self._preprocess_variety_raw(raw)

        out = []
        seen = set()
        for tok in tokens:
            canon = self._match(tok, self.variety)
            if canon and canon not in seen:
                seen.add(canon)
                out.append(canon)
        return out


    def normalize_roast(self, raw:str)->str:
        return self._match(raw, self.roast)

    def normalize_country(self, raw:str)->str:
        return self._match(raw, self.country)
