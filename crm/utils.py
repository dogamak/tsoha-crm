import string
import random

def generate_random_string(length):
    return ''.join(random.choice(string.ascii_letters) for _ in range(0, length))
