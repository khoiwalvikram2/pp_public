from flask import Flask, request
from flask_restful import Resource, Api
from werkzeug.utils import secure_filename
import cv2
import pytesseract
from pytesseract import Output
from pdf2image import convert_from_path
import json
import os

#pytesseract.pytesseract.tesseract_cmd = r'C:\Users\vikram\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

application = Flask(__name__)
api = Api(application)

class MainApp(Resource):
    def post(self):
        pdf = request.files['pdf']
        pdf.save('00.pdf')

        # images = convert_from_path(app.config['UPLOAD_FOLDER'] + '00.pdf', poppler_path=r'D:\poppler\bin', grayscale=True)
        images = convert_from_path('00.pdf', grayscale=True)

        all_images_path = []

        for i, image in enumerate(images):
            image_name = '0'+ str(i) +'.jpg';
            images[i].save(image_name, 'JPEG')
            all_images_path.append(image_name)
        
        for img in all_images_path:
            image = cv2.imread(img)
            image = image[:, 550:]
            cv2.imwrite(img, image)

        matching_data = open('matching_data.json')
        matching_data = json.load(matching_data)
        all_data = []

        def has_numbers(inputString):
            return any(char.isdigit() for char in inputString)

        for img in all_images_path:
            threshold_img = cv2.imread(img)

            custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=0'
            details = pytesseract.image_to_data(threshold_img, output_type=Output.DICT, config=custom_config, lang='eng', nice=1)

            total_boxes = len(details['text'])

            for sequence_number in range(total_boxes):

                if float(details['conf'][sequence_number]) > 30.00:
                    (x, y, w, h) = (details['left'][sequence_number], details['top'][sequence_number], details['width'][sequence_number],  details['height'][sequence_number])
                    threshold_img = cv2.rectangle(threshold_img, (x, y), (x + w, y + h), (0, 255, 0), 2)

            for index, word in enumerate(details['text']):
                if word != '':
                    if word == 'Vitamin':
                        after_word = str(details['text'][index + 1])
                        if after_word == 'B12':
                            data = { 'name': 'Vitamin B12', 'value': str(details['text'][index - 2]) + str(details['text'][index - 1]) }
                        elif after_word == 'D':
                            data = { 'name': 'Vitamin D 25 (OH)', 'value': str(details['text'][index - 2]) + str(details['text'][index - 1]) }
                        all_data.append(data)

                    if word == 'Neutrophils' or word == 'Lymphocytes' or word == 'Monocytes' or word == 'Eosinophils' or word == 'Basophils':
                        after_word = str(details['text'][index + 1])
                        before_word = str(details['text'][index - 2])
                        if after_word == '%':
                            if has_numbers(before_word) == True and any(c.isalpha() for c in before_word) == False:
                                data = { 'name': word + ' %', 'value': str(details['text'][index - 2]) + str(details['text'][index - 1]) }
                            else:
                                data = { 'name': word + ' %', 'value': str(details['text'][index - 1]) }
                            data = { 'name': word + ' %', 'value': str(details['text'][index - 1]) }
                        elif after_word == '#':
                            if has_numbers(before_word) == True and any(c.isalpha() for c in before_word) == False:
                                data = { 'name': word + ' #', 'value': str(details['text'][index - 2]) + str(details['text'][index - 1]) }
                            else:
                                data = { 'name': word + ' #', 'value': str(details['text'][index - 1]) }
                        all_data.append(data)

                    for match_data in matching_data:
                        if match_data['find'] == word:
                            if word == 'eGFR':
                                data = { 'name': match_data['name'], 'value':  str(str(details['text'][index - 2]) + str(details['text'][index - 1])).replace('?', '^2') }
                            elif word == "MCV-Mean":
                                data = { 'name': match_data['name'], 'value': str(details['text'][index - 6]) + str(details['text'][index - 1]) }
                            elif word == "Folic":
                                data = { 'name': match_data['name'], 'value': str(details['text'][index - 1]).replace('-', '.') }
                            else:
                                before_word = str(details['text'][index - 2])
                                if has_numbers(before_word) == True and any(c.isalpha() for c in before_word) == False:
                                    data = { 'name': match_data['name'], 'value': str(details['text'][index - 2]) + str(details['text'][index - 1]).replace('|', 'l') }
                                else:
                                    data = { 'name': match_data['name'], 'value': str(details['text'][index - 1]).replace('|', 'l') }

                            all_data.append(data)

        return json.dumps(all_data)

api.add_resource(MainApp, '/')

if __name__ == '__main__':
    application.run(debug=True)
