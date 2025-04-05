"""
Module dedicated to how great Emily is
"""

from random import choice


REASONS_EMILY_IS_GREAT = [
    "She is super sharp. You can't get anything past her because she WILL notice",
    "She is so pretty, with the eyes, the freckles, the hair, the smile, the cute outfits; the list goes on",
    "She can wrangle nearly any animal without even looking like she's hurting them",
    "She is raw and real, I know she's not hiding anything from me",
    "She takes such good care of the kids, even the bad ones",
    "She is the best hang, to the point I enjoy doing nothing and being bored together",
    "She understands the niche parts of cooking that really matter, like flavour combinations and subtle textures that most people don't think about",
    "She makes me feel like I'm enough as it is",
    "She is a good engineer, great at solving problems",
]


def why_is_emily_great() -> str:
    """
    Get a reason why Emily is great at random

    Returns:
        A reason why Emily is great
    """
    return choice(REASONS_EMILY_IS_GREAT)
