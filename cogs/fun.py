import discord
from discord.ext import commands

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="doggo")
    async def dog(self, ctx):
        m = await ctx.send("doggo")
        self.bot.get_cog("Uninvoke").create_unload(ctx.message, lambda: m.delete())

    @commands.is_owner()
    @commands.command(name="wb")
    async def send_webhook(self, ctx, name, av, *, content):
        await ctx.message.delete()
        webhook = await self.bot.get_webhook_for_channel(ctx.channel)
        webhook: discord.Webhook
        if webhook is not None:
            await webhook.send(content, username=name, avatar_url=av if av.startswith("http") else None)


def setup(bot):
    bot.add_cog(Fun(bot))
