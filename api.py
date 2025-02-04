import base64
import hashlib
import io
import random
import socket
import sys
from datetime import datetime

from python3_anticaptcha import ImageToTextTask

import matplotlib.pyplot as plt
import requests
from PIL import Image
from loguru import logger
from python_rucaptcha import ImageCaptcha

import config
import utils

logger.remove()
logger.add(sys.stderr, format="{time:HH:mm:ss.SSS}{message}", level=config.level)

servers = utils.getServers()


class Client101:
    def __init__(self, _type):
        self._type = _type

    def connect(self, server):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(server)

    def getSessionKey(self):
        currTime = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        self.sock.sendall(utils.marshal(
            {
                "tz": "+02:00",
                "t": currTime,
                "p": 11,
                "pl": "iphone",
                "l": "ru",
                "d": "iPhone8,4",
                "ios": "14.4",
                "v": "1.3.0",
                "n": "101.ios",
                "command": "c"
            }
        ).encode()
                          )
        data = self.sock.recv(4096).decode()
        logger.debug(data)
        key = utils.unMarshal(data)[0]["key"]
        return key

    def verifySession(self, key):
        verifData = base64.b64encode(hashlib.md5((key + config.SIGN_KEY).encode()).digest()).decode()
        self.sock.sendall(
            utils.marshal(
                {
                    "hash": verifData,
                    "command": "sign"
                }
            ).encode()
        )
        data = self.sock.recv(4096).decode()
        logger.debug(data)
        logger.info(f"[{self._type.upper()}] Session verified")

    @logger.catch
    def register(self):
        self.sock.sendall(
            utils.marshal(
                {
                    "command": "get_captcha"
                }
            ).encode()
        )
        data1 = utils.unMarshal(self.sock.recv(4096).decode())
        logger.debug(data1)
        data2 = utils.unMarshal(self.sock.recv(4096).decode())
        logger.debug(data2)
        captcha = ""
        url = data1[0].get("url") or data2[0].get("url")
        if url:
            logger.info(f"[{self._type.upper()}] Solving captcha...")
            if config.HUMAN_CAPTCHA_SOLVE:
                r = requests.get(url)
                plt.imshow(Image.open(io.BytesIO(r.content)))
                plt.show(block=False)
                captcha = input("Answer: ")
                plt.close(1)
            else:
                answer = ImageToTextTask.ImageToTextTask(anticaptcha_key = config.RUCAPTCHA_KEY).captcha_handler(captcha_link=url)
                logger.info(f"[{self._type.upper()}] ANSWER {answer}")
                res = answer.get('solution')
                captcha = res.get("text")
                captchaId = answer.get("taskId")
                logger.info(f"[{self._type.upper()}] {captcha} {captchaId}")

        name = utils.get_random_name()
        self.sock.sendall(
            utils.marshal(
                {
                    "name": name,
                    "captcha": captcha,
                    "command": "register"
                }
            ).encode()
        )
        data = self.sock.recv(4096).decode()
        logger.debug(data)
        if captcha:
            data = self.sock.recv(4096).decode()
            logger.debug(data)
        data = utils.unMarshal(data)
        if data[0].get("command") == "set_token":
            token = data[0]["token"]
            logger.info(f"[{self._type.upper()}] Account is ready(name={name}, token={token})")
            return token
        if not config.HUMAN_CAPTCHA_SOLVE:
            r = requests.get("http://rucaptcha.com/res.php", params={
                "key": config.RUCAPTCHA_KEY,
                "action": "reportbad",
                "id": captchaId,
            })
        logger.info(f"[{self._type.upper()}] Bad captcha")
        return ""

    def auth(self, token):
        self.sock.sendall(
            utils.marshal(
                {
                    "token": token,
                    "command": "auth"
                }
            ).encode()
        )
        for _ in range(3):
            data = self.sock.recv(4096)
            try:
                logger.debug(data.decode())
            except UnicodeDecodeError:
                logger.debug(data)
        logger.info(f"[{self._type.upper()}] Auth is successful")

    def createGame(self, bet) -> int:
        pwd = str(random.randint(1000, 9999))
        self.sock.sendall(
            utils.marshal(
                {
                    "bet": bet,
                    "password": pwd,
                    "fast": True,
                    "players": 2,
                    "deck": 36,
                    "hand": 4,
                    "command": "create"
                }
            ).encode()
        )
        for _ in range(2):
            data = self.sock.recv(4096).decode()
            logger.debug(data)
        logger.info(f"[{self._type.upper()}] Game has been created(pwd={pwd})")
        return pwd

    def sendFriendRequest(self):
        self.sock.sendall(
            utils.marshal(
                {
                    "id": config.USER_ID,
                    "command": "friend_request"
                }
            ).encode()
        )
        data = self.sock.recv(4096).decode()
        logger.info(f"[{self._type.upper()}] Sent friend request")
        logger.debug(data)

    def inviteToGame(self):
        self.sock.sendall(
            utils.marshal(
                {
                    "user_id": config.USER_ID,
                    "command": "invite_to_game"
                }
            ).encode()
        )
        data = self.sock.recv(4096).decode()
        logger.debug(data)
        logger.info(f"[{self._type.upper()}] Invited to game")

    def ready(self):
        self.sock.sendall(
            utils.marshal(
                {
                    "command": "ready"
                }
            ).encode()
        )
        '''for _ in range(2):
            data = self.sock.recv(4096).decode()
            messages = utils.unMarshal(data)
            logger.debug(messages)'''
        logger.info(f"[{self._type.upper()}] Ready")

    def exit(self):
        self.sock.sendall(
            utils.marshal(
                {
                    "command": "surrender"
                }
            ).encode()
        )
        data = self.sock.recv(4096).decode()
        logger.debug(data)
        logger.info(f"[{self._type.upper()}] Game over")
     
    def buy_points(self):
        self.sock.sendall(
        utils.marshal(
                {
                    "command": "buy_points",
                    "id": "com.rstgames.101.points.0"                    
                }
            ).encode()
        )
        data = self.sock.recv(4096).decode()
        logger.info(data)
        logger.info(f"[{self._type.upper()}] Buy Points")
        

    def getMessagesUpdate(self):
        messages = utils.unMarshal(self.sock.recv(1024).decode())
        logger.debug(messages)
        for message in messages:
            if message.get("user"):
                _id = message["user"]["id"]
                return _id
        return ""

    def acceptFriendRequest(self, _id):
        self.sock.sendall(
            utils.marshal(
                {
                    "id": _id,
                    "command": "friend_accept"
                }
            ).encode()
        )
        for _ in range(2):
            data = self.sock.recv(4096).decode()
            logger.debug(data)
        logger.info(f"[{self._type.upper()}] Accepted friend")

    def getInvites(self):
        data = utils.unMarshal(self.sock.recv(4096).decode())
        logger.debug(data)
        if data[0].get("command") == "invite_to_game":
            gameId = data[0]["game_id"]
            return gameId
        return ""

    def join(self, _id, pwd):
        self.sock.sendall(
            utils.marshal(
                {
                    "password": pwd,
                    "id": _id,
                    "command": "join"
                }
            ).encode()
        )
        for _ in range(2):
            data = self.sock.recv(4096).decode()
            logger.debug(data)
        logger.info(f"[{self._type.upper()}] Joined the game")

    def leave(self, _id):
        self.sock.sendall(
            utils.marshal(
                {
                    "id": _id,
                    "command": "leave"
                }
            ).encode()
        )
        for _ in range(3):
            data = utils.unMarshal(self.sock.recv(4096).decode())
            logger.debug(data)
            for i in data:
                if isinstance(i, dict):
                    if i.get("k") == "points":
                        points = i["v"]
        logger.info(f"[{self._type.upper()}] Leaved the game(points={points})")

    def deleteFriend(self, _id):
        self.sock.sendall(
            utils.marshal(
                {
                    "id": _id,
                    "command": "friend_delete"
                }
            ).encode()
        )
        for _ in range(3):
            data = self.sock.recv(4096).decode()
            logger.debug(data)
        logger.info(f"[{self._type.upper()}] Friend has been deleted")

    def turn(self):
        card = random.choice(self.cards)
        self.sock.sendall(
            utils.marshal(
                {
                    "c": card,
                    "command": "t"
                }
            ).encode()
        )
        for _ in range(4):
            data = self.sock.recv(4096).decode()
            logger.debug(data)
        logger.info(f"[{self._type.upper()}] Played with card " + card)
        self.cards.remove(card)

    def waitingFor(self):
        while True:
            messages = utils.unMarshal(self.sock.recv(4096).decode())
            logger.debug(messages)
            for message in messages:
                if message.get("command") == "hand":
                    self.cards: list = message["cards"]
                elif message.get("command") == "turn":
                    self.trump = message["trump"]
                elif message.get("command") in ("mode", "end_turn", "t"):
                    return

    def take(self):
        self.sock.sendall(
            utils.marshal(
                {
                    "command": "take"
                }
            ).encode()
        )
        data = self.sock.recv(4096).decode()
        logger.debug(data)
        logger.info(f"[{self._type.upper()}] Taken the card")

    def _pass(self):
        self.sock.sendall(
            utils.marshal(
                {
                    "command": "pass"
                }
            ).encode()
        )
        for _ in range(2):
            data = self.sock.recv(4096).decode()
            logger.debug(data)
        logger.info(f"[{self._type.upper()}] Done")
