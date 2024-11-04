import re
from abc import ABC, abstractmethod
from numbers import Number
from urllib.parse import urlparse, parse_qsl

from telethon import TelegramClient, Button
from telethon.extensions import markdown
from telethon.tl.custom import InlineResults, InlineResult
from telethon.tl.types import Message, PeerUser, MessageEntityTextUrl

import database


def parse_url(s: str):
    s = s.strip("/")
    if s.startswith("://"):
        return urlparse(s[1:])
    elif not re.match("[a-zA-Z]+://.*", s):
        return urlparse("//" + s)
    return urlparse(s)


class Bot(ABC):

    def __init__(self, id: Number, usernames: list[str], display_name: str, icon: str):
        self.id = id
        self.usernames = usernames
        self.display_name = display_name
        self.icon = icon

    def is_duplicated(self, cheque: str) -> bool:
        return database.is_duplicated(self.usernames[0], cheque)

    @abstractmethod
    def is_valid(self, cheque: str, raw_message: str) -> bool:
        pass

    # @abstractmethod
    # async def activate(self, client: TelegramClient, cheque: str):
    #     pass

    @abstractmethod
    async def send_cheque(self, client: TelegramClient, bot: TelegramClient, target: int, cheque: str,
                          original_message: Message, source: str, name: str):
        pass

    @property
    def supports_inline(self) -> bool:
        raise NotImplementedError


class RocketBot(Bot):
    supports_inline = True

    _rocket_valid: list = [
        "mc", "mci", "t"
    ]

    def __init__(self):
        super().__init__(5014831088, ["xrocket", "tonrocketbot"], "xRocket", "🚀")

    def is_valid(self, cheque: str, raw_message: str) -> bool:
        if "_" in cheque:
            split = cheque.split("_")
            cheque_type = split[0].lower()
            cheque_hash = split[1]
            if len(cheque_hash) == 15 and cheque_type in self._rocket_valid:
                return True
            return False

    async def send_cheque(self, client: TelegramClient, bot: TelegramClient, target: int, cheque: str,
                          original_message: Message, source: str, name: str):
        results: InlineResults = await client.inline_query(self.usernames[0], cheque)
        if len(results) == 1:
            inline: InlineResult = results[0]
            cheque_type = cheque.split("_")[0].lower()
            if cheque_type in self._rocket_valid:
                url = inline.message.reply_markup.rows[0].buttons[0].url
                if "start" in url:
                    url = dict(parse_qsl(parse_url(url).query))
                    new_cheque: str = url["start"]
                    if new_cheque == cheque or (
                            self.is_valid(new_cheque, inline.message.message) and not self.is_duplicated(new_cheque)):
                        if cheque_type.startswith("mc"):
                            description: str = inline.description
                            if description is not None:
                                cheque_info = description.split(' · ')
                                one_activation = cheque_info[0].split(': ')[1]
                                sum = cheque_info[1]
                                activated = cheque_info[2]

                                rocket = False
                                referral = None
                                if len(cheque_info) > 3 and cheque_info[3].strip().endswith("%"):
                                    referral = cheque_info[3].strip()
                                    if referral != "0%":
                                        referral_sum = float(one_activation.split(" ")[0]) * (float(
                                            referral.removesuffix('%')) / 100)
                                        referral = f"{referral_sum} {one_activation.split(' ')[1]} ({referral})"
                                    else:
                                        referral = None
                                    rocket = True

                                premium = False
                                activate_button = inline.message.reply_markup.rows[0].buttons[0]
                                activate_text: str = activate_button.text
                                if "🌟" in activate_text:
                                    activate_text = activate_text.replace('🌟', '').strip()
                                    premium = True
                                activate_text = f"{self.icon} {activate_text}"

                                bot_message: str = markdown.unparse(inline.message.message.
                                                                    replace('[', ' ').
                                                                    replace(']', ' '), inline.message.entities).split(
                                    "\n\n")

                                header = bot_message[0].strip()

                                picture = None
                                if header.startswith('[\u200d]'):
                                    picture = inline.message.entities[0].url

                                requires_password = False
                                if header.endswith("с паролем"):
                                    requires_password = True

                                last = len(bot_message) - 1

                                cheque_description = None
                                if last > 1 and bot_message[2].startswith("💬"):
                                    cheque_description = "\n\n".join(bot_message[2:]) if last != 2 else bot_message[2]

                                info = [
                                    f"{f'**🚀 Rocket-чек ({cheque_type})**' if rocket else '**💵 Мульти-чек**'}{' (🌟)' if premium else ''}{' (🔐)' if requires_password else ''} на **{sum}**",
                                    "",
                                    f"Один чек: **{one_activation}**",
                                    f"Активации: **{activated}**"]

                                if rocket and referral:
                                    info.append(f"Реферальная награда: **{referral}**")

                                if cheque_description is not None:
                                    info.append("")
                                    info.append(cheque_description)

                                info.append("")
                                info.append(
                                    f"#TonRocket #{'Rocket' if rocket else 'Мульти'} ${sum.split(' ')[-1].upper()}{' #Premium' if premium else ' #БезPremium'}{' #Реф' if referral else ' #БезРефа'}{' #Пароль' if requires_password else ' #БезПароля'}")

                                buttons = [[Button.url(activate_text, activate_button.url)],
                                           [Button.url(f"🔎 {name}", source)]]

                                if picture:
                                    print(f"sent xrocket cheque with picture {new_cheque}")

                                    await bot.send_file(entity=target, caption="\n".join(info),
                                                        buttons=buttons,
                                                        link_preview=False, file=picture, force_document=False)
                                else:
                                    print(f"sent xrocket cheque {new_cheque}")

                                    await bot.send_message(entity=target, message="\n".join(info),
                                                           buttons=buttons,
                                                           link_preview=False)
                        elif cheque_type == "t":
                            title = inline.title
                            description: str = inline.description.strip()
                            if description is not None and title is not None:
                                sum = " ".join(title.split(" ")[2:])

                                bot_message: str = markdown.unparse(inline.message.message,
                                                                    inline.message.entities).split(
                                    "\n\n")

                                cheque_description = None
                                if len(bot_message) > 1 and bot_message[1].startswith("💬"):
                                    cheque_description = "\n\n".join(bot_message[1:])

                                header = inline.message.message.split("\n\n")[0].strip()

                                username = None
                                if not header.endswith(sum):
                                    # username = header.split(" ")[-1]
                                    return

                                info = [
                                    f"**💸 Чек** на **{sum}**{f' для **{username}**' if username is not None else ''}"]

                                if cheque_description is not None:
                                    info.append("")
                                    info.append(cheque_description)

                                info.append("")
                                info.append(f"#TonRocket #Персональный ${sum.split(' ')[1]}")

                                activate_button = inline.message.reply_markup.rows[0].buttons[0]

                                print(f"sent xrocket personal {cheque}")

                                await bot.send_message(entity=target, message="\n".join(info),
                                                       buttons=[[Button.url(f"{self.icon} {activate_button.text}",
                                                                            activate_button.url)],
                                                                [Button.url(f"🔎 {name}", source)]],
                                                       link_preview=False)


class CryptoBot(Bot):
    supports_inline = False

    def __init__(self):
        super().__init__(1559501630, ["cryptobot", "send"], "CryptoBot", "💎")

    def is_valid(self, cheque: str, raw_message: str) -> bool:
        if cheque.startswith("CQ") and len(cheque) == 12:
            return True
        elif cheque.startswith("G") and len(cheque) == 13:
            return True

    async def send_cheque(self, client: TelegramClient, bot: TelegramClient, target: int, cheque: str,
                          original_message: Message, source: str, name: str):
        if original_message.via_bot_id == self.id:
            md_message: list[str] = markdown.unparse(original_message.message, original_message.entities).split("\n\n")
            str_message: list[str] = original_message.message.split("\n\n")

            # Работа по заголовку
            header = re.sub('\(.*?\)', "", str_message[0].strip().removeprefix("​").removesuffix(".")).strip()

            gift = header.startswith("💌")

            activate_button = original_message.reply_markup.rows[0].buttons[0]

            if not gift:
                if "для" in header or "given to" in header:
                    return

                multi = "мульти" in header.lower() or "multi-use" in header.lower()

                sum = " ".join(header.split(" ")[-2:])

                currency = header.split(" ")[-1]

                # Картинка, если имеется
                picture = None
                if md_message[0].startswith("​"):
                    picture = original_message.entities[0].url

                # Генерируем базовую инфу
                info = [
                    f"**{'💵 Мульти-чек' if multi else '💸 Чек'}** на **{sum}**"
                ]

                # Операции с мультичеком
                if multi:
                    activation_info = re.sub('\(.*?\)', "", str_message[1]).split("\n")

                    one_activation = " ".join(activation_info[0].strip().split(" ")[-2:])
                    activation_count = activation_info[1].split(" ")[-1]

                    info.append("")
                    info.append(f"Один чек: **{one_activation}**")
                    info.append(f"Активации: **{activation_count}**")

                first = 2 if multi else 1

                if len(md_message) > first and md_message[first].strip().startswith("💬"):
                    cheque_description = "\n\n".join(
                        md_message[first:]) if len(md_message) - 1 != first else md_message[first]

                    info.append("")
                    info.append(cheque_description)

                info.append("")
                info.append(f"#CryptoBot #{'Мульти' if multi else 'Чек'} ${currency} #Инлайн")

                if picture is not None:
                    print(f"sent cryptobot cheque with picture {cheque}")

                    await bot.send_file(entity=target, caption="\n".join(info),
                                        buttons=[
                                            [Button.url(f"{self.icon} {activate_button.text}", activate_button.url)],
                                            [Button.url(f"🔎 {name}", source)]],
                                        link_preview=False, file=picture, force_document=False)
                else:
                    print(f"sent cryptobot cheque {cheque}")

                    await bot.send_message(entity=target, message="\n".join(info),
                                           buttons=[
                                               [Button.url(f"{self.icon} {activate_button.text}", activate_button.url)],
                                               [Button.url(f"🔎 {name}", source)]],
                                           link_preview=False)
            else:
                if not ("для тебя" in header or "for you" in header):
                    return

                info = [
                    f"**💌 Валентинка** ",
                    f"",
                    f"(может забрать любой)",
                    f"",
                    f"#CryptoBot #Валентинка"]

                print(f"sent cryptobot gift {cheque}")

                await bot.send_message(entity=target, message="\n".join(info),
                                       buttons=[
                                           [Button.url(f"{self.icon} Получить валентинку", activate_button.url)],
                                           [Button.url(f"🔎 {name}", source)]],
                                       link_preview=False)
        elif original_message.fwd_from is not None and isinstance(original_message.fwd_from.from_id,
                                                                  PeerUser) and original_message.fwd_from.from_id.user_id == self.id:
            md_message: list[str] = markdown.unparse(original_message.message, original_message.entities).split("\n\n")
            str_message: list[str] = original_message.message.split("\n\n")

            picture = None
            if md_message[0].startswith("[\u200b]"):
                picture = original_message.entities[0].url

            multi = True if str_message[0].endswith("Мультичек") else False

            sums = str_message[1]

            last = len(md_message) - 3

            one_activation = None
            activation_count = None
            done = None
            if multi:
                split = sums.split("\n")

                sum = split[0].split(": ")[1]
                one_activation = " ".join(split[1].split(": ")[1].split(" ")[1:])

                activations_text = md_message[2].split("\n")
                activation_count = activations_text[0].split(": ")[1]
                done = activations_text[1].split(" ")[1]
            else:
                sum = " ".join(sums.split(": ")[1].split(" ")[1:])

            start = 3 if multi else 2
            cheque_description = None
            if md_message[start].startswith("💬"):
                cheque_description = "\n\n".join(md_message[start:last]) if last != start else md_message[last]

            cq_target = md_message[last]

            is_premium = "Premium" in cq_target
            new = "new users" in cq_target or "новый пользователь" in cq_target
            has_password = "ввода пароля" in cq_target or "password" in cq_target

            username = None
            if not is_premium and not new and (cq_target.startswith("Only") or cq_target.startswith("Только")):
                # username = target.split(" ")[1]
                return

            info = [
                f"{'**💵 Мульти-чек**' if multi else '**💸 Чек**'}{' (🌟)' if is_premium else ''}{' (🔐)' if has_password else ''}{' (🆕)' if new else ''} на {sum}{f' для {username}' if username is not None else ''}"
            ]

            if multi:
                info.append(" ")
                info.append(f"Один чек: **{one_activation}**")
                info.append(f"Активаций: **{done}** / {activation_count}")

            if cheque_description is not None:
                info.append(" ")
                info.append(cheque_description)

            info.append(" ")
            info.append(
                f"#CryptoBot #Forward #{'Мульти' if multi else 'Чек'} ${sum.split(' ')[1]}{' #Premium' if is_premium else ' #БезPremium'}{' #Пароль' if has_password else ' #БезПароля'}{' #ДляНовых' if new else ' #ДляВсех'}")

            if picture is not None:
                print(f"sent cryptobot forward with picture {cheque}")

                await bot.send_file(entity=target, caption="\n".join(info),
                                    buttons=[[Button.url(f"{self.icon} Получить {one_activation if multi else sum}",
                                                         f"https://t.me/CryptoBot?start={cheque}")],
                                             [Button.url(f"🔎 {name}", source)]],
                                    link_preview=False, file=picture, force_document=False)
            else:
                print(f"sent cryptobot forward {cheque}")

                await bot.send_message(entity=target, message="\n".join(info),
                                       buttons=[[Button.url(f"{self.icon} Получить {one_activation if multi else sum}",
                                                            f"https://t.me/CryptoBot?start={cheque}")],
                                                [Button.url(f"🔎 {name}", source)]],
                                       link_preview=False)
        else:
            str_message: list[str] = original_message.message.split("\n\n")

            giveaway = cheque.startswith("G")

            header = re.sub('\(.*?\)', "", str_message[0].strip().removeprefix("​")).strip()

            if giveaway and header.startswith("🎁"):
                rus = "Розыгрыш" in header

                sum = " ".join(header.split(" ")[-2:])
                currency = header.split(" ")[-1]

                count_info = re.sub('[ ]+(?=\s)', '', re.sub('\(.*?\)', "", str_message[1].strip().removesuffix(".")).strip()).split(" ")
                winners = count_info[0] if rus else count_info[13]
                each = " ".join(count_info[-2:] if rus else count_info[-3:-1])

                channels = []

                entities = original_message.entities
                if entities is not None:
                    for entity in entities:
                        if isinstance(entity, MessageEntityTextUrl):
                            url = entity.url

                            if "CryptoBot" not in url:
                                channels.append(url)

                if rus:
                    timings = str_message[3].split(" ")

                    time = " ".join(timings[:5])
                else:
                    time = " ".join(count_info[1:6])

                info = [
                    f"🎁 **Розыгрыш** на **{sum}**",
                    "",
                    f"**Одна победа:** {each}",
                    f"**Победителей:** {winners}",
                    ""
                    f"**Закончится**: {time}",
                    "",
                    "**Нужно подписаться:**"
                ]

                for channel in channels:
                    info.append(channel)

                info.append("")
                info.append(f"#CryptoBot #Розыгрыш #{currency}")

                print(f"sent cryptobot giveaway {cheque}")

                await bot.send_message(entity=target, message="\n".join(info),
                                       buttons=[[Button.url(f"{self.icon} Принять участие",
                                                            f"https://t.me/CryptoBot?start={cheque}")],
                                                [Button.url(f"🔎 {name}", source)]],
                                       link_preview=False)
            else:
                info = [f"{'Розыгрыш' if giveaway else 'Чек'} (информация недоступна)",
                        "",
                        f"#CryptoBot #Ссылка{' #Розыгрыш' if giveaway else ''}"]

                print(f"sent cryptobot unknown {'giveaway' if giveaway else 'cheque'} {cheque}")

                await bot.send_message(entity=target, message="\n".join(info),
                                       buttons=[[Button.url(f"{self.icon} Активировать",
                                                            f"https://t.me/CryptoBot?start={cheque}")],
                                                [Button.url(f"🔎 {name}", source)]],
                                       link_preview=False)


class Wallet(Bot):
    supports_inline = True

    def __init__(self):
        super().__init__(1985737506, ["wallet"], "Wallet", "💵")

    def is_valid(self, cheque: str, raw_message: str) -> bool:
        if cheque.startswith("C-") and len(cheque) == 12:
            return True

    async def send_cheque(self, client: TelegramClient, bot: TelegramClient, target: int, cheque: str,
                          original_message: Message, source: str, name: str):
        results: InlineResults = await client.inline_query(self.usernames[0], cheque)
        if len(results) == 1:
            inline: InlineResult = results[0]
            title: str = inline.title
            if title is not None:
                multi = title.endswith("мультичек")

                bot_message: str = markdown.unparse(inline.message.message, inline.message.entities).split("\n\n")

                if multi:
                    sum: str = " ".join(bot_message[0].split(" ")[3:])
                    currency = sum.split(" ≈ ")[0].split(" ")[1].upper()

                    activations = bot_message[1].split("\n")
                    one_activation = activations[0].split(": ")[1]
                    activation_count = activations[1].split(": ")[1]

                    if float(one_activation.split(" ")[0]) < 0.0002:
                        return

                    info = [f"**💵 Мультичек** на **{sum}**",
                            "",
                            f"Один чек: **{one_activation}**",
                            f"Активаций: **{activation_count}**"]
                else:
                    sum: str = " ".join(bot_message[0].split(" ")[3:])

                    if float(sum.split(" ")[0]) < 0.0002:
                        return

                    currency = sum.split(" ≈ ")[0].split(" ")[1]

                    info = [f"**💸 Чек** на **{sum}**"]

                info.append("")
                info.append(f"#Wallet{' #Мульти' if multi else ' #Чек'} ${currency}")

                activate_button = inline.message.reply_markup.rows[0].buttons[0]

                print(f"send wallet cheque {cheque}")

                await bot.send_message(entity=target, message="\n".join(info),
                                       buttons=[[Button.url(f"{self.icon} {activate_button.text}",
                                                            activate_button.url)],
                                                [Button.url(f"🔎 {name}", source)]],
                                       link_preview=False)


class BotRegistry:
    bots: list[Bot] = [
        RocketBot(),
        CryptoBot(),
        Wallet(),
        # JTonBot(),
        # XJetSwap(),
        # Jetton()
    ]

    def get_by_id(self, id: Number):
        if id is not None:
            for bot in self.bots:
                if bot.id == id:
                    return bot
        return None

    def get_by_username(self, username: str):
        if username is not None:
            for bot in self.bots:
                if username.lower() in bot.usernames:
                    return bot
        return None


registry = BotRegistry()
