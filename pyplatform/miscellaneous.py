def hex_to_tuple(hex):
    if isinstance(hex, str):
        hex.strip().upper()
        chars = "0123456789ABCDEF"
        return (chars.find(hex[0])*16+chars.find(hex[1]), chars.find(hex[2])*16+chars.find(hex[3]), chars.find(hex[4])*16+chars.find(hex[5]))

def tuple_to_hex(obj):
    if isinstance(obj, tuple):
        t = obj
        chars = "0123456789ABCDEF"
        chars_to_return = ""
        for i in range(3):
            scc = int(t[i]/16)
            wcc = t[i] - (scc * 16)
            chars_to_return += chars[scc] + chars[wcc]
        return chars_to_return
