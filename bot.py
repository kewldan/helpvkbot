import vk_api #API
from vk_api.longpoll import VkLongPoll, VkEventType #LongPoll
from random import randrange #Случайные числа
from fuzzywuzzy.fuzz import ratio #Библиотека сравнения
from os.path import exists #Для работы с FileSystem
from json import load, dump

#НАСТРОЙКИ
token = "cdea1df1d647fac87586fa58e01dd7f0a930182ef3738d89d2d035ce094c9840dfe6586682cf8c5005d12" #Токен сообщества
adminID = [248451355] #ID администраторов
eventsDebug = False #Включить логирование событей Longpoll
DataBaseFile = "faq.json" #Файл для сохранения вопросов
TempFile = "forModeration.json" #Файл для сохранения предложений
BlackListFile = "blacklist.json" #Файл для сохранения ЧС
blackListLetters = "bad.json" #Файл JSON с нецензурными словами
keyboards = {
    "menu": "./keyboards/menu.json", #JSON клавиатуры меню
    "aMenu": "./keyboards/aMenu.json", #JSON клавиатуры админ меню
    "close": "./keyboards/close.json", #JSON клавиатуры отмены
    "badFAQ": "./keyboards/badFAQ.json" #JSON клавиатуры после получения ответа
}
allowTranslate = False #Включить трансформацию слов (ghbdtn -> привет)
#/////////

if not exists(DataBaseFile):
    open(DataBaseFile, "w", encoding = "UTF-8").write("[]")
if not exists(TempFile):
    open(TempFile, "w", encoding = "UTF-8").write("[]")
if not exists(BlackListFile):
    open(BlackListFile, "w", encoding = "UTF-8").write("{}")


for u in keyboards:
    if not exists(keyboards[u]):
        print("FATAL ERROR: НЕ НАЙДЕНА КЛАВИАТУРА " + u)
        exit(1)

#ЗАГРУЗКА
#Загрузка BlackList (ЧС)
with open(BlackListFile, "r", encoding = "UTF-8") as blf:
    bl = load(blf)

#ЗАГРУЗКА DB:
with open(DataBaseFile, "r", encoding = "UTF-8") as db:
    DB = load(db)

#ЗАГРУЗКА TF:
with open(TempFile, "r", encoding = "UTF-8") as tf:
    TF = load(tf)

#ЗАГРУЗКА bad.json
if exists(blackListLetters):
    with open(blackListLetters, "r", encoding = "UTF-8") as read_file:
       bad = load(read_file)
else:
    print("FATAL ERROR: НЕ НАЙДЕНЫ ПЛОХИЕ СЛОВА")
#/////////

vk_session = vk_api.VkApi(token = token) #Сессия VK

waitUsers = {} #Пользователи которые вводят вопрос
addAdmins = {} #Администраторы которые добавляют вопрос
addUsers = {} #Пользователи которые предлагают свой вопрос

try:
    vk_session.auth() #Авторизуюсь
except vk_api.AuthError: #Если ошибка авторизации
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

def maybeInt(inr):
    try:
        int(inr)
        return True
    except TypeError:
        return False
def send_msgs(peers, message): #Отправить рассылку
    if len(peers) > 100:
        return
    peers2 = []
    for f in range(len(peers)):
        peers2[f] = str(peers[f])
    vk_session.method("messages.send", {"user_ids": ",".join(peers2), "message": message, "random_id": randrange(0, 184467440737095516165, 1)})
    

for event in longpoll.listen(): #Для каждого события
    if event.type == VkEventType.MESSAGE_NEW: #Если событие - сообщение
        if event.to_me: #Если сообщение мне
            if event.user_id in bl: #Если человек в BlackList
                if not bl[event.user_id]: #Если ему ещё не присылали сообщение
                    send_msg_without_keyboard(event.user_id, "Ошибка, вы находитесь в ЧС, если это ошибка - напишите администратору") #Пишу ему сообщение
                    bl[event.user_id] = 1 #Теперь он уже видел сообщение
                    with open(BlackListFile, "w", encoding = "UTF-8") as wf:
                        dump(bl, wf)
                continue #Если человек в ЧС пропускаю обработку команд

            author = get_user(event.user_id)[0] #Получаю профиль автора
            if allowTranslate: #Если включен переводчик
                cmd = translate(str(event.text).lower()) #Получаю команду
            else: #Если же нет
                cmd = str(event.text).lower() #Получаю команду
            aid = event.user_id #ID пользователя

            if aid in addUsers: #Если автор предлагает вопрос
                if cmd == "отменить": #Если человек нажал на кнопку ОТМЕНИТЬ
                    if aid in adminID: #Если он админ
                        send_msg_with_keyboard(aid, "Главное меню (Админ)", keyboards["aMenu"])
                    else: #Для простых смертных
                        send_msg_with_keyboard(aid, "Главное меню", keyboards["menu"])
                    del addUsers[aid] #Удаляю его из массива
                else: #Если он не нажимал на ОТМЕНИТЬ
                    if addUsers[aid][0] == 1: #Если он пока что ничего не ввёл
                        addUsers[aid] = [2, cmd] #Переписываю данные массива
                        send_msg_without_keyboard(aid, "Успешно, жду ответ...") #Отправляю сообщение
                    elif addUsers[aid][0] == 2: #Если он уже ввёл вопрос
                        send_msg_without_keyboard(aid, "Успешно, ваш вопрос/ответ отправлен на модерирование") #Сообщаю заранее что всё прошло ОК

                        TF.append([addUsers[aid][1], cmd, aid])
                        with open(TempFile, "w", encoding = "UTF-8") as tf:
                            dump(TF, tf)
                        del addUsers[aid] #Удаляю из базы
                        if aid in adminID: #Если человек админ
                            send_msg_with_keyboard(aid, "Главное меню (Админ)", keyboards["aMenu"])
                        else: #Если простой смертный
                            send_msg_with_keyboard(aid, "Главное меню", keyboards["menu"])

            if aid in addAdmins: #Если админ добавляет вопрос
                if addAdmins[aid][0] == 1: #Если он ничего пока что не ввёл
                    addAdmins[aid] = [2, cmd] #Добавляю в массив
                    send_msg_without_keyboard(aid, "Успешно, ожидаю ответ...") #Отправляю сообщение чтобы он отправил ответ
                elif addAdmins[aid][0] == 2: #Если админ уже ввёл вопрос
                    DB.append([addAdmins[aid][1], cmd])
                    with open(DataBaseFile, "w", encoding = "UTF-8") as db:
                        dump(DB, db)
                    send_msg_without_keyboard(aid, "Успешно, ваш вопрос/ответ записан") #Сообщаю что всё ОК
                    del addAdmins[aid]
            
            if aid in waitUsers: #Если человек хочет задать вопрос
                if waitUsers[aid][0] == 2 and cmd == "это не ответ на мой вопрос": #Если он уже всё сделал но он написал что это не ответ на мой вопрос
                    if aid in adminID:
                        send_msg_with_keyboard(aid, "Ошибка, я не знаю ответ на ваш вопрос. Я уже написал администратору что надо добавить ваш вопрос в базу", keyboards["aMenu"])
                    else:
                        send_msg_with_keyboard(aid, "Ошибка, я не знаю ответ на ваш вопрос. Я уже написал администратору что надо добавить ваш вопрос в базу", keyboards["menu"]) #Отправляю его в меню
                    send_msgs(adminID, "Человек (https://vk.com/id" + str(aid) + ") не нашёл ответ на свой вопрос: " + str(waitUsers[aid][1])) #Отправляю адмиНАМ что надо добавить вопрос в БД
                    del waitUsers[aid] #Удаляю человека из массива
                elif waitUsers[aid][0] == 2 and cmd == "спасибо": #Тоже самое как вверху только если он нажал на спасибо
                    if aid in adminID: #Если он админ
                        send_msg_with_keyboard(aid, "Главное меню (Админ)", keyboards["aMenu"])
                    else:
                        send_msg_with_keyboard(aid, "Главное меню", keyboards["menu"])
                elif waitUsers[aid][0] == 1: #Если он не ввёл вопрос
                    if cmd == "отменить": #Если нажал на кнопку отменить
                        del waitUsers[aid] #Удаляю из базы
                        if aid in adminID: #Если он админ
                            send_msg_with_keyboard(aid, "Главное меню (Админ)", keyboards["aMenu"])
                        else:
                            send_msg_with_keyboard(aid, "Главное меню", keyboards["menu"])
                    else: #Если он ввёл вопрос

                        #Проверка на плохие слова
                        if not aid in adminID: #Если человек админ - исключение
                            jh = False #Пока что всё хорошо
                            for k in cmd.split():
                                if k in bad:
                                    bl[aid] = 0
                                    with open(BlackListFile, "w", encoding = "UTF-8") as blf:
                                        dump(bl, blf)
                                    if aid in adminID:
                                        send_msg_with_keyboard(aid, "Ты назвал нецензурный вопрос, ты добавлен в ЧС бота", keyboards["aMenu"])
                                    else:
                                        send_msg_with_keyboard(aid, "Ты назвал нецензурный вопрос, ты добавлен в ЧС бота", keyboards["menu"])
                                    jh = True
                            if jh:
                                continue
                        #/////////////////////////

                        r = {"index": 0, "percent": 0} #Как у кеши
                        for l in range(len(DB)): #Для каждой строки в базе
                            h = ratio(cmd, DB[l][0]) #Считаю схожесть строк
                            if h > r["percent"]: #Ищу самый подходящий вопрос
                                r["index"] = l
                        waitUsers[aid][1] = cmd 
                        send_msg_with_keyboard(aid, "Успешно, я выбрал самый похожий вопрос (" + str(DB[r["index"]][0]) + ") и вот на него ответ: " + str(DB[r["index"]][1]), keyboards["badFAQ"])
                        waitUsers[aid][0] = 2 #Ожидаю отзыв
            
            if cmd == "старт" or cmd == "меню" or cmd == "начать": #Основные команды
                if aid in adminID: #Если человек админ
                    send_msg_with_keyboard(aid, "Главное меню (Админ)", keyboards["aMenu"])
                else:
                    send_msg_with_keyboard(aid, "Главное меню", keyboards["menu"])
            elif cmd == "задать вопрос" and not aid in addUsers: #Задать вопрос (Не админ)
                send_msg_with_keyboard(aid, "Ожидаю вопрос...", keyboards["close"])
                waitUsers[aid] = [1, ""]
            elif cmd == "предложить вопрос" and not aid in waitUsers: #Предложить вопрос (Не админ)
                send_msg_with_keyboard(aid, "Ожидаю вопрос...", keyboards["close"])
                addUsers[aid] = [1, "Q"]
            elif cmd == "добавить": #Добавить вопрос/ответ (Админ)
                if not aid in adminID:
                    send_msg_without_keyboard(aid, "Ошибка, вы не Администратор") #Ошибка прав
                    continue
                send_msg_without_keyboard(aid, "Ожидаю вопрос...")
                addAdmins[aid] = [1, "Q"]
            elif cmd == "просмотреть предложения": #Модерировать предложения  (Админ)
                if not aid in adminID:
                    send_msg_without_keyboard(aid, "Ошибка, вы не Администратор")
                    continue
                if len(TF) >= 1: #Если предложения есть
                    string = ""
                    for y in range(len(TF)):
                        string += str(y + 1) + ". " + str(TF[y][0]) + "  Ответ: " + str(TF[y][1]) + "  От: https://vk.com/id" + str(TF[y][2]) + " ;\n"
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
                if not maybeInt(cmd.split()[1]):
                    send_msg_without_keyboard(aid, "Ошибка, Index не int")
                    continue
                if have(TF, int(cmd.split()[1]) - 1):
                    del TF[int(cmd.split()[1]) - 1]
                    with open(TempFile, "w", encoding = "UTF-8") as tf:
                        dump(TF, tf)
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
                if not maybeInt(cmd.split()[1]):
                    send_msg_without_keyboard(aid, "Ошибка, Index не int")
                    continue
                if not have(TF, int(cmd.split()[1]) - 1):
                    send_msg_without_keyboard(aid, "Ошибка, в базе данных нету строки с индексом " + str(cmd.split()[1]))
                    continue
                else:
                    h = int(cmd.split()[1]) - 1
                DB.append([TF[h][0], TF[h][1]])
                with open(DataBaseFile, "w", encoding = "UTF-8") as db:
                    dump(DB, db)
                del TF[int(cmd.split()[1]) - 1]
                with open(TempFile, "w", encoding = "UTF-8") as tf:
                    dump(TF, tf)
                send_msg_without_keyboard(aid, "Успешно, предложение принято")
            elif cmd == "мы":
                send_msg_without_keyboard(aid, """
Создатель: Даниил Тенишев
Версия: 1.3
Библиотеки: vk_api, requests, fuzzywuzzy
                """)

            vk_session.method("messages.markAsRead", {"peer_id": aid, "message_id": vk_session.method("messages.getHistory", {"user_id": aid, "count": 1})["items"][0]["id"]}) #Читаю сообщение
    else:
        if eventsDebug: #Если отладка
            print(event.type, event.raw[1:]) #Пишу событие