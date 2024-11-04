import re
from urllib.parse import parse_qsl

from telethon import TelegramClient, events
from telethon.tl.custom import InlineResults, InlineResult
from telethon.tl.types import Message, MessageEntityTextUrl, KeyboardButtonUrl, ReplyInlineMarkup, \
    ReplyKeyboardMarkup, User, Channel, Chat, PeerUser

import bots
import database

api_id = 111111
api_hash = 'REDACTED'

main_client = TelegramClient(session='anon',
                             api_id=api_id,
                             api_hash=api_hash,
                             device_model="SlivaHosting",
                             app_version='1.0',
                             system_version="4.16.30-vxCUSTOM",
                             lang_code='ru')

bot = TelegramClient(session='bot',
                     api_id=api_id,
                     api_hash=api_hash)

container_id = 1702836252
owner_id = 834854911
agchat_id = 1965206713
agchat_id_bot = -1001965206713

url_regex = r"([https?:\/\/]?(?:www\.|(?!www))[a-zA-Z0-9]+\.[a-zA-Z0-9]+[^\s]{1,}|www\.[a-zA-Z0-9]+\.[a-zA-Z0-9]+[" \
            r"^\s]{1,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[a-zA-Z0-9]+[^\s]{1,}|www\.[a-zA-Z0-9]+\.[" \
            r"a-zA-Z0-9]+[^\s]{1,})"


@main_client.on(events.NewMessage(incoming=True))
async def on_message(event: events.NewMessage.Event):
    message: Message = event.message
    entity = await main_client.get_entity(message.peer_id)
    group_id = entity.username if entity.username is not None else f"c/{entity.id}"

    if database.is_blacklisted(group_id.lower()): return

    name = None
    if isinstance(entity, User):
        name = f"{entity.first_name} {entity.last_name}"
    elif isinstance(entity, Channel) or isinstance(entity, Chat):
        name = entity.title

    if group_id != f"c/{container_id}":
        message_id = message.id

        src_url = f"https://t.me/{group_id}/{message_id}"

        cbot = bots.registry.get_by_id(message.via_bot_id)

        if cbot is not None and message.reply_markup is not None:
            btn = message.reply_markup.rows[0].buttons[0]
            if isinstance(btn, KeyboardButtonUrl):
                url = btn.url

                if "start" in url:
                    try:
                        url = dict(parse_qsl(bots.parse_url(url).query))

                        if "start" in url:
                            cheque: str = url["start"]

                            if cheque.startswith("mci") and group_id == f"c/{agchat_id}":
                                results: InlineResults = await main_client.inline_query("xrocket", cheque)

                                if len(results) == 1:
                                    inline: InlineResult = results[0]

                                    new_url = inline.message.reply_markup.rows[0].buttons[0].url
                                    if "start" in new_url:
                                        new_url = dict(parse_qsl(bots.parse_url(new_url).query))
                                        new_cheque: str = new_url["start"]

                                        if new_cheque != cheque:
                                            await bot.delete_messages(entity=agchat_id_bot, message_ids=[message_id])

                            if not cbot.is_duplicated(cheque) and cbot.is_valid(cheque, None):
                                await cbot.send_cheque(main_client, bot, container_id, cheque, message, src_url, name)
                        elif "startapp" in url:
                            cheque: str = url["startapp"].split("-")[1]
                            if not cbot.is_duplicated(cheque) and cbot.is_valid(cheque, None):
                                await cbot.send_cheque(main_client, bot, container_id, cheque, message, src_url, name)
                    except:
                        ...

        else:
            raw_message = message.message
            urls = re.findall(url_regex, raw_message)
            entities = message.entities
            if entities is not None:
                for i in entities:
                    if isinstance(i, MessageEntityTextUrl):
                        _url = i.url
                        if re.match(url_regex, _url) is not None:
                            urls.append(_url)

            reply_markup = message.reply_markup
            if reply_markup is not None and (
                    isinstance(reply_markup, ReplyKeyboardMarkup) or isinstance(reply_markup, ReplyInlineMarkup)):
                for row in reply_markup.rows:
                    for button in row.buttons:
                        if isinstance(button, KeyboardButtonUrl):
                            _url = button.url
                            if re.match(url_regex, _url) is not None:
                                urls.append(_url)

            urls = [*set(urls)]

            for raw_url in urls:
                url = bots.parse_url(raw_url)

                address = url.netloc.lower()

                if address == "t.me":
                    q = dict(parse_qsl(url.query))

                    cbot = bots.registry.get_by_username(url.path.removeprefix("/").split("/")[0])

                    if cbot is not None:
                        if "start" in q:
                            cheque: str = q["start"]

                            if cheque.startswith("mci") and group_id == f"c/{agchat_id}":
                                results: InlineResults = await main_client.inline_query("xrocket", cheque)

                                if len(results) == 1:
                                    inline: InlineResult = results[0]

                                    new_url = inline.message.reply_markup.rows[0].buttons[0].url
                                    if "start" in new_url:
                                        new_url = dict(parse_qsl(bots.parse_url(new_url).query))
                                        new_cheque: str = new_url["start"]

                                        if new_cheque != cheque:
                                            await bot.delete_messages(entity=agchat_id_bot, message_ids=[message_id])

                            if not cbot.is_duplicated(cheque) and cbot.is_valid(cheque, raw_message):
                                await cbot.send_cheque(main_client, bot, container_id, cheque, message, src_url, name)
                        elif "startapp" in q:
                            cheque: str = q["startapp"].split("-")[1]
                            if not cbot.is_duplicated(cheque) and cbot.is_valid(cheque, raw_message):
                                await cbot.send_cheque(main_client, bot, container_id, cheque, message, src_url, name)


@bot.on(events.NewMessage(incoming=True))
async def on_bot_message(event: events.NewMessage.Event):
    message = event.message

    source = message.from_id

    if isinstance(source, PeerUser) and source.user_id == owner_id:
        text: str = message.message

        if text.startswith("/"):
            split = text[1:].split(' ')

            cmd: str = split[0].lower()

            if cmd == "help":
                await event.reply("**Команды: **\n\n/cleardb\n/stats\n/blacklist")
            if cmd == "cleardb":
                await database.clean_db()
            elif cmd == "stats":
                await database.print_stats()
            elif cmd == "blacklist":
                if len(split) > 1:
                    subcommand = split[1].lower()

                    if subcommand == "add":
                        if len(split) > 2:
                            username = split[2].lower()

                            database.add_to_blacklist(username)

                            await event.reply(f"**{username}** добавлен в черный список.")
                    elif subcommand == "remove":
                        if len(split) > 2:
                            username = split[2].lower()

                            database.remove_from_blacklist(username)

                            await event.reply(f"**{username}** удален из черного списка.")
                    elif subcommand == "list":
                        await event.reply("**Черный список:**\n\n" + "\n".join(database.get_blacklist()))

                else:
                    await event.reply("Используй /blacklist <add/remove/list> ...")




def start():
    main_client.start()
    bot.start()

    bot.loop.run_until_complete(bot.send_message(entity=container_id, message="Container started"))

    main_client.loop.run_forever()
    bot.loop.run_forever()
