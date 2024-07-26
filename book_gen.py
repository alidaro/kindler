from flask import Flask, render_template, request, send_file, jsonify
import json
import openai
import os
from dotenv import load_dotenv
from io import BytesIO
from fpdf import FPDF
import asyncio

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
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=prompt
        )
        gpt_response = response['choices'][0]['message']['content']
        return gpt_response
    except Exception as e:
        print(f"Error generating chapters: {e}")
        return None

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
    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=prompt
        )
        gpt_response = response['choices'][0]['message']['content']
        return gpt_response
    except Exception as e:
        print(f"Error generating content for {subchapter}: {e}")
        return None

async def generate_chapter_content(chapter_name, subchapters, book_title):
    sections = []
    tasks = []
    for subchapter_name in subchapters:
        tasks.append(asyncio.create_task(generate_content(chapter_name, subchapter_name, book_title)))
    
    results = await asyncio.gather(*tasks)
    for i, content in enumerate(results):
        if content:
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

class PDF(FPDF):
    def __init__(self, book_title, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.book_title = book_title
        self.chapters_list = []

    def header(self):
        self.set_font('Times', 'B', 12)
        self.cell(0, 10, self.book_title.encode('latin1', 'replace').decode('latin1'), 0, 1, 'C')
        self.ln(10)

    def chapter_title(self, chapter_title):
        self.set_font('Times', 'B', 14)
        self.cell(0, 10, chapter_title.encode('latin1', 'replace').decode('latin1'), 0, 1, 'L')
        self.ln(5)
        self.chapters_list.append((chapter_title, self.page_no()))

    def chapter_body(self, body):
        self.set_font('Times', '', 12)
        body_text = "\n".join(body)
        self.multi_cell(0, 10, body_text.encode('latin1', 'replace').decode('latin1'))
        self.ln()

    def footer(self):
        self.set_y(-15)
        self.set_font('Times', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def add_title_page(self):
        self.add_page()
        self.set_font('Times', 'B', 24)
        self.cell(0, 100, self.book_title.encode('latin1', 'replace').decode('latin1'), 0, 1, 'C')
        self.ln(10)
        self.set_font('Times', '', 16)
        self.cell(0, 10, 'Alidar Panaguzhiyev', 0, 1, 'C')
        self.ln(50)

    def add_table_of_contents(self):
        self.add_page()
        self.set_font('Times', 'B', 16)
        self.cell(0, 10, 'Table of Contents', 0, 1, 'C')
        self.ln(10)

        self.set_font('Times', '', 12)
        for chapter_title, page_num in self.chapters_list:
            self.cell(0, 10, f'{chapter_title} - Page {page_num}', 0, 1, 'L')

def gen_pdf(title, chapters):
    pdf = PDF(book_title=title)
    
    pdf.add_title_page()
    
    for chapter in chapters:
        pdf.add_page()
        pdf.chapter_title(chapter['chapter_title'])
        combined_subchapters = [subchapter['content'] for subchapter in chapter['subchapters']]
        pdf.chapter_body(combined_subchapters)

    pdf.add_table_of_contents()
    
    pdf_filename = f"{title.replace(' ', '_').replace(':', '-').replace('?', '')}.pdf"
    pdf.output(f'static/books/{pdf_filename}', 'F')
    return pdf_filename

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
async def generate():
    book_title = request.form['book_title']
    
    chapters_names = await generate_chapters(book_title)
    if not chapters_names:
        return jsonify({"error": "Failed to generate chapters"}), 500

    save('static/books/chapters.json', chapters_names)

    try:
        chapters_json = json.loads(chapters_names)
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return jsonify({"error": "Failed to decode JSON"}), 500

    tasks = []
    for chapter_name, subchapters in chapters_json.items():
        tasks.append(asyncio.create_task(generate_chapter_content(chapter_name, subchapters, book_title)))

    chapters = await asyncio.gather(*tasks)

    book_out = os.path.join('static/books', book_title.replace(' ', '_').replace(':', '-').replace('?', '') + '.json')
    save(book_out, json.dumps(chapters, indent=4, ensure_ascii=False))

    pdf_filename = gen_pdf(book_title, chapters)
    pdf_out = os.path.join('static/books', pdf_filename)
    
    if not os.path.exists(pdf_out):
        return jsonify({"error": "PDF file not found"}), 500
    
    return jsonify({"filename": pdf_filename})

@app.route('/download/<filename>')
def download(filename):
    filepath = os.path.join('static/books', filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "File not found"}), 404
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
