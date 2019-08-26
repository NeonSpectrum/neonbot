import asyncio
import random
import re

import discord
import youtube_dl
from addict import Dict
from discord.ext import commands

from bot import servers
from helpers import log
from helpers.constants import CHOICES_EMOJI, FFMPEG_OPTIONS, YOUTUBE_REGEX
from helpers.database import Database
from helpers.utils import (Embed, PaginationEmbed, format_seconds, plural,
                           raise_and_send)
from helpers.ytdl import YTDLExtractor, get_related_videos, is_link_expired

DEFAULT_CONFIG = Dict({
  "connection": None,
  "config": None,
  "current_queue": 0,
  "queue": [],
  "messages": {
    "last_playing": None,
    "last_finished": None
  }
})


def get_server(guild_id):
  if guild_id not in servers:
    config = Database(guild_id).config
    servers[guild_id] = DEFAULT_CONFIG
    servers[guild_id].config = config.music

  return servers[guild_id]


def update_config(guild_id, key, value):
  database = Database(guild_id)
  database.config.music[key] = value
  database.update_config().refresh_config()
  servers[guild_id].config = database.config.music
  return servers[guild_id].config


def in_voice_channel(ctx):
  if ctx.author.voice != None and ctx.author.voice.channel != None:
    return True
  else:
    raise_and_send(ctx, "You need to be in a voice channel.")


def must_in_argument(choices):
  async def check(ctx):
    command = " ".join(ctx.message.content.split(" ")[1:])
    if command in choices or command == "":
      return True
    await ctx.send(embed=Embed(description=f"Invalid argument. ({' | '.join(choices)})"))
    return False

  return commands.check(check)


class Music(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.send = lambda ctx, msg, **kwargs: ctx.send(embed=Embed(description=msg, **kwargs))

  @commands.command(hidden=True)
  @commands.guild_only()
  @commands.is_owner()
  async def evalmusic(self, ctx, *args):
    server = get_server(ctx.guild.id)
    bot = self.bot
    try:
      if args[0] == "await":
        output = await eval(args[1])
      else:
        output = eval(args[0])
    except Exception as e:
      output = e
    finally:
      output = str(output)

    max_length = 1800

    if len(output) > max_length:
      msg_array = [output[i:i + max_length] for i in range(0, len(output), max_length)]
    else:
      msg_array = [output]

    for i in msg_array:
      await ctx.send(f"```py\n{i}```")

  @commands.command(aliases=["p"])
  @commands.guild_only()
  @commands.check(in_voice_channel)
  async def play(self, ctx, *, args):
    server = get_server(ctx.guild.id)

    if re.search(YOUTUBE_REGEX, args):
      ytdl = YTDLExtractor().extract_info(args)
      ytdl_list = ytdl.get_list()

      if len(ytdl_list) > 1:
        info = ytdl_list
        embed = Embed(description=f"Adding {len(info)} {plural(len(info), 'song', 'songs')} to queue")
      else:
        info = ytdl_list[0]
        embed = Embed(title=f"Adding song to queue #{len(server.queue)+1}", description=ytdl_list[0].title)
    else:
      ytdl = YTDLExtractor({"extract_flat": "in_playlist"}).extract_info(args)
      choice = await self._display_choices(ctx, ytdl.get_choices())
      if choice < 0:
        return
      info = YTDLExtractor().extract_info(ytdl.info[choice].id).get_list()[0]
      embed = Embed(title=f"You have selected #{choice+1}. Adding song to queue #{len(server.queue)+1}",
                    description=info.title)
    await ctx.send(embed=embed, delete_after=5)
    self._add_to_queue(ctx, info)

    if not ctx.guild.voice_client:
      server.connection = await ctx.author.voice.channel.connect()
      log.cmd(ctx, f"Connected to {ctx.author.voice.channel}.")
      self._play(ctx)

  @commands.command(aliases=["next"])
  @commands.guild_only()
  async def skip(self, ctx):
    server = get_server(ctx.guild.id)
    self._next(ctx, skip=True)

  @commands.command()
  @commands.guild_only()
  async def stop(self, ctx):
    server = get_server(ctx.guild.id)
    server.current_queue = 0
    server.connection.stop()
    log.cmd(ctx, "Player stopped.")
    await self.send(ctx, "Player stopped.", delete_after=5)

  @commands.command()
  @commands.guild_only()
  async def pause(self, ctx):
    server = get_server(ctx.guild.id)

    if server.connection.is_paused():
      return

    server.connection.pause()
    log.cmd(ctx, "Player paused.")

    await self.send(ctx, "Player paused.", delete_after=5)

  @commands.command()
  @commands.guild_only()
  async def resume(self, ctx):
    server = get_server(ctx.guild.id)

    if server.connection.is_playing():
      return

    server.connection.resume()
    log.cmd(ctx, "Player resumed.")

    await self.send(ctx, "Player resumed.", delete_after=5)

  @commands.command()
  @commands.guild_only()
  async def reset(self, ctx):
    server = get_server(ctx.guild.id)
    server.connection.stop()
    await server.connection.disconnect()
    del servers[ctx.guild.id]
    await self.send(ctx, "Player reset.", delete_after=5)

  @commands.command()
  @commands.guild_only()
  async def removesong(self, ctx, index: int):
    index -= 1
    server = get_server(ctx.guild.id)
    queue = server.queue[index]

    if index < server.current_queue:
      server.current_queue -= 1
    elif index == server.current_queue:
      self._next(ctx)

    embed = Embed(title=queue.title, url=queue.url)
    embed.set_author(name=f"Removed song #{index+1}", icon_url="https://i.imgur.com/SBMH84I.png")
    embed.set_footer(text=queue.requested, icon_url=queue.requested.avatar_url)

    del queue

    await ctx.send(embed=embed, delete_after=5)

  @commands.command(aliases=["vol"])
  @commands.guild_only()
  async def volume(self, ctx, vol: int):
    server = get_server(ctx.guild.id)
    server.connection.source.volume = vol / 100
    update_config(ctx.guild.id, "volume", vol)
    await self.send(ctx, f"Volume changed to {vol}%", delete_after=5)

  @volume.error
  async def _volume_value(self, ctx, error):
    server = get_server(ctx.guild.id)
    if isinstance(error, commands.MissingRequiredArgument):
      await self.send(ctx, f"Volume is set to {server.config.volume}%.", delete_after=5)

  @commands.command()
  @commands.guild_only()
  @must_in_argument(["off", "single", "all"])
  async def repeat(self, ctx, args):
    server = get_server(ctx.guild.id)
    update_config(ctx.guild.id, "repeat", args)
    await self.send(ctx, f"Repeat changed to {args}.", delete_after=5)

  @repeat.error
  async def _repeat_value(self, ctx, error):
    server = get_server(ctx.guild.id)
    if isinstance(error, commands.MissingRequiredArgument):
      await self.send(ctx, f"Repeat is set to {server.config.repeat}.", delete_after=5)
                      
  @commands.command()
  @commands.guild_only()
  async def autoplay(self, ctx):
    server = get_server(ctx.guild.id)
    config = update_config(ctx.guild.id, "autoplay", not server.config.autoplay)
    await self.send(ctx, f"Autoplay is set to {'enabled' if config.autoplay else 'disabled'}.", delete_after=5)

  @commands.command(aliases=["list"])
  @commands.guild_only()
  async def playlist(self, ctx):
    server = get_server(ctx.guild.id)
    config = server.config
    queue = server.queue
    queue_length = len(queue)
    embeds = []
    temp = []
    duration = 0

    if queue_length == 0:
      return await self.send(ctx, "Empty playlist.", delete_after=5)

    for i, song in enumerate(server.queue):
      description = f"""\
      `{'*' if server.current_queue == i else ''}{i+1}.` [{queue[i].title}]({queue[i].url})
      - - - `{format_seconds(queue[i].duration)}` `{queue[i].requested}`"""
      temp.append(description)
      duration += queue[i].duration

      if (i != 0 and (i + 1) % 10 == 0) or i == len(queue) - 1:
        embeds.append(Embed(description='\n'.join(temp)))
        temp = []

    footer = [
      f"{plural(queue_length, 'song', 'songs')}",
      format_seconds(duration), f"Volume: {config.volume}%", f"Repeat: {config.repeat}",
      f"Shuffle: {'on' if config.shuffle else 'off'}", f"Autoplay: {'on' if config.autoplay else 'off'}"
    ]

    embed = PaginationEmbed(self.bot, array=embeds, authorized_users=[ctx.author.id])
    embed.set_author(name="Player Queue", icon_url="https://i.imgur.com/SBMH84I.png")
    embed.set_footer(text=" | ".join(footer), icon_url=self.bot.user.avatar_url)
    await embed.build(ctx)

  def _play(self, ctx):
    server = get_server(ctx.guild.id)
    current_queue = self._get_current_queue(server)

    if is_link_expired(current_queue.stream):
      current_queue = YTDLExtractor().extract_info(current_queue.id).get_list()[0]

    log.cmd(ctx, f"Now playing {current_queue.title}")

    self.bot.loop.create_task(self._playing_message(ctx, server.current_queue, current_queue))

    song = discord.FFmpegPCMAudio(current_queue.stream, before_options=FFMPEG_OPTIONS)
    source = discord.PCMVolumeTransformer(song, volume=server.config.volume / 100)

    server.connection.play(source, after=lambda error: self._next(ctx, error))

  async def _playing_message(self, ctx, index, current_queue):
    server = get_server(ctx.guild.id)
    config = server.config

    if server.messages.last_playing:
      await server.messages.last_playing.delete()

    footer = [
      str(current_queue.requested),
      format_seconds(current_queue.duration), f"Volume: {config.volume}%", f"Repeat: {config.repeat}",
      f"Shuffle: {'on' if config.shuffle else 'off'}", f"Autoplay: {'on' if config.autoplay else  'off'}"
    ]

    embed = Embed(title=current_queue.title, url=current_queue.url)
    embed.set_author(name=f"Now Playing #{index+1}", icon_url="https://i.imgur.com/SBMH84I.png")
    embed.set_footer(text=" | ".join(footer), icon_url=current_queue.requested.avatar_url)

    server.messages.last_playing = await ctx.send(embed=embed)

  async def _finished_message(self, ctx, index, current_queue):
    server = get_server(ctx.guild.id)
    config = server.config

    if server.messages.last_finished:
      await server.messages.last_finished.delete()

    footer = [
      str(current_queue.requested),
      format_seconds(current_queue.duration), f"Volume: {config.volume}%", f"Repeat: {config.repeat}",
      f"Shuffle: {'on' if config.shuffle else 'off'}", f"Autoplay: {'on' if config.autoplay else  'off'}"
    ]

    embed = Embed(title=current_queue.title, url=current_queue.url)
    embed.set_author(name=f"Finished Playing #{index+1}", icon_url="https://i.imgur.com/SBMH84I.png")
    embed.set_footer(text=" | ".join(footer), icon_url=current_queue.requested.avatar_url)

    server.messages.last_finished = await ctx.send(embed=embed)

  def _next(self, ctx, error=None, skip=False):
    server = get_server(ctx.guild.id)
    current_queue = self._get_current_queue(server)
    config = server.config

    # if error: print(type(error))
    log.cmd(ctx, f"Finished playing {current_queue.title}")
    self.bot.loop.create_task(self._finished_message(ctx, server.current_queue, current_queue))

    server.connection.source.cleanup()

    if skip:
      server.connection.stop()

      if server.current_queue == len(server.queue) - 1:
        if config.repeat == "off" and config.autoplay:
          self._process_autoplay(ctx)
          server.current_queue += 1
        else:
          server.current_queue = 0
      else:
        server.current_queue += 1
      self._play(ctx)
      return

    if self._process_repeat(ctx):
      self._play(ctx)

  def _process_repeat(self, ctx):
    server = get_server(ctx.guild.id)
    config = server.config

    if server.current_queue == len(server.queue) - 1:
      if config.repeat == "all":
        server.current_queue = 0
      elif config.repeat == "off":
        if config.autoplay:
          self._process_autoplay(ctx)
          server.current_queue += 1
        else:
          # reset queue to index 0 and stop playing
          server.current_queue = 0
          return False
    elif config.repeat != "single":
      server.current_queue += 1

    return True

  def _process_autoplay(self, ctx):
    server = get_server(ctx.guild.id)
    current_queue = self._get_current_queue(server)
    print(current_queue.id)
    related_videos = get_related_videos(current_queue.id)
    print(related_videos)
    video_id = random.choice(related_videos).id.videoId
    info = YTDLExtractor().extract_info(video_id).get_list()[0]
    self._add_to_queue(ctx, info)

  async def _display_choices(self, ctx, entries):
    server = get_server(ctx.guild.id)
    embed = Embed(title="Choose 1-5 below.")

    for index, entry in enumerate(entries, start=1):
      embed.add_field(name=f"{index}. {entry['title']}", value=entry.url)

    msg = await ctx.send(embed=embed)

    async def react_to_msg():
      for emoji in CHOICES_EMOJI:
        try:
          await msg.add_reaction(emoji)
        except discord.NotFound:
          return

    asyncio.ensure_future(react_to_msg())

    try:
      reaction, user = await self.bot.wait_for("reaction_add",
                                               timeout=30,
                                               check=lambda reaction, user: reaction.emoji in CHOICES_EMOJI
                                               and ctx.author == user and reaction.message.id == msg.id)
      if reaction.emoji == "🗑":
        raise asyncio.TimeoutError
    except asyncio.TimeoutError:
      await msg.delete()
      return -1
    else:
      await msg.delete()
      index = CHOICES_EMOJI.index(reaction.emoji)
      return index

  def _add_to_queue(self, ctx, data):
    server = get_server(ctx.guild.id)
    if isinstance(data, list):
      for info in data:
        info.requested = ctx.author
      server.queue += data
    else:
      data.requested = ctx.author
      server.queue.append(data)

  def _get_current_queue(self, server):
    return server.queue[server.current_queue]


def setup(bot):
  bot.add_cog(Music(bot))
