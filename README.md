# Telegram Speech-to-Text Python Google Cloud Bot

Bot allows to decode voice message into text using Google Storage and Google Speech-to-Text services.
Commands
* /hello - welcome message
* /get_config - view active configuration
* /set_config - load default configuration
* /set_config {"a":1} - set specific configuration

Deploy
```
git clone https://github.com/nasled/sst_bot.git
cd sst_bot
pip install -r requirements.txt
```

Config 
* update CLOUD_TOKEN and BUCKET_NAME
* upload credentials.json 

Run
```
chmod 0777 speech_config.json data
chmod +x main.py
main.py
```

