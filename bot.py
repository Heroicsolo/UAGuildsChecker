import discord
import requests
import json
import functools
import typing
import asyncio
import nest_asyncio
import aiohttp
import time
import sys
import re
import redis
import disnake
from disnake.ext import commands
from math import floor
from datetime import datetime

class CharacterInfoFetcher:
    # Ініціалізуємо клас CharacterInfoFetcher та ставимо кількість запитів за один раз (250 з 300 можливих)
    def __init__(self, members, ignore_rio = False, min_rio = 0, min_ilvl = 0, batch_size=250):
        self.members = members
        self.batch_size = batch_size
        self.all_results = []
        self.ignore_rio = ignore_rio
        self.min_rio = min_rio
        self.min_ilvl = min_ilvl

    async def get_character_info(self, session, name, region, realm, spec_name, class_name, race_name, line_number):
        url = f"https://raider.io/api/v1/characters/profile?region={region}&realm={realm}&name={name}&fields=gear%2Cmythic_plus_scores_by_season%3Acurrent"

        start_time = time.time()
        # HTTP-запит 
        try:
          async with session.get(url) as response:
            data = await response.json(content_type=None)

            end_time = time.time()

            if response.status == 200:
              # Якщо запит успішний, витягуємо інформацію про персонажа з отриманих даних. 
              name = data.get("name", "Unknown")
              item_level_equipped = data["gear"].get("item_level_equipped", 0)
              mplus_score_block = data.get("mythic_plus_scores_by_season", None)
              all_score = 0
              if mplus_score_block != None:
                all_score = data["mythic_plus_scores_by_season"][0]["scores"]["all"]
              response_time = round(end_time - start_time, 2)
              if self.ignore_rio == False:
                return (line_number, f"{name}, ``{spec_name} {class_name}, {race_name}, rio = {all_score}, ilvl = {item_level_equipped}``")
              else:
                return (line_number, f"{name}, ``{spec_name} {class_name}, {race_name}, ilvl = {item_level_equipped}``")
            else:
              # Якщо запит не успішний, повертаємо помилку для зазначеного персонажа. 
              return (line_number, f"Error while parsing char - {name}")
        except json.decoder.JSONDecodeError:
            return (line_number, f"Error while parsing char - {name}")
        
    async def process_profiles_batch(self, session, members, start_line, end_line):
        # Функція для опрацювання профілів персонажів. 
        tasks = []
        for i in range(start_line, end_line):
            member = members[i]
            character_name = member['character']['name']
            region = member['character']['region']
            realm = member['character']['realm']
            spec_name = member['character']['active_spec_name']
            class_name = member['character']['class']
            race_name = member['character']['race']
            task = self.get_character_info(session, character_name, region, realm, spec_name, class_name, race_name, i + 1)
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        return results

    async def process_profiles(self):
        # Функція для обробки всіх профілів персонажів. 
        async with aiohttp.ClientSession() as session:
            total_lines = len(self.members)

            print("Profiles info:")
            for start in range(0, total_lines, self.batch_size):
                end = min(start + self.batch_size, total_lines)
                batch_results = await self.process_profiles_batch(session, self.members, start, end)
                self.all_results.extend(batch_results)
                for line_number, result in batch_results:
                    print(f"{line_number}. {result}")

                if end < total_lines:
                    # Пауза між запитами через обмеження raider io (можна ставити звісно і 60, але краще взяти з запасом 65 секунд). 
                    remaining = total_lines - end
                    for remaining_time in reversed(range(1, 66)):
                        sys.stdout.write(f"\rProcessed {end}/{total_lines} requests. Pausing for {remaining_time:02d} seconds...")
                        sys.stdout.flush()
                        await asyncio.sleep(1)

            sys.stdout.write("\n")

    def filter_top_characters(self):
        # Фільтруємо і сортуємо результати, щоб отримати топ-25 персонажів за Ilvl та RIO. 
      if self.ignore_rio == False:
        top_characters = [result for result in self.all_results if "ilvl = " in result[1] and float(result[1].split("ilvl = ")[1].split("``")[0]) >= self.min_ilvl and float(result[1].split("rio = ")[1].split(",")[0]) >= self.min_rio]
        top_characters = sorted(top_characters, key=lambda x: (float(x[1].split("rio = ")[1].split(",")[0]), float(x[1].split("ilvl = ")[1].split("``")[0])), reverse=True)[:25]
        return top_characters
      else:
        top_characters = [result for result in self.all_results if "ilvl = " in result[1] and float(result[1].split("ilvl = ")[1].split("``")[0]) >= self.min_ilvl]
        top_characters = sorted(top_characters, key=lambda x: (float(x[1].split("ilvl = ")[1].split("``")[0])), reverse=True)[:25]  
        return top_characters

nest_asyncio.apply()

EPHEMERAL_ANSWERS = False
MAX_REQUESTS = 2
MAX_RESULTS = 25
file = open("info.json", "r")
info = json.load(file)
discordToken = info[0]
bot_channels = [info[3],info[4],info[5],info[6]]
officer_channels = [None, 1077559955399381002, 1135632187841069086, 1150558321229692958]
vending_channels = [1131161239955976192, None, None, None]
bot_channel_links = ["<#" + str(bot_channels[0]) + ">","<#" + str(bot_channels[1]) + ">","<#" + str(bot_channels[2]) + ">"]
bnetToken=[info[1],info[2]]
test_guilds = [1017729130407678016, 1075902688790859817, 502062965462269953, 1136709124839723109] #502062965462269953 - MRIYA
raider_io_bot_id = [None, 1101472816068575232, 1142504499630583940, 1174499934888808450]
officer_role_ids = [None, "1076056736730988594", "1140704158735945838", "1205706354837295174"]
moder_role_ids = [None, "1082275372726489140", "968091538053816320", None]
ua_wow_guilds = [('terokkar', 'Arey'), ('terokkar', 'Ukrainian-alliance'), ('terokkar', 'Knaipa-variativ'), ('terokkar', 'Komora'), ('silvermoon', 'MRIYA'), ('silvermoon', 'Ukraine'), ('ravencrest', 'Ababagalamaga'), ('tarren-mill', 'Tauren-milfs'), ('silvermoon', 'BAPTA-KOTIB'), ('tarren-mill', 'Draenei-milfs'), ('twisting-nether', 'MOROK'), ('kazzak', 'Borsch Battalion'), ('silvermoon', 'Mythologeme'), ('tarren-mill', 'Нехай-Щастить'), ('tarren-mill', 'Mayhem-soul'), ('tarren-mill', 'The Toxic Avengers'), ('silvermoon', 'Героям Слава'), ('tarren-mill', 'Nomads TM'), ('terokkar', 'Khorugva'), ('silvermoon', 'BCECBIT')]
ua_wow_guilds_names = ['Ukrainian Alliance', 'Tauren Milfs', 'Synevyr', 'Arey', 'Knaipa Variativ', 'Ukraine', 'Bavovna', 'Komora', 'MRIYA', 'Borsch Battalion', 'Mythologeme', 'Нехай Щастить', 'Mayhem Soul', 'HWG', 'Героям Слава', 'Nomads TM', 'Khorugva', 'BCECBIT']
whitelist_guilds = ['Нехай Щастить', 'Бавовна', 'Козаки', 'Эйситерия', 'СБОРНАЯ УКРАИНЫ', 'Героям Слава', 'Фортеця']
requests_count = 0
users_requests_timestamps = {}

PLAYER_REGEX = "https://raider.io/characters/eu/(.+)/(.+)\?+"

LEVEL_CAP = 70
MIN_ACHIEV_POINTS = 2500
CURR_RAID_ID = 'amirdrassil-the-dreams-hope'
LAST_BOSS_ID = 'fyrakk-the-blazing'
NO_CHARS_FOUND = 'Знайдено 0 персонажів по заданим критеріям'
NO_GUILD_FOUND = 'Гільдію не знайдено. Перевірте правильність написання назви серверу та гільдії.\nНаприклад: !{cmd} terokkar ukrainian-alliance 400'
CMD_HELP_3_ARGS = 'Введіть команду в такому форматі: !{cmd} realm guild-name\nНаприклад: !{cmd} terokkar ukrainian-alliance'
CMD_HELP_4_ARGS = 'Введіть команду в такому форматі: !{cmd} realm guild-name ilvl\nНаприклад: !{cmd} terokkar ukrainian-alliance 400'
ORDER_INFO_MSG_TSHIRT = 'Якщо так, то мершій заповнювати анкету замовлення у наступній Google-формі, щоб отримати цю круту футболку:\nhttps://forms.gle/CWMzWYommRLMKWWMA\nПісля заповнення анкети залиште будь-яку реакцію на це повідомлення, щоб я сповістив менеджера про це замовлення :)\n*Термін відправлення замовлення: до 5 днів*'
ORDER_INFO_MSG_HOODIE = 'Якщо так, то мершій заповнювати анкету замовлення у наступній Google-формі, щоб отримати цей крутий худі:\nhttps://forms.gle/2vEnMQdHRynaJF7Z7\nПісля заповнення анкети залиште будь-яку реакцію на це повідомлення, щоб я сповістив менеджера про це замовлення :)\n*Термін відправлення замовлення: до 5 днів*'
ORDER_INFO_MSG_HOODIE_FML = 'Якщо так, то мершій заповнювати анкету замовлення у наступній Google-формі, щоб отримати цей крутий худі:\nhttps://forms.gle/g51UUQ5fQ1jKkeCN6\nПісля заповнення анкети залиште будь-яку реакцію на це повідомлення, щоб я сповістив менеджера про це замовлення :)\n*Термін відправлення замовлення: до 5 днів*'
ORDER_INFO_MSG_SOCKS = 'Якщо так, то мершій заповнювати анкету замовлення у наступній Google-формі, щоб отримати ці круті шкарпетки:\nhttps://forms.gle/8QrnU4SEFUviHuRu5\nПісля заповнення анкети залиште будь-яку реакцію на це повідомлення, щоб я сповістив менеджера про це замовлення :)*Термін відправлення замовлення: до 5 днів*'
ORDER_SENT_MSG = 'Дякуємо! Я вже передав ваше замовлення нашим адміністраторам, будемо намагатися надіслати його якнайшвидше :) Якщо виникнуть якісь запитання, то звертайтеся до адміністратора Heroicsolo. Гарного вам дня!'
#MERCH_MANAGER_ID = 464165695312101391 #Nikotika
MERCH_MANAGER_ID = 236891312131932161 #Heroicsolo

intents = disnake.Intents.all()
intents.message_content = True
intents.dm_reactions = True
intents.members = True

bot = commands.Bot(command_prefix=disnake.ext.commands.when_mentioned, intents=intents)

pool = redis.ConnectionPool(host='redis-19946.c300.eu-central-1-1.ec2.cloud.redislabs.com', port=19946, db=0, password="LTjgWW2L8iwA1XAoT9M3GEwz7VGVG5Lx")
redis = redis.Redis(connection_pool=pool)

async def no_guild_found_msg(command, inter):
    reply_text = NO_GUILD_FOUND.format(cmd = command)
    await inter.followup.send(reply_text, ephemeral=EPHEMERAL_ANSWERS)

async def cmd_help_msg(command, inter, msgtemplate):
    reply_text = msgtemplate.format(cmd = command)
    await inter.followup.send(reply_text, ephemeral=EPHEMERAL_ANSWERS)

async def do_guild_request(guild, realm):
    return requests.get("https://raider.io/api/v1/guilds/profile?region=eu&realm=" + realm + "&name=" + guild + "&fields=members%2Craid_progression%2Craid_rankings")

async def do_raid_request(difficulty):
    return requests.get("https://raider.io/api/v1/raiding/progression?raid=" + CURR_RAID_ID + "&difficulty=" + difficulty + "&region=eu")

async def proccess_guild_answer(prog_msg, answer, inter, returnmsg, command, args, role):
    if answer.status_code != 200:
        await no_guild_found_msg(command, inter)
        return None
    answer = answer.json()

    min_ilvl = float(args[3])
    min_rio = args[4]

    if min_rio is None:
        sorted_chars = get_sorted_characters(prog_msg, inter, answer['members'], role, min_ilvl)
    else:
        sorted_chars = get_sorted_characters_by_rio(prog_msg, inter, answer['members'], role, float(min_rio), min_ilvl)
    if sorted_chars != None:
        for line_number, result in enumerate(sorted_chars, start=1):
           returnmsg += str(line_number) + ". " + result[1] + "\n"
          
        await inter.followup.send(returnmsg, ephemeral=EPHEMERAL_ANSWERS)
    else:
        await inter.followup.send(NO_CHARS_FOUND, ephemeral=EPHEMERAL_ANSWERS)

async def find_guild_master(answer, message, guild, realm):
    if answer.status_code != 200:
        await no_guild_found_msg('гм', message)
        return None
    answer = answer.json()
    for member in answer['members']:
        if member['rank'] == 0:
            await message.followup.send('ГМ гільдії ' + guild + "-" + realm + ": ``" + member['character']["name"] + "``", ephemeral=EPHEMERAL_ANSWERS)

def get_sorted_characters_by_rio(prog_msg, inter, members, role, rio, ilvl):
  character_info_fetcher = CharacterInfoFetcher(members, False, rio, ilvl)
  asyncio.get_event_loop().run_until_complete(character_info_fetcher.process_profiles())
  return character_info_fetcher.filter_top_characters()
    
def get_sorted_characters(prog_msg, inter, members, role, ilvl):
  character_info_fetcher = CharacterInfoFetcher(members, True, 0, ilvl)
  asyncio.get_event_loop().run_until_complete(character_info_fetcher.process_profiles())
  return character_info_fetcher.filter_top_characters()

@bot.event
async def on_message(message):
  if message.author.id == raider_io_bot_id[test_guilds.index(message.guild.id)] and len(message.embeds) > 0:
    if re.search('[А-Яа-яЁё]+', message.embeds[0].description) != None:
      party_players = re.findall(PLAYER_REGEX, message.embeds[0].description)
      whitelist_players = await get_whitelisted_players(party_players)
      ua_players_list = await get_ua_players(party_players)
      if (len(whitelist_players) >= len(party_players) or len(ua_players_list) == 0):
        return
      thread = await message.create_thread(name=str(datetime.now()), auto_archive_duration = 1440)
      reply_text = "<@&" + officer_role_ids[test_guilds.index(message.guild.id)] + "> <@&" + moder_role_ids[test_guilds.index(message.guild.id)] + "> Імпостер(и) знайдені: "
      await thread.send(reply_text)
      reply_text = ""
      for name, strikes in ua_players_list.items():
        reply_text += name + " (Страйків: " + str(strikes) + ")\n"
      await thread.send(reply_text)

async def is_player_from_ua_guild(name, realm):
  charresponse = requests.get("https://raider.io/api/v1/characters/profile?region=eu&realm=" + realm + "&name=" + name + "&fields=guild")
  if charresponse.status_code == 200:
    charcontent = charresponse.json()
    if charcontent['guild'] != None:
      return ua_wow_guilds_names.count(charcontent['guild']['name']) > 0
    return False

async def is_whitelisted_player(name, realm):
  charresponse = requests.get("https://raider.io/api/v1/characters/profile?region=eu&realm=" + realm + "&name=" + name + "&fields=guild")
  if charresponse.status_code == 200:
    charcontent = charresponse.json()
    if charcontent['guild'] != None:
      return whitelist_guilds.count(charcontent['guild']['name']) > 0 or re.search('[А-Яа-яЁё]+', name) == None or is_player_in_whitelist(name+'-'+realm)
    return re.search('[А-Яа-яЁё]+', name) == None or is_player_in_whitelist(name+'-'+realm)
  else:
    return re.search('[А-Яа-яЁё]+', name) == None or is_player_in_whitelist(name+'-'+realm)

async def get_whitelisted_players(party_players):
  results_list = []
  for x in party_players:
    isWhitelisted = await is_whitelisted_player(x[1], x[0])
    if isWhitelisted:
      results_list.append(x[1]+"-"+x[0])
      print("whitelisted: " + x[1]+"-"+x[0])
  return results_list

async def get_ua_players(party_players):
  results_list = {}
  for x in party_players:
    print(x[1]+"-"+x[0])
    isUAPlayer = await is_player_from_ua_guild(x[1], x[0])
    if isUAPlayer:
      strikes_count = redis.get(x[1]+"-"+x[0])
      if strikes_count == None:
        strikes_count = 0
      else:
        strikes_count = int(strikes_count)
      strikes_count += 1
      redis.set(x[1]+"-"+x[0], strikes_count)
      results_list[x[1]] = strikes_count
  return results_list

@bot.event
async def on_raw_reaction_add(payload):
    channel = await bot.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    user = await bot.fetch_user(payload.user_id)
    emoji = payload.emoji

    if channel.id in vending_channels:
      if emoji.name == '👕':
        if "Футболка" in message.content:
          await user.send("Привіт! Я бачу, ви зацікавились цією футболкою?")
          await user.send(message.attachments[0])
          nextMsg = await user.send(ORDER_INFO_MSG_TSHIRT)
          def check(reaction, reactor):
            return reactor.id == user.id and reaction.message.id == nextMsg.id
          await bot.wait_for("reaction_add", check = check)
          managerUsr = await bot.fetch_user(MERCH_MANAGER_ID)
          await managerUsr.send("Нове замовлення футболки від " + user.name)
          await user.send(ORDER_SENT_MSG)
        elif "Шкарпетки" in message.content:
          await user.send("Привіт! Я бачу, ви зацікавились цими шкарпеточками?")
          await user.send(message.attachments[0])
          nextMsg = await user.send(ORDER_INFO_MSG_SOCKS)
          def check(reaction, reactor):
            return reactor.id == user.id and reaction.message.id == nextMsg.id
          await bot.wait_for("reaction_add", check = check)
          managerUsr = await bot.fetch_user(MERCH_MANAGER_ID)
          await managerUsr.send("Нове замовлення шкарпеток від " + user.name)
          await user.send(ORDER_SENT_MSG)
        elif "Чоловічий худі" in message.content:
          await user.send("Привіт! Я бачу, ви зацікавились цим худі?")
          await user.send(message.attachments[0])
          nextMsg = await user.send(ORDER_INFO_MSG_HOODIE)
          def check(reaction, reactor):
            return reactor.id == user.id and reaction.message.id == nextMsg.id
          await bot.wait_for("reaction_add", check = check)
          managerUsr = await bot.fetch_user(MERCH_MANAGER_ID)
          await managerUsr.send("Нове замовлення худі від " + user.name)
          await user.send(ORDER_SENT_MSG)
        elif "Жіночий худі" in message.content:
          await user.send("Привіт! Я бачу, ви зацікавились цим худі?")
          await user.send(message.attachments[0])
          nextMsg = await user.send(ORDER_INFO_MSG_HOODIE_FML)
          def check(reaction, reactor):
            return reactor.id == user.id and reaction.message.id == nextMsg.id
          await bot.wait_for("reaction_add", check = check)
          managerUsr = await bot.fetch_user(MERCH_MANAGER_ID)
          await managerUsr.send("Нове замовлення худі від " + user.name)
          await user.send(ORDER_SENT_MSG)

@bot.slash_command(guild_ids=[1075902688790859817, 502062965462269953, 1136709124839723109], description="Скинути кількість страйків у гравця")
async def resetstrikes(inter, charname:str, realm:str):
  await inter.response.defer()
  if inter.channel.id in officer_channels:
      await proccess_command('resetstrikes', ['resetstrikes', charname, realm, None, None], inter)
  else:
      await inter.followup.send('Гільдійний Ревізор працює з цією командою лише в каналі офіцерів', ephemeral=True)

@bot.slash_command(guild_ids=[1075902688790859817, 502062965462269953, 1136709124839723109], description="Перевірити, чи є гравець у білому списку")
async def checkwhitelist(inter, charname:str, realm:str):
  await inter.response.defer()
  if inter.channel.id in officer_channels:
      await proccess_command('checkwhitelist', ['checkwhitelist', charname, realm, None, None], inter)
  else:
      await inter.followup.send('Гільдійний Ревізор працює з цією командою лише в каналі офіцерів', ephemeral=True)

@bot.slash_command(guild_ids=[1075902688790859817, 502062965462269953, 1136709124839723109], description="Додати гравця у білий список")
async def addtowhitelist(inter, charname:str, realm:str):
  await inter.response.defer()
  if inter.channel.id in officer_channels:
      await proccess_command('addtowhitelist', ['addtowhitelist', charname, realm, None, None], inter)
  else:
      await inter.followup.send('Гільдійний Ревізор працює з цією командою лише в каналі офіцерів', ephemeral=True)

@bot.slash_command(guild_ids=[1075902688790859817, 502062965462269953, 1136709124839723109], description="Прибрати гравця з білого списку")
async def remfromwhitelist(inter, charname:str, realm:str):
  await inter.response.defer()
  if inter.channel.id in officer_channels:
      await proccess_command('remfromwhitelist', ['remfromwhitelist', charname, realm, None, None], inter)
  else:
      await inter.followup.send('Гільдійний Ревізор працює з цією командою лише в каналі офіцерів', ephemeral=True)

@bot.slash_command(guild_ids=test_guilds, description="Дізнатися список українських гільдій на EU та їх рейдовий прогрес")
async def uaguilds(inter):
    await inter.response.defer()
    if inter.channel.id in bot_channels:
        await proccess_command('uaguilds', ['uaguilds', None, None, None, None], inter)
    else:
        await inter.followup.send('Гільдійний Ревізор працює лише в каналі ' + bot_channel_links[test_guilds.index(inter.guild.id)], ephemeral=True)

@bot.slash_command(guild_ids=test_guilds, description="Дізнатися нікнейм гільд майстра гільдії")
async def gm(inter, realm:str, guild:str):
    await inter.response.defer()
    if inter.channel.id in bot_channels:
        await proccess_command('гм', ['гм', realm, guild, None, None], inter)
    else:
        await inter.followup.send('Гільдійний Ревізор працює лише в каналі ' + bot_channel_links[test_guilds.index(inter.guild.id)], ephemeral=True)

@bot.slash_command(guild_ids=test_guilds, description="Дізнатися список персоанжів гільдії з RIO та ілвл вище вказаних (максимум топ 25 персонажів)")
async def rio(inter, realm:str, guild:str, ilvl:int, min_rio:int):
    await inter.response.defer()
    if inter.channel.id in bot_channels:
        await proccess_command('rio', ['rio', realm, guild, ilvl, min_rio], inter)
    else:
        await inter.followup.send('Гільдійний Ревізор працює лише в каналі ' + bot_channel_links[test_guilds.index(inter.guild.id)], ephemeral=True)

@bot.slash_command(guild_ids=test_guilds, description="Дізнатися список персонажів гільдії з ілвл, більше вказаного (максимум топ 25 персонажів)")
async def bestgear(inter, realm:str, guild:str, ilvl:int):
    await inter.response.defer()
    if inter.channel.id in bot_channels:
        await proccess_command('товстісраки', ['товстісраки', realm, guild, ilvl, None], inter)
    else:
        await inter.followup.send('Гільдійний Ревізор працює лише в каналі ' + bot_channel_links[test_guilds.index(inter.guild.id)], ephemeral=True)

@bot.slash_command(guild_ids=test_guilds, description="Дізнатися список танків гільдії з ілвл, більшим, ніж вказаний (максимум топ 25 персонажів)")
async def tanks(inter, realm:str, guild:str, ilvl:int):
    await inter.response.defer()
    if inter.channel.id in bot_channels:
        await proccess_command('танки', ['танки', realm, guild, ilvl, None], inter)
    else:
        await inter.followup.send('Гільдійний Ревізор працює лише в каналі ' + bot_channel_links[test_guilds.index(inter.guild.id)], ephemeral=True)

@bot.slash_command(guild_ids=test_guilds, description="Дізнатися список хілів гільдії з ілвл, більшим, ніж вказаний (максимум топ 25 персонажів)")
async def healers(inter, realm:str, guild:str, ilvl:int):
    await inter.response.defer()
    if inter.channel.id in bot_channels:
        await proccess_command('хіли', ['хіли', realm, guild, ilvl, None], inter)
    else:
        await inter.followup.send('Гільдійний Ревізор працює лише в каналі ' + bot_channel_links[test_guilds.index(inter.guild.id)], ephemeral=True)

def is_player_in_whitelist(characterStr):
  whitelist = redis.lrange('whitelist', 0, -1)
  for whitelistChar in whitelist:
    whitelistChar = whitelistChar.decode("utf-8")
    if whitelistChar == characterStr:
      return True
  return False

async def proccess_command(command, args, inter):
    global requests_count
    guild_slug = args[2]
    if guild_slug != None:
        guild_slug = guild_slug.replace(' ', '-')
    if requests_count > MAX_REQUESTS:
        await inter.followup.send('Гільдійний Ревізор зараз дуже зайнятий і обробляє ще ' + str(requests_count) + ' запитів... Почекайте, будь ласка.', ephemeral=EPHEMERAL_ANSWERS)
        return
    requests_count += 1
    if command == 'гм':
        if len(args) < 3:
            await cmd_help_msg(command, inter, CMD_HELP_3_ARGS)
            requests_count -= 1
            return
        args[2] = args[2].replace('-', ' ').capitalize()
        answer = await do_guild_request(args[2], args[1])
        await find_guild_master(answer, inter, args[2], args[1])
        requests_count -= 1
    elif command == 'resetstrikes':
        characterStr = args[1]+'-'+args[2]
        redis.set(characterStr, 0)
        await inter.followup.send("Персонаж " + characterStr + " тепер має 0 страйків", ephemeral=EPHEMERAL_ANSWERS)
        requests_count -= 1
    elif command == 'addtowhitelist':
        characterStr = args[1]+'-'+args[2]
        if not is_player_in_whitelist(characterStr):
          redis.lpush('whitelist', characterStr)
          await inter.followup.send("Персонаж " + characterStr + " був внесений у білий список", ephemeral=EPHEMERAL_ANSWERS)
        else:
          await inter.followup.send("Персонаж " + characterStr + " вже присутній у білому списку", ephemeral=EPHEMERAL_ANSWERS)
        requests_count -= 1
    elif command == 'remfromwhitelist':
        characterStr = args[1]+'-'+args[2]
        if is_player_in_whitelist(characterStr):
          redis.lrem('whitelist', 0, characterStr)
          await inter.followup.send("Персонаж " + characterStr + " був видалений з білого списку", ephemeral=EPHEMERAL_ANSWERS)
        requests_count -= 1
    elif command == 'checkwhitelist':
        characterStr = args[1]+'-'+args[2]
        if not is_player_in_whitelist(characterStr):
          await inter.followup.send("Персонаж " + characterStr + " НЕ зареєстрований у білому списку", ephemeral=EPHEMERAL_ANSWERS)
        else:
          await inter.followup.send("Персонаж " + characterStr + " присутній у білому списку", ephemeral=EPHEMERAL_ANSWERS)
        requests_count -= 1
    elif command == 'uaguilds':
        prog_msg = 'Дивлюся список українських гільдій на EU...'
        await inter.followup.send(prog_msg, ephemeral=EPHEMERAL_ANSWERS)
        returnmsg = "Українські гільдії на EU: \n"
        result_list = {}
        idx = 0
        all_count = len(ua_wow_guilds)

        await inter.edit_original_response(prog_msg + ' [' + (str)(floor(100 * idx / (all_count + 1))) + '%]')

        nm_answer_parsed = False
        hc_answer_parsed = False
        m_answer_parsed = False
        raid_answer_nm = await do_raid_request("normal")
        if raid_answer_nm.status_code == 200:
          raid_answer_nm = raid_answer_nm.json()
          nm_answer_parsed = True
        raid_answer_hc = await do_raid_request("heroic")
        if raid_answer_hc.status_code == 200:
          raid_answer_hc = raid_answer_hc.json()
          hc_answer_parsed = True
        raid_answer_m = await do_raid_request("mythic")
        if raid_answer_m.status_code == 200:
          raid_answer_m = raid_answer_m.json()
          m_answer_parsed = True

        nm_guilds_count = 0

        if nm_answer_parsed == True:
          for nm_boss_prog in raid_answer_nm["progression"]:
            nm_guilds_count += (int)(nm_boss_prog["totalGuilds"])

        hc_guilds_count = 0

        if hc_answer_parsed == True:
          for hc_boss_prog in raid_answer_hc["progression"]:
            hc_guilds_count += (int)(hc_boss_prog["totalGuilds"])

        m_guilds_count = 0

        if m_answer_parsed == True:
          for m_boss_prog in raid_answer_m["progression"]:
            m_guilds_count += (int)(m_boss_prog["totalGuilds"])

        print("nm: " + (str)(nm_guilds_count) + ", hc: " + (str)(hc_guilds_count) + ", m: " + (str)(m_guilds_count))

        idx += 1
        await inter.edit_original_response(prog_msg + ' [' + (str)(floor(100 * idx / (all_count + 1))) + '%]')
          
        for guild in ua_wow_guilds:
            idx += 1
            guild_name = guild[1].replace('-', ' ').capitalize()
            realm_name = guild[0].replace('-', ' ').capitalize()
            answer = await do_guild_request(guild_name, guild[0])
            await inter.edit_original_response(prog_msg + ' [' + (str)(floor(100 * idx / (all_count + 1))) + '%]')
            if answer.status_code == 200:
                answer = answer.json()
                bosses_count = (int)(answer['raid_progression'][CURR_RAID_ID]['total_bosses'])
                m_rank = (int)(answer['raid_rankings'][CURR_RAID_ID]['mythic']['world'])
                hc_rank = (int)(answer['raid_rankings'][CURR_RAID_ID]['heroic']['world'])
                nm_rank = (int)(answer['raid_rankings'][CURR_RAID_ID]['normal']['world'])
                hc_prog = (int)(answer['raid_progression'][CURR_RAID_ID]['heroic_bosses_killed'])
                nm_prog = (int)(answer['raid_progression'][CURR_RAID_ID]['normal_bosses_killed'])
                m_prog = (int)(answer['raid_progression'][CURR_RAID_ID]['mythic_bosses_killed'])

                m_full_prog_guilds = 24
                hc_full_prog_guilds = 5985
                nm_full_prog_guilds = 13409
              
                hc_coef = nm_full_prog_guilds / hc_full_prog_guilds
                m_coef = nm_full_prog_guilds / m_full_prog_guilds

                if (nm_prog == 0):
                  nm_rank = 2 * nm_guilds_count
              
                if (m_prog == 0):
                  m_rank = 2 * m_guilds_count

                if (hc_prog == 0):
                  hc_rank = 2 * hc_guilds_count
              
                min_rank = min(m_rank, hc_rank, nm_rank)

                max_guilds_count = max(m_guilds_count, hc_guilds_count, nm_guilds_count)

                m_score = 2 * m_guilds_count - m_rank
                hc_score = 2 * hc_guilds_count - hc_rank
                nm_score = 2 * nm_guilds_count - nm_rank

                if (min_rank == 0):
                  min_rank = 2 * max_guilds_count
              
                rank_points = max(0, 2 * max_guilds_count - min_rank)
              
                score = floor((m_score * m_coef + hc_score * hc_coef + nm_score) / 1000)

                nm_prog_str = str(nm_prog) + "/" + str(bosses_count) + " N "
                hc_prog_str = str(hc_prog) + "/" + str(bosses_count) + " H "
                m_prog_str = str(m_prog) + "/" + str(bosses_count) + " M "

                if (nm_prog == 0):
                  nm_prog_str = ""
                if (hc_prog == 0):
                  hc_prog_str = ""
                if (m_prog == 0):
                  m_prog_str = ""

                if (nm_prog + hc_prog + m_prog == 0):
                  prog_str_full = "Нема прогресу"
                else:
                  prog_str_full = m_prog_str + hc_prog_str + nm_prog_str
              
                result_list[guild_name] = (prog_str_full, score, realm_name, len(answer['members']), hc_prog == bosses_count)

        sorted_guilds = sorted(result_list.items(), key=lambda x:x[1][1], reverse=True)
        sorted_guilds = dict(sorted_guilds)

        for i, (k, v) in enumerate(sorted_guilds.items()):
            returnmsg += str(i+1) + ". " + k + '-' + v[2] + " ``" + v[0] + "``, ``Raid score: " + (str)(v[1]) + "``, ``" + (str)(v[3]) + " персонажів``\n"
        
        await inter.followup.send(returnmsg, ephemeral=EPHEMERAL_ANSWERS)
        #await inter.delete_original_message()
        requests_count -= 1
    elif command == 'rio':
        if len(args) < 4:
            await cmd_help_msg(command, inter, CMD_HELP_4_ARGS)
            requests_count -= 1
            return
        args[2] = args[2].replace('-', ' ').capitalize()
        prog_msg = 'Дивлюся список найкращих М+ персонажів гільдії ' + args[2] + '-' + args[1]+ ' з ілвл >= ' + str(args[3]) + ' та RIO >= ' + str(args[4]) + ' (топ 25)... '
        await inter.followup.send(prog_msg, ephemeral=EPHEMERAL_ANSWERS)
        answer = await do_guild_request(args[2], args[1])
        returnmsg = "Товсті M+ сраки гільдії " + args[2] + ": \n"
        await proccess_guild_answer(prog_msg, answer, inter, returnmsg, command, args, None)
        #await inter.delete_original_message()
        requests_count -= 1
    elif command == 'товстісраки':
        if len(args) < 4:
            await cmd_help_msg(command, inter, CMD_HELP_4_ARGS)
            requests_count -= 1
            return
        args[2] = args[2].replace('-', ' ').capitalize()
        prog_msg = 'Дивлюся список персонажів гільдії ' + args[2] + '-' + args[1]+ ' з ілвл >= ' + str(args[3]) + ' (топ 25)... '
        await inter.followup.send(prog_msg, ephemeral=EPHEMERAL_ANSWERS)
        answer = await do_guild_request(args[2], args[1])
        returnmsg = "Товсті сраки гільдії " + args[2] + ": \n"
        await proccess_guild_answer(prog_msg, answer, inter, returnmsg, command, args, None)
        #await inter.delete_original_message()
        requests_count -= 1
    elif command == 'танки':
        if len(args) < 4:
            await cmd_help_msg(command, inter, CMD_HELP_4_ARGS)
            requests_count -= 1
            return
        args[2] = args[2].replace('-', ' ').capitalize()
        prog_msg = 'Дивлюся список танків гільдії ' + args[2] + '-' + args[1]+ ' з ілвл >= ' + str(args[3]) + ' (топ 25)... '
        await inter.followup.send(prog_msg, ephemeral=EPHEMERAL_ANSWERS)
        answer = await do_guild_request(args[2], args[1])
        returnmsg = "Танки гільдії " + args[2] + ": \n"
        await proccess_guild_answer(prog_msg, answer, inter, returnmsg, command, args, 'TANK')
        #await inter.delete_original_message()
        requests_count -= 1
    elif command == 'хіли':
        if len(args) < 4:
            await cmd_help_msg(command, inter, CMD_HELP_4_ARGS)
            requests_count -= 1
            return
        args[2] = args[2].replace('-', ' ').capitalize()
        prog_msg = 'Дивлюся список хілів гільдії ' + args[2] + '-' + args[1]+ ' з ілвл >= ' + str(args[3]) + ' (топ 25)... '
        await inter.followup.send(prog_msg, ephemeral=EPHEMERAL_ANSWERS)
        answer = await do_guild_request(args[2], args[1])
        returnmsg = "Хіли гільдії " + args[2] + ": \n"
        await proccess_guild_answer(prog_msg, answer, inter, returnmsg, command, args, 'HEALING')
        #await inter.delete_original_message()
        requests_count -= 1

bot.run(discordToken)
