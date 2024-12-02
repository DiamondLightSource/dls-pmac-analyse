from dls_pmacanalyse.errors import GeneralError
from dls_pmacanalyse.utils import tokenIsFloat, tokenToFloat


class PmacToken:
    def __init__(self, text=None):
        self.fileName = ""
        self.line = ""
        self.text = ""
        self.compareFail = False
        if text is not None:
            self.text = text

    def set(self, text, fileName, line):
        self.text = text
        self.fileName = fileName
        self.line = line
        self.compareFail = False

    def __str__(self):
        return self.text

    def __eq__(self, other):
        return self.text == str(other)

    def __ne__(self, other):
        return self.text != str(other)

    def __len__(self):
        return len(self.text)

    def lower(self):
        return self.text.lower()


class PmacVariable:
    spaces = "                        "

    def __init__(self, prefix, n, v):
        self.typeStr = f"{prefix}{n}"
        self.n = n
        self.v = v
        self.ro = False

    def addr(self):
        return self.typeStr

    def set(self, v):
        self.v = v

    def compare(self, other):
        if self.ro or other.ro:
            return True
        elif tokenIsFloat(self.v) and tokenIsFloat(other.v):
            a = tokenToFloat(self.v)
            b = tokenToFloat(other.v)
            return (a >= b - 0.00001) and (a <= b + 0.00001)
        else:
            return self.v == other.v

    def valStr(self):
        if isinstance(self.v, float):
            result = (f"{self.v:.12f}").rstrip("0")
            if result.endswith("."):
                result += "0"
        else:
            result = f"{self.v}"
        return result

    def getFloatValue(self):
        return float(self.v)

    def html(self, page, parent):
        page.text(parent, self.valStr())

    def isEmpty(self):
        return False

    def htmlCompare(self, page, parent, other):
        return self.html(page, parent)


class PmacIVariable(PmacVariable):
    useHexAxis = [2, 3, 4, 5, 10, 24, 25, 42, 43, 44, 55, 81, 82, 83, 84, 91, 95]
    useHexGlobal = range(8000, 8192)
    axisVarMin = 100
    axisVarMax = 3299
    varsPerAxis = 100

    def __init__(self, n, v=0, ro=False):
        PmacVariable.__init__(self, "i", n, v)
        self.ro = ro

    def dump(self, typ=0, comment=""):
        result = ""
        if typ == 1:
            result = f"{self.valStr()}"
        else:
            if self.ro:
                result += ";"
            result += f"i{self.n}={self.valStr()}"
            if len(comment) == 0:
                result += "\n"
            else:
                if len(result) < len(self.spaces):
                    result += self.spaces[len(result) :]
                result += f";{comment}\n"
        return result

    def copyFrom(self):
        result = PmacIVariable(self.n)
        result.v = self.v
        result.ro = self.ro
        return result

    def valStr(self):
        if isinstance(self.v, float):
            result = (f"{self.v:.12f}").rstrip("0")
            if result.endswith("."):
                result += "0"
        else:
            useHex = False
            if self.n >= self.axisVarMin and self.n <= self.axisVarMax:
                useHex = (self.n % self.varsPerAxis) in self.useHexAxis
            else:
                useHex = self.n in self.useHexGlobal
            if useHex:
                result = f"${self.v:x}"
            else:
                result = f"{self.v}"
        return result


class PmacMVariable(PmacVariable):
    def __init__(self, n, type="*", address=0, offset=0, width=0, format="U"):
        PmacVariable.__init__(self, "m", n, 0)
        self.set(type, address, offset, width, format)

    def dump(self, typ=0):
        if typ == 1:
            result = f"{self.valStr()}"
        else:
            result = f"m{self.n}->{self.valStr()}\n"
        return result

    def valStr(self):
        result = ""
        if self.type == "*":
            result += "*"
        elif self.type in ["X", "Y"]:
            result += f"{self.type}:${self.address:x}"
            if self.width == 24:
                result += ",24"
                if not self.format == "U":
                    result += f",{self.format}"
            else:
                result += f",{self.offset}"
                if not self.width == 1 or not self.format == "U":
                    result += f",{self.width}"
                    if not self.format == "U":
                        result += f",{self.format}"
        elif self.type in ["D", "DP", "F", "L"]:
            result += f"{self.type}:${self.address:x}"
        elif self.type in ["TWS", "TWR", "TWD", "TWB"]:
            result += f"{self.type}:${self.address:x}"
        else:
            raise GeneralError("Unsupported")
        return result

    def contentsStr(self):
        return PmacVariable.valStr(self)

    def set(self, type, address, offset, width, format):
        self.type = type
        self.address = address
        self.offset = offset
        self.width = width
        self.format = format

    def setValue(self, v):
        self.v = v

    def copyFrom(self):
        result = PmacMVariable(self.n)
        result.v = self.v
        result.ro = self.ro
        result.type = self.type
        result.address = self.address
        result.offset = self.offset
        result.width = self.width
        result.format = self.format
        return result

    def compare(self, other):
        if self.ro or other.ro:
            return True
        else:
            return (
                self.type == other.type
                and self.address == other.address
                and self.offset == other.offset
                and self.width == other.width
                and self.format == other.format
            )


class PmacPVariable(PmacVariable):
    def __init__(self, n, v=0):
        PmacVariable.__init__(self, "p", n, v)

    def dump(self, typ=0):
        if typ == 1:
            result = f"{self.valStr()}"
        else:
            result = f"p{self.n}={self.valStr()}\n"
        return result

    def copyFrom(self):
        result = PmacPVariable(self.n)
        result.v = self.v
        result.ro = self.ro
        return result


class PmacQVariable(PmacVariable):
    def __init__(self, cs, n, v=0):
        PmacVariable.__init__(self, f"&{cs}q", n, v)
        self.cs = cs

    def dump(self, typ=0):
        if typ == 1:
            result = f"{self.valStr()}"
        else:
            result = f"&{self.cs}q{self.n}={self.valStr()}\n"
        return result

    def copyFrom(self):
        result = PmacQVariable(self.cs, self.n)
        result.v = self.v
        result.ro = self.ro
        return result


class PmacFeedrateOverride(PmacVariable):
    def __init__(self, cs, v=0):
        PmacVariable.__init__(self, f"&{cs}%", 0, v)
        self.cs = cs

    def dump(self, typ=0):
        if typ == 1:
            result = f"{self.valStr()}"
        else:
            result = f"&{self.cs}%{self.valStr()}\n"
        return result

    def copyFrom(self):
        result = PmacFeedrateOverride(self.cs)
        result.v = self.v
        result.ro = self.ro
        return result


class PmacMsIVariable(PmacVariable):
    def __init__(self, ms, n, v="", ro=False):
        PmacVariable.__init__(self, f"ms{ms}i", n, v)
        self.ms = ms
        self.ro = ro

    def dump(self, typ=0):
        if typ == 1:
            result = f"{self.valStr()}"
        else:
            result = ""
            if self.ro:
                result += ";"
            result += f"ms{self.ms},i{self.n}={self.valStr()}\n"
        return result

    def copyFrom(self):
        result = PmacMsIVariable(self.ms, self.n)
        result.v = self.v
        result.ro = self.ro
        return result
