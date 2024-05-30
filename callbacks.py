from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from heandlers import start
from cfg import TOKEN
from fsm import FSM
from db import add_message, get_messages, get_chats, get_message, get_chat, delete_chat, delete_message, get_sends, \
    delete_send, set_send_unactive, get_send, get_button, delete_button, get_buttons, find_send, edit_pin

callbacks = Router()
bot = Bot(token=TOKEN, parse_mode='html')
@callbacks.callback_query(F.data.startswith('pin_message_'))
async def pin_message(call: CallbackQuery):
    message_id = int(call.data.split('_')[2])
    await edit_pin(message_id, 1)
    await call.message.answer('Сообщение закреплено', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Назад', callback_data=f'message_{message_id}')]
    ]))
@callbacks.callback_query(F.data.startswith('unpin_message_'))
async def unpin_message(call: CallbackQuery):
    message_id = int(call.data.split('_')[2])
    await edit_pin(message_id, 0)
    await call.message.answer('Сообщение откреплено', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Назад', callback_data=f'message_{message_id}')]
    ]))
@callbacks.callback_query(F.data.startswith('show_messages'))
async def show_messages(call: CallbackQuery):
    page = int(call.data.split('_')[2])
    messages = await get_messages()
    len_messages = len(messages)
    messages = messages[page * 45:(page+1) * 45]
    markup = InlineKeyboardBuilder()
    for msg in messages:
        if msg[1]:
            markup.row(InlineKeyboardButton(text=msg[1], callback_data=f'message_{msg[0]}'))
        else:
            markup.row(InlineKeyboardButton(text=msg[3], callback_data=f'message_{msg[0]}'))
    if page > 0 and len_messages > (page + 1) * 45:
        markup.row(InlineKeyboardButton(text='◀', callback_data=f'show_messages_{page-1}'),
            InlineKeyboardButton(text='▶', callback_data=f'show_messages_{page+1}'))
    elif page > 0:
        markup.row(InlineKeyboardButton(text='◀', callback_data=f'show_messages_{page-1}'))
    elif len_messages > (page + 1) * 45:
        markup.row(InlineKeyboardButton(text='▶', callback_data=f'show_messages_{page+1}'))
    markup.row(InlineKeyboardButton(text='Назад', callback_data='menu'))
    markup = markup.as_markup()
    await call.message.answer('Сохраненные сообщения:', reply_markup=markup)
@callbacks.callback_query(F.data == 'menu')
async def menu(call: CallbackQuery, state: FSMContext):
    await state.set_state(FSM.Normal)
    await start(call.message, state=state)
@callbacks.callback_query(F.data == 'show_chats')
async def show_groups(call: CallbackQuery):
    chats = await get_chats()
    markup = InlineKeyboardBuilder()
    for chat in chats:
        markup.add(InlineKeyboardButton(text=chat[1], callback_data=f'chat_{chat[0]}'))
    markup.add(InlineKeyboardButton(text='Назад', callback_data='menu'))
    markup = markup.adjust(1).as_markup()
    await call.message.answer('Сохраненные группы:', reply_markup=markup)
@callbacks.callback_query(F.data == 'add_message')
async def set_message(call: CallbackQuery, state: FSMContext):
    await call.message.answer('Введите текст cообщения:', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Отмена', callback_data='menu')],
        [InlineKeyboardButton(text='Продолжить без текста', callback_data='no_text')]]))
    await state.set_state(FSM.set_message_text)
@callbacks.callback_query(F.data == 'no_text')
async def no_text(call: CallbackQuery, state: FSMContext):
    await state.update_data(message_text=None)
    await call.message.answer('Отправь фото рассылки:', reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text='Отмена', callback_data='menu')
    ]]))
    await state.set_state(FSM.set_message_photo)
@callbacks.callback_query(F.data == 'no_photo')
async def no_photo(call: CallbackQuery, state: FSMContext):
    await state.update_data(message_photo_id=None, type='photo')
    await call.message.answer('Введите текст кнопки:', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Продолжить без кнопки', callback_data='no_button')],
        [InlineKeyboardButton(text='Отмена', callback_data='menu')]]))
    await state.set_state(FSM.set_button_text)
@callbacks.callback_query(F.data == 'no_button')
async def no_button(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if data['type']:
        await add_message(data['message_text'], data['message_photo_id'], data['type'])
    else:
        await add_message(data['message_text'], data['message_photo_id'])
    msg = await find_send(data['message_text'], data['message_photo_id'])
    await state.set_state(FSM.Normal)
    markup = InlineKeyboardBuilder()
    markup.add(InlineKeyboardButton(text='Функции:', callback_data='dddddd'))
    markup.add(InlineKeyboardButton(text='Изменить текст', callback_data=f'edit_message_text_{msg[0]}'))
    markup.add(InlineKeyboardButton(text='Добавить кнопку', callback_data=f'add_button_{msg[0]}'))
    markup.add(InlineKeyboardButton(text='Назначить отправку', callback_data=f'start_message_{msg[0]}'))
    if msg[4] == 0:
        markup.add(InlineKeyboardButton(text='Закрепить при отправке', callback_data=f'pin_message_{msg[0]}'))
    else:
        markup.add(InlineKeyboardButton(text='Не закреплять при отправке', callback_data=f'unpin_message_{msg[0]}'))
    markup.add(InlineKeyboardButton(text='Удалить', callback_data=f'delete_message_{msg[0]}'))
    markup.add(InlineKeyboardButton(text='Назад', callback_data=f'show_messages_0'))
    markup = markup.adjust(1).as_markup()
    try:
        if data['type'] == 'photo':
            if data['message_text']:
                if data['message_photo_id']:
                    await call.message.answer_photo(photo=data['message_photo_id'], caption=data['message_text'][:4096],
                                               reply_markup=markup)
                else:
                    await call.message.answer(text=data['message_text'][:4096], reply_markup=markup)
            else:
                await call.message.answer_photo(photo=data['message_photo_id'], reply_markup=markup)
        elif data['type'] == 'video':
            if data['message_text']:
                if data['message_photo_id']:
                    await call.message.answer_video(video=data['message_photo_id'], caption=data['message_text'][:4096],
                                               reply_markup=markup)
                else:
                    await call.message.answer(text=data['message_text'][:4096], reply_markup=markup)
            else:
                await call.message.answer_video(video=data['message_photo_id'], reply_markup=markup)
        elif data['type'] == 'gif':
            if data['message_text']:
                if data['message_photo_id']:
                    await call.message.answer_animation(animation=data['message_photo_id'],
                                                        caption=data['message_text'][:4096], reply_markup=markup)
                else:
                    await call.message.answer(text=data['message_text'][:4096], reply_markup=markup)
            else:
                await call.message.answer_animation(animation=data['message_photo_id'], reply_markup=markup)
    except Exception as e:
        await call.message.answer(f'{msg[1][:3900]}\n⚠  Возникла ошибка: {e}\nДанное сообщение не будет корректно '
                                  f'обработано у пользователя.', reply_markup=markup, parse_mode='Markdown')
@callbacks.callback_query(F.data.startswith('edit_message_text_'))
async def edit_message_text(call: CallbackQuery, state: FSMContext):
    message_id = call.data.split('_')[3]
    await state.update_data(message_id=int(message_id))
    await call.message.answer('Введите новый текст сообщения:', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Отмена', callback_data='menu')]]))
    await state.set_state(FSM.edit_message_text)
@callbacks.callback_query(F.data.startswith('message_'))
async def show_message(call: CallbackQuery):
    message_id = call.data.split('_')[1]
    msg = await get_message(int(message_id))
    markup = InlineKeyboardBuilder()
    buttons = await get_buttons(int(message_id))
    if buttons:
        for button in buttons:
            markup.add(InlineKeyboardButton(text=button[2], callback_data=f'button_{button[0]}'))
    markup.add(InlineKeyboardButton(text='Функции:', callback_data='dddddd'))
    markup.add(InlineKeyboardButton(text='Изменить текст', callback_data=f'edit_message_text_{message_id}'))
    markup.add(InlineKeyboardButton(text='Добавить кнопку', callback_data=f'add_button_{message_id}'))
    markup.add(InlineKeyboardButton(text='Назначить отправку', callback_data=f'start_message_{message_id}'))
    if msg[4] == 0:
        markup.add(InlineKeyboardButton(text='Закрепить при отправке', callback_data=f'pin_message_{msg[0]}'))
    else:
        markup.add(InlineKeyboardButton(text='Не закреплять при отправке', callback_data=f'unpin_message_{msg[0]}'))
    markup.add(InlineKeyboardButton(text='Удалить', callback_data=f'delete_message_{message_id}'))
    markup.add(InlineKeyboardButton(text='Назад', callback_data=f'show_messages_0'))
    markup = markup.adjust(1).as_markup()
    try:
        if msg[3] == 'photo':
            if msg[1]:
                if msg[2]:
                    await call.message.answer_photo(photo=msg[2], caption=msg[1][:4096], reply_markup=markup)
                else:
                    await call.message.answer(text=msg[1][:4096], reply_markup=markup)
            else:
                await call.message.answer_photo(photo=msg[2], reply_markup=markup)
        elif msg[3] == 'video':
            if msg[1]:
                if msg[2]:
                    await call.message.answer_video(video=msg[2], caption=msg[1][:4096], reply_markup=markup)
                else:
                    await call.message.answer(text=msg[1][:4096], reply_markup=markup)
            else:
                await call.message.answer_video(video=msg[2], reply_markup=markup)
        elif msg[3] == 'gif':
            if msg[1]:
                if msg[2]:
                    await call.message.answer_animation(animation=msg[2], caption=msg[1][:4096], reply_markup=markup)
                else:
                    await call.message.answer(text=msg[1][:4096], reply_markup=markup)
            else:
                await call.message.answer_animation(animation=msg[2], reply_markup=markup)
    except Exception as e:
        await call.message.answer(f'{msg[1][:3900]}\n⚠  Возникла ошибка: {e}\n'
                                  f'Данное сообщение не будет корректно обработано '
                                  f'у пользователя.', reply_markup=markup, parse_mode='Markdown')
@callbacks.callback_query(F.data.startswith('add_button_'))
async def add_button(call: CallbackQuery, state: FSMContext):
    message_id = call.data.split('_')[2]
    await state.update_data(message_id=int(message_id))
    await call.message.answer('Введите текст кнопки:', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Отмена', callback_data='menu')]]))
    await state.set_state(FSM.add_button_text)


@callbacks.callback_query(F.data.startswith('chat_'))
async def show_chat(call: CallbackQuery):
    chat_id = call.data.split('_')[1]
    chat = await get_chat(int(chat_id))
    markup = InlineKeyboardBuilder()
    markup.add(InlineKeyboardButton(text='Функции:', callback_data='dddddd'))
    markup.add(InlineKeyboardButton(text='Назначить отправку', callback_data=f'start_chat_{chat_id}'))
    markup.add(InlineKeyboardButton(text='Удалить', callback_data=f'delete_chat_{chat_id}'))
    markup.add(InlineKeyboardButton(text='Назад', callback_data='show_chats'))
    markup = markup.adjust(1).as_markup()
    await call.message.answer(text=f'{chat[1]}', reply_markup=markup)
@callbacks.callback_query(F.data.startswith('delete_message_'))
async def del_message(call: CallbackQuery):
    message_id = call.data.split('_')[2]
    await delete_message(int(message_id))
    await call.message.answer('Сообщение удалено', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Назад', callback_data='show_messages_0')],
        [InlineKeyboardButton(text='Меню', callback_data='menu')]
    ]))
@callbacks.callback_query(F.data.startswith('start_message_'))
async def choose_message(call: CallbackQuery, state: FSMContext):
    await state.update_data(message_id=int(call.data.split('_')[2]))
    chats = await get_chats()
    markup = InlineKeyboardBuilder()
    for chat in chats:
        markup.add(InlineKeyboardButton(text=chat[1], callback_data=f'select_chat_{chat[0]}'))
    markup.add(InlineKeyboardButton(text='Назад', callback_data='menu'))
    markup = markup.adjust(1).as_markup()
    await call.message.answer('Сохраненные группы:', reply_markup=markup)
@callbacks.callback_query(F.data.startswith('select_chat_'))
async def select_chat(call: CallbackQuery, state: FSMContext):
    chat_id = call.data.split('_')[2]
    await state.update_data(chat_id=int(chat_id), active=False)
    await call.message.answer('Введите интервал отправки в минутах:',
                              reply_markup=InlineKeyboardMarkup(
                                  inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data='menu')]]))
    await state.set_state(FSM.set_time_interval)
@callbacks.callback_query(F.data.startswith('delete_chat_'))
async def del_chat(call: CallbackQuery):
    message_id = call.data.split('_')[2]
    await delete_chat(int(message_id))
    await call.message.answer('Чат удален',
                              reply_markup=InlineKeyboardMarkup(
                                    inline_keyboard=[
                                        [InlineKeyboardButton(text='Назад', callback_data='show_chats')],
                                        [InlineKeyboardButton(text='Меню', callback_data='menu')]
                                    ]))
@callbacks.callback_query(F.data.startswith('start_chat_'))
async def choose_chat(call: CallbackQuery):
    chat_id = int(call.data.split('_')[2])
    messages = await get_messages()
    markup = InlineKeyboardBuilder()
    for msg in messages:
        if msg[1]:
            markup.add(InlineKeyboardButton(text=msg[1], callback_data=f'start_send_{chat_id}_{msg[0]}'))
        else:
            markup.add(InlineKeyboardButton(text=msg[0], callback_data=f'start_send_{chat_id}_{msg[0]}'))
    markup.add(InlineKeyboardButton(text='Назад', callback_data='menu'))
    markup = markup.adjust(1).as_markup()
    await call.message.answer('Сохраненные сообщения:', reply_markup=markup)
@callbacks.callback_query(F.data.startswith('select_message_'))
async def select_message(call: CallbackQuery, state: FSMContext):
    message_id = call.data.split('_')[2]
    await state.update_data(message_id=int(message_id), active=False)
    await call.message.answer('Введите интервал отправки в минутах:', reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data='menu')]]))
    await state.set_state(FSM.set_time_interval)
@callbacks.callback_query(F.data.startswith('show_sends_'))
async def show_sends(call: CallbackQuery):
    page = int(call.data.split('_')[2])
    sends = await get_sends()
    len_sends = len(sends)
    sends = sends[page*45:(page+1)*45]
    markup = InlineKeyboardBuilder()
    for send in sends:
        try:
            chat = await get_chat(send[0])
            message = await get_message(send[1])
            if message:
                if send[3] == 1:
                    markup.row(InlineKeyboardButton(text=f'(Активно, {send[2]}мин){chat[1]}: {message[1][:30]}',
                                                    callback_data=f'send_{send[0]}_{send[1]}'))
                else:
                    markup.row(InlineKeyboardButton(text=f'{chat[1]}: {message[1][:30]}',
                                                    callback_data=f'send_{send[0]}_{send[1]}'))
        except Exception:
            pass
    if len_sends > (page+1)*45 and page > 0:
        markup.row(InlineKeyboardButton(text='◀', callback_data=f'show_sends_{page-1}'),
                   InlineKeyboardButton(text='▶', callback_data=f'show_sends_{page+1}'))
    elif len_sends > (page+1)*45:
        markup.row(InlineKeyboardButton(text='▶', callback_data=f'show_sends_{page+1}'))
    elif page > 0:
        markup.row(InlineKeyboardButton(text='◀', callback_data=f'show_sends_{page-1}'))
    markup.row(InlineKeyboardButton(text='Назад', callback_data='menu'))
    markup = markup.adjust(1).as_markup()
    await call.message.answer('Сохраненные cообщения:', reply_markup=markup)
@callbacks.callback_query(F.data.startswith('time_start_send_'))
async def admin_time_start_send(call: CallbackQuery, state: FSMContext):
    await state.update_data(chat_id=int(call.data.split('_')[3]), message_id=call.message.message_id,
                            msg_id=int(call.data.split('_')[4]))
    await call.message.answer('Введите время начала отправки в формате ЧЧ:ММ',
                              reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                               [InlineKeyboardButton(text='Отмена', callback_data=f'send_{call.data.split("_")[3]}')]]))
    await state.set_state(FSM.set_send_start_time)
@callbacks.callback_query(F.data.startswith('time_end_send_'))
async def admin_time_end_send(call: CallbackQuery, state: FSMContext):
    await state.update_data(chat_id=int(call.data.split('_')[3]), message_id=call.message.message_id,
                            msg_id=int(call.data.split('_')[4]))
    await call.message.answer('Введите время окончания отправки в формате ЧЧ:ММ',
                              reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                               [InlineKeyboardButton(text='Отмена', callback_data=f'send_{call.data.split("_")[3]}')]]))
    await state.set_state(FSM.set_send_end_time)

@callbacks.callback_query(F.data.startswith('send_'))
async def choose_send(call: CallbackQuery, state: FSMContext):
    await state.set_state(FSM.Normal)
    message_id = call.data.split('_')[2]
    chat_id = call.data.split('_')[1]
    message = await get_message(int(message_id))
    chat = await get_chat(int(chat_id))
    send = await get_send(int(chat_id), int(message_id))
    markup = InlineKeyboardBuilder()
    buttons = await get_buttons(int(message_id))
    for button in buttons:
        markup.add(InlineKeyboardButton(text=button[2], url=button[3]))
    if send[3] == 0:
        markup.add(InlineKeyboardButton(text='Начать отправку', callback_data=f'start_send_{chat_id}_{message_id}'))
    else:
        markup.add(InlineKeyboardButton(text='Оcтановить отправку',
                                        callback_data=f'cancel_send_{chat_id}_{message_id}'))
    markup.add(InlineKeyboardButton(text='Установить время начала отправки',
                                    callback_data=f'time_start_send_{send[0]}_{send[1]}'))
    markup.add(InlineKeyboardButton(text='Устанивть время окончания отправки',
                                    callback_data=f'time_end_send_{send[0]}_{send[1]}'))
    markup.add(InlineKeyboardButton(text='Удалить', callback_data=f'delete_send_{chat_id}_{message_id}'))
    markup.add(InlineKeyboardButton(text='Назад', callback_data='show_sends_0'))
    markup.add(InlineKeyboardButton(text='Меню', callback_data='menu'))
    markup = markup.adjust(1).as_markup()
    if message[1] is not None:
        text = (f'{chat[1]}: {message[1][:30]}, интервал: {send[2]} {"Время начала: " + send[4] if send[4] else ""} '
                f'{"Время окончания: " + send[5] if send[5] else ""}')
    else:
        text = (f'{chat[1]}: Фото, интервал: {send[2]} {"Время начала: " + send[4] if send[4] else ""} '
                f'{"Время окончания: " + send[5] if send[5] else ""}')
    if send[3] == 1:
        text = f'(Активно){text}'
    await call.message.answer(text[:3900], reply_markup=markup)
@callbacks.callback_query(F.data.startswith('delete_send_'))
async def del_send(call: CallbackQuery, apscheduler: AsyncIOScheduler):
    message_id = call.data.split('_')[3]
    chat_id = call.data.split('_')[2]
    try:
        apscheduler.remove_job(job_id=f'{chat_id}_{message_id}')
    except JobLookupError:
        pass
    await delete_send(int(chat_id), int(message_id))
    await call.message.answer('Отправка удалена из списка', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Назад', callback_data='show_sends_0')],
        [InlineKeyboardButton(text='Меню', callback_data='menu')]
    ]))
@callbacks.callback_query(F.data.startswith('start_send_'))
async def start_send(call: CallbackQuery, state: FSMContext, apscheduler: AsyncIOScheduler):
    chat_id = call.data.split('_')[2]
    message_id = call.data.split('_')[3]
    try:
        apscheduler.remove_job(job_id=f'{chat_id}_{message_id}')
    except JobLookupError:
        pass
    await state.update_data(chat_id=int(chat_id), message_id=int(message_id), active=True)
    await call.message.answer('Введите интервал отправки в минутах:',
                              reply_markup=InlineKeyboardMarkup(
                                  inline_keyboard=[[InlineKeyboardButton(text='Отмена', callback_data='menu')]]))
    await state.set_state(FSM.set_time_interval)
@callbacks.callback_query(F.data.startswith('cancel_send'))
async def cancel_send(call: CallbackQuery, apscheduler: AsyncIOScheduler):
    chat_id = call.data.split('_')[2]
    message_id = call.data.split('_')[3]
    await set_send_unactive(int(chat_id), int(message_id))
    try:
        apscheduler.remove_job(job_id=f'{chat_id}_{message_id}')
    except JobLookupError:
        await call.message.answer('Отправка не найдена', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text='Назад', callback_data='show_sends_0')],
            [InlineKeyboardButton(text='Меню', callback_data='menu')]]))
    await call.message.answer('Отправка отменена', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Назад', callback_data='show_sends_0')],
        [InlineKeyboardButton(text='Меню', callback_data='menu')]
    ]))
@callbacks.callback_query(F.data.startswith('button_'))
async def button_menu(call: CallbackQuery):
    button_id = call.data.split('_')[1]
    button = await get_button(int(button_id))
    markup = InlineKeyboardBuilder()
    markup.add(InlineKeyboardButton(text=f'{button[2]}', url=f'{button[3]}'))
    markup.add(InlineKeyboardButton(text='Функции:', callback_data='dddddd'))
    markup.add(InlineKeyboardButton(text='Изменить текст', callback_data=f'edit_button_text_{button_id}'))
    markup.add(InlineKeyboardButton(text='Изменить ссылку', callback_data=f'edit_button_url_{button_id}'))
    markup.add(InlineKeyboardButton(text='Удалить', callback_data=f'delete_button_{button_id}'))
    markup.add(InlineKeyboardButton(text='Назад', callback_data='menu'))
    markup = markup.adjust(1).as_markup()
    await call.message.answer(f'Кнопка: {button[2]}', reply_markup=markup)
@callbacks.callback_query(F.data.startswith('edit_button_text_'))
async def edit_button_text(call: CallbackQuery, state: FSMContext):
    button_id = call.data.split('_')[3]
    await state.update_data(button_id=int(button_id))
    await call.message.answer('Введите новый текст кнопки:', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Отмена', callback_data=f'button_{button_id}')]]))
    await state.update_data(button_id=int(button_id))
    await state.set_state(FSM.set_new_button_text)
@callbacks.callback_query(F.data.startswith('edit_button_url_'))
async def edit_button_url(call: CallbackQuery, state: FSMContext):
    button_id = call.data.split('_')[3]
    await state.update_data(button_id=int(button_id))
    await call.message.answer('Введите новую ссылку кнопки:', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Отмена', callback_data=f'button_{button_id}')]]))
    await state.set_state(FSM.set_new_button_url)
@callbacks.callback_query(F.data.startswith('delete_button_'))
async def delete_button_call(call: CallbackQuery):
    button_id = call.data.split('_')[2]
    button = await get_button(int(button_id))
    await delete_button(int(button_id))
    await call.message.answer('Кнопка удалена', reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='Назад', callback_data=f'message_{button[1]}')]
    ]))