import os
import telebot

import torch
from transformers import AutoTokenizer
import re

import psycopg2
import logging
import datetime

model = torch.load('models/sent_model.pth', map_location=torch.device('cpu'))
tokenizer = AutoTokenizer.from_pretrained('lxyuan/distilbert-base-multilingual-cased-sentiments-student')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BOT_TOKEN = os.environ.get('BOT_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "I am Kavin, how are you doing?")


user_name_dic = {}
user_sent_dic = {}

def score_update(user_id, sentiment):
    if user_id not in user_sent_dic:
        user_sent_dic[user_id] = 0
    if sentiment == 0:
        score = int(user_sent_dic[user_id])
        score += 1
        user_sent_dic[user_id] = score
    elif sentiment == 2:
        score = int(user_sent_dic[user_id])
        score -= 1
        user_sent_dic[user_id] = score
    
def connect():
    conn = psycopg2.connect(
        dbname="sentiment_bot",
        user="postgres",
        password="pass",
        host= '172.18.0.2',
        port=5432)
    
    if conn:
        logging.info("Connected to the database.")
    else:
        logging.info("Failed to connect to the database.")
    return conn

def create_table(connection, table_name):
    cur = connection.cursor()
    commands = (f"CREATE TABLE IF NOT EXISTS {table_name} (index SERIAL PRIMARY KEY UNIQUE, message VARCHAR(500000) UNIQUE, sentiment VARCHAR(20), update_time TIMESTAMP)")
    try:
        cur.execute(commands)
        logging.info(f"Table {table_name} created.")
    except Exception as e:
        logging.info(e)
    cur.close()
    connection.commit()

conn = connect()
tb_name = 'bot_test'
create_table(conn, tb_name)
    
@bot.message_handler(content_types=['document', 'audio'])
def handle_docs_audio(message):
	print(message)

@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    if message.chat.type == 'group' or message.chat.type == 'supergroup':
        text = str(message.text)
    pattern = r"@\w+"
    text = re.sub(pattern, "", text)
        
    tokens = tokenizer(text, return_tensors = 'pt')
    out = model(**tokens).logits
    sentiment = torch.argmax(out)
    sentiment = sentiment.item()

    cur = conn.cursor()
    insert_query = f'''
            INSERT INTO {tb_name} (message, sentiment, update_time) 
            VALUES (%s, %s, %s)
            '''
    time_now = datetime.datetime.now()
    insert_data = (text, sentiment, time_now)
    try:
        cur.execute(insert_query, insert_data)
        conn.commit()
        logging.info(f"Data inserted to {tb_name}")
    except Exception as e:
        logging.info(e)
        conn.rollback()
    cur.close()

if __name__ == '__main__':
    bot.infinity_polling()
    conn.close()
