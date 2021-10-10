import asyncio
import datetime
import inspect
import json
import threading
import time
import typing

import aiohttp
import discord
import requests
from discord.ext import commands

button_functions = []

parameter_types = {int: 4, bool: 4, discord.member.Member: 6, discord.TextChannel: 7, discord.Role: 8}

intent_enabled = False


def _create_info(command, choices):
    description = command.description or command.help
    if description == "":
        description = "No description provided"
    options = []
    command_choices = None
    try:
        command_choices = choices[command.name]
    except KeyError:
        command_choices = []
    inspection = inspect.signature(command.callback)
    for k, v in inspection.parameters.items():
        if k == "ctx" or k == "self":
            continue
        required = True
        t = 3
        annotation = v.annotation
        if v.default is not inspect._empty:
            required = False
        for parameter_type, discord_value in parameter_types.items():
            if annotation is parameter_type:
                t = discord_value

        options.append({
            "name": k,
            "description": k,
            "type": t,
            "required": required,
            "choices": command_choices,
            "kind": v.kind
        })
    return {
        "name": command.name,
        "description": description,
        "options": options
    }


async def _get(url, json_dict=None, headers=None):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, json=json_dict, headers=headers) as response:
            try:
                return json.loads(await response.text())
            except json.decoder.JSONDecodeError:
                return await response.text()


async def _post(url, json_dict=None, headers=None):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=json_dict, headers=headers) as response:
            try:
                return json.loads(await response.text())
            except json.decoder.JSONDecodeError:
                return await response.text()


async def _patch(url, json_dict=None, headers=None):
    async with aiohttp.ClientSession() as session:
        async with session.patch(url, json=json_dict, headers=headers) as response:
            try:
                return json.loads(await response.text())
            except json.decoder.JSONDecodeError:
                return await response.text()


async def _delete(url, json_dict=None, headers=None):
    async with aiohttp.ClientSession() as session:
        async with session.delete(url, json=json_dict, headers=headers) as response:
            try:
                return json.loads(await response.text())
            except json.decoder.JSONDecodeError:
                return await response.text()


def _get_headers(client):
    return {"Authorization": f"Bot {client.http.token}"}


def _get_sync(url, json_dict=None, headers=None):
    return json.loads(requests.get(url, json=json_dict, headers=headers).text)


def _post_sync(url, json_dict=None, headers=None):
    return json.loads(requests.post(url, json=json_dict, headers=headers).text)


def _patch_sync(url, json_dict=None, headers=None):
    return json.loads(requests.patch(url, json=json_dict, headers=headers).text)


def _delete_sync(url, json_dict=None, headers=None):
    return json.loads(requests.delete(url, json=json_dict, headers=headers).text)


class SlashContext:
    def __init__(self, dictionary, client):
        global intent_enabled
        self.message = SlashMessage(dictionary["d"], dictionary["d"]["token"], client)
        self.guild = client.get_guild(int(dictionary["d"]["guild_id"]))
        self.channel = client.get_channel(int(dictionary["d"]["channel_id"]))
        if intent_enabled:
            self.author = client.get_guild(int(dictionary["d"]["guild_id"])).get_member(
                int(dictionary["d"]["member"]["user"]["id"]))
        if not intent_enabled:
            self.author = Author(dictionary["d"]["member"]["user"])
        self.bot = client
        self.dictionary = dictionary

    async def send(self, message: str = None, *, embed: discord.Embed = None, buttons=[], file: discord.File = None):
        components = [{"type": 1, "components": []}]
        if isinstance(buttons, list):
            if len(buttons) > 0:
                for items in buttons:
                    if isinstance(items, Button):
                        components[0]["components"].append(items.dictionary())
            if len(buttons) == 0:
                components = []
        if not isinstance(buttons, list):
            components = None
            if message == None:
                if embed == None:
                    raise ValueError("You must send either an embed or message")
        if embed != None:
            if not isinstance(embed, list):
                embed = [embed]
            for t, v in enumerate(embed):
                embed[t] = v.to_dict()
        message_dictionary = {
            "content": message,
            "embeds": embed,
            "components": components
        }
        response = await _patch(
            f"https://discord.com/api/v9/webhooks/{self.bot.user.id}/{self.dictionary['d']['token']}/messages/@original",
            headers=_get_headers(self.bot), json_dict=message_dictionary)
        try:
            if response["message"] == "You are being rate limited.":
                await asyncio.sleep(int(response["retry_after"]))
                await _patch(
                    f"https://discord.com/api/v9/webhooks/{self.bot.user.id}/{self.dictionary['d']['token']}/messages/@original",
                    headers=_get_headers(self.bot), json_dict=message_dictionary)
        except KeyError:
            pass
        return SlashMessage(self.dictionary["d"], self.dictionary["d"]["token"], self.bot)


class SlashMessage:
    def __init__(self, discord_dict, token, client):
        global intent_enabled
        self.token = token
        self.id = int(discord_dict["id"])
        self.channel = client.get_channel(int(discord_dict["channel_id"]))
        if intent_enabled:
            self.author = client.get_guild(int(discord_dict["guild_id"])).get_member(
                int(discord_dict["member"]["user"]["id"]))
        if not intent_enabled:
            self.author = Author(discord_dict["member"]["user"])
        self.client = client
        self.attachments = discord_dict.get("attachments")
        self.embeds = discord_dict.get("embeds")
        self.mentions = discord_dict.get("mentions")
        self.pinned = discord_dict.get("pinned")
        self.mention_everyone = discord_dict.get("mention_everyone")
        self.tts = discord_dict.get("tts")
        self.created_at = datetime.datetime.now()
        self.edited_timestamp = discord_dict.get("edited_timestamp")
        self.flags = discord_dict.get("flags")

    async def edit(self, content):
        await _patch(f"https://discord.com/api/v9/webhooks/{self.client.user.id}/{self.token}/messages/@original",
                     headers=_get_headers(self.client), json_dict={"content": content})

    async def delete(self):
        await _delete(f"https://discord.com/api/v9/webhooks/{self.client.user.id}/{self.token}/messages/@original",
                      headers=_get_headers(self.client))


class Author:
    def __init__(self, discord_dict):
        self.username = discord_dict.get("username")
        self.public_flags = discord_dict.get("public_flags")
        self.id = int(discord_dict.get("id"))
        self.discriminator = discord_dict.get("discriminator")
        self.avatar = discord_dict.get("avatar")


class Button:
    def __init__(self, click_function=None, type=2, style=1, label=None, emoji=None, url=None, disabled=False,
                 parameters=None, sent_button=False):
        self.click_function = click_function
        self.type = type
        self.style = style
        self.label = label
        self.emoji = emoji
        if click_function:
            if sent_button:
                self.custom_id = self.click_function
                if callable(self.click_function):
                    self.custom_id = self.custom_id.__name__
            if not sent_button:
                self.custom_id = self.click_function.__name__
                button_functions.append(self.click_function)
        if not click_function:
            self.custom_id = None
        self.url = url
        self.disabled = disabled
        if self.url:
            if self.click_function or style != 5:
                raise ValueError("URL buttons cannot have a click function and must have the BUTTON_LINK style")
        if parameters:
            for k, v in parameters.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise ValueError("All keys and values must be strings")
                self.custom_id = self.custom_id + f" {k}:{v}"

    def dictionary(self):
        return {
            "type": self.type,
            "style": self.style,
            "label": self.label,
            "emoji": self.emoji,
            "custom_id": self.custom_id,
            "url": self.url,
            "disabled": self.disabled
        }


def _add_commands(bot_commands, command_list, choices, hidden, client):
    for x in bot_commands:
        command_list.append(_create_info(x, choices))

    for x in command_list:
        w = _post_sync(f"https://discord.com/api/v9/applications/{client.user.id}/commands", json_dict=x,
                       headers=_get_headers(client))
        try:
            if w["name"] == x["name"]:
                print(f"Synced command {x['name']}")
        except KeyError:
            print(f"Error syncing command {x['name']}: {w}")
        time.sleep(10)

    slash_commands = _get_sync(f"https://discord.com/api/v9/applications/{client.user.id}/commands",
                               headers=_get_headers(client))
    name_list = []
    for x in command_list:
        name_list.append(x["name"])
    for x in slash_commands:
        if x["name"] not in name_list or x["name"] in hidden:
            t = _get_sync(f"https://discord.com/api/v9/applications/{client.user.id}/commands/{x['id']}",
                          headers=_get_headers(client))
            if t == "":
                print(f"Removed command {x['name']}")


async def sync_all_commands(client: typing.Union[
    discord.ext.commands.Bot, discord.ext.commands.AutoShardedBot, discord.Client, discord.AutoShardedClient],
                            case_sensitive=True, loading_message="Loading", send_hidden=False, hidden_commands=[],
                            choices={}, error_function=None):
    global intent_enabled

    commands = []
    for x in client.intents:
        if x[0] == "members":
            if x[1] == True:
                intent_enabled = True

    threading.Thread(target=_add_commands, args=[client.commands, commands, choices, hidden_commands, client],
                     daemon=True).start()

    flags = 64

    if not send_hidden:
        flags = None

    async def on_socket_response(msg):
        if msg["t"] == "INTERACTION_CREATE":

            args = []
            kwargs = {}

            ack = await _post(f"https://discord.com/api/v9/interactions/{msg['d']['id']}/{msg['d']['token']}/callback",
                              headers=_get_headers(client),
                              json_dict={"type": 5, "data": {"content": loading_message, "flags": flags}})

            for x in client.commands:
                try:
                    msg["d"]["data"]["name"]
                except KeyError:
                    for functions in button_functions:
                        info = msg["d"]["data"]["custom_id"].split(" ")
                        message_components = msg["d"]["message"]["components"][0]["components"]
                        component_list = []
                        parameter_dict = {}
                        if info[0] == functions.__name__:
                            if len(info) > 1:
                                for data in info[1:]:
                                    parameter_data = data.split(":")
                                    parameter_dict[parameter_data[0]] = parameter_data[1]
                            for components in message_components:
                                component_list.append(Button(label=components.get("label"), type=components.get("type"),
                                                             style=components.get("style"),
                                                             emoji=components.get("emoji"), url=components.get("url"),
                                                             disabled=components.get("disabled"),
                                                             click_function=components.get("custom_id"),
                                                             sent_button=True))
                            result = await functions(SlashContext(msg, client), component_list, parameter_dict)
                            result_list = []
                            for r in result:
                                result_list.append(r.dictionary())
                            result = result_list
                            if isinstance(result, list):
                                result = {"components": [{"type": 1, "components": result}]}
                                await _patch(
                                    f"https://discord.com/api/v9/webhooks/{client.user.id}/{msg['d']['token']}/messages/{msg['d']['message']['id']}",
                                    headers=_get_headers(client), json_dict=result)
                    return
                if x.name == msg["d"]["data"]["name"]:
                    data = msg["d"]["data"]
                    for m in commands:
                        if m["name"] == data["name"]:
                            context = SlashContext(msg, client)
                            args.append(context)
                            for w in m["options"]:
                                if w["required"]:
                                    if w["type"] == 3:
                                        for n in data["options"]:
                                            if n["name"] == w["name"]:
                                                if w["kind"] is inspect._ParameterKind.KEYWORD_ONLY:
                                                    kwargs[n["name"]] = n["value"]
                                                if not w["kind"] is inspect._ParameterKind.KEYWORD_ONLY:
                                                    args.append(n["value"])

                                    if w["type"] == 4:
                                        for n in data["options"]:
                                            if n["name"] == w["name"]:
                                                args.append(n["value"])

                                    if w["type"] == 6:
                                        for n in data["options"]:
                                            if n["name"] == w["name"]:
                                                args.append(client.get_guild((int(msg["d"]["guild_id"]))).get_member(
                                                    int(n["value"])))
                                    if w["type"] == 7:
                                        for n in data["options"]:
                                            if n["name"] == w["name"]:
                                                args.append(client.get_channel(int(n["value"])))
                                    if w["type"] == 8:
                                        for n in data["options"]:
                                            if n["name"] == w["name"]:
                                                args.append(client.get_guild(int(msg["d"]["guild_id"])).get_role(
                                                    int(n["value"])))

                                if not w["required"]:
                                    try:
                                        data["options"]
                                    except KeyError:
                                        continue
                                    if w["type"] == 3:
                                        for n in data["options"]:
                                            if n["name"] == w["name"]:
                                                kwargs[n["name"]] = n["value"]

                                    if w["type"] == 4:
                                        for n in data["options"]:
                                            if n["name"] == w["name"]:
                                                kwargs[n["name"]] = n["value"]

                                    if w["type"] == 6:
                                        for n in data["options"]:
                                            if n["name"] == w["name"]:
                                                kwargs[n["name"]] = client.get_guild(
                                                    (int(msg["d"]["guild_id"]))).get_member(int(n["value"]))

                                    if w["type"] == 7:
                                        for n in data["options"]:
                                            if n["name"] == w["name"]:
                                                kwargs[n["name"]] = client.get_channel(int(n["value"]))
                                    if w["type"] == 8:
                                        for n in data["options"]:
                                            if n["name"] == w["name"]:
                                                kwargs[n["name"]] = client.get_guild(
                                                    int(msg["d"]["guild_id"])).get_role(int(n["value"]))

                    try:
                        if not case_sensitive:
                            for w in range(len(args)):
                                if not isinstance(args[w], str):
                                    continue
                                args[w] = args[w].lower()
                            for m in kwargs.keys():
                                kwargs[m] = kwargs[m].lower()

                        for m in x.checks:
                            if inspect.iscoroutinefunction(m):
                                await m(SlashContext(msg, client))
                            if not inspect.iscoroutinefunction(m):
                                m(SlashContext(msg, client))

                        await x(*args, **kwargs)

                    except Exception as error:
                        if error_function != None:
                            await error_function(SlashContext(msg, client), error)
                        if error_function == None:
                            await args[0].send(str(error))

    client.add_listener(on_socket_response)


BUTTON_PRIMARY = 1
BUTTON_SECONDARY = 2
BUTTON_SUCCESS = 3
BUTTON_DANGER = 4
BUTTON_LINK = 5
