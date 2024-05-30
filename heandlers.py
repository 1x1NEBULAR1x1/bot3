import asyncio
import datetime
import re
import requests
from aiogram import Router, Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from cfg import ADMINS_IDS, TOKEN
from fsm import FSM
from db import (add_chat, add_message, add_send, get_chat, get_message, set_send_active, get_message_id, add_button,
    find_send, get_buttons, update_button_text, update_button_url, update_message_text, update_message_photo, get_send,
    set_end_time, set_start_time)
from requests.exceptions import MissingSchema
from apscheduler.schedulers.asyncio import AsyncIOScheduler
heandlers = Router()
bot = Bot(token=TOKEN, parse_mode='html')

async def send_message(chat_id: str, message_id: str, bot: Bot):
    msg = await get_message(int(message_id))
    buttons = await get_buttons(int(message_id))
    mg = None
    send = await get_send(int(chat_id), int(message_id))
    if send[4]:
        if datetime.datetime.now().time() < datetime.datetime.strptime(send[4], '%H:%M').time():
            return
    if send[5]:
        if datetime.datetime.now().time() > datetime.datetime.strptime(send[5], '%H:%M').time():
            return
    if buttons:
        markup = InlineKeyboardBuilder()
        for button in buttons:
            markup.add(InlineKeyboardButton(text=button[2], url=button[3]))
        markup = markup.adjust(1).as_markup()
    else:
        markup = None
    if msg[3] == 'photo':
        if msg[1]:
            if msg[2]:
                mg = await bot.send_photo(chat_id=chat_id, photo=msg[2], caption=msg[1][:4096], reply_markup=markup)
            else:
                mg = await bot.send_message(chat_id=chat_id, text=msg[1][:4096], reply_markup=markup)
        else:
            mg = await bot.send_photo(chat_id=chat_id, photo=msg[2], reply_markup=markup)
    elif msg[3] == 'video':
        if msg[1]:
            if msg[2]:
                mg = await bot.send_video(chat_id=chat_id, video=msg[2], caption=msg[1][:4096], reply_markup=markup)
            else:
                mg = await bot.send_message(chat_id=chat_id, text=msg[1][:4096], reply_markup=markup)
        else:
            mg = await bot.send_video(chat_id=chat_id, video=msg[2], reply_markup=markup)
    elif msg[3] == 'gif':
        if msg[1]:
            if msg[2]:
                mg = await bot.send_animation(chat_id=chat_id, animation=msg[2], caption=msg[1][:4096],
                                              reply_markup=markup)
            else:
                mg = await bot.send_message(chat_id=chat_id, text=msg[1][:4096], reply_markup=markup)
        else:
            mg = await bot.send_animation(chat_id=chat_id, animation=msg[2], reply_markup=markup)
    if msg[4] == 1:
        await bot.pin_chat_message(chat_id=chat_id, message_id=mg.message_id)
async def is_admin(message) -> bool:
    return message.chat.id in ADMINS_IDS

@heandlers.message(Command(commands=['add_to_list']))
async def add_to_list(message: Message):
    if message.chat.type != 'private':
        await add_chat(message.chat.id, message.chat.title)
        await message.answer('Группа добавлена')
        await asyncio.sleep(1)
        await message.delete()
    else:
        await message.answer('Команда работает только в группах')
        await asyncio.sleep(1)
        await message.delete()
@heandlers.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.set_state(FSM.Normal)
    if await is_admin(message):
        await message.answer('Меню админа:', reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='Добавить cообщение', callback_data='add_message')],
            [InlineKeyboardButton(text='Список сообщений', callback_data='show_messages_0')],
            [InlineKeyboardButton(text='Список групп', callback_data='show_chats')],
            [InlineKeyboardButton(text='Список активных рассылок', callback_data='show_sends_0')]]))
    else:
        await message.answer('Привет, я бот для рассылки сообщений')

async def add_sender(message: Message, state: FSMContext):
    await message.answer('Введите текст cообщения:', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Отмена', callback_data='menu')],
        [InlineKeyboardButton(text='Продолжить без текста', callback_data='no_text')]]))
    await state.set_state(FSM.set_message_text)
@heandlers.message(FSM.set_message_text)
async def set_message_text(message: Message, state: FSMContext):
    await state.update_data(message_text=message.text)
    await message.answer('Отправь фото сообщения:',
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                             [InlineKeyboardButton(text='Продолжить без фото', callback_data='no_photo')],
                             [InlineKeyboardButton(text='Отмена', callback_data='menu')]]))
    await state.set_state(FSM.set_message_photo)
@heandlers.message(FSM.set_message_photo, F.photo)
async def set_message_photo(message: Message, state: FSMContext):
    await state.update_data(message_photo_id=message.photo[-1].file_id)
    await state.update_data(type='photo')
    await message.answer('Введите текст кнопки:', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Продолжить без кнопки', callback_data='no_button')],
        [InlineKeyboardButton(text='Отмена', callback_data='menu')]]))
    await state.set_state(FSM.set_button_text)
@heandlers.message(FSM.set_message_photo, F.video)
async def set_message_photo(message: Message, state: FSMContext):
    await state.update_data(message_photo_id=message.video.file_id)
    await state.update_data(type='video')
    await message.answer('Введите текст кнопки:', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Продолжить без кнопки', callback_data='no_button')],
        [InlineKeyboardButton(text='Отмена', callback_data='menu')]]))
    await state.set_state(FSM.set_button_text)
@heandlers.message(FSM.set_message_photo, F.animation)
async def set_message_photo(message: Message, state: FSMContext):
    await state.update_data(message_photo_id=message.animation.file_id)
    await state.update_data(type='gif')
    await message.answer('Введите текст кнопки:', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Продолжить без кнопки', callback_data='no_button')],
        [InlineKeyboardButton(text='Отмена', callback_data='menu')]]))
    await state.set_state(FSM.set_button_text)
@heandlers.message(FSM.set_button_text)
async def set_text(message: Message, state: FSMContext):
    await state.update_data(button_text=message.text)
    await message.answer('Введите url кнопки:')
    await state.set_state(FSM.set_button_url)
@heandlers.message(FSM.set_send_start_time)
async def set_send_start_time(message: Message, state: FSMContext):
    data = await state.get_data()
    send = await get_send(data["chat_id"], data["msg_id"])
    if not send:
        await message.answer('Рассылка не найдена', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Отмена', callback_data='menu')]]))
        await state.set_state(FSM.Normal)
        return
    try:
        match_ = re.match(r"([0-2][0-9]):([0-5][0-9])", message.text)
        if not match_:
            raise AttributeError
        else:
            start_time = message.text
            await set_start_time(data['chat_id'], data['msg_id'], start_time)
            await message.answer('Время начала отправки установлено на ' + start_time,
                                 reply_markup=InlineKeyboardMarkup(
                                     inline_keyboard=[
                                      [InlineKeyboardButton(text='Назад', callback_data=f'send_{send[0]}_{send[1]}')]]))
    except AttributeError:
        await message.answer('Неверный формат времени, попробуйте еще раз',
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                              [InlineKeyboardButton(text='Назад', callback_data=f'send_{send[0]}_{send[1]}')]]))
        await state.set_state(FSM.set_send_start_time)
        return
@heandlers.message(FSM.set_send_end_time)
async def set_send_end_time(message: Message, state: FSMContext):
    data = await state.get_data()
    send = await get_send(data["chat_id"], data["msg_id"])
    if not send:
        await message.answer('Рассылка не найдена', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Отмена', callback_data='menu')]]))
        await state.set_state(FSM.Normal)
        return
    try:
        match_ = re.match(r'([0-2][0-9]):([0-5][0-9])', message.text)
        if not match_:
            raise AttributeError
        else:
            end_time = message.text
            await set_end_time(data['chat_id'], data['msg_id'], end_time)
            await message.answer('Время окончания отправки установлено на ' + end_time,
                                 reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                  [InlineKeyboardButton(text='Назад', callback_data=f'send_{send[0]}_{send[1]}')]]))
    except AttributeError:
        await message.answer('Неверный формат времени, попробуйте еще раз',
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                              [InlineKeyboardButton(text='Назад', callback_data=f'send_{send[0]}_{send[1]}')]]))
        await state.set_state(FSM.set_send_end_time)
        return
@heandlers.message(FSM.set_button_url)
async def set_url(message: Message, state: FSMContext):
    await state.update_data(button_url=message.text)
    data = await state.get_data()
    try:
        check = requests.get(data['button_url'])
        if check.status_code != 200:
            await message.answer('Нерабочая ссылка, попробуйте еще раз или введите другую ссылку:')
            await state.set_state(FSM.set_button_url)
            return
    except MissingSchema:
        await message.answer('Нерабочая ссылка, попробуйте еще раз или введите другую ссылку:')
        await state.set_state(FSM.set_button_url)
        return
    if data["type"]:
        await add_message(data['message_text'], data['message_photo_id'], type=data['type'])
    else:
        await add_message(data['message_text'], data['message_photo_id'])
    message_id = await get_message_id(data['message_text'], data['message_photo_id'])
    await state.set_state(FSM.Normal)
    await message.answer('Кнопка добавлена')
    markup = InlineKeyboardBuilder()
    if data['button_url']:
        await add_button(message_id, data['button_text'], data['button_url'])
    if data['message_photo_id'] and data['message_text']:
        send = await find_send(data['message_text'], data['message_photo_id'])
    elif data['message_photo_id']:
        send = await find_send(data['message_photo_id'], '')
    else:
        send = await find_send(data['message_text'], '')
    buttons = await get_buttons(send[0])
    for button in buttons:
        markup.add(InlineKeyboardButton(text=button[2], callback_data=f'button_{button[0]}'))
    markup.add(InlineKeyboardButton(text='Изменить текст', callback_data=f'edit_message_text_{message_id}'))
    markup.add(InlineKeyboardButton(text='Добавить кнопку', callback_data=f'add_button_{message_id}'))
    markup.add(InlineKeyboardButton(text='Назначить отправку', callback_data=f'start_message_{message_id}'))
    if send[4] == 0:
        markup.add(InlineKeyboardButton(text='Закрепить при отправке', callback_data=f'pin_message_{message_id}'))
    else:
        markup.add(InlineKeyboardButton(text='Не закреплять при отправке', callback_data=f'unpin_message_{message_id}'))
    markup.add(InlineKeyboardButton(text='Удалить', callback_data=f'delete_message_{message_id}'))
    markup.add(InlineKeyboardButton(text='Назад', callback_data=f'show_messages_0'))
    markup = markup.adjust(1).as_markup()
    try:
        if data['type'] == 'photo':
            if data['message_text']:
                if data['message_photo_id']:
                    await message.answer_photo(photo=data['message_photo_id'], caption=data['message_text'][:4096],
                                               reply_markup=markup)
                else:
                    await message.answer(text=data['message_text'][:4096], reply_markup=markup)
            else:
                await message.answer_photo(photo=data['message_photo_id'], reply_markup=markup)
        elif data['type'] == 'video':
            if data['message_text']:
                if data['message_photo_id']:
                    await message.answer_video(video=data['message_photo_id'], caption=data['message_text'][:4096],
                                               reply_markup=markup)
                else:
                    await message.answer(text=data['message_text'][:4096], reply_markup=markup)
            else:
                await message.answer_video(video=data['message_photo_id'], reply_markup=markup)
        elif data['type'] == 'gif':
            if data['message_text']:
                if data['message_photo_id']:
                    await message.answer_animation(animation=data['message_photo_id'],
                                                   caption=data['message_text'][:4096], reply_markup=markup)
                else:
                    await message.answer(text=data['message_text'][:4096], reply_markup=markup)
            else:
                await message.answer_animation(animation=data['message_photo_id'], reply_markup=markup)
    except Exception as e:
        await message.answer(text=f'{data["message_text"][:3900]}\n⚠  Возникла ошибка: {e}\n'
                                  f'Данное сообщение не будет корректно отправлено', reply_markup=markup,
                             parse_mode='Markdown')
@heandlers.message(FSM.add_button_text)
async def add_button_text(message: Message, state: FSMContext):
    await state.update_data(button_text=message.text)
    await message.answer('Введите url кнопки:')
    await state.set_state(FSM.add_button_url)
@heandlers.message(FSM.add_button_url)
async def add_button_url(message: Message, state: FSMContext):
    await state.update_data(button_url=message.text)
    data = await state.get_data()
    await add_button(data['message_id'], data['button_text'], data['button_url'])
    await message.answer('Кнопка добавлена', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Назад', callback_data=f'message_{data["message_id"]}')]]))
@heandlers.message(FSM.edit_message_text)
async def edit_message_text(message: Message, state: FSMContext):
    data = await state.get_data()
    await update_message_text(data['message_id'], message.text)
    await message.answer('Текст изменен на ' + message.text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Назад', callback_data=f'message_{int(data["message_id"])}')]]))
    await state.set_state(FSM.Normal)
@heandlers.message(FSM.edit_message_photo, F.photo)
async def edit_message_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    await update_message_photo(data['message_id'], message.photo[-1].file_id, 'photo')
    await message.answer('Фото изменено', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Назад', callback_data=f'message_{int(data["message_id"])}')]]))
    await state.set_state(FSM.Normal)
@heandlers.message(FSM.edit_message_photo, F.video)
async def edit_message_video(message: Message, state: FSMContext):
    data = await state.get_data()
    await update_message_photo(data['message_id'], message.video.file_id, 'video')
    await message.answer('Видео изменено', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Назад', callback_data=f'message_{int(data["message_id"])}')]]))
    await state.set_state(FSM.Normal)
@heandlers.message(FSM.edit_message_photo, F.animation)
async def edit_message_gif(message: Message, state: FSMContext):
    data = await state.get_data()
    await update_message_photo(data['message_id'], message.gif.file_id, 'gif')
    await message.answer('GIF изменено', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Назад', callback_data=f'message_{int(data["message_id"])}')]]))
    await state.set_state(FSM.Normal)
@heandlers.message(FSM.set_new_button_text)
async def set_new_button_text(message: Message, state: FSMContext):
    data = await state.get_data()
    await update_button_text(data['button_id'], message.text)
    await message.answer('Текст кнопки изменен на ' + message.text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Назад', callback_data=f'button_{int(data["button_id"])}')]]))
    await state.set_state(FSM.Normal)
@heandlers.message(FSM.set_new_button_url)
async def set_new_button_url(message: Message, state: FSMContext):
    data = await state.get_data()
    await update_button_url(data['button_id'], message.text)
    await message.answer('URL кнопки изменен на ' + message.text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Назад', callback_data=f'button_{int(data["button_id"])}')]]))
    await state.set_state(FSM.Normal)
@heandlers.message(FSM.Normal)
async def normal(message: Message):
    if message.chat.type != 'private':
        return
    await message.delete()
@heandlers.message(FSM.set_time_interval)
async def accept_sending(message: Message, state: FSMContext, apscheduler: AsyncIOScheduler):
    if not message.text.isdigit():
        await message.answer('Введите число')
        await state.set_state(FSM.set_time_interval)
        return
    await state.update_data(time_interval=message.text)
    data = await state.get_data()
    chat = await get_chat(data['chat_id'])
    msg = await get_message(data['message_id'])
    await add_send(data['chat_id'], data['message_id'], data['time_interval'])
    await set_send_active(data['chat_id'], data['message_id'], data['time_interval'])
    await message.answer(f'Сообщение {msg[1]} отправляется в группу {chat[1]} с интервалом '
                         f'{data["time_interval"]} минут', reply_markup=InlineKeyboardMarkup(
                                            inline_keyboard=[
                                                [InlineKeyboardButton(text='Меню', callback_data='menu')],
                                                [InlineKeyboardButton(text='Отменить',
                                                callback_data=f'cancel_send_{data["chat_id"]}_{data["message_id"]}')]]))
    apscheduler.add_job(send_message, trigger='interval', minutes=int(data['time_interval']),
                        id=f'{data["chat_id"]}_{data["message_id"]}',
                        kwargs={'chat_id': data['chat_id'], 'message_id': data['message_id'], 'bot': bot})
    await state.clear()
    await state.set_state(FSM.Normal)
