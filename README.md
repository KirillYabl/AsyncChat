# Async chat

There are two async scripts:
1. Chat listener
Listen messages in chat and write it history of chat locally
2. Chat writer
Submit message to chat
Authorize if user pass token or username in local cache of user credentials
Else try to register user

### How to install

Python3 should be already installed (version 3.6 or above).
Then use `pip` (or `pip3`, if there is a conflict with Python2) to install dependencies:

```
pip install -r requirements.txt
```

### How to use

#### Chat listener

```bash
python chat_listener.py -host HOST -p PORT -hp HISTORY_PATH [-l]
```

Параметры:
  -host HOST, --host HOST host of chat
  -p PORT, --port PORT port of chat
  -hp HISTORY_PATH, --history_path HISTORY_PATH
  -l, --logging is do logging

#### Chat writer

```bash
python chat_writer.py -host HOST -p PORT -m MESSAGE [-t TOKEN] [-u USERNAME] [-cp CREDENTIAL_PATH] [-l]

```

Параметры:
  -host HOST, --host HOST host of chat
  -p PORT, --port PORT  port of chat
  -m MESSAGE, --message MESSAGE message to send
  -t TOKEN, --token TOKEN token of registered user
  -u USERNAME, --username USERNAME username for new user or cached
  -cp CREDENTIAL_PATH, --credential_path CREDENTIAL_PATH path with credentials
  -l, --logging is do logging

### Project Goals

The code is written for educational purposes on online-course for web-developers [dvmn.org](https://dvmn.org/).
