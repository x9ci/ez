#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Translator
Created: 2025-01-21 18:26:08
Author: x9ci
"""
from reportlab.lib.pagesizes import letter
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from googletrans import Translator
import re
import logging
from PIL import Image, ImageFont
import os
from pathlib import Path
import shutil
from datetime import datetime
from typing import List, Dict
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import tempfile
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
import arabic_reshaper
from bidi.algorithm import get_display
import sys
import time
import json
from tqdm import tqdm

# واردات المكونات المحلية (من نفس المجلد)
from arabic_handler import ArabicHandler  # بدون نقطة
from page_processor import PageProcessor   # بدون نقطة

# تهيئة التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

VERSION = '1.0.0'  # إضافة إصدار البرنامج هنا


def initialize_system():
    """تهيئة النظام والتحقق من المتطلبات"""
    try:
        print("تهيئة النظام...")
        
        # التحقق من وجود المجلدات المطلوبة
        for directory in ['input', 'output', 'fonts']:
            Path(directory).mkdir(exist_ok=True)
            
        # تهيئة معالج النصوص العربية
        arabic_handler = ArabicHandler()
        if not arabic_handler.initialize_fonts():
            print("تحذير: قد تكون هناك مشاكل في عرض النصوص العربية")
            
        return True
        
    except Exception as e:
        print(f"خطأ في تهيئة النظام: {e}")
        return False

if __name__ == "__main__":
    if not initialize_system():
        print("فشل في تهيئة النظام")
        sys.exit(1)
        
    # متابعة تنفيذ البرنامج...
    print("تم تهيئة النظام بنجاح")

def __init__(self, text_processor):
    self.text_processor = text_processor
    self.batch_size = 10
    self.processed_blocks = set()
    self.initialize_fonts()  # تهيئة الخطوط عند إنشاء الكائن

class TextProcessor:
    def __init__(self):
        self.translator = Translator()
        self.batch_size = 10

    def clean_text(self, text: str) -> str:
        text = re.sub(r'^\d+$', '', text)
        text = re.sub(r'[^\w\s\-.,?!]', ' ', text)
        text = ' '.join(text.split())
        return text.strip()

    def is_chess_notation(self, text: str) -> bool:
        patterns = [
            r'^[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](\+|#)?$',
            r'^O-O(-O)?$',
            r'^[0-1](/[0-1])?-[0-1](/[0-1])?$',
            r'\d{1,4}\.',
            r'½-½',
        ]
        return any(bool(re.match(pattern, text.strip())) for pattern in patterns)

    def prepare_arabic_text(self, text: str) -> str:
        try:
            reshaped_text = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped_text)
            return text
        except Exception as e:
            logging.error(f"Error preparing Arabic text: {str(e)}")
            return text

    def process_text_batch(self, texts: List[str]) -> List[str]:
        """معالجة مجموعة من النصوص"""
        translated_texts = []
        arabic_handler = ArabicTextHandler()
        
        print(f"معالجة دفعة من {len(texts)} نص")
        
        for text in texts:
            try:
                if not text or len(text.strip()) < 3:
                    translated_texts.append("")
                    continue
                    
                # ترجمة النص
                translated = self.translator.translate(text, src='en', dest='ar').text
                
                # معالجة النص العربي
                processed_text = arabic_handler.process_arabic_text(translated)
                translated_texts.append(processed_text)
                
                print(f"النص الأصلي: {text}")
                print(f"الترجمة: {processed_text}")
                
                time.sleep(0.5)  # تأخير لتجنب التقييد
                
            except Exception as e:
                print(f"خطأ في ترجمة النص: {str(e)}")
                translated_texts.append("")
        
        return translated_texts


class FontManager:
    def __init__(self):
        self.font_name = 'Arabic'
        self.font_size = 14
        self.initialize_fonts()

    def initialize_fonts(self):
        """تهيئة الخطوط العربية"""
        try:
            font_paths = [
                "/usr/share/fonts/truetype/arabic/Amiri-Regular.ttf",
                "./fonts/Amiri-Regular.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                "./fonts/FreeSans.ttf"
            ]

            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont(self.font_name, font_path))
                        print(f"تم تحميل الخط: {font_path}")
                        return True
                    except Exception as e:
                        print(f"خطأ في تحميل الخط {font_path}: {e}")
                        continue

            print("تحذير: لم يتم العثور على خط عربي مناسب")
            return False

        except Exception as e:
            print(f"خطأ في تهيئة الخطوط: {e}")
            return False


class ArabicWriter:
    def __init__(self):
        self.font_size = 14
        self.initialize_fonts()

    def initialize_fonts(self):
        """تهيئة الخطوط العربية"""
        try:
            # قائمة الخطوط العربية
            font_paths = [
                "/usr/share/fonts/truetype/arabic/Amiri-Regular.ttf",
                "./fonts/Amiri-Regular.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                "./fonts/FreeSans.ttf"
            ]

            font_loaded = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        # تسجيل الخط مرة واحدة فقط
                        if 'Arabic' not in pdfmetrics.getRegisteredFontNames():
                            pdfmetrics.registerFont(TTFont('Arabic', font_path))
                            font_loaded = True
                            print(f"تم تحميل الخط العربي: {font_path}")
                            break
                    except Exception as e:
                        print(f"خطأ في تحميل الخط {font_path}: {e}")
                        continue

            if not font_loaded:
                print("تحذير: لم يتم العثور على خط عربي مناسب")
                return False

            return True

        except Exception as e:
            print(f"خطأ في تهيئة الخطوط: {e}")
            return False

    def write_arabic_text(self, canvas, text, x, y, width=None, height=None, align='right'):
        """كتابة نص عربي على الصفحة"""
        try:
            # معالجة النص العربي
            reshaped_text = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped_text)

            # تعيين الخط والحجم
            canvas.setFont('Arabic', self.font_size)

            # حساب العرض إذا لم يتم تحديده
            if width is None:
                width = canvas.stringWidth(bidi_text, 'Arabic', self.font_size)

            # تحديد موقع الكتابة حسب المحاذاة
            if align == 'right':
                x = x + width
                canvas.drawRightString(x, y, bidi_text)
            elif align == 'center':
                x = x + width/2
                canvas.drawCentredString(x, y, bidi_text)
            else:
                canvas.drawString(x, y, bidi_text)

            return width, self.font_size

        except Exception as e:
            print(f"خطأ في كتابة النص العربي: {e}")
            return 0, 0

    def get_text_dimensions(self, text):
        """حساب أبعاد النص"""
        try:
            reshaped_text = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped_text)
            width = len(bidi_text) * self.font_size * 0.6
            height = self.font_size * 1.5
            return width, height
        except Exception as e:
            print(f"خطأ في حساب أبعاد النص: {e}")
            return 0, 0


class PageProcessor:
    def __init__(self, text_processor):
        self.text_processor = text_processor
        self.batch_size = 10
        self.processed_blocks = set()

    def process_page(self, page_content, page_num: int):
        """معالجة صفحة كاملة"""
        logging.info(f"معالجة الصفحة {page_num + 1}")
        translated_blocks = []
        text_batch = []
        blocks_to_process = []
        
        # ترتيب المحتوى من أعلى إلى أسفل ومن اليمين إلى اليسار
        sorted_content = sorted(
            page_content,
            key=lambda x: (-x['bbox'][1], -x['bbox'][0])
        )

        for block in sorted_content:
            try:
                if not self.validate_block(block):
                    continue

                text = self.text_processor.clean_text(block.get('text', ''))
                if len(text.strip()) < 3 or self.text_processor.is_chess_notation(text):
                    continue

                text_batch.append(text)
                blocks_to_process.append(block)

                if len(text_batch) >= self.batch_size:
                    self.process_and_add_translations(
                        text_batch, blocks_to_process, translated_blocks, page_num
                    )
                    text_batch = []
                    blocks_to_process = []

            except Exception as e:
                logging.error(f"خطأ في معالجة كتلة النص: {str(e)}")
                continue

        # معالجة الكتل المتبقية
        if text_batch:
            self.process_and_add_translations(
                text_batch, blocks_to_process, translated_blocks, page_num
            )

        return translated_blocks

    def validate_block(self, block: dict) -> bool:
        """التحقق من صحة كتلة النص"""
        try:
            if not isinstance(block, dict):
                return False
            
            if 'text' not in block or 'bbox' not in block:
                return False
                
            text = block.get('text', '').strip()
            if not text:
                return False
                
            bbox = block['bbox']
            if not isinstance(bbox, (tuple, list)) or len(bbox) != 4:
                return False

            return True
        except Exception as e:
            logging.debug(f"خطأ في التحقق من الكتلة: {str(e)}")
            return False

    def process_and_add_translations(self, texts: List[str], blocks: List[Dict], 
                                   translated_blocks: List[Dict], page_num: int):
        """معالجة وإضافة الترجمات"""
        translations = self.text_processor.process_text_batch(texts)
        for trans, block in zip(translations, blocks):
            if trans and trans.strip():
                translated_blocks.append({
                    'text': trans,
                    'bbox': block['bbox'],
                    'original_bbox': block['bbox'],
                    'type': 'text',
                    'page': page_num,
                    'original': block.get('text', '')
                })

    def create_translated_overlay(self, translated_blocks, page_num, page_size):
        """إنشاء طبقة الترجمة"""
        packet = BytesIO()
        width, height = float(page_size[0]), float(page_size[1])
        c = canvas.Canvas(packet, pagesize=(width, height))
        used_positions = []

        for block in translated_blocks:
            try:
                if block['type'] != 'text':
                    continue

                text = self.text_processor.prepare_arabic_text(block['text'])
                if not text:
                    continue

                bbox = block['original_bbox']
                font_size = 10  # حجم الخط الافتراضي
                text_width, text_height = self.calculate_text_dimensions(text, font_size)
                
                x, y = self.find_optimal_position(
                    bbox, text_width, text_height, used_positions, width, height
                )

                self.draw_text_background(c, x, y, text_width, text_height)
                
                c.setFont("Arabic", font_size)
                c.setFillColorRGB(0, 0, 0)
                c.drawRightString(x + text_width, y + text_height, text)
                
                self.draw_connection_line(c, x, y, bbox, text_width, text_height, height)
                used_positions.append((x, y, text_width, text_height))

            except Exception as e:
                logging.error(f"خطأ في إضافة النص المترجم: {str(e)}")
                continue

        c.save()
        packet.seek(0)
        return packet

    def calculate_text_dimensions(self, text: str, font_size: float) -> tuple:
        """حساب أبعاد النص"""
        return len(text) * font_size * 0.6, font_size * 1.2

    def find_optimal_position(self, bbox, text_width, text_height, used_positions, 
                            page_width, page_height):
        """إيجاد أفضل موقع للنص المترجم"""
        x = bbox[0]
        y = page_height - bbox[3] - text_height - 5
        
        x = max(5, min(x, page_width - text_width - 5))
        y = max(5, min(y, page_height - text_height - 5))
        
        while self.check_overlap((x, y, text_width, text_height), used_positions):
            y -= text_height + 5
            if y < 5:
                y = page_height - text_height - 5
                x += text_width + 10
                if x + text_width > page_width - 5:
                    x = 5
                    y = page_height - text_height - 5
                    break

        return x, y

    def check_overlap(self, current_rect, used_positions):
        """التحقق من تداخل النصوص"""
        x, y, w, h = current_rect
        for used_x, used_y, used_w, used_h in used_positions:
            if (x < used_x + used_w and x + w > used_x and
                y < used_y + used_h and y + h > used_y):
                return True
        return False
class PDFHandler:
    def __init__(self, config, page_processor):
        self.config = config
        self.page_processor = page_processor
        self.temp_dir = tempfile.mkdtemp()
        self.current_pdf_path = None

    def translate_pdf(self, input_path: str):
        """ترجمة ملف PDF"""
        input_path = Path(input_path)
        self.current_pdf_path = str(input_path)
        output_path = Path(self.config.OUTPUT_DIR) / f"translated_{input_path.stem}.pdf"
        
        try:
            if not self.validate_pdf(str(input_path)):
                raise ValueError("ملف PDF غير صالح")

            logging.info(f"بدء ترجمة: {input_path}")
            
            with pdfplumber.open(str(input_path)) as plumber_pdf:
                pdf_reader = PdfReader(str(input_path))
                pdf_writer = PdfWriter()
                total_pages = len(plumber_pdf.pages)
                
                progress_bar = self.create_progress_bar(total_pages)
                
                for page_num in range(total_pages):
                    try:
                        page = plumber_pdf.pages[page_num]
                        text_content = self.extract_words_safely(page)
                        
                        if text_content:
                            translated_blocks = self.page_processor.process_page(text_content, page_num)
                            
                            if translated_blocks:
                                width, height = float(page.width), float(page.height)
                                overlay_packet = self.page_processor.create_translated_overlay(
                                    translated_blocks,
                                    page_num,
                                    (width, height)
                                )
                                
                                overlay_pdf = PdfReader(overlay_packet)
                                page_obj = pdf_reader.pages[page_num]
                                page_obj.merge_page(overlay_pdf.pages[0])
                                pdf_writer.add_page(page_obj)
                            else:
                                pdf_writer.add_page(pdf_reader.pages[page_num])
                        else:
                            pdf_writer.add_page(pdf_reader.pages[page_num])
                            
                        if progress_bar:
                            progress_bar.update(1)
                            
                        if page_num % 5 == 0:
                            self.optimize_memory_usage()
                            
                    except Exception as e:
                        logging.error(f"خطأ في معالجة الصفحة {page_num + 1}: {str(e)}")
                        pdf_writer.add_page(pdf_reader.pages[page_num])
                        continue

                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(str(output_path), 'wb') as output_file:
                    pdf_writer.write(output_file)
                
                self.save_translation_metadata(input_path, output_path)
                logging.info("اكتملت الترجمة بنجاح")
                
        except Exception as e:
            logging.error(f"خطأ في عملية الترجمة: {str(e)}")
            raise
        finally:
            self.cleanup()

    def validate_pdf(self, file_path: str) -> bool:
        """التحقق من صلاحية ملف PDF"""
        try:
            with open(file_path, 'rb') as file:
                PdfReader(file)
            return True
        except Exception as e:
            logging.error(f"ملف PDF غير صالح: {str(e)}")
            return False

    def extract_words_safely(self, page) -> list:
        """استخراج الكلمات من الصفحة بشكل آمن"""
        try:
            words = page.extract_words(
                keep_blank_chars=True,
                x_tolerance=3,
                y_tolerance=3,
                extra_attrs=['fontname', 'size']
            )
            return [word for word in words if word.get('text', '').strip()]
        except Exception as e:
            logging.error(f"خطأ في استخراج الكلمات: {str(e)}")
            return []

    def create_progress_bar(self, total_pages: int):
        """إنشاء شريط تقدم العملية"""
        try:
            return tqdm(
                total=total_pages,
                desc="تقدم الترجمة",
                unit="صفحة",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} صفحات"
            )
        except Exception:
            return None

    def save_translation_metadata(self, input_path: Path, output_path: Path):
        """حفظ البيانات الوصفية للترجمة"""
        try:
            metadata = {
                'source_file': str(input_path),
                'output_file': str(output_path),
                'translation_date': datetime.now().isoformat(),
                'user': 'x9ci',
                'version': '2.0.0'
            }
            
            metadata_path = output_path.with_suffix('.meta.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.warning(f"خطأ في حفظ البيانات الوصفية: {str(e)}")

    def cleanup(self):
        """تنظيف الملفات المؤقتة"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            logging.warning(f"خطأ في حذف الملفات المؤقتة: {str(e)}")

    def optimize_memory_usage(self):
        """تحسين استخدام الذاكرة"""
        import gc
        gc.collect()

class PDFTranslatorConfig:
    def __init__(self):
        # تحديد المسارات الأساسية
        base_dir = Path(__file__).parent
        self.INPUT_DIR = base_dir / "input"
        self.OUTPUT_DIR = base_dir / "output"
        self.TEMP_DIR = base_dir / "temp"
        self.LOG_DIR = base_dir / "logs"
        self.FONTS_DIR = base_dir / "fonts"

        # إنشاء المجلدات المطلوبة
        for dir_path in [self.INPUT_DIR, self.OUTPUT_DIR, self.TEMP_DIR, 
                        self.LOG_DIR, self.FONTS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def setup_logging(self):
        """إعداد نظام التسجيل"""
        log_file = self.LOG_DIR / f"translation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(str(log_file), encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

class PDFTranslator:
    def __init__(self):
        """تهيئة المترجم"""
        self.config = PDFTranslatorConfig()
        self.translator = Translator()
        self.setup_tesseract()
        self.initialize_fonts()
        self.temp_dir = tempfile.mkdtemp()
        self.processed_blocks = set()  # لتتبع الكتل المعالجة
        self.batch_size = 10  # عدد الكتل للمعالجة في كل دفعة

    def setup_tesseract(self):
        """إعداد Tesseract OCR"""
        if os.name == 'nt':  # Windows
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        else:  # Linux/Mac
            if not shutil.which('tesseract'):
                raise RuntimeError("Tesseract غير مثبت. الرجاء تثبيته أولاً.")

    
    
    
    def initialize_fonts(self):
        """تهيئة الخطوط العربية"""
        try:
            font_paths = [
                "/usr/share/fonts/truetype/arabic/Amiri-Regular.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('Arabic', font_path))
                    return
            
            # استخدام الخط الافتراضي إذا لم يتم العثور على الخطوط العربية
            pdfmetrics.registerFont(TTFont('Arabic', "/usr/share/fonts/truetype/freefont/FreeSans.ttf"))
        except Exception as e:
            logging.error(f"خطأ في تحميل الخطوط: {e}")
            raise

    def cleanup(self):
        """تنظيف الملفات المؤقتة"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            logging.warning(f"خطأ في حذف الملفات المؤقتة: {str(e)}")
    def prepare_arabic_text(self, text: str) -> str:
        """تحضير النص العربي للعرض بشكل صحيح"""
        try:
            # إعادة تشكيل النص العربي
            reshaped_text = arabic_reshaper.reshape(text)
            # تطبيق خوارزمية BIDI للاتجاه الصحيح
            bidi_text = get_display(reshaped_text)
            # تحسين تنسيق النص
            bidi_text = self.improve_arabic_text(bidi_text)
            return bidi_text
        except Exception as e:
            logging.error(f"خطأ في تحضير النص العربي: {e}")
            return text

    def improve_arabic_text(self, text: str) -> str:
        """تحسين تنسيق النص العربي"""
        # تحويل الأرقام إلى أرقام عربية
        text = text.translate(str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩'))
        # تصحيح علامات الترقيم العربية
        text = text.replace('?', '؟').replace(';', '؛').replace(',', '،')
        # تحسين المسافات حول علامات الترقيم
        text = re.sub(r'\s*([،؛؟!:])\s*', r'\1 ', text)
        # إزالة المسافات الزائدة
        text = ' '.join(text.split())
        return text.strip()

    def translate_text_with_retry(self, text: str, max_attempts: int = 3) -> str:
        """ترجمة النص مع إعادة المحاولة في حالة الفشل"""
        if not text or len(text.strip()) < 3:
            return ""

        for attempt in range(max_attempts):
            try:
                # ترجمة النص
                translated = self.translator.translate(text, src='en', dest='ar').text
                # تحسين النص المترجم
                translated = self.prepare_arabic_text(translated)
                
                if translated and translated.lower() != text.lower():
                    return translated
                
                time.sleep(0.5)  # تأخير لتجنب التقييد
            except Exception as e:
                if attempt == max_attempts - 1:
                    logging.error(f"فشلت الترجمة: {str(e)}")
                    return ""
                time.sleep(1)  # انتظار قبل إعادة المحاولة
        return ""

    def process_text_batch(self, texts: List[str]) -> List[str]:
        """معالجة مجموعة من النصوص دفعة واحدة"""
        translated_texts = []
        for text in texts:
            try:
                # تنظيف النص قبل الترجمة
                cleaned_text = self.clean_text(text)
                if len(cleaned_text.strip()) < 3:
                    translated_texts.append("")
                    continue
                
                # ترجمة النص
                translated = self.translate_text_with_retry(cleaned_text)
                translated_texts.append(translated)
                
                # تأخير صغير بين الترجمات
                time.sleep(0.2)
            except Exception as e:
                logging.error(f"خطأ في ترجمة النص: {str(e)}")
                translated_texts.append("")
        
        return translated_texts

    def clean_text(self, text: str) -> str:
        """تنظيف وتحضير النص للترجمة"""
        # إزالة الأرقام المنفردة
        text = re.sub(r'^\d+$', '', text)
        # إزالة الرموز الخاصة
        text = re.sub(r'[^\w\s\-.,?!]', ' ', text)
        # توحيد المسافات
        text = ' '.join(text.split())
        # إزالة المسافات في البداية والنهاية
        return text.strip()

    def split_text_into_chunks(self, text: str, max_length: int = 1000) -> List[str]:
        """تقسيم النص الطويل إلى أجزاء أصغر"""
        if len(text) <= max_length:
            return [text]
            
        chunks = []
        while text:
            # محاولة تقسيم النص عند نقطة مناسبة
            if len(text) <= max_length:
                chunks.append(text)
                break
                
            # البحث عن نقطة نهاية الجملة
            split_point = text.rfind('.', 0, max_length)
            if split_point == -1:
                # إذا لم يتم العثور على نقطة، البحث عن مسافة
                split_point = text.rfind(' ', 0, max_length)
            if split_point == -1:
                # إذا لم يتم العثور على مسافة، التقسيم عند الحد الأقصى
                split_point = max_length
                
            chunks.append(text[:split_point].strip())
            text = text[split_point:].strip()
            
        return chunks

    def is_chess_notation(self, text: str) -> bool:
        """التحقق مما إذا كان النص تدوين شطرنج"""
        chess_patterns = [
            r'^[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](\+|#)?$',
            r'^O-O(-O)?$',
            r'^[0-1](/[0-1])?-[0-1](/[0-1])?$',
            r'\d{1,4}\.',
            r'½-½',
        ]
        return any(bool(re.match(pattern, text.strip())) for pattern in chess_patterns)
    

    class TextProcessor:
        def __init__(self):
            self.translator = Translator()
            self.batch_size = 10

    def prepare_arabic_text(self, text: str) -> str:
        """تحضير النص العربي للعرض"""
        try:
            reshaped_text = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped_text)
            return self.improve_arabic_text(bidi_text)
        except Exception as e:
            logging.error(f"خطأ في تحضير النص العربي: {e}")
            return text

    def improve_arabic_text(self, text: str) -> str:
        """تحسين النص العربي"""
        # تحويل الأرقام والعلامات
        text = text.translate(str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩'))
        text = text.replace('?', '؟').replace(';', '؛').replace(',', '،')
        
        # تحسين المسافات
        text = re.sub(r'\s*([،؛؟!:])\s*', r'\1 ', text)
        text = ' '.join(text.split())
        return text.strip()

    def translate_text_with_retry(self, text: str, max_attempts: int = 3) -> str:
        """ترجمة النص مع إعادة المحاولة"""
        if not text or len(text.strip()) < 3:
            return ""

        for attempt in range(max_attempts):
            try:
                translated = self.translator.translate(text, src='en', dest='ar').text
                translated = self.prepare_arabic_text(translated)
                if translated and translated.lower() != text.lower():
                    return translated
                time.sleep(0.5)
            except Exception as e:
                if attempt == max_attempts - 1:
                    logging.error(f"فشلت الترجمة: {str(e)}")
                    return ""
                time.sleep(1)
        return ""

    def process_text_batch(self, texts: List[str]) -> List[str]:
        """معالجة مجموعة من النصوص دفعة واحدة"""
        translated_texts = []
        for text in texts:
            try:
                if not text or len(text.strip()) < 3:
                    translated_texts.append("")
                    continue
                    
                print(f"جاري ترجمة: {text}")
                translator = Translator()
                translated = translator.translate(text, src='en', dest='ar').text
                print(f"الترجمة: {translated}")
                
                translated_texts.append(translated)
                time.sleep(0.5)  # تأخير لتجنب التقييد
            except Exception as e:
                logging.error(f"خطأ في ترجمة النص: {str(e)}")
                translated_texts.append("")
                
        return translated_texts

    def clean_text(self, text: str) -> str:
        """تنظيف النص"""
        text = re.sub(r'^\d+$', '', text)
        text = re.sub(r'[^\w\s\-.,?!]', ' ', text)
        text = ' '.join(text.split())
        return text.strip()

    def is_chess_notation(self, text: str) -> bool:
        """التحقق من نقلات الشطرنج"""
        patterns = [
            r'^[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](\+|#)?$',
            r'^O-O(-O)?$',
            r'^[0-1](/[0-1])?-[0-1](/[0-1])?$',
            r'\d{1,4}\.',
            r'½-½',
        ]
        return any(bool(re.match(pattern, text.strip())) for pattern in patterns)
    
    def process_page(self, page_content, page_num: int):
        """معالجة صفحة كاملة مع تجنب التكرار"""
        logging.info(f"معالجة الصفحة {page_num + 1}")
        translated_blocks = []
        text_batch = []
        blocks_to_process = []
        
        # ترتيب المحتوى من أعلى إلى أسفل ومن اليمين إلى اليسار
        sorted_content = sorted(
            page_content,
            key=lambda x: (-x['bbox'][1], -x['bbox'][0])  # ترتيب عكسي للمحور X للنص العربي
        )

        for block in sorted_content:
            try:
                if not self.validate_block(block):
                    continue

                text = self.clean_text(block.get('text', ''))
                if len(text.strip()) < 3 or self.is_chess_notation(text):
                    continue

                text_batch.append(text)
                blocks_to_process.append(block)

                # معالجة الدفعة عندما تصل إلى الحجم المحدد
                if len(text_batch) >= self.batch_size:
                    self.process_and_add_translations(
                        text_batch, blocks_to_process, translated_blocks, page_num
                    )
                    text_batch = []
                    blocks_to_process = []

            except Exception as e:
                logging.error(f"خطأ في معالجة كتلة النص: {str(e)}")
                continue

        # معالجة الكتل المتبقية
        if text_batch:
            self.process_and_add_translations(
                text_batch, blocks_to_process, translated_blocks, page_num
            )

        return translated_blocks

    def process_and_add_translations(self, texts: List[str], blocks: List[Dict], 
                                   translated_blocks: List[Dict], page_num: int):
        """معالجة وإضافة الترجمات للكتل"""
        translations = self.process_text_batch(texts)
        for trans, block in zip(translations, blocks):
            if trans and trans.strip():
                translated_blocks.append({
                    'text': trans,
                    'bbox': block['bbox'],
                    'original_bbox': block['bbox'],
                    'type': 'text',
                    'page': page_num,
                    'original': block.get('text', '')
                })

    def create_translated_overlay(self, translated_blocks, page_num, page_size):
        """إنشاء طبقة الترجمة"""
        packet = BytesIO()
        width, height = float(page_size[0]), float(page_size[1])
        c = canvas.Canvas(packet, pagesize=(width, height))
        used_positions = []

        print(f"عدد الكتل المترجمة: {len(translated_blocks)}")
        
        for block in translated_blocks:
            try:
                if block['type'] != 'text':
                    continue

                text = self.text_processor.prepare_arabic_text(block['text'])
                if not text:
                    continue

                print(f"إضافة نص مترجم: {text}")
                
                bbox = block['original_bbox']
                font_size = 12  # زيادة حجم الخط
                text_width, text_height = self.calculate_text_dimensions(text, font_size)
                
                x, y = self.find_optimal_position(
                    bbox, text_width, text_height, used_positions, width, height
                )

                # إضافة خلفية بيضاء شفافة
                self.draw_text_background(c, x, y, text_width, text_height)
                
                # تعيين الخط العربي
                c.setFont("Arabic", font_size)
                c.setFillColorRGB(0, 0, 0)  # لون أسود للنص
                
                # كتابة النص من اليمين إلى اليسار
                c.drawRightString(x + text_width, y + text_height, text)
                
                # إضافة خط توضيحي
                self.draw_connection_line(c, x, y, bbox, text_width, text_height, height)
                used_positions.append((x, y, text_width, text_height))

            except Exception as e:
                logging.error(f"خطأ في إضافة النص المترجم: {str(e)}")
                continue

        c.save()
        packet.seek(0)
        return packet

    def find_optimal_position(self, bbox, text_width, text_height, used_positions, 
                            page_width, page_height):
        """إيجاد أفضل موقع للنص المترجم"""
        x = bbox[0]  # البدء من نفس الموقع الأفقي للنص الأصلي
        y = page_height - bbox[3] - text_height - 5  # وضع النص فوق النص الأصلي
        
        # تجنب الخروج عن حدود الصفحة
        x = max(5, min(x, page_width - text_width - 5))
        y = max(5, min(y, page_height - text_height - 5))
        
        # تجنب التداخل مع النصوص الأخرى
        while self.check_overlap((x, y, text_width, text_height), used_positions):
            y -= text_height + 5
            if y < 5:  # إذا وصلنا إلى أسفل الصفحة
                y = page_height - text_height - 5
                x += text_width + 10
                if x + text_width > page_width - 5:
                    x = 5
                    y = page_height - text_height - 5
                    break

        return x, y

    def draw_text_background(self, canvas_obj, x, y, width, height):
        """رسم خلفية شفافة للنص"""
        padding = 4
        canvas_obj.setFillColorRGB(1, 1, 1, 0.9)  # خلفية بيضاء شبه شفافة
        canvas_obj.rect(
            x - padding,
            y - padding,
            width + (2 * padding),
            height + (2 * padding),
            fill=True,
            stroke=False
        )

    def draw_connection_line(self, canvas_obj, x, y, original_bbox, text_width, 
                           text_height, page_height):
        """رسم خط يربط النص المترجم بالنص الأصلي"""
        canvas_obj.setStrokeColorRGB(0.7, 0.7, 0.7, 0.5)
        canvas_obj.setLineWidth(0.3)
        # نقطة بداية ونهاية الخط
        start_x = x + text_width / 2
        start_y = y + text_height / 2
        end_x = (original_bbox[0] + original_bbox[2]) / 2
        end_y = page_height - ((original_bbox[1] + original_bbox[3]) / 2)
        canvas_obj.line(start_x, start_y, end_x, end_y)
    
    def translate_pdf(self, input_path: str):
        """الدالة الرئيسية لترجمة ملف PDF"""
        input_path = Path(input_path)
        self.current_pdf_path = str(input_path)
        output_path = Path(self.config.OUTPUT_DIR) / f"translated_{input_path.stem}.pdf"
        
        try:
            if not self.validate_pdf(str(input_path)):
                raise ValueError("ملف PDF غير صالح")

            logging.info(f"بدء ترجمة: {input_path}")
            
            # فتح الملف وإنشاء القارئ والكاتب
            with pdfplumber.open(str(input_path)) as plumber_pdf:
                pdf_reader = PdfReader(str(input_path))
                pdf_writer = PdfWriter()
                total_pages = len(plumber_pdf.pages)
                
                # إنشاء شريط التقدم
                progress_bar = self.create_progress_bar(total_pages)
                
                # معالجة كل صفحة
                for page_num in range(total_pages):
                    try:
                        logging.info(f"معالجة الصفحة {page_num + 1}")
                        
                        # استخراج النص من الصفحة
                        page = plumber_pdf.pages[page_num]
                        text_content = self.extract_words_safely(page)
                        
                        if text_content:
                            # معالجة النص واستخراج الترجمات
                            translated_blocks = self.process_page(text_content, page_num)
                            
                            if translated_blocks:
                                # إنشاء طبقة الترجمة
                                width, height = float(page.width), float(page.height)
                                overlay_packet = self.create_translated_overlay(
                                    translated_blocks,
                                    page_num,
                                    (width, height)
                                )
                                
                                # دمج الترجمة مع الصفحة الأصلية
                                overlay_pdf = PdfReader(overlay_packet)
                                page_obj = pdf_reader.pages[page_num]
                                page_obj.merge_page(overlay_pdf.pages[0])
                                pdf_writer.add_page(page_obj)
                            else:
                                pdf_writer.add_page(pdf_reader.pages[page_num])
                        else:
                            pdf_writer.add_page(pdf_reader.pages[page_num])
                            
                        # تحديث شريط التقدم
                        if progress_bar:
                            progress_bar.update(1)
                            
                        # تحسين استخدام الذاكرة
                        if page_num % 5 == 0:
                            self.optimize_memory_usage()
                            
                    except Exception as e:
                        logging.error(f"خطأ في معالجة الصفحة {page_num + 1}: {str(e)}")
                        pdf_writer.add_page(pdf_reader.pages[page_num])
                        continue

                # حفظ الملف المترجم
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(str(output_path), 'wb') as output_file:
                    pdf_writer.write(output_file)
                
                # حفظ البيانات الوصفية
                self.save_translation_metadata(input_path, output_path)
                
                logging.info("اكتملت الترجمة بنجاح")
                
        except Exception as e:
            logging.error(f"خطأ في عملية الترجمة: {str(e)}")
            raise
        finally:
            self.cleanup()

    def extract_words_safely(self, page) -> list:
        """استخراج الكلمات من الصفحة بشكل آمن"""
        try:
            words = page.extract_words(
                keep_blank_chars=True,
                x_tolerance=3,
                y_tolerance=3,
                extra_attrs=['fontname', 'size']
            )
            
            processed_words = []
            for word in words:
                if word.get('text', '').strip():
                    # إنشاء bbox من x0, top, x1, bottom
                    x0 = float(word.get('x0', 0))
                    top = float(word.get('top', 0)) 
                    x1 = float(word.get('x1', x0 + 50))  # قيمة افتراضية إذا لم تكن موجودة
                    bottom = float(word.get('bottom', top + 20))  # قيمة افتراضية إذا لم تكن موجودة
                    
                    word['bbox'] = (x0, top, x1, bottom)
                    processed_words.append(word)
            
            return processed_words
        except Exception as e:
            logging.error(f"خطأ في استخراج الكلمات: {str(e)}")
            return []

    
    def process_page(self, page_content, page_num: int):
        """معالجة صفحة كاملة"""
        logging.info(f"معالجة الصفحة {page_num + 1}")
        translated_blocks = []
        text_batch = []
        blocks_to_process = []
        
        if not page_content:
            logging.warning(f"لا يوجد محتوى في الصفحة {page_num + 1}")
            return []
            
        try:
            # ترتيب المحتوى من أعلى إلى أسفل ومن اليمين إلى اليسار
            sorted_content = sorted(
                page_content,
                key=lambda x: (-x.get('bbox', [0,0,0,0])[1], -x.get('bbox', [0,0,0,0])[0])
            )

            for block in sorted_content:
                try:
                    # تحويل الإحداثيات إلى bbox إذا لم تكن موجودة
                    if 'bbox' not in block and all(key in block for key in ['x0', 'top', 'x1', 'bottom']):
                        block['bbox'] = (block['x0'], block['top'], block['x1'], block['bottom'])

                    if not self.validate_block(block):
                        continue

                    text = self.text_processor.clean_text(block.get('text', ''))
                    if len(text.strip()) < 3 or self.text_processor.is_chess_notation(text):
                        continue

                    text_batch.append(text)
                    blocks_to_process.append(block)

                    if len(text_batch) >= self.batch_size:
                        self.process_and_add_translations(
                            text_batch, blocks_to_process, translated_blocks, page_num
                        )
                        text_batch = []
                        blocks_to_process = []

                except Exception as e:
                    logging.error(f"خطأ في معالجة كتلة النص: {str(e)}")
                    continue

            # معالجة الكتل المتبقية
            if text_batch:
                self.process_and_add_translations(
                    text_batch, blocks_to_process, translated_blocks, page_num
                )

            return translated_blocks
            
        except Exception as e:
            logging.error(f"خطأ في معالجة الصفحة {page_num + 1}: {str(e)}")
            return []
    
    
    def save_translation_metadata(self, input_path: Path, output_path: Path):
        """حفظ البيانات الوصفية عن الترجمة"""
        try:
            metadata = {
                'source_file': str(input_path),
                'output_file': str(output_path),
                'translation_date': datetime.now().isoformat(),
                'user': os.getenv('USER', 'x9ci'),  # استخدام اسم المستخدم الحالي
                'version': '2.0.0'
            }
            
            metadata_path = output_path.with_suffix('.meta.json')
            import json
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.warning(f"خطأ في حفظ البيانات الوصفية: {str(e)}")

    def create_progress_bar(self, total_pages: int):
        """إنشاء شريط تقدم العملية"""
        try:
            from tqdm import tqdm
            return tqdm(
                total=total_pages,
                desc="تقدم الترجمة",
                unit="صفحة",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} صفحات"
            )
        except ImportError:
            return None

    def optimize_memory_usage(self):
        """تحسين استخدام الذاكرة"""
        import gc
        gc.collect()

    import logging
from typing import List, Dict
from io import BytesIO
from reportlab.pdfgen import canvas
from PIL import ImageFont
import time

class PageProcessor:
    def __init__(self, text_processor):
        self.text_processor = text_processor
        self.batch_size = 10
        self.processed_blocks = set()

    def process_page(self, page_content, page_num: int):
        """معالجة صفحة كاملة"""
        logging.info(f"معالجة الصفحة {page_num + 1}")
        translated_blocks = []
        text_batch = []
        blocks_to_process = []
        
        if not page_content:
            logging.warning(f"لا يوجد محتوى في الصفحة {page_num + 1}")
            return []
            
        try:
            # ترتيب المحتوى من أعلى إلى أسفل ومن اليمين إلى اليسار
            sorted_content = sorted(
                page_content,
                key=lambda x: (-float(x.get('bbox', (0,0,0,0))[1]), -float(x.get('bbox', (0,0,0,0))[0]))
            )

            for block in sorted_content:
                try:
                    text = self.text_processor.clean_text(block.get('text', ''))
                    if len(text.strip()) < 3 or self.text_processor.is_chess_notation(text):
                        continue

                    if 'bbox' not in block:
                        continue

                    text_batch.append(text)
                    blocks_to_process.append(block)

                    if len(text_batch) >= self.batch_size:
                        self.process_and_add_translations(
                            text_batch, blocks_to_process, translated_blocks, page_num
                        )
                        text_batch = []
                        blocks_to_process = []

                except Exception as e:
                    logging.error(f"خطأ في معالجة كتلة النص: {str(e)}")
                    continue

            # معالجة الكتل المتبقية
            if text_batch:
                self.process_and_add_translations(
                    text_batch, blocks_to_process, translated_blocks, page_num
                )

            return translated_blocks
                
        except Exception as e:
            logging.error(f"خطأ في معالجة الصفحة {page_num + 1}: {str(e)}")
            return []
   
    def process_and_add_translations(self, texts: List[str], blocks: List[Dict], translated_blocks: List[Dict], page_num: int):
        """معالجة وإضافة الترجمات"""
        try:
            print(f"معالجة {len(texts)} نص للترجمة")
            translations = self.text_processor.process_text_batch(texts)
            
            for trans, block in zip(translations, blocks):
                try:
                    if trans and trans.strip():
                        # إضافة معلومات الترجمة
                        translated_block = {
                            'text': trans,
                            'bbox': block['bbox'],
                            'original_bbox': block['bbox'],
                            'type': 'text',
                            'page': page_num,
                            'original': block.get('text', '')
                        }
                        
                        translated_blocks.append(translated_block)
                        print(f"تمت إضافة الترجمة: {trans}")
                        
                except Exception as e:
                    print(f"خطأ في إضافة الترجمة للكتلة: {str(e)}")
                    logging.error(f"خطأ في إضافة الترجمة للكتلة: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"خطأ في معالجة دفعة الترجمة: {str(e)}")
            logging.error(f"خطأ في معالجة دفعة الترجمة: {str(e)}")
    
    
    def calculate_font_size(self, text: str, bbox: tuple) -> float:
        """حساب حجم الخط المناسب بناءً على مساحة النص"""
        try:
            bbox_width = bbox[2] - bbox[0]
            bbox_height = bbox[3] - bbox[1]
            text_length = len(text)
            
            # حساب حجم الخط بناءً على عرض المساحة المتاحة
            suggested_size = bbox_width / (text_length * 0.6)
            
            # التأكد من أن حجم الخط مناسب للارتفاع
            if suggested_size * 1.2 > bbox_height:
                suggested_size = bbox_height / 1.2
                
            # تحديد الحد الأدنى والأقصى لحجم الخط
            min_size = 8
            max_size = 16
            
            return max(min_size, min(suggested_size, max_size))
        except Exception as e:
            print(f"خطأ في حساب حجم الخط: {str(e)}")
            return 10  # حجم افتراضي
   
    def draw_text_background(self, canvas_obj, x, y, width, height):
        """رسم خلفية شفافة للنص"""
        try:
            padding = 4
            # تعيين لون الخلفية إلى أبيض شبه شفاف
            canvas_obj.setFillColorRGB(1, 1, 1, 0.8)
            canvas_obj.setStrokeColorRGB(0.9, 0.9, 0.9, 0.3)
            canvas_obj.rect(
                x - padding,
                y - padding,
                width + (2 * padding),
                height + (2 * padding),
                fill=True,
                stroke=True
            )
        except Exception as e:
            print(f"خطأ في رسم خلفية النص: {str(e)}")
            logging.error(f"خطأ في رسم خلفية النص: {str(e)}")

def draw_connection_line(self, canvas_obj, x, y, bbox, text_width, text_height, page_height):
    """رسم خط يربط النص المترجم بالنص الأصلي"""
    try:
        # تعيين لون وسمك الخط
        canvas_obj.setStrokeColorRGB(0.7, 0.7, 0.7, 0.5)
        canvas_obj.setLineWidth(0.3)
        
        # حساب نقاط البداية والنهاية
        start_x = x + text_width / 2
        start_y = y + text_height / 2
        end_x = (bbox[0] + bbox[2]) / 2
        end_y = page_height - ((bbox[1] + bbox[3]) / 2)
        
        # رسم الخط
        canvas_obj.line(start_x, start_y, end_x, end_y)
    except Exception as e:
        print(f"خطأ في رسم خط الربط: {str(e)}")
        logging.error(f"خطأ في رسم خط الربط: {str(e)}")
    
    
    def validate_block(self, block: dict) -> bool:
        """التحقق من صحة كتلة النص وخصائصه"""
        try:
            # التحقق من نوع الكتلة
            if not isinstance(block, dict):
                return False
            
            # التحقق من وجود النص
            if 'text' not in block or not block.get('text', '').strip():
                return False
                
            # معالجة bbox
            if 'bbox' not in block:
                # محاولة إنشاء bbox من الإحداثيات المنفصلة
                bbox_keys = ['x0', 'top', 'x1', 'bottom']
                if all(key in block for key in bbox_keys):
                    block['bbox'] = tuple(float(block[key]) for key in bbox_keys)
                else:
                    return False
            
            # التحقق من صحة bbox
            bbox = block['bbox']
            if not isinstance(bbox, (tuple, list)) or len(bbox) != 4:
                return False

            # التحقق من صحة قيم bbox
            if any(not isinstance(v, (int, float)) for v in bbox):
                return False

            # التحقق من ترتيب الإحداثيات
            x0, y0, x1, y1 = bbox
            if x0 > x1 or y0 > y1:
                return False

            return True
            
        except Exception as e:
            logging.debug(f"خطأ في التحقق من كتلة النص: {str(e)}")
            return False
    
    
    def validate_block(self, block: dict) -> bool:
        """التحقق من صحة كتلة النص"""
        try:
            if not isinstance(block, dict):
                return False
            
            if 'text' not in block or 'bbox' not in block:
                return False
                
            text = block.get('text', '').strip()
            if not text:
                return False
                
            bbox = block['bbox']
            if not isinstance(bbox, (tuple, list)) or len(bbox) != 4:
                return False

            return True
        except Exception as e:
            logging.debug(f"خطأ في التحقق من الكتلة: {str(e)}")
            return False

    def process_and_add_translations(self, texts: List[str], blocks: List[Dict], 
                                   translated_blocks: List[Dict], page_num: int):
        """معالجة وإضافة الترجمات"""
        translations = self.text_processor.process_text_batch(texts)
        for trans, block in zip(translations, blocks):
            if trans and trans.strip():
                translated_blocks.append({
                    'text': trans,
                    'bbox': block['bbox'],
                    'original_bbox': block['bbox'],
                    'type': 'text',
                    'page': page_num,
                    'original': block.get('text', '')
                })

    def create_translated_overlay(self, translated_blocks, page_num, page_size):
        """إنشاء طبقة الترجمة"""
        try:
            packet = BytesIO()
            width, height = float(page_size[0]), float(page_size[1])
            c = canvas.Canvas(packet, pagesize=(width, height))
            used_positions = []
            
            # إنشاء كائن ArabicWriter
            arabic_writer = ArabicWriter()

            print(f"إنشاء طبقة الترجمة للصفحة {page_num + 1}")
            print(f"عدد الكتل المترجمة: {len(translated_blocks)}")

            for block in translated_blocks:
                try:
                    if block['type'] != 'text':
                        continue

                    text = block['text']
                    if not text:
                        continue

                    # حساب أبعاد النص
                    text_width, text_height = arabic_writer.get_text_dimensions(text)
                    
                    # تحديد الموقع
                    bbox = block['original_bbox']
                    x, y = self.find_optimal_position(
                        bbox, text_width, text_height, used_positions, width, height
                    )

                    # رسم خلفية بيضاء شفافة
                    self.draw_text_background(c, x, y, text_width, text_height)

                    # كتابة النص العربي
                    actual_width, actual_height = arabic_writer.write_arabic_text(
                        c, text, x, y + text_height, align='right'
                    )

                    # رسم خط توضيحي
                    self.draw_connection_line(c, x, y, bbox, actual_width, actual_height, height)
                    
                    # تحديث المواقع المستخدمة
                    used_positions.append((x, y, actual_width, actual_height))
                    print(f"تمت إضافة النص: {text}")

                except Exception as e:
                    print(f"خطأ في معالجة كتلة نص: {str(e)}")
                    continue

            c.save()
            packet.seek(0)
            return packet

        except Exception as e:
            print(f"خطأ في إنشاء طبقة الترجمة: {str(e)}")
            return self.create_empty_page(width, height)
    
    def calculate_text_dimensions(self, text: str, font_size: float) -> tuple:
        """حساب أبعاد النص"""
        return len(text) * font_size * 0.6, font_size * 1.2

    def find_optimal_position(self, bbox, text_width, text_height, used_positions, 
                            page_width, page_height):
        """إيجاد أفضل موقع للنص المترجم"""
        x = bbox[0]
        y = page_height - bbox[3] - text_height - 5
        
        x = max(5, min(x, page_width - text_width - 5))
        y = max(5, min(y, page_height - text_height - 5))
        
        while self.check_overlap((x, y, text_width, text_height), used_positions):
            y -= text_height + 5
            if y < 5:
                y = page_height - text_height - 5
                x += text_width + 10
                if x + text_width > page_width - 5:
                    x = 5
                    y = page_height - text_height - 5
                    break

        return x, y

    def check_overlap(self, current_rect, used_positions):
        """التحقق من تداخل النصوص"""
        x, y, w, h = current_rect
        for used_x, used_y, used_w, used_h in used_positions:
            if (x < used_x + used_w and x + w > used_x and
                y < used_y + used_h and y + h > used_y):
                return True
        return False


class PDFHandler:
    def __init__(self, config, page_processor):
        self.config = config
        self.page_processor = page_processor
        self.temp_dir = tempfile.mkdtemp()
        self.current_pdf_path = None

    def translate_pdf(self, input_path: str):
        """ترجمة ملف PDF"""
        input_path = Path(input_path)
        self.current_pdf_path = str(input_path)
        output_path = Path(self.config.OUTPUT_DIR) / f"translated_{input_path.stem}.pdf"
        
        try:
            if not self.validate_pdf(str(input_path)):
                raise ValueError("ملف PDF غير صالح")

            logging.info(f"بدء ترجمة: {input_path}")
            
            with pdfplumber.open(str(input_path)) as plumber_pdf:
                pdf_reader = PdfReader(str(input_path))
                pdf_writer = PdfWriter()
                total_pages = len(plumber_pdf.pages)
                
                progress_bar = self.create_progress_bar(total_pages)
                
                for page_num in range(total_pages):
                    try:
                        page = plumber_pdf.pages[page_num]
                        text_content = self.extract_words_safely(page)
                        
                        if text_content:
                            translated_blocks = self.page_processor.process_page(text_content, page_num)
                            
                            if translated_blocks:
                                width, height = float(page.width), float(page.height)
                                overlay_packet = self.page_processor.create_translated_overlay(
                                    translated_blocks,
                                    page_num,
                                    (width, height)
                                )
                                
                                overlay_pdf = PdfReader(overlay_packet)
                                page_obj = pdf_reader.pages[page_num]
                                page_obj.merge_page(overlay_pdf.pages[0])
                                pdf_writer.add_page(page_obj)
                            else:
                                pdf_writer.add_page(pdf_reader.pages[page_num])
                        else:
                            pdf_writer.add_page(pdf_reader.pages[page_num])
                            
                        if progress_bar:
                            progress_bar.update(1)
                            
                        if page_num % 5 == 0:
                            self.optimize_memory_usage()
                            
                    except Exception as e:
                        logging.error(f"خطأ في معالجة الصفحة {page_num + 1}: {str(e)}")
                        pdf_writer.add_page(pdf_reader.pages[page_num])
                        continue

                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(str(output_path), 'wb') as output_file:
                    pdf_writer.write(output_file)
                
                self.save_translation_metadata(input_path, output_path)
                logging.info("اكتملت الترجمة بنجاح")
                
        except Exception as e:
            logging.error(f"خطأ في عملية الترجمة: {str(e)}")
            raise
        finally:
            self.cleanup()

    def validate_pdf(self, file_path: str) -> bool:
        """التحقق من صلاحية ملف PDF"""
        try:
            with open(file_path, 'rb') as file:
                PdfReader(file)
            return True
        except Exception as e:
            logging.error(f"ملف PDF غير صالح: {str(e)}")
            return False

    def extract_words_safely(self, page) -> list:
        """استخراج الكلمات من الصفحة بشكل آمن"""
        try:
            print("جاري استخراج النصوص من الصفحة...")
            
            # استخدام extract_text بدلاً من extract_words للحصول على النص كاملاً
            text = page.extract_text()
            if not text:
                print("لم يتم العثور على نص في الصفحة")
                return []
                
            print(f"النص المستخرج: {text}")
            
            # تقسيم النص إلى كلمات
            words = []
            lines = text.split('\n')
            y_position = float(page.height)
            line_height = float(page.height) / len(lines)
            
            for line in lines:
                if line.strip():
                    word_dict = {
                        'text': line.strip(),
                        'bbox': (10, y_position - line_height, float(page.width) - 10, y_position),
                        'x0': 10,
                        'top': y_position - line_height,
                        'x1': float(page.width) - 10,
                        'bottom': y_position
                    }
                    words.append(word_dict)
                    y_position -= line_height
                    print(f"تمت إضافة كلمة: {line.strip()}")
            
            print(f"تم استخراج {len(words)} كلمة")
            return words
            
        except Exception as e:
            logging.error(f"خطأ في استخراج الكلمات: {str(e)}")
            print(f"خطأ في استخراج الكلمات: {str(e)}")
            return []
    
    def create_progress_bar(self, total_pages: int):
        """إنشاء شريط تقدم العملية"""
        try:
            return tqdm(
                total=total_pages,
                desc="تقدم الترجمة",
                unit="صفحة",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} صفحات"
            )
        except Exception:
            return None

    def save_translation_metadata(self, input_path: Path, output_path: Path):
        """حفظ البيانات الوصفية للترجمة"""
        try:
            metadata = {
                'source_file': str(input_path),
                'output_file': str(output_path),
                'translation_date': datetime.now().isoformat(),
                'user': 'x9ci',
                'version': '2.0.0'
            }
            
            metadata_path = output_path.with_suffix('.meta.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.warning(f"خطأ في حفظ البيانات الوصفية: {str(e)}")

    def cleanup(self):
        """تنظيف الملفات المؤقتة"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            logging.warning(f"خطأ في حذف الملفات المؤقتة: {str(e)}")

    def optimize_memory_usage(self):
        """تحسين استخدام الذاكرة"""
        import gc
        gc.collect()

def initialize_system():
    """تهيئة النظام والتحقق من المتطلبات"""
    try:
        # التحقق من وجود المكتبات المطلوبة
        required_packages = [
            'pdfplumber',
            'PyPDF2',
            'reportlab',
            'googletrans',
            'arabic-reshaper',
            'python-bidi',
            'tqdm'
        ]
        
        import importlib.metadata
        installed_packages = [pkg.metadata['Name'].lower() for pkg in importlib.metadata.distributions()]
        
        missing_packages = [pkg for pkg in required_packages 
                          if pkg.lower() not in installed_packages]
        
        if missing_packages:
            raise ImportError(
                f"المكتبات التالية مفقودة: {', '.join(missing_packages)}\n"
                f"قم بتثبيتها باستخدام: pip install {' '.join(missing_packages)}"
            )
            
        # زيادة حد التكرار
        sys.setrecursionlimit(10000)
        
        return True
        
    except Exception as e:
        print(f"خطأ في تهيئة النظام: {str(e)}")
        return False

def validate_input_file(file_path: Path) -> bool:
    """التحقق من وجود وصلاحية ملف الإدخال"""
    if not file_path.exists():
        print(f"الملف غير موجود: {file_path}")
        return False
        
    if not file_path.is_file():
        print(f"المسار ليس ملفاً: {file_path}")
        return False
        
    if file_path.suffix.lower() != '.pdf':
        print(f"الملف ليس بصيغة PDF: {file_path}")
        return False
        
    return True


import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from pathlib import Path

class ArabicTextHandler:
    def __init__(self):
        self.font_size = 12
        self.initialize_fonts()

    def initialize_fonts(self):
        """تهيئة الخطوط العربية"""
        try:
            # قائمة المسارات المحتملة للخطوط
            current_dir = Path(__file__).parent
            font_paths = [
                "/usr/share/fonts/truetype/arabic/Amiri-Regular.ttf",
                str(current_dir / "fonts" / "Amiri-Regular.ttf"),
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                str(current_dir / "fonts" / "FreeSans.ttf")
            ]

            # إنشاء مجلد الخطوط إذا لم يكن موجوداً
            fonts_dir = current_dir / "fonts"
            fonts_dir.mkdir(exist_ok=True)

            # محاولة تحميل الخط العربي
            font_loaded = False
            for font_path in font_paths:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('Arabic', font_path))
                    print(f"تم تحميل الخط: {font_path}")
                    font_loaded = True
                    break

            if not font_loaded:
                # إذا لم يتم العثور على الخط، قم بتحميله
                self.download_arabic_font()

        except Exception as e:
            print(f"خطأ في تهيئة الخطوط: {e}")
            raise

    def download_arabic_font(self):
        """تحميل الخط العربي"""
        try:
            import requests
            font_url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
            font_path = Path(__file__).parent / "fonts" / "Amiri-Regular.ttf"
            
            response = requests.get(font_url)
            response.raise_for_status()
            
            with open(font_path, 'wb') as f:
                f.write(response.content)
            
            pdfmetrics.registerFont(TTFont('Arabic', str(font_path)))
            print("تم تحميل الخط العربي بنجاح")
            
        except Exception as e:
            print(f"خطأ في تحميل الخط العربي: {e}")
            raise

    def process_arabic_text(self, text):
        """معالجة النص العربي"""
        try:
            # إعادة تشكيل النص العربي
            reshaped_text = arabic_reshaper.reshape(text)
            # تطبيق خوارزمية BIDI
            bidi_text = get_display(reshaped_text)
            return bidi_text
        except Exception as e:
            print(f"خطأ في معالجة النص العربي: {e}")
            return text

    def get_text_dimensions(self, text):
        """حساب أبعاد النص"""
        try:
            processed_text = self.process_arabic_text(text)
            width = len(processed_text) * self.font_size * 0.6
            height = self.font_size * 1.2
            return width, height
        except Exception as e:
            print(f"خطأ في حساب أبعاد النص: {e}")
            return 0, 0

def main():
    try:
        print("بدء تشغيل برنامج ترجمة PDF...")
        
        # تأكد من تثبيت googletrans بالإصدار الصحيح
        try:
            from googletrans import Translator
            translator = Translator()
            test_translation = translator.translate("Hello", dest='ar')
            print(f"اختبار الترجمة: {test_translation.text}")
        except Exception as e:
            print("خطأ في Googletrans. جاري إعادة التثبيت...")
            os.system('pip install googletrans==3.1.0a0')
            print("تم إعادة تثبيت Googletrans")
        
        
        # إنشاء مجلد للخطوط إذا لم يكن موجوداً
        fonts_dir = Path("fonts")
        fonts_dir.mkdir(exist_ok=True)
        
        config = PDFTranslatorConfig()
        text_processor = TextProcessor()
        page_processor = PageProcessor(text_processor)
        pdf_handler = PDFHandler(config, page_processor)
        
        input_file = Path("/home/dc/Public/pdftopdf/pdftran/input/test1.pdf")
        
        if not validate_input_file(input_file):
            return
        
        print(f"جاري ترجمة: {input_file.name}")
        print("هذه العملية قد تستغرق بعض الوقت، يرجى الانتظار...")
        
        # تأكد من وجود خط عربي
        if not any(Path(p).exists() for p in [
            "/usr/share/fonts/truetype/arabic/Amiri-Regular.ttf",
            "./fonts/Amiri-Regular.ttf"
        ]):
            print("تحميل الخط العربي...")
            # هنا يمكنك إضافة كود لتحميل الخط العربي تلقائياً
            
        pdf_handler.translate_pdf(str(input_file))
        
        print("\nتمت الترجمة بنجاح!")
        print(f"يمكنك العثور على الملف المترجم في مجلد: {config.OUTPUT_DIR}")

    except Exception as e:
        print(f"\nحدث خطأ: {str(e)}")
        logging.error(f"خطأ في البرنامج الرئيسي: {str(e)}")
    finally:
        print("\nانتهى البرنامج")

if __name__ == "__main__":
    main()