def hex_to_list(hex):
    if isinstance(hex, str):
        hex.strip().upper()
        chars = "0123456789ABCDEF"
        charlen = len(chars)
        return (chars.find(hex[0])*charlen+chars.find(hex[1]), chars.find(hex[2])*charlen+chars.find(hex[3]), chars.find(hex[4])*charlen+chars.find(hex[5]))
