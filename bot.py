import vk_api #API
from vk_api.longpoll import VkLongPoll, VkEventType #LongPoll
from random import randrange #Случайные числа
from fuzzywuzzy.fuzz import ratio #Библиотека сравнения
from os.path import exists #Для работы с FileSystem
import json


#НАСТРОЙКИ
token = "" #Токен сообщества
adminID = [248451355] #ID администраторов
eventsDebug = False #Включить логирование событей Longpoll
DataBaseFile = "faq.txt" #Файл для сохранения вопросов
TempFile = "forModeration.txt" #Файл для сохранения предложений
BlackListFile = "blacklist.txt" #Файл для сохранения ЧС
blackListLetters = "bad.json" #Файл JSON с нецензурными словами
keyboards = {
    "menu": "./keyboards/menu.json", #JSON клавиатуры меню
    "aMenu": "./keyboards/aMenu.json", #JSON клавиатуры админ меню
    "close": "./keyboards/close.json", #JSON клавиатуры отмены
    "badFAQ": "./keyboards/badFAQ.json" #JSON клавиатуры после получения ответа
}
allowTranslate = True #Включить трансформацию слов (ghbdtn -> привет)
#/////////

if not exists(DataBaseFile):
    open(DataBaseFile, "w", encoding = "UTF-8")
if not exists(TempFile):
    open(TempFile, "w", encoding = "UTF-8")
if not exists(BlackListFile):
    open(BlackListFile, "w", encoding = "UTF-8")

for u in keyboards:
    if not exists(keyboards[u]):
        print("FATAL ERROR: НЕ НАЙДЕНА КЛАВИАТУРА " + u)
        exit(1)

bl = {}
blf = open(BlackListFile, "r", encoding = "UTF-8").read().split("\n")
for f in range(len(blf)):
    if blf[f]:
        bl[int(blf[f].split()[0])] = int(blf[f].split()[1])

if exists(blackListLetters):
    with open(blackListLetters, "r", encoding = "UTF-8") as read_file:
       bad = json.load(read_file)
else:
    print("FATAL ERROR: НЕ НАЙДЕНЫ ПЛОХИЕ СЛОВА")

vk_session = vk_api.VkApi(token = token)

waitUsers = {} #Пользователи которые вводят вопрос
addAdmins = {} #Администраторы которые добавляют вопрос
addUsers = {} #Пользователи которые предлагают свой вопрос

try:
    vk_session.auth() #Авторизуюсь
except vk_api.AuthError:
    pass

longpoll = VkLongPoll(vk_session) #Сессия LongPoll

def get_user(user_id): #Получить профиль человека
    return vk_session.method("users.get", {"user_id": user_id, "fields": "city, sex", "name_case": "Nom"})

def send_msg_without_keyboard(peer, message): #Отправить сообщение без клавиатуры
    vk_session.method("messages.send", {"peer_id": peer, "message": message, "random_id": randrange(0, 184467440737095516165, 1)})

def send_msg_with_keyboard(peer, message, keyboardFilePath): #Отправить сообщение с клавиатурой
    vk_session.method("messages.send", {"peer_id": peer, "message": message, "keyboard": open(keyboardFilePath, "r", encoding="UTF-8").read(), "random_id": randrange(0, 184467440737095516165, 1)})

def have(m, i): #Имеет ли массив индекс
    try:
        m[i]
        return True
    except IndexError:
        return False

def translate(cmd):
    replacer = {
            "q":"й", "w":"ц", "e":"у", "r":"к", "t":"е", "y":"н", "u":"г",
            "i":"ш", "o":"щ", "p":"з", "[":"х", "]":"ъ", "a":"ф", "s":"ы",
            "d":"в", "f":"а", "g":"п", "h":"р", "j":"о", "k":"л", "l":"д",
            ";":"ж", "'":"э", "z":"я", "x":"ч", "c":"с", "v":"м", "b":"и",
            "n":"т", "m":"ь", ",":"б", ".":"ю", "/":"."
    }  
    t = ""
    for j in cmd:
        try:
            t += replacer[j]
        except KeyError:
            t += j
    return t

def send_msgs(peers, message): #Отправить рассылку
    if len(peers) > 100:
        return
    rt = ""
    for key in range(len(peers)):
        if key:
            rt += "," + str(peers[key])
        else:
            rt += str(peers[key])
    vk_session.method("messages.send", {"user_ids": rt, "message": message, "random_id": randrange(0, 184467440737095516165, 1)})
    

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW: #Если событие - сообщение
        if event.to_me: #Если сообщение мне
            if event.user_id in bl:
                if not bl[event.user_id]:
                    send_msg_without_keyboard(event.user_id, "Ошибка, вы находитесь в ЧС, если это ошибка - напишите администратору")
                    bl[event.user_id] = 1
                    nCont = ""
                    for g in bl:
                        nCont += str(g) + " " + str(bl[g]) + "\n"
                    open(BlackListFile, "w", encoding = "UTF-8").write(nCont)
                continue

            author = get_user(event.user_id)[0] #Получаю профиль автора
            if allowTranslate:
                cmd = translate(str(event.text).lower()) #Получаю команду
            else:
                cmd = str(event.text).lower() #Получаю команду
            aid = event.user_id #ID пользователя
            if aid in addUsers: #Если автор предлагает вопрос
                if cmd == "отменить":
                    if aid in adminID:
                        send_msg_with_keyboard(aid, "Главное меню (Админ)", keyboards["aMenu"])
                    else:
                        send_msg_with_keyboard(aid, "Главное меню", keyboards["menu"])
                    del addUsers[aid]
                else:
                    if addUsers[aid][0] == 1:
                        send_msg_without_keyboard(aid, "Успешно, жду ответ...")
                        addUsers[aid] = [2, cmd]
                    elif addUsers[aid][0] == 2:
                        send_msg_without_keyboard(aid, "Успешно, ваш вопрос/ответ отправлен на модерирование")
                        j = open(TempFile, "a", encoding = "UTF-8")
                        j.write("\n" + addUsers[aid][1] + "**&?<Mod>*" + cmd + "**&?<Mod>*" + str(aid))
                        j.close()
                        del addUsers[aid]
                        if aid in adminID:
                            send_msg_with_keyboard(aid, "Главное меню (Админ)", keyboards["aMenu"])
                        else:
                            send_msg_with_keyboard(aid, "Главное меню", keyboards["menu"])

            if aid in addAdmins: #Если админ добавляет вопрос
                if addAdmins[aid][0] == 1:
                    addAdmins[aid] = [2, cmd]
                    send_msg_without_keyboard(aid, "Успешно, ожидаю ответ...")
                elif addAdmins[aid][0] == 2:
                    DB = open(DataBaseFile, "a", encoding = "UTF-8")
                    DB.write("\n" + addAdmins[aid][1] + "**&?<How>*" + cmd)
                    DB.close()
                    send_msg_without_keyboard(aid, "Успешно, ваш вопрос/ответ записан: " + addAdmins[aid][1] + "**&?<How>*" + cmd)
                    del addAdmins[aid]
            if aid in waitUsers:
                if waitUsers[aid][0] == 2 and cmd == "это не ответ на мой вопрос":
                    send_msg_with_keyboard(aid, "Ошибка, я не знаю ответ на ваш вопрос. Я уже написал администратору что надо добавить ваш вопрос в базу", keyboards["menu"])
                    send_msgs(adminID, "Человек (https://vk.com/id" + str(aid) + ") не нашёл ответ на свой вопрос: " + str(waitUsers[aid][1]))
                    del waitUsers[aid]
                elif waitUsers[aid][0] == 2 and cmd == "спасибо":
                    if aid in adminID:
                        send_msg_with_keyboard(aid, "Главное меню (Админ)", keyboards["aMenu"])
                    else:
                        send_msg_with_keyboard(aid, "Главное меню", keyboards["menu"])
                elif waitUsers[aid][0] == 1:
                    if cmd == "отменить":
                        del waitUsers[aid]
                        if aid in adminID:
                            send_msg_with_keyboard(aid, "Главное меню (Админ)", keyboards["aMenu"])
                        else:
                            send_msg_with_keyboard(aid, "Главное меню", keyboards["menu"])
                    else:
                        #Проверка на плохие слова
                        jh = False 
                        for k in cmd.split():
                            if k in bad:
                                nCont = ""
                                for g in bl:
                                    nCont += str(g) + " " + str(bl[g]) + "\n"
                                nCont += str(aid) + " 0\n"
                                bl[aid] = 0
                                open(BlackListFile, "w", encoding = "UTF-8").write(nCont)
                                if aid in adminID:
                                    send_msg_with_keyboard(aid, "Ты назвал нецензурный вопрос, ты добавлен в ЧС бота", keyboards["aMenu"])
                                else:
                                    send_msg_with_keyboard(aid, "Ты назвал нецензурный вопрос, ты добавлен в ЧС бота", keyboards["menu"])
                                jh = True
                        if jh:
                            continue
                        DataBase = open(DataBaseFile, "r", encoding = "UTF-8").read().split("\n")
                        r = {"index": 0, "percent": 0}
                        for l in range(len(DataBase)):
                            if not DataBase[l]:
                                continue
                            h = ratio(cmd, DataBase[l].split("**&?<How>*")[0])
                            if h > r["percent"]:
                                r["index"] = l
                        waitUsers[aid][1] = cmd
                        send_msg_with_keyboard(aid, "Успешно, я выбрал самый похожий вопрос (" + str(DataBase[r["index"]].split("**&?<How>*")[0]) + ") и вот на него ответ: " + str(DataBase[r["index"]].split("**&?<How>*")[1]), keyboards["badFAQ"])
                        waitUsers[aid][0] = 2
            if cmd == "старт" or cmd == "меню" or cmd == "начать": #Основные команды
                if aid in adminID:
                    send_msg_with_keyboard(aid, "Главное меню (Админ)", keyboards["aMenu"])
                else:
                    send_msg_with_keyboard(aid, "Главное меню", keyboards["menu"])
            elif cmd == "задать вопрос" and not aid in addUsers:
                send_msg_with_keyboard(aid, "Ожидаю вопрос...", keyboards["close"])
                waitUsers[aid] = [1, ""]
            elif cmd == "предложить вопрос" and not aid in waitUsers:
                send_msg_with_keyboard(aid, "Ожидаю вопрос...", keyboards["close"])
                addUsers[aid] = [1, "Q"]
            elif cmd == "добавить":
                if not aid in adminID:
                    send_msg_without_keyboard(aid, "Ошибка, вы не Администратор")
                    continue
                send_msg_without_keyboard(aid, "Ожидаю вопрос...")
                addAdmins[aid] = [1, "Q"]
            elif cmd == "просмотреть предложения":
                if not aid in adminID:
                    send_msg_without_keyboard(aid, "Ошибка, вы не Администратор")
                    continue
                DB = list(filter(None, open(TempFile, "r", encoding = "UTF-8").read().split("\n")))
                string = ""
                for y in range(len(DB)):
                    if y:
                        string += str(y) + ". " + str(DB[y].split("**&?<Mod>*")[0]) + "  Ответ: " + str(DB[y].split("**&?<Mod>*")[1]) + "  От: https://vk.com/id" + str(DB[y].split("**&?<Mod>*")[2]) + " ;\n"
                if len(DB) >= 1:
                    send_msg_without_keyboard(aid, "Вопросы на модерацию:\n" + string)
                    send_msg_without_keyboard(aid, "Подсказка: введите удалить {Index} что бы отклонить предложение\nВведите проверка {Index} что бы добавить предложение в основную БД")
                else:
                    send_msg_without_keyboard(aid, "Ошибка, нет предложений на модерацию")
            elif cmd.split()[0] == "удалить":
                if not aid in adminID:
                    send_msg_without_keyboard(aid, "Ошибка, вы не Администратор")
                    continue
                if not have(cmd.split(), 1):
                    send_msg_without_keyboard(aid, "Ошибка, вы не ввели index")
                    continue
                loaded = open(TempFile, "r", encoding = "UTF-8").read().split("\n")
                if have(loaded, int(cmd.split()[1])):
                    del loaded[int(cmd.split()[1])]
                    open(TempFile, "w", encoding = "UTF-8").write('\n'.join(str(e) for e in loaded))
                    send_msg_without_keyboard(aid, "Успешно, предложение отклонено")
                else:
                    send_msg_without_keyboard(aid, "Ошибка, в базе данных нету строки с индексом " + str(cmd.split()[1]))
                    continue
            elif cmd.split()[0] == "проверка":
                if not aid in adminID:
                    send_msg_without_keyboard(aid, "Ошибка, вы не Администратор")
                    continue
                if not have(cmd.split(), 1):
                    send_msg_without_keyboard(aid, "Ошибка, вы не ввели index")
                    continue
                h = open(TempFile, "r", encoding = "UTF-8").read().split("\n")
                if not have(h, int(cmd.split()[1])):
                    send_msg_without_keyboard(aid, "Ошибка, в базе данных нету строки с индексом " + str(cmd.split()[1]))
                    continue
                else:
                    h = h[int(cmd.split()[1])]
                g = open(DataBaseFile, "a", encoding = "UTF-8")
                g.write("\n" + h.split("**&?<Mod>*")[0] + "**&?<How>*" + h.split("**&?<Mod>*")[1])
                g.close()
                loaded = open(TempFile, "r", encoding="UTF-8").read().split("\n")
                del loaded[int(cmd.split()[1])]
                open(TempFile, "w", encoding = "UTF-8").write('\n'.join(str(e) for e in loaded))
                send_msg_without_keyboard(aid, "Успешно, предложение принято")
            elif cmd == "мы":
                send_msg_without_keyboard(aid, """
Создатель: Даниил
Discord: Avenger#1818
Версия: 1.1
Библиотеки: vk_api, requests, fuzzywuzzy
                """)

            vk_session.method("messages.markAsRead", {"peer_id": aid, "message_id": vk_session.method("messages.getHistory", {"user_id": aid, "count": 1})["items"][0]["id"]}) #Читаю сообщение
    else:
        if eventsDebug: #Если отладка
            print(event.type, event.raw[1:]) #Пишу событие
