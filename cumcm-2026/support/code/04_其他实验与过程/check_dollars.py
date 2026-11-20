"""扫描流程图脚本里"美元符号不成对"的文本条目（会导致 matplotlib 不渲染公式）"""
import re
import os

BASE = os.path.dirname(os.path.abspath(__file__))
pat = re.compile(r'\(\s*"([^"]+)"\s*,\s*"((?:[^"\\]|\\.)*)"\s*\)')


def unescape(s):
    return s.replace("\\\\", "\\")


def main():
    for f in ("ch58_flowcharts.py",):
        src = open(os.path.join(BASE, f), encoding="utf-8").read()
        bad = []
        self_test = 0
        for m in pat.finditer(src):
            tag, txt = m.group(1), unescape(m.group(2))
            n = txt.count("$")
            self_test += 1
            if n % 2:
                bad.append((tag, txt, n))
        print("%s：扫描到 %d 条文本，其中美元符号不成对 %d 条" % (f, self_test, len(bad)))
        for tag, txt, n in bad:
            print("   [%s] $x%d  %s" % (tag, n, txt[:90]))


if __name__ == "__main__":
    main()
