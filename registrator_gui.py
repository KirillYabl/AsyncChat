import asyncio
import tkinter as tk
from dataclasses import dataclass
import subprocess
import sys
from tkinter import messagebox

from anyio import create_task_group


class TkAppClosed(Exception):
    pass


@dataclass
class Credentials:
    nickname: str
    token: str


async def update_tk(root_frame, interval=1 / 120):
    while True:
        try:
            root_frame.update()
        except tk.TclError:
            # if application has been destroyed/closed
            raise TkAppClosed()
        await asyncio.sleep(interval)


def process_new_message(input_field, sending_queue):
    text = input_field.get()
    sending_queue.put_nowait(text)
    input_field.delete(0, tk.END)


def on_focus_in(entry):
    if entry.cget('state') == 'disabled':
        entry.configure(state='normal')
        entry.delete(0, 'end')


def on_focus_out(entry, placeholder):
    if entry.get() == "":
        entry.insert(0, placeholder)
        entry.configure(state='disabled')


def create_credentials_panel(root_frame):
    status_frame = tk.Frame(root_frame)
    status_frame.pack(side="bottom", fill=tk.X)

    creds_frame = tk.Frame(status_frame)
    creds_frame.pack(side="left")

    nickname_label = tk.Label(creds_frame, height=1, fg='grey', font='arial 10', anchor='w')
    nickname_label.pack(side="top", fill=tk.X)

    token_label = tk.Label(creds_frame, height=1, fg='grey', font='arial 10', anchor='w')
    token_label.pack(side="top", fill=tk.X)

    return nickname_label, token_label


async def update_credentials_panel(creds_labels, creds_updates_queue, options, enter_button):
    nickname_label, token_label = creds_labels

    nickname_label['text'] = 'Никнейм пользователя: неизвестно'
    token_label['text'] = 'Токен пользователя: неизвестно'

    while True:
        msg = await creds_updates_queue.get()
        if isinstance(msg, Credentials):
            nickname_label['text'] = f'Никнейм пользователя: {msg.nickname}'
            token_label['text'] = f'Токен пользователя: {msg.token}'
            options.token = msg.token
            enter_button.configure(state='normal')
            messagebox.showinfo("Успешная регистрация",
                                f"""Вы успешно зарегистрировались!
Данные сохранены в файл {options.credential_path}.
Вы можете перейти в чат по кнопке "Войти в чат" или зарегистрировать еще одного пользователя.
""")


def enter_to_chat(options, root):
    subprocess.Popen([sys.executable, 'messenger.py',
                      '-lh', options.listen_host,
                      '-lp', str(options.listen_port),
                      '-wh', options.write_host,
                      '-wp', str(options.write_port),
                      '-t', options.token,
                      '-hp', options.history_path
                      ])
    root.destroy()


async def draw(sending_queue, creds_updates_queue, options):
    root = tk.Tk()

    root.title('Чат Майнкрафтера. Регистрация')

    root_frame = tk.Frame()
    root_frame.pack(fill="both", expand=True)

    creds_labels = create_credentials_panel(root_frame)

    input_frame = tk.Frame(root_frame)
    input_frame.pack(side="top", fill=tk.X)

    enter_nickname_placeholder = 'Введите никнейм...'
    input_field = tk.Entry(input_frame)
    input_field.insert(0, enter_nickname_placeholder)
    input_field.configure(state='disabled')
    input_field.pack(side="left", fill=tk.X, expand=True)
    input_field.bind('<Button-1>', lambda x: on_focus_in(input_field))
    input_field.bind(
        '<FocusOut>', lambda x: on_focus_out(input_field, enter_nickname_placeholder))

    input_field.bind("<Return>", lambda event: process_new_message(input_field, sending_queue))

    send_button = tk.Button(input_frame)
    send_button["text"] = "Зарегистрироваться"
    send_button["command"] = lambda: process_new_message(input_field, sending_queue)
    send_button.pack(side="left")

    enter_frame = tk.Frame(root_frame)
    enter_frame.pack(side="bottom", fill=tk.X)

    enter_button = tk.Button(root_frame)
    enter_button["text"] = "Войти в чат"
    enter_button.configure(state='disabled')
    enter_button["command"] = lambda: enter_to_chat(options, root)
    enter_button.pack(fill="x", expand=True)

    async with create_task_group() as tg:
        tg.start_soon(update_tk, root_frame)
        tg.start_soon(update_credentials_panel, creds_labels, creds_updates_queue, options, enter_button)
