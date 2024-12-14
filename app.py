from flask import Flask, render_template, request, send_file
import requests
import zipfile
import io
from flask_caching import Cache
from urllib.parse import unquote
from typing import List, Dict, Any
import re


app = Flask(__name__)

# Настройка кэширования
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Замените 'YOUR_YANDEX_DISK_TOKEN' на ваш токен доступа к Яндекс.Диску
YANDEX_DISK_TOKEN: str = 'YOUR_YANDEX_DISK_TOKEN'

@app.route('/')
def index() -> str:
    """Отображает главную страницу приложения."""
    return render_template('index.html')

@cache.cached(timeout=300, query_string=True)
@app.route('/list_files', methods=['POST'])
def list_files() -> str | tuple[str, int]:
    """
            Получает список файлов из Яндекс.Диска по публичному ключу.

            Returns:
                str: HTML-шаблон с отображением файлов
                tuple: или ошибка при получении файлов
    """

    public_key: str = request.form['public_key']
    file_type: str = request.form.get('file_type', 'all')  # Получаем тип файла из формы

    headers: Dict[str, str] = {
        'Authorization': f'OAuth {YANDEX_DISK_TOKEN}'
    }

    response: requests.Response = requests.get(
        f'https://cloud-api.yandex.net/v1/disk/public/resources?public_key={public_key}',
        headers=headers
    )

    if response.status_code == 200:
        files: List[Dict[str, Any]] = response.json().get('_embedded', {}).get('items', [])

        # Фильтрация по типу файла
        if file_type != 'all':
            files = [file for file in files if file['mime_type'].startswith(file_type)]

        return render_template('index.html', files=files, selected_type=file_type)
    else:
        return "Ошибка при получении файлов", 400

@app.route('/download_file', methods=['GET'])
def download_file() -> Any:
    """
        Загружает файл по-указанному URL.

        Returns:
            Any: Файл для скачивания или ошибка при загрузке файла
            tuple: или ошибка при получении файлов
        """
    file_url: Dict[str, str] = request.args
    url: str = ''

    for k in file_url:
        if k == 'url':
            url += f'{file_url.get(k)}'
        else:
            url += f'&{k}={file_url.get(k)}'

    filename: str = request.args.get('filename')
    response: requests.Response = requests.get(url)

    if response.status_code == 200:
        return send_file(io.BytesIO(response.content), as_attachment=True, download_name=filename)
    else:
        return "Ошибка при загрузке файла", 400

@app.route('/download_multiple_files', methods=['POST'])
def download_multiple_files() -> Any:
    """
       Загружает несколько файлов и создает ZIP-архив.

       Returns:
           Any: ZIP-архив с файлами или ошибка при загрузке файлов
           tuple: или ошибка при получении файлов
       """
    file_urls: List[str] = request.form.getlist('file_urls')

    # Создаем ZIP-архив
    zip_buffer: io.BytesIO = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for url in file_urls:
            response: requests.Response = requests.get(url)

            if response.status_code == 200:
                regex = re.compile("&filename=(.*)&disposition=")
                filename: str = unquote(regex.findall(url)[0])  # Извлекаем имя файла из URL
                zip_file.writestr(filename, response.content)
            else:
                return "Ошибка при загрузке файлов", 400

    zip_buffer.seek(0)
    return send_file(zip_buffer, as_attachment=True, download_name='files.zip', mimetype='application/zip')


if __name__ == '__main__':
    app.run(debug=True)