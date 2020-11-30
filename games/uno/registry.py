import asyncio
import random
from collections import namedtuple
from enum import Enum
import utils


class CardType:
    @staticmethod
    async def other_place_attempt(this, other, game):
        return this.color == other.color or \
               (this.number == other.number and other.number is not None) or other.color is None

    @staticmethod
    def get_user_friendly(this):
        return f"{this.number} {color_to_emoji[this.color]}"

    @staticmethod
    async def place(this, game, attributes):
        return True

    @staticmethod
    async def force_place(this, game):
        return True

    @staticmethod
    async def required_attributes(this):
        return {}


class ChangeColorOnPlaceCardType(CardType):
    @staticmethod
    async def place(this, game, attributes):
        this.color = attributes["color"]
        return True

    @staticmethod
    async def force_place(this, game):
        this.color = Color.YELLOW

    @staticmethod
    def get_user_friendly(this):
        if this.color is None:
            return f"{this.number if this.number is not None else 'Color change'} ⬛"
        else:
            return f"{this.number if this.number is not None else 'Color change'} {color_to_emoji[this.color]}"

    @staticmethod
    async def required_attributes(this):
        return {"color": Color}


class ReverseDirection(CardType):
    @staticmethod
    async def place(this, game, attributes):
        if game.direction == Direction.UP_WARDS:
            game.direction = Direction.DOWN_WARDS
        else:
            game.direction = Direction.UP_WARDS
        return True

    @staticmethod
    async def other_place_attempt(this, other, game):
        return other.cls is ReverseDirection or await CardType.other_place_attempt(this, other, game)

    @staticmethod
    def get_user_friendly(this):
        return f"Reverse Card {color_to_emoji[this.color]}"


class BlockPersonCardType(CardType):
    @staticmethod
    async def place(this, game, attributes):
        game.cycle_round()
        return True

    @staticmethod
    async def other_place_attempt(this, other, game):
        return other.cls is BlockPersonCardType or await CardType.other_place_attempt(this, other, game)

    @staticmethod
    def get_user_friendly(this):
        return f"Block Card {color_to_emoji[this.color]}"


class AdversaryPayCardType(CardType):
    @staticmethod
    async def other_place_attempt(this, other, game):
        if game.cards_to_take > 0:
            return issubclass(other.cls, AdversaryPayCardType) and await CardType.other_place_attempt(this, other, game)
        else:
            return await CardType.other_place_attempt(this, other, game)

    @staticmethod
    async def place(this, game, attributes):
        game.cards_to_take += this.number

    @staticmethod
    async def force_place(this, game):
        await AdversaryPayCardType.place(this, game, {})

    @staticmethod
    def get_user_friendly(this):
        return f"+{this.number} {color_to_emoji[this.color]}"


class AdversaryPayColorOnPlaceCardType(AdversaryPayCardType, ChangeColorOnPlaceCardType):
    @staticmethod
    def get_user_friendly(this):
        if this.color is None:
            return f"+{this.number} ⬛"
        else:
            return f"+{this.number} {color_to_emoji[this.color]}"

    @staticmethod
    async def place(this, game, attributes):
        await AdversaryPayCardType.place(this, game, attributes)
        await ChangeColorOnPlaceCardType.place(this, game, attributes)

    @staticmethod
    async def force_place(this, game):
        await AdversaryPayCardType.force_place(this, game)
        await ChangeColorOnPlaceCardType.force_place(this, game)

    @staticmethod
    async def other_place_attempt(this, other, game):
        return await AdversaryPayCardType.other_place_attempt(this, other, game)


class Color(Enum):
    RED = 1
    YELLOW = 2
    GREEN = 3
    BLUE = 4


class Direction(Enum):
    UP_WARDS = 1
    DOWN_WARDS = 2


color_to_emoji = {
    Color.GREEN: "🟩",
    Color.YELLOW: "🟨",
    Color.RED: "🟥",
    Color.BLUE: "🟦"
}

emoji_to_color = {
    "🟩": Color.GREEN,
    "🟨": Color.YELLOW,
    "🟥": Color.RED,
    "🟦": Color.BLUE
}


class CardInstance:
    def __init__(self, cls, color, number):
        self.number = number
        self.color = color
        self.cls = cls

    def __getattr__(self, item):
        def _(*args, **kwargs):
            return getattr(self.cls, item)(self, *args, **kwargs)

        return _


def generate_deck():
    deck = []

    for c in range(1, 5):
        for i in range(1, 10):
            deck.append(CardInstance(CardType, Color(c), i))
            deck.append(CardInstance(CardType, Color(c), i))

        deck.append(CardInstance(CardType, Color(c), 0))

        deck.append(CardInstance(BlockPersonCardType, Color(c), None))
        deck.append(CardInstance(BlockPersonCardType, Color(c), None))

        deck.append(CardInstance(ReverseDirection, Color(c), None))
        deck.append(CardInstance(ReverseDirection, Color(c), None))

        deck.append(CardInstance(AdversaryPayCardType, Color(c), 2))
        deck.append(CardInstance(AdversaryPayCardType, Color(c), 2))

        deck.append(CardInstance(ChangeColorOnPlaceCardType, None, None))

        deck.append(CardInstance(AdversaryPayColorOnPlaceCardType, None, 4))

    random.shuffle(deck)
    return deck


def setup():
    return [CardType, ChangeColorOnPlaceCardType, BlockPersonCardType,
            AdversaryPayCardType, AdversaryPayColorOnPlaceCardType]
