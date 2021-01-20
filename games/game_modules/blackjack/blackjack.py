import asyncio
from collections import namedtuple
from functools import partial

import discord

from games.Game import Game, EndGame
from games.GamePlayer import GamePlayer
from games.game_modules.blackjack.cards import generate_deck, CardNumber


class BlackJackGamePlayer(GamePlayer):
    def __init__(self, user, bound_channel):
        super().__init__(user, bound_channel)
        self.hand = []
        self.points = 0


BlackJackPair = namedtuple("BlackJackPair", "hand score owner")


def build_hand(hand):
    return "\t".join(str(i) for i in hand).replace("♠", "<:betterspades:801468794320453732>") \
                                          .replace("♣", "<:betterclubs:801468950101229650>")


def calculate_score(hand):
    ret = 0
    aces = 0
    for card in hand:
        if card.number in (CardNumber.J, CardNumber.K, CardNumber.Q):
            ret += 10
        elif card.number == CardNumber.A:
            ret += 11
            aces += 1
        else:
            ret += card.number.value

    while (ret > 21) and (aces > 0):
        ret -= 10
        aces -= 1

    return ret


class BlackJackGame(Game):
    # this game does not follow the traditional rounded game so it inherits game instead of round game
    game_player_class = BlackJackGamePlayer

    def __init__(self, cog, channel, players):
        super().__init__(cog, channel, players)
        self.round_timeout = None
        self.hitting_player_idx = 0
        self.hitting = []
        self.global_deck = None
        self.dealer_deck = None

    async def decrement(self):
        while self.running:
            await asyncio.sleep(1)
            self.round_timeout -= 1

            if self.round_timeout == 0:
                await self.call_wrap(self.timeout_decision())

    async def on_start(self):
        self.round_timeout = 20
        loop = asyncio.get_running_loop()
        loop.call_soon(partial(asyncio.ensure_future, self.decrement(), loop=loop))
        await self.round_start()

    async def on_message(self, message, player):
        if player.id == self.hitting_player.id:
            op = message.content.lower()
            if op == "hit":
                await self.decision_hit()
            elif op == "stay":
                await self.decision_stay()

    async def round_start(self):
        self.global_deck = generate_deck()
        self.dealer_deck = []

        for player in self.players:
            player.hand.clear()
            for _ in range(2):
                player.hand.append(self.global_deck.pop())

        for _ in range(2):
            self.dealer_deck.append(self.global_deck.pop())

        self.hitting_player_idx = 0
        self.hitting = self.players.copy()

        await self.decision_start()

    async def decision_start(self):
        self.round_timeout = 20
        embed = discord.Embed(title="Your decision", description=f"\"hit\" or \"stay\"?", color=0x444444)

        embed.add_field(name="Your hand", value=f"{build_hand(self.hitting_player.hand)}\n"
                                                f"(score: {calculate_score(self.hitting_player.hand)})",
                        inline=False)

        embed.add_field(name="The dealer's hand", value=f"{str(build_hand(self.dealer_deck[0:1]))}\t??\n"
                                                        f"(score (of visible): "
                                                        f"{calculate_score(self.dealer_deck[0:1])})", inline=False)

        await self.hitting_player.send(embed=embed)
        await self.excluding(self.hitting_player).send(f"{self.hitting_player.mention} is deciding")

    async def decision_hit(self):
        card = self.global_deck.pop()
        await self.hitting_player.send(f"You hit {str(card)}")
        await self.excluding(self.hitting_player).send(f"{self.hitting_player.mention} hits")
        self.hitting_player.hand.append(card)
        score = calculate_score(self.hitting_player.hand)
        if score > 21:
            hand = build_hand(self.hitting_player.hand)
            await self.hitting_player.send(f"You busted\n"
                                           f"{hand} ({score})")
            await self.excluding(self.hitting_player).send(f"{self.hitting_player.mention} busted\n"
                                                           f"{hand} ({score})")

            self.hitting.pop(self.hitting_player_idx)
            self.hitting_player_idx -= 1

        await self.end_decision()

    async def decision_stay(self):
        await self.hitting_player.send("You stay")
        await self.excluding(self.hitting_player).send(f"{self.hitting_player.mention} stays")
        self.hitting.pop(self.hitting_player_idx)
        self.hitting_player_idx -= 1
        await self.end_decision()

    async def end_decision(self):
        if len(self.hitting) == 0:
            await self.round_end()
        else:
            self.hitting_player_idx = (self.hitting_player_idx + len(self.hitting) + 1) % len(self.hitting)
            await self.decision_start()

    def dealer_logic(self):
        should_attempt = False

        for player in self.players:
            score = calculate_score(player.hand)
            if score <= 21:
                should_attempt = True
                break

        if should_attempt:
            while calculate_score(self.dealer_deck) < 15:
                self.dealer_deck.append(self.global_deck.pop())

    async def round_end(self):
        self.dealer_logic()

        hands = []

        for player in self.players:
            hands.append(BlackJackPair(player.hand, calculate_score(player.hand), player))

        hands.append(BlackJackPair(self.dealer_deck, calculate_score(self.dealer_deck), "Dealer"))

        current_score = 0
        winning_player = hands[0].owner
        is_tie = False

        for hand in hands:
            if hand.score > 21:
                continue

            if hand.score > current_score:
                current_score = hand.score
                winning_player = hand.owner
                is_tie = False
            elif hand.score == current_score:
                is_tie = True

        if winning_player is None:
            embed_description = "It seems that no one managed to get it under 22!"
        else:
            if is_tie:
                embed_description = "It seems that a tie occurred!"
            else:
                if isinstance(winning_player, str):
                    winner = winning_player
                else:
                    winner = winning_player.mention
                    winning_player.points += 1

                embed_description = f"It seems that " \
                                    f"{winner} got " \
                                    f"the best out of this one!"

        embed = discord.Embed(title="Game", description=embed_description, color=0xaaaaaa)

        game_winner = None

        for hand in hands:
            if isinstance(hand.owner, str):
                field_name = hand.owner
            else:
                field_name = hand.owner.name

            if hand.score > 21:
                field_name += " 🚫"

            if not isinstance(hand.owner, str):
                field_name += f" ({hand.owner.points} points)"
                if hand.owner.points >= 3:
                    game_winner = hand.owner

            embed.add_field(name=field_name,
                            value=build_hand(hand.hand) + f"({hand.score})",
                            inline=False)

        await self.send(embed=embed)
        self.round_timeout = -1

        if game_winner is not None:
            await self.end_game(EndGame.WIN, game_winner)
        else:
            self.after(10, self.round_start())

    @property
    def hitting_player(self):
        return self.hitting[self.hitting_player_idx]

    async def timeout_decision(self):
        await self.decision_stay()

    async def player_leave(self, player):
        if player == self.hitting_player:
            await self.decision_stay()

        await super(BlackJackGame, self).player_leave(player)

    @classmethod
    def is_playable(cls, size):
        return size > 0
