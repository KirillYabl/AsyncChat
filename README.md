# Async chat

### How to install

Python3 should be already installed (version 3.6 or above).
Then use `pip` (or `pip3`, if there is a conflict with Python2) to install dependencies:

```
pip install -r requirements.txt
```

### How to use

#### Chat listener

```bash
python chat_listener.py -host HOST -p PORT -hp HISTORY_PATH
```

Параметры:
  -host HOST, --host HOST host of chat
  -p PORT, --port PORT port of chat
  -hp HISTORY_PATH, --history_path HISTORY_PATH

#### Chat writer

```bash
python chat_writer.py -host HOST -p PORT -m MESSAGE
```

Параметры:
  -host HOST, --host HOST host of chat
  -p PORT, --port PORT port of chat
  -m MESSAGE, --message MESSAGE message to send


### References

### Project Goals

The code is written for educational purposes on online-course for web-developers [dvmn.org](https://dvmn.org/).
