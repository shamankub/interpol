import asyncio
import datetime
import json
import os
import sqlite3
import sys
import uuid

import aiohttp
from rich.progress import track

HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exc", "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
}
PROXY = "http://waJSU1:KxEBSK@149.126.222.47:9923"

current_time = datetime.datetime.now().strftime("%Y-%m-%d--%H-%M")


async def fetch(session, url):
    async with session.get(url, headers=HEADERS, proxy=PROXY) as response:
        return await response.text()


async def get_data():
    async with aiohttp.ClientSession() as session:
        # Немного хардкодим. Получаем уже готовые сылки из файла
        with open('red_notices_urls.json') as f:
            data = json.load(f)

        pages_list = list(data.keys())

        global data_list
        data_list = []

        tasks = []
        
        for page in pages_list:  # Для проверки кода можно ограничить длину списка. Например: pages_list[:20]
            tasks.append(asyncio.create_task(fetch(session, page)))
        # Отправляем запрос на каждую ссылку из списка
        for response in track(
            asyncio.as_completed(tasks),
            total=len(tasks),
            description=f"Идёт загрузка... ",
        ):
            page_data = json.loads(await response)
            total_wanted = page_data.get("total")
            items = page_data.get("_embedded").get("notices")
            for i in range(total_wanted):  
                # Получаем данные по конкретному преступнику
                name = items[i].get("name")
                forename = items[i].get("forename")
                birthday = items[i].get("date_of_birth")
                nationalities = items[i].get("nationalities")
                link = items[i].get("_links").get("self")["href"]
                thumbnail = items[i].get("_links").get("thumbnail")
                if thumbnail:
                    img = thumbnail["href"]
                else:
                    img = "https://www.interpol.int/bundles/interpolfront/images/photo-not-available.png"
                # Делаем запрос к профилю преступника для получения дополнительной информации
                charge = await fetch(session, link)
                charge = json.loads(charge)  
                if charge.get("arrest_warrants") is not None:
                    charge_text = charge.get("arrest_warrants")[0].get("charge")
                else:
                    charge_text = "N/A"
                if page_data.get('query').get('name'):
                    # Если фильтруем по фамилии, то добавляем в список данные по каждому преступнику
                    data_list.append(
                        {
                            "uuid": str(uuid.uuid4()),
                            "name": name,
                            "forename": forename,
                            "birthday": birthday,
                            "nationalities": nationalities,
                            "link": link,
                            "img": img,
                            "charge": charge_text,
                        }
                    )
                if not name:
                    # Если фильтруем по имени, то добавляем в список только тех, у кого в поле фамилия "null"
                    data_list.append(
                        {
                            "uuid": str(uuid.uuid4()),
                            "name": name,
                            "forename": forename,
                            "birthday": birthday,
                            "nationalities": nationalities,
                            "link": link,
                            "img": img,
                            "charge": charge_text,
                        }
                    )

        data_dict = {}
        data_dict["red_notices"] = data_list

        # Записываем полученные данные в файл
        with open(f"red_notices_{current_time}.json", "a") as file:
            json.dump(data_dict, file, indent=4, ensure_ascii=False)


async def download_image(image_url, directory):
    # Скачиваем фото и сохраняем в директорию на диске
    async with aiohttp.ClientSession() as session:
        async with session.get(url=image_url, headers=HEADERS, proxy=PROXY) as response:
            filename = image_url.split("/")[-1]
            file_path = os.path.join(directory, filename)
            with open(file_path, "wb") as f:
                while True:
                    chunk = await response.content.read(1024)
                    if not chunk:
                        break
                    f.write(chunk)


async def get_images():
    # Создаем список всех ссылок на фото преступников
    image_url_list = [el.get("img") for el in data_list]
    directory = f"red_notices_images_{current_time}"

    if not os.path.exists(directory):
        os.makedirs(directory)

    tasks = [download_image(image_url, directory) for image_url in image_url_list]
    await asyncio.gather(*tasks)


def create_sql_table():
    # Создаем SQL таблицы
    conn = sqlite3.connect(f"red_notices_{current_time}.db")
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE criminals 
        (
            uuid CHAR(36) PRIMARY KEY,
            name VARCHAR(255),
            forename VARCHAR(255),
            birthday DATE,
            link VARCHAR(255),
            img VARCHAR(255),
            charge VARCHAR(255)
        );
    """
    )

    cur.execute(
        """
        CREATE TABLE nationalities 
        (
            criminal_id CHAR(36),
            nationality VARCHAR(255),
            FOREIGN KEY (criminal_id) REFERENCES criminals(uuid)
        );
    """
    )

    conn.commit()
    conn.close()


def insert_values_into_table():
    # Добавляем данные в талицы
    conn = sqlite3.connect(f"red_notices_{current_time}.db")
    cur = conn.cursor()

    params_list = [
        (
            el["uuid"],
            el["name"],
            el["forename"],
            el["birthday"],
            el["link"],
            el["img"],
            el["charge"],
        )
        for el in data_list
    ]

    cur.executemany(
        "INSERT INTO criminals (uuid, name, forename, birthday, link, img, charge) VALUES (?, ?, ?, ?, ?, ?, ?)",
        params_list,
    )

    params_list = []
    for data in data_list:
        if data.get("nationalities"):
            for nationality in data.get("nationalities"):
                params_list.append((data["uuid"], nationality))
        else:
            params_list.append((data["uuid"], "null"))
    cur.executemany(
        "INSERT INTO nationalities (criminal_id, nationality) VALUES (?, ?)",
        params_list,
    )

    conn.commit()
    conn.close()


def clear_stdout():
    # Очистка окна терминала
    sys.stdout.flush()
    sys.stdout.write("\033[2J\033[1;1H")


def main():
    clear_stdout()
    asyncio.run(get_data())
    create_sql_table()
    insert_values_into_table()

    answer = input("Хотите скачать картинки? (Y/N): ")
    if answer.lower() == "y":
        asyncio.run(get_images())
    else:
        print("Скачивание картинок было отменено!")


if __name__ == "__main__":
    main()
