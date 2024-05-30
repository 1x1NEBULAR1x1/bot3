from aiogram.fsm.state import StatesGroup, State

class FSM(StatesGroup):
    Normal = State()
    set_message_photo = State()
    set_message_text = State()
    set_button_text = State()
    set_button_url = State()
    set_time_interval = State()
    scheduler = State()
    set_new_button_text = State()
    set_new_button_url = State()
    edit_message_text = State()
    edit_message_photo = State()
    add_button_text = State()
    add_button_url = State()
    set_send_start_time = State()
    set_send_end_time = State()