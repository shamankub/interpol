import datetime
import itertools
import json
import sys
import uuid

import requests
from rich.progress import track

HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exc",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
}
PROXIES = {
    "https": "http://waJSU1:KxEBSK@149.126.222.47:9923",
}

skip_reading_profiles = True
result_url_dict = {}
criminal_data_list = []
current_time = datetime.datetime.now().strftime("%Y-%m-%d--%H-%M")


def create_url_combination(filter_field):
    # Создаем список ссылок, на которые будем отправлять запросы, используя regex
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    combinations = ["".join(i) for i in itertools.product(alphabet, repeat=2)]

    url_list = [
        f"https://ws-public.interpol.int/notices/v1/red?&{filter_field}=^{combination}.*&resultPerPage=160&page=1"
        for combination in combinations
    ]

    url_list.extend(
        [
            f"https://ws-public.interpol.int/notices/v1/red?&{filter_field}=^[a-z][^a-z].*&resultPerPage=160&page=1",
            f"https://ws-public.interpol.int/notices/v1/red?&{filter_field}=^[^a-z].*&resultPerPage=160&page=1",
            f"https://ws-public.interpol.int/notices/v1/red?&{filter_field}=^[a-z]{{0,1}}$.*&resultPerPage=160&page=1",
        ]
    )
    return url_list


def clear_stdout():
    # Очистка окна терминала
    sys.stdout.flush()
    sys.stdout.write("\033[2J\033[1;1H")


def get_current_criminal_data(data_lst):
    # Получаем данные по конкретному преступнику
    total_wanted = data_lst.get("total")
    items = data_lst.get("_embedded").get("notices")
    for i in range(total_wanted):
        name = items[i].get("name")  # Фамилия
        forename = items[i].get("forename")  # Имя
        birthday = items[i].get("date_of_birth")
        nationalities = items[i].get("nationalities")
        link = items[i].get("_links").get("self")["href"]
        thumbnail = items[i].get("_links").get("thumbnail")
        charge_text = "some text"
        if thumbnail:
            img = thumbnail["href"]
        else:
            img = "https://www.interpol.int/bundles/interpolfront/images/photo-not-available.png"
        if not skip_reading_profiles:
            # Делаем запрос к профилю преступника для получения дополнительной информации
            charge = requests.get(url=link, headers=HEADERS, proxies=PROXIES).text
            charge = json.loads(charge)
            if charge.get("arrest_warrants") is not None:
                charge_text = charge.get("arrest_warrants")[0].get("charge")
            else:
                charge_text = "N/A"

        if data_lst.get("query").get("name"):
            # Если фильтруем по фамилии, то добавляем в список данные по каждому преступнику
            criminal_data_list.append(
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
            criminal_data_list.append(
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


def get_data_by_filter_field(url_list, field):
    #  Получаем данные с фильтрацией по какому-то определенному полю (имя или фамилия)
    for url in track(url_list, description=f"Фильтрация по {field} Идёт загрузка... "):
        data = requests.get(
            url=url,
            headers=HEADERS,
            proxies=PROXIES,
        ).text
        data = json.loads(data)
        total_wanted = data.get("total")

        if total_wanted:
            if total_wanted > 160:
                # Если число совпадений больше 160, то добавляем фильтрацию по возрасту
                age_filter_list = [
                    (0, 10),
                    (11, 20),
                    (21, 30),
                    (31, 33),
                    (34, 35),
                    (36, 40),
                    (41, 50),
                    (51, 120),
                ]
                for age in age_filter_list:
                    fragmented_url = f"{url}&ageMin={age[0]}&ageMax={age[1]}"
                    data = requests.get(
                        url=fragmented_url,
                        headers=HEADERS,
                        proxies=PROXIES,
                    ).text

                    data = json.loads(data)
                    total_wanted = data.get("total")

                    result_url_dict[fragmented_url] = total_wanted
                    get_current_criminal_data(data)
            else:
                result_url_dict[url] = total_wanted
                get_current_criminal_data(data)


def get_all_data():
    # Получаем данные
    url_list_lastname = create_url_combination("name")
    url_list_firstname = create_url_combination("forename")

    clear_stdout()
    get_data_by_filter_field(url_list_lastname, "фамилии.")
    get_data_by_filter_field(url_list_firstname, "имени.  ")


def write_files():
    # Записываем полученные данные в файл
    with open("red_notices_urls.json", "w") as file:
        json.dump(result_url_dict, file, indent=4, ensure_ascii=False)

    with open("red_notices_{current_time}.json", "w") as file:
        json.dump(criminal_data_list, file, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    get_all_data()
    write_files()
