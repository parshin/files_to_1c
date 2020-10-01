import logging
import time
import re
import requests
import json
import sys
import os
import glob
from os import listdir
from os.path import isfile, join
from pdf2image import convert_from_path
from conf import files_dir
from conf import addresses
from pyzbar.pyzbar import decode
from PIL import Image
from PIL import ImageEnhance
from base64 import b64encode


def check_access():

    # Проверка разрешений на каталог
    folder = files_dir['FOLDER']
    if not os.access(folder, os.X_OK | os.W_OK):
        logging.error('Access is not allowed ' + folder)
        return False

    folder = files_dir['RECOGNIZED']
    if not os.access(folder, os.X_OK | os.W_OK):
        logging.error('Access is not allowed ' + folder)
        return False

    folder = files_dir['UNRECOGNIZED']
    if not os.access(folder, os.X_OK | os.W_OK):
        logging.error('Access is not allowed ' + folder)
        return False

    return True


def enhance_img(jpg_file):

    # улучшим контрастность и резкость
 
    image = Image.open(jpg_file)

    image = ImageEnhance.Contrast(image)
    image = image.enhance(2)

    image = ImageEnhance.Sharpness(image)
    image = image.enhance(1)

    image.save(jpg_file)


if __name__ == "__main__":

    start_time = time.time()

    logging.basicConfig(filename="barcodes.log",
                        level=logging.INFO,
                        format='%(levelname)-8s [%(asctime)s] %(message)s')
    
    path = files_dir["FOLDER"]

    logging.info('start reading from: ' + path)

    if not check_access():
        raise SystemExit(0)
    
    # Считываем все pdf файлы в каталоге
    pdf_file_list = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith('pdf')]
    total_files = len(pdf_file_list)
    logging.info('total files: ' + str(total_files))
    
    recognized_files = 0

    for pdf_file in pdf_file_list:
        
        # получим имя файла без расширения
        filename = re.search(r'^.*(?=\.pdf)', pdf_file).group(0)

        # извлечем из pdf-файла 1-ю страницу. На ней нужный штрихкод
        try:
            jpg_file = convert_from_path(path + pdf_file, 200,
                                         output_folder=path,
                                         output_file=filename,
                                         fmt='jpg',
                                         thread_count=4,
                                         paths_only=True,
                                         first_page=1,
                                         last_page=1)
        except:
            logging.error("Can't convert to jpg: " + pdf_file)
            continue

        # прочитаем штрихкоды
        detected_barcodes = decode(Image.open(jpg_file[0]))

        # не удалось считать штрихкод.
        if not detected_barcodes:
            # попытаемся улучшить изображение
            enhance_img(jpg_file[0])
            detected_barcodes = decode(Image.open(jpg_file[0]))
            # если не удалось считать то удалим файл изображение и пересетим pdf-файл в нераспознанные
            if not detected_barcodes:
                logging.error("barcode was n't recognized: " + pdf_file)

                try:
                    logging.info("moving " + path + pdf_file + " to " + files_dir['UNRECOGNIZED'] + pdf_file)
                    os.rename(path+pdf_file, files_dir['UNRECOGNIZED']+pdf_file)
                    os.remove(jpg_file[0])
                except IOError:
                    err_type, value, traceback = sys.exc_info()
                    logging.error('error moving pdf file ' + pdf_file + " to " + files_dir['UNRECOGNIZED'])
                    logging.error('error detail:' + value.strerror)

                # продолжим чтение файлов
                continue

        # удаление файла изображения
        try:
            os.remove(jpg_file[0])
        except IOError:
            err_type, value, traceback = sys.exc_info()
            logging.error('error moving jpg file ' + jpg_file)
            logging.error('detail:' + value.strerror)

        for barcode in detected_barcodes:
            # фильтр типу штрихкода
            if barcode.type != 'CODE128':
                continue

            recognized_files += 1

            logging.info(' pdf_file ' + pdf_file +
                         ' type: ' + barcode.type +
                         ' barcode: ' + str(barcode.data))

            try:
                f = open(path+pdf_file, 'rb')
            except IOError:
                logging.error("Can't open " + path+pdf_file)
                continue

            # кодируем в base64 для отправки на http сервис
            base64_bytes = b64encode(f.read())
            base64_string = base64_bytes.decode('utf-8')

            response = requests.post(addresses["upload_file_address"], data=json.dumps({
                'barcode': barcode.data.decode('utf-8'), # распознанный штрихкод
                'file': base64_string, # данные файла
                'doc_type': 'doc', # описание что отправляем. Используется для фильтра в 1с (первичка, складские, прочие доки)
                'file_name': filename, # имя файла. 
            }))

            f.close()

            if response.status_code != 200:
                logging.error('error form 1c: ' + response.text)
                continue

            try:
                response = response.json()
                if response["result"]:
                    logging.info(response["description"])
                    os.rename(path+pdf_file, files_dir['RECOGNIZED']+pdf_file)
                else:
                    logging.info('file not attached: ' + pdf_file)
                    os.rename(path+pdf_file, files_dir['UNRECOGNIZED']+pdf_file)
            except IOError:
                err_type, value, traceback = sys.exc_info()
                logging.error('response form 1c: ' + str(response))
                logging.error('error detail:' + value.strerror)

    logging.info('total files: ' + str(total_files))
    if total_files > 0:
        logging.info('recognized files: ' + str(recognized_files) + "/" +
                     str(round(recognized_files*100/total_files)) + "%")
    logging.info('execution time, sec.: ' + str(round(time.time() - start_time)))
