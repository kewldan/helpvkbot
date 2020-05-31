#VK MINECRAFT BOT#
#  By: Avenger   #
#   31.05.2020   #
#  Version: 2.0  #

import vk_api #API #pip install vk_api
from vk_api.longpoll import VkLongPoll, VkEventType #LongPoll
from random import randrange #Случайные числа
from os.path import exists #Для работы с FileSystem
from json import load, dump #JSON
from requests import post #Запросы к YCAPI #pip install requests
from hashlib import sha256 #Хеширование
from sqlite3 import connect #Для БД AuthMe
from ftplib import FTP #Для скачивания БД AuthMe
from threading import Thread #Для потоков

#НАСТРОЙКИ
token = "" #Главный токен

LoggedUsersPath = "./logged.json" #JSON файл для БД
keyboards = {
    "auth": "./keyboards/auth.json", #JSON клавиатуры меню
    "Nauth": "./keyboards/nauth.json", #JSON клавиатуры админ меню
    "close": "./keyboards/close.json" #JSON клавиатуры отмены
}
Keyboards = {
    "guest": "./keyboards2/guest.json", #Клавиатура гостя
    "owner": "./keyboards2/owner.json" #Клавиатура владельца сервера
}
#/////////

if not exists(LoggedUsersPath):
    open(LoggedUsersPath, "w", encoding = "UTF-8").write("{}")
    DataBase = {}
else:
    with open(LoggedUsersPath, "r") as rf:
        DataBase = load(rf)

def have(self, m, i): #Имеет ли массив индекс
    try:
        m[i]
        return True
    except IndexError:
        return False

def checkToken(token):
    temp = vk_api.VkApi(token = token)
    try:
        temp.auth()
    except vk_api.AuthError:
        pass
    try:
        VkLongPoll(temp)
    except vk_api.ApiError as err:
        if err.error["error_code"] == 5:
            return False
        else:
            return err.error["error_code"]
    return True
                                    

def maybeInt(self, inr):
    try:
        int(inr)
        return True
    except TypeError:
        return False

def checkPassword(linePass, checkPass): #Проверяю корректность пароля
    args = linePass.split("$")
    g = sha256(checkPass.encode("UTF-8")).hexdigest() + args[2]
    return linePass == "$SHA$" + args[2] + "$" + sha256(g.encode("UTF-8")).hexdigest()

for u in keyboards:
    if not exists(keyboards[u]):
        print("FATAL ERROR: НЕ НАЙДЕНА КЛАВИАТУРА " + u)
        exit(1)

class Main(Thread):
    def __init__(self, token):
        Thread.__init__(self)
        self.requestAuth = {}
        self.deleteUsers = {}
        self.vk = vk_api.VkApi(token = token) #Сессия VK

        try:
            self.vk.auth() #Авторизуюсь
        except vk_api.AuthError: #Если ошибка авторизации
            pass

    def checkOwner(self, owner_id):
        for h in DataBase:
            if DataBase[h]["OWNER"] == str(owner_id):
                return True
        return False

    def toMenu(self, user_id):
        if self.checkOwner(user_id):
            self.send_msg_with_keyboard(user_id, "Главное меню (Владелец)", Keyboards["owner"])
        else:
            self.send_msg_with_keyboard(user_id, "Главное меню (Гость)", Keyboards["guest"])
    
    def run(self):
        print("Main bot active")
        longpoll = VkLongPoll(self.vk) #Сессия LongPoll

        for event in longpoll.listen(): #Для каждого события
            if event.type == VkEventType.MESSAGE_NEW: #Если событие - сообщение
                if event.to_me: #Если сообщение мне
                    aid = str(event.user_id)
                    cmd = str(event.text).lower()
                    txt = event.text

                    if aid in self.requestAuth:
                        if cmd == "отменить":
                            self.send_msg_without_keyboard(aid, "Успешно, операция отменена")
                            self.toMenu(aid)
                            del self.requestAuth[aid]
                            continue
                        if self.requestAuth[aid][0] == 1:
                            if not txt in DataBase:
                                self.requestAuth[aid][1] = txt
                                self.requestAuth[aid][0] = 2
                                self.send_msg_without_keyboard(aid, "Успешно, введите Токен сообщества сервера (https://vk.com/dev/access_token?f=2.%20Ключ%20доступа%20сообщества)")
                            else:
                                self.send_msg_without_keyboard(aid, "Ошибка, сервер с таким названием уже существует")
                                self.toMenu(aid)
                                del self.requestAuth[aid]
                                continue
                        elif self.requestAuth[aid][0] == 2:
                            if checkToken(txt):
                                self.requestAuth[aid][2]["TOKEN"] = txt
                                self.requestAuth[aid][0] = 3
                                self.send_msg_without_keyboard(aid, "Успешно, введите IP сервера")
                            else:
                                self.send_msg_without_keyboard(aid, "Ошибка, токен не корректен")
                                self.toMenu(aid)
                                del self.requestAuth[aid]
                                continue
                        elif self.requestAuth[aid][0] == 3:
                            self.requestAuth[aid][2]["HOST"] = txt
                            self.requestAuth[aid][0] = 4
                            self.send_msg_without_keyboard(aid, "Успешно, введите привелегию, при которой можно возпользоватся консолью")
                        elif self.requestAuth[aid][0] == 4:
                            self.requestAuth[aid][2]["ConsoleAllowDonate"] = txt
                            self.requestAuth[aid][0] = 5
                            self.send_msg_without_keyboard(aid, "Успешно, введите RCON порт")
                        elif self.requestAuth[aid][0] == 5:
                            self.requestAuth[aid][2]["RCON"]["PORT"] = txt
                            self.requestAuth[aid][0] = 6
                            self.send_msg_without_keyboard(aid, "Успешно, введите RCON пароль")
                        elif self.requestAuth[aid][0] == 6:
                            self.requestAuth[aid][2]["RCON"]["PASSWORD"] = txt
                            self.requestAuth[aid][0] = 7
                            self.send_msg_without_keyboard(aid, "Успешно, введите MINECRAFT порт")
                        elif self.requestAuth[aid][0] == 7:
                            self.requestAuth[aid][2]["MINECRAFT"]["PORT"] = txt
                            self.requestAuth[aid][0] = 8
                            self.send_msg_without_keyboard(aid, "Успешно, введите FTP (Корневая папка - папка с server.jar) пользователя (Нужно право на чтение файлов)")
                        elif self.requestAuth[aid][0] == 8:
                            self.requestAuth[aid][2]["FTP"]["USERNAME"] = txt
                            self.requestAuth[aid][0] = 9
                            self.send_msg_without_keyboard(aid, "Успешно, введите FTP (Корневая папка - папка с server.jar) пароль от пользователя")
                        elif self.requestAuth[aid][0] == 9:
                            self.requestAuth[aid][2]["FTP"]["PASSWORD"] = txt
                            self.requestAuth[aid][0] = 10
                            self.send_msg_without_keyboard(aid, "Успешно, введите FTP (Корневая папка - папка с server.jar) название файла ./plugins/AuthMe/??????.db (По умолчанию это authme.db)")
                        elif self.requestAuth[aid][0] == 10:
                            self.requestAuth[aid][2]["FTP"]["DataBaseFile"] = txt
                            self.send_msg_without_keyboard(aid, "Успешно, ваш сервер зарегистрирован! Бот начнёт работать в ближайшее время")
                            DataBase[self.requestAuth[aid][1]] = self.requestAuth[aid][2]
                            with open(LoggedUsersPath, "w", encoding = "UTF-8") as f:
                                dump(DataBase, f)
                            bots.bots.append(MineBot(self.requestAuth[aid][2]["TOKEN"], self.requestAuth[aid][2], self.requestAuth[aid][1]))
                            bots.bots[len(bots.bots) - 1].start()
                            self.toMenu(aid)
                    
                    if aid in self.deleteUsers:
                        if cmd == "отменить":
                            self.send_msg_without_keyboard(aid, "Успешно, операция отменена")
                            self.toMenu(aid)
                            del self.deleteUsers[aid]
                            continue
                        else:
                            if txt == self.deleteUsers[aid]:
                                del DataBase[txt]
                                with open(LoggedUsersPath, "w", encoding = "UTF-8") as f:
                                    dump(DataBase, f)
                                self.send_msg_without_keyboard(aid, "Успешно, сервер удалён")
                                self.toMenu(aid)
                                del self.deleteUsers[aid]
                                continue
                            else:
                                self.send_msg_without_keyboard(aid, "Ошибка, название сервера не корректно")
                                self.toMenu(aid)
                                del self.deleteUsers[aid]
                                continue

                    
                    if cmd in ["начать", "меню", "старт", "привет", "Start"]:
                        self.toMenu(aid)
                    elif cmd == "зарегистрировать сервер" and not self.checkOwner(aid):
                        self.requestAuth[aid] = [1, "name", {
                            "TOKEN": "",
                            "OWNER": aid,
                            "HOST": "ip",
                            "ConsoleAllowDonate": "console",
                            "authed": {},
                            "RCON": {
                                "PORT": -1,
                                "PASSWORD": "rpass"
                            },
                            "MINECRAFT": {
                                "PORT": -1
                            },
                            "FTP": {
                                "USERNAME": "user",
                                "PASSWORD": "fpass",
                                "DataBaseFile": "dbf"
                            }
                        }]
                        self.send_msg_with_keyboard(aid, "Успешно, запрос обрабатывается, введите Название сервера", keyboards["close"])
                    elif cmd == "удалить сервер" and self.checkOwner(aid):
                        nam = ""
                        for f in DataBase:
                            if DataBase[f]["OWNER"] == aid:
                                nam = f
                        self.deleteUsers[aid] = nam
                        self.send_msg_with_keyboard(aid, "Успешно, введите название сервера для подтверждения операции (" + nam + ")", keyboards["close"])
                    elif cmd == "управлять сервером" and self.checkOwner(aid):
                        self.send_msg_without_keyboard(aid, "Извините, данная функция в разработке =(")
                    self.vk.method("messages.markAsRead", {"peer_id": aid, "message_id": self.vk.method("messages.getHistory", {"user_id": aid, "count": 1})["items"][0]["id"]}) #Читаю сообщение

    def send_msg_without_keyboard(self, peer, message): #Отправить сообщение без клавиатуры
        self.vk.method("messages.send", {"peer_id": peer, "message": message, "random_id": randrange(0, 184467440737095516165, 1)})

    def send_msg_with_keyboard(self, peer, message, keyboardFilePath): #Отправить сообщение с клавиатурой
        self.vk.method("messages.send", {"peer_id": peer, "message": message, "keyboard": open(keyboardFilePath, "r", encoding="UTF-8").read(), "random_id": randrange(0, 184467440737095516165, 1)})

class MineBot(Thread):
    def __init__(self, token, settings, name):
        Thread.__init__(self)
        self.Server = settings
        self.name = name
        self.authed = self.Server["authed"]
        self.vk = vk_api.VkApi(token = token) #Сессия VK

        self.authUsers = {} #Пользователи которые авториуются
        self.enterUsers = {} #Пользователи которые вводят команду
        self.changeUsers = {}

        try:
            self.vk.auth() #Авторизуюсь
        except vk_api.AuthError: #Если ошибка авторизации
            pass
    
    def run(self):
        print("Mine bot " + self.name + " is active")
        longpoll = VkLongPoll(self.vk) #Сессия LongPoll

        for event in longpoll.listen(): #Для каждого события
            if event.type == VkEventType.MESSAGE_NEW: #Если событие - сообщение
                if event.to_me: #Если сообщение мне
                    aid = str(event.user_id)
                    cmd = str(event.text).lower()

                    if aid in self.authUsers:
                        if cmd == "отменить":
                            self.send_msg_with_keyboard(aid, "Для доступа к консоли введите логин и пароль", keyboards["Nauth"])
                            del self.authUsers[aid]
                        elif self.authUsers[aid][0] == 1:
                            self.authUsers[aid] = [2, event.text]
                            self.send_msg_without_keyboard(aid, "Успешно, введите пароль")
                        elif self.authUsers[aid][0] == 2:
                            if self.getDBFile(self.Server["HOST"], self.Server["FTP"]["USERNAME"], self.Server["FTP"]["PASSWORD"]) == -1:
                                self.send_msg_with_keyboard(aid, "Ошибка, ошибка настроек сервера", keyboards["Nauth"])
                                del self.authUsers[aid]
                                continue
                            conn = connect("DB" + self.name + ".db")
                            cursor = conn.cursor()
                            cursor.execute("SELECT * FROM 'authme'")
                            conn.commit()
                            isHave = -1
                            for u in cursor.fetchall():
                                if u[1] == self.authUsers[aid][1]:
                                    isHave = u[3]
                            if isHave == -1:
                                self.send_msg_with_keyboard(aid, "Ошибка, вас нету в базе данных AuthMe", keyboards["Nauth"])
                                del self.authUsers[aid]
                                continue
                            valid = True
                            free = False
                            if not checkPassword(isHave, event.text):
                                valid = False
                            if valid: #Если логин и пароль верны
                                for i in self.authed: #Если нету такого ника в базе
                                    if self.authed[i][0] == self.authUsers[aid][1]:
                                        self.send_msg_with_keyboard(aid, "Ошибка, к этому аккаунту уже привязан ВК профиль", keyboards["Nauth"])
                                        del self.authUsers[aid]
                                        free = True
                                if free:
                                    continue
                                rs = post("https://ylousrp.ru/API/getPlayerDonate.php", data = {"ip": self.Server["HOST"], "port": self.Server["RCON"]["PORT"], "password": self.Server["RCON"]["PASSWORD"], "player": self.authUsers[aid][1]})
                                if not rs.status_code == 200:
                                    self.send_msg_with_keyboard(aid, "Ошибка, YCAPI не доступен", keyboards["Nauth"])
                                    del self.authUsers[aid]
                                    continue
                                else:
                                    if rs.text == "Connecting error":
                                        self.send_msg_with_keyboard(aid, "Ошибка, сервер Minecraft отключен", keyboards["Nauth"])
                                        del self.authUsers[aid]
                                        continue
                                    else:
                                         if not rs.text == self.Server["ConsoleAllowDonate"]:
                                            self.send_msg_with_keyboard(aid, "Ошибка, пользователь с этим ником не имеет привелегии " + self.Server["ConsoleAllowDonate"], keyboards["Nauth"])
                                            del self.authUsers[aid]
                                            continue
                                self.authed[aid] = [self.authUsers[aid][1], event.text]
                                with open(LoggedUsersPath, "w") as wf:
                                    dump(self.authed, wf)
                                self.send_msg_with_keyboard(aid, "Успешно, вы авторизованы", keyboards["auth"])
                                del self.authUsers[aid]
                            else:
                                self.send_msg_with_keyboard(aid, "Ошибка, логин или пароль некорректны", keyboards["Nauth"])
                                del self.authUsers[aid]
                                continue

                    if aid in self.enterUsers:
                        if cmd == "отменить":
                            self.send_msg_with_keyboard(aid, "Главное меню", keyboards["auth"])
                            del self.enterUsers[aid]
                        elif self.enterUsers[aid][0] == 1:
                            rs = post("https://ylousrp.ru/API/rcon.php", data = {"ip": self.Server["HOST"], "port": self.Server["RCON"]["PORT"], "password": self.Server["RCON"]["PASSWORD"], "cmd": event.text})
                            if not rs.status_code == 200:
                                print(rs.status_code)
                                self.send_msg_with_keyboard(aid, "Ошибка, YCAPI не доступен", keyboards["auth"])
                                del self.enterUsers[aid]
                            else:
                                if rs.text == "Connecting error":
                                    self.send_msg_with_keyboard(aid, "Ошибка, сервер Minecraft отключен", keyboards["auth"])
                                    del self.enterUsers[aid]
                                elif rs.text == "REQUEST INVALID":
                                    print("ERROR:", rs.text)
                                    self.send_msg_with_keyboard(aid, "Ошибка, внутриняя ошибка скрипта бота", keyboards["auth"])
                                    del self.enterUsers[aid]
                                else: 
                                    try:
                                        self.send_msg_with_keyboard(aid, rs.text, keyboards["auth"])
                                    except:
                                        pass
                                    del self.enterUsers[aid]

                    if aid in self.changeUsers:
                        if cmd == "отменить":
                            self.send_msg_with_keyboard(aid, "Главное меню", keyboards["auth"])
                            del self.changeUsers[aid]
                        elif self.changeUsers[aid][0] == 1:
                            self.changeUsers[aid] = [2, event.text]
                            self.send_msg_without_keyboard(aid, "Успешно, введите новый пароль")
                        elif self.changeUsers[aid][0] == 2:
                            if self.authed[aid][1] == self.changeUsers[aid][1]:
                                rs = post("https://ylousrp.ru/API/rcon.php", data = {"ip": self.Server["HOST"], "port": self.Server["RCON"]["PORT"], "password": self.Server["RCON"]["PASSWORD"], "cmd": "authme password " + self.authed[aid][0] + " " + event.text})
                                if not rs.status_code == 200:
                                    print(rs.status_code)
                                    self.send_msg_with_keyboard(aid, "Ошибка, YCAPI не доступен", keyboards["auth"])
                                    del self.changeUsers[aid]
                                else:
                                    if rs.text == "Connecting error":
                                        self.send_msg_with_keyboard(aid, "Ошибка, сервер Minecraft отключен", keyboards["auth"])
                                        del self.changeUsers[aid]
                                    elif rs.text == "REQUEST INVALID":
                                        print("ERROR:", rs.text)
                                        self.send_msg_with_keyboard(aid, "Ошибка, внутриняя ошибка скрипта бота", keyboards["auth"])
                                        del self.changeUsers[aid]
                                    else: 
                                        self.send_msg_with_keyboard(aid, "Успешно, пароль изменён", keyboards["auth"])
                                        del self.changeUsers[aid]
                            else:
                                self.send_msg_with_keyboard(aid, "Ошибка, ваш старый пароль некорректен", keyboards["auth"])
                                del self.changeUsers[aid]

                    if cmd in ["начать", "меню", "старт", "привет", "Start"]:
                        if aid in self.authed:
                            self.send_msg_with_keyboard(aid, "Главное меню", keyboards["auth"])
                        else:
                            self.send_msg_with_keyboard(aid, "Для доступа к консоли введите логин и пароль", keyboards["Nauth"])
                    elif cmd == "зарегистрироваться" and not aid in self.authed:
                        self.authUsers[aid] = [1, "login"]
                        self.send_msg_with_keyboard(aid, "Введите свой никнейм", keyboards["close"])
                    elif cmd == "ввести команду" and aid in self.authed and not aid in self.changeUsers:
                        self.enterUsers[aid] = [1, "cmd"]
                        self.send_msg_with_keyboard(aid, "Успешно, введите команду", keyboards["close"])
                    elif cmd == "сменить пароль" and aid in self.authed and not aid in self.enterUsers:
                        self.changeUsers[aid] = [1, "oldPass"]
                        self.send_msg_with_keyboard(aid, "Успешно, введите старый пароль", keyboards["close"])
                    self.vk.method("messages.markAsRead", {"peer_id": aid, "message_id": self.vk.method("messages.getHistory", {"user_id": aid, "count": 1})["items"][0]["id"]}) #Читаю сообщение

    def getDBFile(self, host, user, password): #Получаю по FTP БД AuthMe
        try:
            ftp = FTP(host, user, password)
        except:
            return -1
        ftp.login(user, password)
        ftp.cwd("plugins")
        ftp.cwd("AuthMe")
        if post("https://ylousrp.ru/API/monitoring.php", {"ip": self.Server["MINECRAFT"]["HOST"], "port": self.Server["MINECRAFT"]["PORT"]}).json()["online"]:
            post("https://ylousrp.ru/API/rcon.php", data = {"ip": self.Server["HOST"], "port": self.Server["RCON"]["PORT"], "password": self.Server["RCON"]["PASSWORD"], "cmd": "plugman disable AuthMe"})
        with open("DB" + self.name + ".db", "wb") as f:
            ftp.retrbinary("RETR " + self.Server["FTP"]["DataBaseFile"], f.write)
        ftp.quit()
        if post("https://ylousrp.ru/API/monitoring.php", {"ip": self.Server["MINECRAFT"]["HOST"], "port": self.Server["MINECRAFT"]["PORT"]}).json()["online"]:
            post("https://ylousrp.ru/API/rcon.php", data = {"ip": self.Server["HOST"], "port": self.Server["RCON"]["PORT"], "password": self.Server["RCON"]["PASSWORD"], "cmd": "plugman enable AuthMe"})

    def send_msg_without_keyboard(self, peer, message): #Отправить сообщение без клавиатуры
        self.vk.method("messages.send", {"peer_id": peer, "message": message, "random_id": randrange(0, 184467440737095516165, 1)})

    def send_msg_with_keyboard(self, peer, message, keyboardFilePath): #Отправить сообщение с клавиатурой
        self.vk.method("messages.send", {"peer_id": peer, "message": message, "keyboard": open(keyboardFilePath, "r", encoding="UTF-8").read(), "random_id": randrange(0, 184467440737095516165, 1)})



class Bots:
    def __init__(self, mainToken):
        self.bots = []
        self.mainBot = Main(mainToken)
        for b in DataBase:
            self.bots.append(MineBot(DataBase[b]["TOKEN"], DataBase[b], b))
            self.bots[len(self.bots) - 1].start()
        self.mainBot.start()
bots = Bots(token)