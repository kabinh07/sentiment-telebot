FROM python:3.10.12-slim

COPY . ./app

WORKDIR /app

RUN pip install --no-cache -r requirements.txt

ARG ENV_FILE=.env
RUN export $(egrep -v '^#' .env | xargs)

CMD ["python", "bot.py"]