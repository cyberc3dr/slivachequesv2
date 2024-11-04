import sqlite3
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import bots
import container

con = sqlite3.connect('cheques.db')

con.execute("CREATE TABLE IF NOT EXISTS cheques (bot VARCHAR, cheque VARCHAR)")
con.execute("CREATE TABLE IF NOT EXISTS blacklist (username VARCHAR)")
con.commit()


def add_to_blacklist(username: str):
    con.execute("INSERT INTO blacklist VALUES (?)", [username])
    con.commit()


def remove_from_blacklist(username: str):
    con.execute("DELETE FROM blacklist WHERE username = ?", [username])
    con.commit()


def is_blacklisted(username: str) -> bool:
    if con.execute("SELECT * FROM blacklist WHERE username = ?", [username]).fetchall():
        return True


def get_blacklist():
    return [list(i)[0] for i in con.execute("SELECT * FROM blacklist").fetchall()]


def is_duplicated(bot: str, cheque: str) -> bool:
    if not con.execute("SELECT * FROM cheques WHERE bot = ? AND cheque = ?", [bot, cheque]).fetchall():
        con.execute("INSERT INTO cheques VALUES (?, ?)", [bot, cheque])
        con.commit()
        return False
    else:
        return True


def count_cheques(bot: str) -> int:
    return len(con.execute("SELECT * FROM cheques WHERE bot = ?", [bot]).fetchall())


def clean_db():
    con.execute("DELETE FROM cheques")
    con.commit()


sched = AsyncIOScheduler()
sched.start()


@sched.scheduled_job(CronTrigger(hour=0))
async def print_stats():
    message = "**Сводка по количеству чеков:**\n\n"

    for bot in bots.registry.bots:
        username = bot.usernames[0]

        cheque_count = count_cheques(username)

        message += f"**{bot.icon} {bot.display_name}:** {cheque_count}\n\n"

    message += "#Сводка"

    await container.bot.send_message(entity=container.container_id, message=message)


@sched.scheduled_job(CronTrigger(day_of_week='sun'))
async def update_task():
    clean_db()
    await container.bot.send_message(entity=container.container_id, message="Таблица была очищена")
