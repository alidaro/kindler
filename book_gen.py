from flask import Flask, render_template, request, send_file, jsonify
import json
import openai
import os
from dotenv import load_dotenv
from bookgen_topdf import gen_pdf
from io import BytesIO
from PIL import Image
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

# Загружаем переменные окружения из .env файла
load_dotenv()

# Импортируем API-ключ из переменных окружения
openai.api_key = os.getenv('OPENAI_KEY')

app = Flask(__name__)

def save(filename, text):
    with open(filename, 'w+', encoding='utf-8') as f:
        f.write(text)

async def generate_chapters(book_title):
    prompt = [
        {
            "role": "system",
            "content": f"generate a list of chapters and subchapters for a book titled {book_title} in json format. do not include any explanation or code formatting. format it in this way: "+"{\"chapter_name\":[\"subchapter_names\"],}"+". please include between 5 and 10 subchapters per chapter. use this format exactly."
        },
        {
            "role": "user",
            "content": "generate with 4 space indents"
        },
    ]
    response = await openai.ChatCompletion.acreate(
        model="gpt-4o-mini",
        messages=prompt
    )
    gpt_response = response['choices'][0]['message']['content']
    return gpt_response

async def generate_content(chaptername, subchapter, book_title):
    prompt = [
        {
            "role": "system",
            "content": f"generate the content for a subchapter in a book. the chapter title is {chaptername}. the title of the subchapter is {subchapter}. the title of the book is {book_title}. please only include the requested data."
        },
        {
            "role": "user",
            "content": "do not include the chapter title, the subchapter title, or the book title in the data, only the chapter content."
        },
    ]
    response = await openai.ChatCompletion.acreate(
        model="gpt-4o-mini",
        messages=prompt
    )
    gpt_response = response['choices'][0]['message']['content']
    return gpt_response

async def generate_chapter_content(chapter_name, subchapters, book_title):
    sections = []
    tasks = []
    for subchapter_name in subchapters:
        tasks.append(asyncio.create_task(generate_content(chapter_name, subchapter_name, book_title)))
    
    results = await asyncio.gather(*tasks)
    for i, content in enumerate(results):
        section = {
            "subchapter": subchapters[i],
            "content": content,
        }
        sections.append(section)
    
    chapter = {
        "chapter_title": chapter_name,
        "subchapters": sections
    }
    return chapter

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
async def generate():
    book_title = request.form['book_title']
    
    chapters_names = await generate_chapters(book_title)
    save('chapters.json', chapters_names)

    try:
        chapters_json = json.loads(chapters_names)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return "Failed to decode JSON", 500

    chapters = []
    tasks = []
    for chapter_name, subchapters in chapters_json.items():
        tasks.append(asyncio.create_task(generate_chapter_content(chapter_name, subchapters, book_title)))

    chapters = await asyncio.gather(*tasks)

    book_out = book_title.replace(' ', '_').replace(':', '-').replace('?', '') + '.json'
    save(book_out, json.dumps(chapters, indent=4, ensure_ascii=False))

    pdf_filename = gen_pdf(book_title, chapters)

    return jsonify({"filename": pdf_filename})

@app.route('/download/<filename>')
def download(filename):
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
