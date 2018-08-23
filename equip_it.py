# -*- coding: utf-8 -*-

import config
import telebot
import requests
import json
import csv
import time
from datetime import datetime, date, timedelta
from collections import defaultdict
from telebot import types

bot = telebot.TeleBot(config.token)
MAX_INT = 2**32-1
USER_DATA = 'https://habitica.com/export/userdata.json'
EQUIP = 'https://habitica.com/api/v3/user/equip/{}/{}'
CONTENT = 'https://habitica.com/api/v3/content'
CAST = 'https://habitica.com/api/v3/user/class/cast/{}'
GEMS ='https://habitica.com/api/v3/user/purchase/gems/gem'
SEND_GEMS = 'https://habitica.com/api/v3/members/transfer-gems'
PARTY = 'https://habitica.com/api/v3/groups/party'
ACCEPT = 'https://habitica.com/api/v3/groups/party/quests/accept'


def make_auth_header(user):
  return {'x-api-user':user['user_id'], 'x-api-key':user['token']}


def get_user_by_name(name):
	for user in config.USERS:
		if user['user'] == name:
			return user


@bot.message_handler(func=lambda x: x.text in ('урон', 'boss_sum'))
def get_quest_boss_sum(message):
	result = list()
	progresses = list()
	sum = defaultdict(int)
	hp = 0
	auth_headers = make_auth_header(config.USERS[0])
	params = {'language': 'ru'} 
	x = requests.get(CONTENT, headers=auth_headers, params=params)
	quests_content = json.loads(x.text)['data']['quests']

	t_user_data = json.loads(requests.get(USER_DATA, headers=auth_headers).text)    
	if 'key' in t_user_data['party']['quest']:
		key = t_user_data['party']['quest']['key']
		cur_quest = quests_content[key]

	progress = json.loads(requests.get(PARTY, headers=auth_headers).text)['data']['quest']['progress']

	if 'hp' in progress:
		boss_cur_hp = progress['hp']
		result.append('Текущий квест: {}.\nОставшееся Здоровье босса: {}/{}, сила босса: {}\n\n'
			.format(cur_quest['text'], round(boss_cur_hp,2), cur_quest['boss']['hp'], cur_quest['boss']['str']))

		for user in config.USERS:
			a = json.loads(requests.get(USER_DATA, headers=make_auth_header(user)).text)
			last_cron = 'неизвестно :('
			progress = 0
			if 'lastCron' in a:
				da = datetime.strptime(a['lastCron'],'%Y-%m-%dT%H:%M:%S.%fZ')
				da = da + timedelta(hours=+3)
				last_cron = da.strftime('%d %b, %H:%M')
			if 'party' in a and 'quest' in a['party']: 
				progress = a['party']['quest']['progress']['up']
			is_sleeping = 'S' if a['preferences']['sleep'] else 'A'
			day_start = a['preferences']['dayStart']
			progresses.append((is_sleeping, user['user'], round(progress, 2), last_cron, day_start))
			sum[is_sleeping] += progress
			progresses = sorted(progresses, key=lambda k: k[-1])
		for res in progresses:
			result.append('[{}] {}: {}. Прошлый логин: {}. Начало дня {}:00. Принудительный крон 9:00\n'.format(*res))
			t = ' + '.join(['[{}] {}'.format(k, round(v, 2)) for k,v in sum.items()])
		result.append('------------\n{}\n\nОсталось нанести {}'.format(t, max(0, round(boss_cur_hp-sum['A'],2))))
	elif 'collect' in progress:
		need_to_collect = progress['collect']
		need_to_collect_names = ['{}-{}'.format(key, value) for key, value in need_to_collect.items()]
		result.append('Текущий квест: {}.\nНадо собрать: {}'.format(cur_quest['text'], '\n'.join(need_to_collect_names)))
	'''
    for user in config.USERS:
        auth_headers = {'x-api-user':user['user_id'], 'x-api-key':user['token']}
        z = requests.get(user_data, headers=auth_headers)
        a = json.loads(z.text)
        last_cron = 'неизвестно :('
        progress = 0
        if 'lastCron' in a:
           da = datetime.strptime(a['lastCron'],'%Y-%m-%dT%H:%M:%S.%fZ')
           da = da + timedelta(hours=+3)
           last_cron = da.strftime('%d %b, %H:%M')
        is_sleeping = 'S' if a['preferences']['sleep'] else 'A'
        day_start = a['preferences']['dayStart']
        progresses.append((is_sleeping, user['user'], round(progress, 2), last_cron, day_start))
        sum[is_sleeping] += progress
        progresses = sorted(progresses, key=lambda k: k[-1])
    for res in progresses:
      result.append('[{}] {}: {}. Прошлый логин: {}. Начало дня {}:00. Принудительный крон 9:00\n'.format(*res))
      t = ' + '.join(['[{}] {}'.format(k, round(v, 2)) for k,v in sum.items()])
      result.append('------------\n{}\n\nОсталось нанести {}'.format(t, max(0, round(boss_cur_hp-sum['A'],2))))
      '''
  #print(message.chat.id, ''.join(result))
	bot.send_message(message.chat.id, ''.join(result))

@bot.message_handler(func=lambda x: x.text in ('принять квест', 'quest'))
def accept_quest(message):
  for user in config.USERS:
      a = json.loads(requests.post(ACCEPT, headers=make_auth_header(user)).text)
      if 'message' in a: 
        if a['message'] != 'Ваша команда уже участвует в квесте. Попробуйте снова, когда закончите текущий квест.':
          bot.send_message(message.chat.id, a['message'])
  return bot.send_message(message.chat.id, 'Сделано!')


@bot.message_handler(func=lambda x: x.text.startswith('купить') or x.text.startswith('buy_gems'))
def buy_gems(message):
	_, user_name, count = message.text.split()
	user = get_user_by_name(user_name)
	if not user:
		return bot.send_message(message.chat.id, 'Неправильное имя человека')
	
	auth_headers = make_auth_header(user)
	for _ in range(count):
		tmp = requests.post(GEMS, headers=auth_headers)
		result = json.loads(tmp.text)
		if 'message' in result:
			return bot.send_message(message.chat.id, result[message])


@bot.message_handler(func=lambda x: x.text.startswith('отправить') or x.text.startswith('send_gems'))
def send_gems_to_asya(message):
	_, user_name, count = message.text.split()
	user = get_user_by_name(user_name)
	if not user:
		return bot.send_message(message.chat.id, 'Неправильное имя человека')
	params={
		'message': 'Самоцветы отправлены программой',
		'toUserId': config.USERS[1]['user_id'],
		'gemAmount': count
	}
	tmp = requests.post(SEND_GEMS, headers=make_auth_header(user), data=params)
	result = json.loads(tmp.text)
	bot.send_message(message.chat.id, result)


def get_current_gear_pack(user):
	auth_headers = make_auth_header(user)
	tmp = requests.get(USER_DATA, headers=auth_headers)
	users_gear = json.loads(tmp.text)['items']['gear']['equipped']
	return list(users_gear.values())
	

def put_on_gear_pack(user, pack):
	# TODO: проверка что этот объект ещё не надет
	auth_headers = make_auth_header(user)
	for gear in pack:
		tmp = requests.post(EQUIP.format('equipped', gear), headers=auth_headers)
		a = json.loads(tmp.text)
		if 'success' in a and not a['success']:
			print(a)


def get_content():
	params = {'language': 'ru'} 
	auth_headers = make_auth_header(config.USERS[0])
	tmp = requests.get(CONTENT, headers=auth_headers, params=params)
	return json.loads(tmp.text)


def get_users_gear_content(user, gear_content):
	auth_headers = make_auth_header(user)
	tmp = requests.get(USER_DATA, headers=auth_headers)
	users_gear = json.loads(tmp.text)['items']['gear']['owned']
	result = defaultdict(list)
	for key, value in gear_content.items():
		if key in users_gear and users_gear[key]:
			result[value['type']].append(value)
	return result


def get_best_possible_by_points_gear_pack(stat_sort, users_gear_content):
	result = list()
	for gear_type, gears in users_gear_content.items():
		if gear_type in ('weapon', 'shield'):
			continue
		tmp_best_gear = None
		tmp_best_gear_stats = (0, 0, 0, 0)
		for gear in gears:
			# TODO: по-человечески
			cur_stats = (gear[stat_sort[0]], gear[stat_sort[1]], gear[stat_sort[2]], gear[stat_sort[3]])
			if cur_stats >= tmp_best_gear_stats:
				tmp_best_gear_stats = cur_stats
				tmp_best_gear = gear
		result.append(tmp_best_gear['key'])
	tmp_best_gear = None
	tmp_best_gear_stats = (0, 0, 0, 0)
	for weapon in users_gear_content['weapon']:
		weapon_stats = (weapon[stat_sort[0]], weapon[stat_sort[1]], weapon[stat_sort[2]], weapon[stat_sort[3]])
		if 'twoHanded' in weapon and weapon['twoHanded']:
			if weapon_stats >= tmp_best_gear_stats:
				tmp_best_gear_stats = weapon_stats
				tmp_best_gear = [None, weapon['key']]
		else:
			for shield in users_gear_content['shield']:
				shield_stats = (shield[stat_sort[0]], shield[stat_sort[1]], shield[stat_sort[2]], shield[stat_sort[3]])
				if 'twoHanded' in shield and shield['twoHanded']:
					if shield_stats >= tmp_best_gear_stats:
						tmp_best_gear_stats = shield_stats
						tmp_best_gear = [shield['key'], None]
				else:
					res = [0, 0, 0, 0]
					for i in range(4):
						res[i] = shield_stats[i] + weapon_stats[i]
					res_stats = tuple(res)
					if res_stats >= tmp_best_gear_stats:
						tmp_best_gear_stats = res_stats
						tmp_best_gear = [['shield', (shield['key'], shield['text']), shield_stats],
										 ['weapon', (weapon['key'], weapon['text']), weapon_stats]]
						tmp_best_gear = [shield['key'], weapon['key']]
	result.append(tmp_best_gear[0])
	result.append(tmp_best_gear[1])
	return result


@bot.message_handler(func=lambda x: x.text.startswith('скастовать') or x.text.startswith('cast_skill'))
def cast_skill(message):
	_, user_name, spell_id, count = message.text.split()
	user = get_user_by_name(user_name)
	print(user)
	auth_headers = make_auth_header(user)
	gear_content = get_content()['data']['gear']['flat']
	params = None
	if spell_id not in ('fireball', 'mpheal', 'earth', 'frost', 'smash', 'defensiveStance', 
		'valorousPresence', 'intimidate', 'pickPocket', 'backStab', 'toolsOfTrade', 'stealth', 
		'heal', 'protectAura', 'brightness', 'healAll'):
		print('Это что за покемон, неизвестный каст')
		return
	if spell_id not in ( 
		# Маг
		'mpheal', # Эфирная зарядка
		'earth', # Землетрясение
		# Воин
		'valorousPresence', # Присутствие духа
		'intimidate', # Устрашающий взор
		# Разбойник
		'toolsOfTrade', # Орудия Труда
		# Целитель
		'protectAura', # 'Защитная аура'
		'healAll' # 'Благословение'
		): 
		print('Не реализованы они ещё')
		return
	priority = ('int', 'str', 'per', 'con')
	times_to_cast = 1
	if spell_id == 'toolsOfTrade':
		priority = ('per', 'str', 'int', 'con')
		times_to_cast = count
	if spell_id == 'mpheal':
		priority = ('int', 'str', 'per', 'con')
		times_to_cast = count	
	old_pack = get_current_gear_pack(user)
	users_gear_content = get_users_gear_content(user, gear_content)	
	new_pack = get_best_possible_by_points_gear_pack(priority, users_gear_content)
	for_put_on_gear_pack = list(set(new_pack) - set(old_pack))
	put_on_gear_pack(user, for_put_on_gear_pack)
	for i in range(times_to_cast):
		tmp = requests.post(CAST.format(spell_id), headers=auth_headers, params=params)
		a = json.loads(tmp.text)
		if 'success' in a and not a['success']:
			print(a)
	put_on_gear_pack(user, list(set(old_pack) - set(for_put_on_gear_pack)))


def quests_table():
	quests_content = get_content()['data']['quests']
	quests = defaultdict(dict)	
	for key, value in quests_content.items():
		for user in config.USERS:
			quests[key][user['user']] = dict()
		if 'boss' in value:
			quests[key]['type'] = 'boss'
			quests[key]['text'] = value['text']
			quests[key]['about'] = value['boss']
		elif 'collect' in value:
			to_collect = list()
			for v, k in value['collect'].items():
				to_collect.append("{} - {}".format(k['text'], k['count']))
			quests[key]['type'] = 'collect'
			quests[key]['text'] = value['text']
			quests[key]['about'] = '\n'.join(to_collect)
		else:
			print(value['text'], value.keys())
		if 'drop' in value and 'items' in value['drop'] and 'eggs' in [a['type'] for a in value['drop']['items']]:
			quests[key]['type'] = 'pet'
	for user in config.USERS:
		auth_headers = make_auth_header(user)
		tmp = requests.get(USER_DATA, headers=auth_headers)
		tmp = json.loads(tmp.text)
		# TODO: объединить то что в руках и то что пройдено по каждому человеку
		completed = tmp['achievements']['quests'] # пройдены
		for k, v in completed.items():
			quests[k][user['user']]['completed'] = v
		in_pocket = tmp['items']['quests'] # что на руках
		for k, v in in_pocket.items():
			quests[k][user['user']]['in_pocket'] = v
	return quests


def write_csv_quests(quests):
	with open('quests_test.csv', "w", newline='') as csv_file:
		writer = csv.writer(csv_file, delimiter=',')
		header = list()
		header.append('название')
		header.append('тип')
		header.append('hp/about')
		header.append('сила')
		header.append('защита')
		for user in config.USERS:
			header.append('завершено у {}'.format(user['dat']))
			header.append('на руках у {}'.format(user['dat']))
		header.append('пройдено каждым')
		header.append('суммарно на руках')
		header.append('надо ещё купить')
		writer.writerow(header)
		for key, value in quests.items():
			min_done, bought, need_to_buy = MAX_INT, 0, 7 # TODO исключить неправильных pet'ов
			result = list()
			result.append(value['text'])
			result.append(value['type'])
			if value['type'] in ('boss', 'pet') and isinstance(value['about'], dict):
				result.append(value['about']['hp'])
				result.append(value['about']['str'])
				result.append(value['about']['def'])
			else:
				result.append(value['about'])
				result.append('')
				result.append('')
			for user in config.USERS:
				if 'completed' not in value[user['user']]:
					value[user['user']]['completed'] = 0
				if 'in_pocket' not in value[user['user']]:
					value[user['user']]['in_pocket'] = 0
				result.append(value[user['user']]['completed'])
				result.append(value[user['user']]['in_pocket'])
				
				min_done = min(min_done, value[user['user']]['completed'])
				bought += max(0, value[user['user']]['in_pocket'])
			if value['type'] == 'pet':
				need_to_buy -= min_done
				need_to_buy -= bought
			else:
				need_to_buy = 0
			result.append(min_done)
			result.append(bought)
			result.append(max(0, need_to_buy))
			writer.writerow(result)


if __name__ == '__main__':
    bot.polling(none_stop=True)

 