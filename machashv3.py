import uuid
import hashlib

def get_mac_address():
    mac_int = uuid.getnode()
    mac_str = ':'.join(f'{(mac_int >> ele) & 0xff:02x}' for ele in range(40, -1, -8))
    return mac_str

def hash_mac_to_digits(mac):
    # SHA-256 hash → bytes
    digest = hashlib.sha256(mac.encode()).digest()

    # Convert bytes to a large integer, then to digit string
    digit_str = str(int.from_bytes(digest, byteorder="big"))

    return digit_str

def format_digits_phone_style(digit_str):
    # Need 5 groups * 4 digits = 20 digits
    # If digit string is shorter (unlikely), pad; if longer, slice
    needed = 20
    if len(digit_str) < needed:
        digit_str = digit_str.ljust(needed, "0")
    else:
        digit_str = digit_str[:needed]

    # Break into 5 groups of 4 digits
    groups = [digit_str[i:i+4] for i in range(0, 20, 4)]

    # First group is forced to "1337"
    final_groups = ["1337"] + groups

    return "-".join(final_groups)

if __name__ == "__main__":
    mac = get_mac_address()
    digit_string = hash_mac_to_digits(mac)
    formatted = format_digits_phone_style(digit_string)

    print(f"Formatted (numbers-only): {formatted}")

